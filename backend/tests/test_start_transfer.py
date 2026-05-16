"""Tests for the POST /api/transfers/{id}/start endpoint (H4)."""

from unittest.mock import patch

from app.core.security import create_access_token
from app.models.connected_account import ConnectedAccount
from app.models.transfer import TransferItem, TransferJob, JobStatus, ItemStatus
from app.models.user import User


def _auth(db_session):
    user = User(email="starter@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return user, {"Authorization": f"Bearer {token}"}


def test_start_transfer_dispatches_orchestrator(client, db_session):
    user, headers = _auth(db_session)
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        source_provider="onedrive",
        dest_provider="google_drive",
        config={},
    )
    job.items.append(
        TransferItem(
            source_file_id="f1",
            source_path="a.txt",
            dest_path="a.txt",
            status=ItemStatus.PENDING,
            size=10,
        )
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    with patch(
        "app.services.transfer_worker.transfer_job_orchestrator.delay"
    ) as delay:
        response = client.post(f"/api/transfers/{job_id}/start", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    delay.assert_called_once_with(job_id)


def test_start_transfer_rejects_job_without_items(client, db_session):
    user, headers = _auth(db_session)
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        source_provider="onedrive",
        dest_provider="google_drive",
        config={},
    )
    db_session.add(job)
    db_session.commit()

    with patch("app.services.transfer_worker.transfer_job_orchestrator.delay"):
        response = client.post(f"/api/transfers/{job.id}/start", headers=headers)

    assert response.status_code == 400
    assert "no items" in response.json()["detail"].lower()


def test_start_transfer_404_for_other_users_job(client, db_session):
    owner, _ = _auth(db_session)
    other = User(email="intruder@example.com", password_hash="x")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)
    intruder_headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(other.id)})}"
    }

    job = TransferJob(
        user_id=owner.id,
        status=JobStatus.PENDING,
        source_provider="onedrive",
        dest_provider="google_drive",
        config={},
    )
    db_session.add(job)
    db_session.commit()

    with patch("app.services.transfer_worker.transfer_job_orchestrator.delay"):
        response = client.post(
            f"/api/transfers/{job.id}/start", headers=intruder_headers
        )

    assert response.status_code == 404
