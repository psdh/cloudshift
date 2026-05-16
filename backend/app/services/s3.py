"""
S3 intermediate storage service.

All public methods are async (boto3 is synchronous, so blocking calls run in
a thread via asyncio.to_thread). Object keys are always the first argument.
Streaming helpers (multipart upload / chunked download) keep memory bounded
so large files do not have to be buffered whole — see transfer_worker.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

# 8 MiB parts: above S3's 5 MiB multipart minimum, small enough to stream.
_MULTIPART_PART_SIZE = 8 * 1024 * 1024
_DOWNLOAD_CHUNK_SIZE = 8 * 1024 * 1024


class S3Service:
    """Async wrapper around the S3 intermediate bucket."""

    def __init__(self):
        self._client = None
        self.bucket_name = settings.S3_BUCKET_NAME

    @property
    def s3_client(self):
        # Lazy: importing this module must not require AWS credentials.
        if self._client is None:
            self._client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
        return self._client

    async def upload_bytes(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> bool:
        """Upload an in-memory object (encrypted at rest)."""
        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
            logger.info(f"Uploaded {len(data)} bytes to s3://{self.bucket_name}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False

    async def upload_stream(
        self, key: str, chunk_iter: AsyncIterator[bytes]
    ) -> bool:
        """Stream an object to S3 with a multipart upload.

        Only one ~8 MiB part is held in memory at a time, so arbitrarily
        large files can be transferred without buffering the whole object.
        """
        create = await asyncio.to_thread(
            self.s3_client.create_multipart_upload,
            Bucket=self.bucket_name,
            Key=key,
            ServerSideEncryption="AES256",
        )
        upload_id = create["UploadId"]
        parts = []
        part_number = 1
        buffer = bytearray()

        try:
            async for chunk in chunk_iter:
                buffer.extend(chunk)
                while len(buffer) >= _MULTIPART_PART_SIZE:
                    part_data = bytes(buffer[:_MULTIPART_PART_SIZE])
                    del buffer[:_MULTIPART_PART_SIZE]
                    parts.append(await self._upload_part(key, upload_id, part_number, part_data))
                    part_number += 1

            # Final (possibly smaller) part. A multipart upload needs >=1 part.
            if buffer or not parts:
                parts.append(
                    await self._upload_part(key, upload_id, part_number, bytes(buffer))
                )

            await asyncio.to_thread(
                self.s3_client.complete_multipart_upload,
                Bucket=self.bucket_name,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            logger.info(f"Completed multipart upload to s3://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.error(f"Multipart upload failed for {key}: {e}; aborting")
            try:
                await asyncio.to_thread(
                    self.s3_client.abort_multipart_upload,
                    Bucket=self.bucket_name,
                    Key=key,
                    UploadId=upload_id,
                )
            except ClientError:
                pass
            return False

    async def _upload_part(self, key, upload_id, part_number, data: bytes) -> dict:
        resp = await asyncio.to_thread(
            self.s3_client.upload_part,
            Bucket=self.bucket_name,
            Key=key,
            UploadId=upload_id,
            PartNumber=part_number,
            Body=data,
        )
        return {"ETag": resp["ETag"], "PartNumber": part_number}

    async def download_stream(
        self, key: str, chunk_size: int = _DOWNLOAD_CHUNK_SIZE
    ) -> AsyncIterator[bytes]:
        """Yield an object's contents in chunks without buffering it whole."""
        obj = await asyncio.to_thread(
            self.s3_client.get_object, Bucket=self.bucket_name, Key=key
        )
        body = obj["Body"]
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            await asyncio.to_thread(body.close)

    async def download_bytes(self, key: str) -> Optional[bytes]:
        """Download a whole object into memory (use only for small objects)."""
        try:
            obj = await asyncio.to_thread(
                self.s3_client.get_object, Bucket=self.bucket_name, Key=key
            )
            return await asyncio.to_thread(obj["Body"].read)
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            return None

    async def delete_file(self, key: str) -> bool:
        try:
            await asyncio.to_thread(
                self.s3_client.delete_object, Bucket=self.bucket_name, Key=key
            )
            logger.info(f"Deleted s3://{self.bucket_name}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            return False

    async def file_exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(
                self.s3_client.head_object, Bucket=self.bucket_name, Key=key
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            logger.error(f"Error checking S3 object existence: {e}")
            return False

    async def get_file_size(self, key: str) -> Optional[int]:
        try:
            resp = await asyncio.to_thread(
                self.s3_client.head_object, Bucket=self.bucket_name, Key=key
            )
            return resp["ContentLength"]
        except ClientError as e:
            logger.error(f"Failed to get S3 object size: {e}")
            return None

    async def generate_presigned_url(
        self, key: str, expiration: int = 3600, method: str = "get_object"
    ) -> Optional[str]:
        try:
            return await asyncio.to_thread(
                self.s3_client.generate_presigned_url,
                method,
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None


# Global S3 service instance (boto3 client created lazily on first use).
s3_service = S3Service()
