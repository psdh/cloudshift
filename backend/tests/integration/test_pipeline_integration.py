"""
Real-infrastructure integration test for the transfer pipeline.

This exercises the ACTUAL code paths against real services:
  * real PostgreSQL  (job/item state, ItemStatus, exactly-once bookkeeping)
  * real Redis        (progress_tracker)
  * real S3           (MinIO) — the multipart `upload_stream` and the
                        chunked `download_stream` that back the 100 GB
                        streaming requirement

Only the two external SaaS boundaries are mocked, because they need
Microsoft/Google sandbox credentials this environment does not have:
  * OneDriveService.download_file  -> yields a known >part-size payload
  * GoogleDriveService.list_folder -> [] (no conflict)
  * GoogleDriveService.upload_file -> *drains the real S3 download_stream*
                                       (so the S3 read path is exercised
                                       for real) and returns the file meta

Skipped unless CLOUDSHIFT_INTEGRATION=1, so the normal unit suite / CI
without infra is unaffected.

Runbook
-------
    docker run -d --name pg    -e POSTGRES_USER=cloudshift \
        -e POSTGRES_PASSWORD=cloudshift_dev_password \
        -e POSTGRES_DB=cloudshift -p 5433:5432 postgres:15-alpine
    docker run -d --name redis -p 6380:6379 redis:7-alpine
    docker run -d --name minio -p 9000:9000 \
        -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
        minio/minio server /data

    DATABASE_URL=postgresql+asyncpg://cloudshift:cloudshift_dev_password@localhost:5433/cloudshift \
      alembic upgrade head

    CLOUDSHIFT_INTEGRATION=1 \
    DATABASE_URL=postgresql+asyncpg://cloudshift:cloudshift_dev_password@localhost:5433/cloudshift \
    REDIS_URL=redis://localhost:6380/0 \
    AWS_S3_ENDPOINT_URL=http://localhost:9000 \
    AWS_ACCESS_KEY_ID=minioadmin AWS_SECRET_ACCESS_KEY=minioadmin \
    AWS_REGION=us-east-1 S3_BUCKET_NAME=cloudshift-it \
      pytest tests/integration -q

To extend to a *fully* real run, drop the OneDrive/Drive mocks and supply
real provider sandbox OAuth accounts.
"""

import asyncio
import hashlib
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("CLOUDSHIFT_INTEGRATION") != "1",
    reason="integration test; needs real Postgres+Redis+S3 (set CLOUDSHIFT_INTEGRATION=1)",
)

PAYLOAD_SIZE = 12 * 1024 * 1024  # 12 MiB -> forces a multi-part S3 upload (8 + 4)


@pytest.fixture(scope="module")
def payload():
    return os.urandom(PAYLOAD_SIZE)


@pytest.fixture(scope="module")
def _bucket():
    from app.services.s3 import S3Service

    client = S3Service().s3_client
    try:
        client.create_bucket(Bucket=os.environ["S3_BUCKET_NAME"])
    except Exception:
        pass  # already exists
    return os.environ["S3_BUCKET_NAME"]


async def _seed(payload_len: int):
    """Create a user, connected accounts, and a one-item job in real PG."""
    from app.core.database import worker_session
    from app.models.connected_account import ConnectedAccount
    from app.models.transfer import TransferItem, TransferJob, JobStatus, ItemStatus
    from app.models.user import User
    from app.services.encryption import EncryptionService
    from datetime import datetime, timedelta
    import uuid

    async with worker_session() as db:
        user = User(email=f"it-{uuid.uuid4().hex[:8]}@example.com", password_hash="x")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        for provider in ("onedrive", "google_drive"):
            db.add(
                ConnectedAccount(
                    user_id=user.id,
                    provider=provider,
                    access_token=EncryptionService.encrypt("fake-access"),
                    refresh_token=EncryptionService.encrypt("fake-refresh"),
                    token_expiry=datetime.utcnow() + timedelta(hours=1),
                    account_email="it@example.com",
                )
            )
        job = TransferJob(
            user_id=user.id,
            status=JobStatus.RUNNING,
            source_provider="onedrive",
            dest_provider="google_drive",
            config={},
        )
        item = TransferItem(
            source_file_id="src-1",
            source_path="big.bin",
            dest_path="big.bin",
            status=ItemStatus.PENDING,
            size=payload_len,
        )
        job.items.append(item)
        db.add(job)
        await db.commit()
        await db.refresh(job)
        await db.refresh(item)
        return job.id, item.id


def test_pipeline_streams_through_real_s3(monkeypatch, payload, _bucket):
    """OneDrive(mock) -> real S3 multipart -> Drive(mock draining real S3)."""
    from app.core.celery_app import celery_app
    from app.models.transfer import ItemStatus
    from app.services import transfer_worker
    from app.services.google_drive import GoogleDriveService, GoogleDriveFile
    from app.services.onedrive import OneDriveService
    from app.services.s3 import S3Service

    job_id, item_id = asyncio.run(_seed(len(payload)))

    # --- mock ONLY the external SaaS boundaries ---
    async def fake_download(account, file_id):
        for i in range(0, len(payload), 1024 * 1024):
            yield payload[i : i + 1024 * 1024]

    monkeypatch.setattr(OneDriveService, "download_file", staticmethod(fake_download))

    async def fake_list_folder(account, folder_id, *a, **k):
        return []  # no conflict

    monkeypatch.setattr(
        GoogleDriveService, "list_folder", staticmethod(fake_list_folder)
    )

    seen = {}

    async def fake_upload(account, name, stream, folder_id="root", **kwargs):
        # Drain the *real* S3 download_stream so MinIO's read path runs.
        h = hashlib.md5()
        total = 0
        async for chunk in stream:
            h.update(chunk)
            total += len(chunk)
        seen["md5"] = h.hexdigest()
        seen["size"] = total
        return GoogleDriveFile(
            {"id": "drive-123", "name": name, "size": str(total)}
        )

    monkeypatch.setattr(
        GoogleDriveService, "upload_file", staticmethod(fake_upload)
    )

    # Run the real Celery task body synchronously.
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    result = transfer_worker.transfer_single_file.apply(args=(item_id,)).get()

    expected_md5 = hashlib.md5(payload).hexdigest()

    # The data round-tripped through real S3 byte-for-byte.
    assert seen["size"] == len(payload)
    assert seen["md5"] == expected_md5
    assert result["status"] == "success"
    assert result["checksum"] == expected_md5
    assert result["dest_file_id"] == "drive-123"

    # Exactly-once: the intermediate S3 object was deleted after confirm.
    s3 = S3Service()
    key = f"transfers/{job_id}/{item_id}/big.bin"
    assert asyncio.run(s3.file_exists(key)) is False

    # DB reflects completion.
    async def _check():
        from app.core.database import worker_session
        from app.models.transfer import TransferItem, ItemStatus
        from sqlalchemy import select

        async with worker_session() as db:
            item = (
                await db.execute(
                    select(TransferItem).where(TransferItem.id == item_id)
                )
            ).scalar_one()
            return item.status, item.error_message

    status, err = asyncio.run(_check())
    assert status == ItemStatus.COMPLETED
    assert err is None
