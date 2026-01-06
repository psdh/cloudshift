import boto3
from botocore.exceptions import ClientError
from typing import BinaryIO, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for interacting with AWS S3 for intermediate file storage."""

    def __init__(self):
        """Initialize S3 client with credentials from settings."""
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Upload a file to S3 bucket with server-side encryption.

        Args:
            file_obj: File-like object to upload
            key: S3 object key (path) for the file
            metadata: Optional metadata dictionary

        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            extra_args = {
                "ServerSideEncryption": "AES256",  # Enable encryption at rest
            }

            if metadata:
                extra_args["Metadata"] = metadata

            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs=extra_args,
            )

            logger.info(f"Successfully uploaded file to s3://{self.bucket_name}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False

    def download_file(self, key: str, file_obj: BinaryIO) -> bool:
        """
        Download a file from S3 bucket.

        Args:
            key: S3 object key (path) of the file
            file_obj: File-like object to write downloaded data to

        Returns:
            bool: True if download successful, False otherwise
        """
        try:
            self.s3_client.download_fileobj(
                self.bucket_name,
                key,
                file_obj,
            )

            logger.info(f"Successfully downloaded file from s3://{self.bucket_name}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            return False

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3 bucket.

        Args:
            key: S3 object key (path) of the file to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key,
            )

            logger.info(f"Successfully deleted file from s3://{self.bucket_name}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False

    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in S3 bucket.

        Args:
            key: S3 object key (path) to check

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Error checking file existence in S3: {e}")
            return False

    def get_file_size(self, key: str) -> Optional[int]:
        """
        Get the size of a file in S3 bucket.

        Args:
            key: S3 object key (path)

        Returns:
            Optional[int]: File size in bytes, or None if error
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return response["ContentLength"]

        except ClientError as e:
            logger.error(f"Failed to get file size from S3: {e}")
            return None

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "get_object",
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary access to S3 object.

        Args:
            key: S3 object key (path)
            expiration: URL expiration time in seconds (default: 1 hour)
            method: S3 method (get_object, put_object, etc.)

        Returns:
            Optional[str]: Presigned URL or None if error
        """
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                },
                ExpiresIn=expiration,
            )
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None


# Global S3 service instance
s3_service = S3Service()
