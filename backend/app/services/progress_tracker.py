"""
Progress tracking service for transfer jobs.
Stores progress in Redis for fast reads and real-time updates.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Service for tracking transfer job progress in Redis."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if not self.redis_client:
            if not settings.REDIS_URL:
                raise Exception("REDIS_URL not configured")
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client

    def _progress_key(self, job_id: int) -> str:
        """Get Redis key for job progress."""
        return f"transfer_progress:{job_id}"

    async def initialize_progress(self, job_id: int, total_files: int, total_size: int) -> None:
        """
        Initialize progress tracking for a transfer job.

        Args:
            job_id: Transfer job ID
            total_files: Total number of files to transfer
            total_size: Total bytes to transfer
        """
        client = await self.get_client()
        progress = {
            "job_id": job_id,
            "total_files": total_files,
            "total_size": total_size,
            "files_completed": 0,
            "files_failed": 0,
            "bytes_transferred": 0,
            "current_file": None,
            "current_file_bytes": 0,
            "current_file_total": 0,
            "started_at": datetime.utcnow().isoformat(),
            "last_update": datetime.utcnow().isoformat()
        }

        await client.set(
            self._progress_key(job_id),
            json.dumps(progress),
            ex=86400  # Expire after 24 hours
        )

        logger.info(f"Initialized progress tracking for job {job_id}: {total_files} files, {total_size} bytes")

    async def update_file_start(self, job_id: int, file_name: str, file_size: int) -> None:
        """
        Update progress when a file transfer starts.

        Args:
            job_id: Transfer job ID
            file_name: Name of the file being transferred
            file_size: Size of the file in bytes
        """
        client = await self.get_client()
        progress_key = self._progress_key(job_id)

        progress_json = await client.get(progress_key)
        if not progress_json:
            logger.warning(f"No progress data found for job {job_id}")
            return

        progress = json.loads(progress_json)
        progress["current_file"] = file_name
        progress["current_file_bytes"] = 0
        progress["current_file_total"] = file_size
        progress["last_update"] = datetime.utcnow().isoformat()

        await client.set(progress_key, json.dumps(progress), ex=86400)

    async def update_file_progress(self, job_id: int, bytes_uploaded: int) -> None:
        """
        Update progress during file upload.

        Args:
            job_id: Transfer job ID
            bytes_uploaded: Bytes uploaded for current file
        """
        client = await self.get_client()
        progress_key = self._progress_key(job_id)

        progress_json = await client.get(progress_key)
        if not progress_json:
            return

        progress = json.loads(progress_json)
        progress["current_file_bytes"] = bytes_uploaded
        progress["last_update"] = datetime.utcnow().isoformat()

        await client.set(progress_key, json.dumps(progress), ex=86400)

    async def update_file_complete(self, job_id: int, success: bool, bytes_transferred: int) -> None:
        """
        Update progress when a file transfer completes.

        Args:
            job_id: Transfer job ID
            success: Whether the transfer was successful
            bytes_transferred: Bytes successfully transferred
        """
        client = await self.get_client()
        progress_key = self._progress_key(job_id)

        progress_json = await client.get(progress_key)
        if not progress_json:
            return

        progress = json.loads(progress_json)

        if success:
            progress["files_completed"] += 1
            progress["bytes_transferred"] += bytes_transferred
        else:
            progress["files_failed"] += 1

        progress["current_file"] = None
        progress["current_file_bytes"] = 0
        progress["current_file_total"] = 0
        progress["last_update"] = datetime.utcnow().isoformat()

        await client.set(progress_key, json.dumps(progress), ex=86400)

        logger.debug(f"Job {job_id} progress: {progress['files_completed']}/{progress['total_files']} completed, "
                    f"{progress['files_failed']} failed")

    async def get_progress(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current progress for a transfer job.

        Args:
            job_id: Transfer job ID

        Returns:
            Progress data dict or None if not found
        """
        client = await self.get_client()
        progress_json = await client.get(self._progress_key(job_id))

        if not progress_json:
            return None

        return json.loads(progress_json)

    async def delete_progress(self, job_id: int) -> None:
        """
        Delete progress data for a completed/cancelled job.

        Args:
            job_id: Transfer job ID
        """
        client = await self.get_client()
        await client.delete(self._progress_key(job_id))
        logger.info(f"Deleted progress data for job {job_id}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


# Global progress tracker instance
progress_tracker = ProgressTracker()
