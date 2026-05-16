"""
Conflict detection service for file transfers.
Checks if files already exist at destination before upload.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

from app.models.connected_account import ConnectedAccount
from app.services.google_drive import GoogleDriveService, GoogleDriveFile
from app.services.onedrive import OneDriveService, OneDriveFile

logger = logging.getLogger(__name__)


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    SKIP = "skip"
    RENAME = "rename"
    OVERWRITE = "overwrite"
    ASK = "ask"


class FileConflict:
    """Represents a file conflict with metadata."""

    def __init__(
        self,
        source_name: str,
        source_size: int,
        source_modified: Optional[str],
        dest_file: Optional[GoogleDriveFile] = None
    ):
        self.source_name = source_name
        self.source_size = source_size
        self.source_modified = source_modified
        self.dest_file = dest_file
        self.has_conflict = dest_file is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "source_name": self.source_name,
            "source_size": self.source_size,
            "source_modified": self.source_modified,
            "has_conflict": self.has_conflict,
            "existing_file": self.dest_file.to_dict() if self.dest_file else None
        }


class ConflictDetectionService:
    """Service for detecting file conflicts before upload."""

    @staticmethod
    async def check_conflict(
        dest_account: ConnectedAccount,
        file_name: str,
        dest_folder_id: str,
        case_insensitive: bool = False
    ) -> Optional[GoogleDriveFile]:
        """
        Check if a file with the given name exists in the destination folder.

        Args:
            dest_account: Connected Google Drive account
            file_name: Name of the file to check
            dest_folder_id: Destination folder ID
            case_insensitive: If True, perform case-insensitive comparison

        Returns:
            GoogleDriveFile if conflict exists, None otherwise
        """
        # List the destination folder once and look for a name collision.
        # (Single listing keeps this consistent with check_conflicts_batch
        # and avoids a separate per-file query.)
        files = await GoogleDriveService.list_folder(dest_account, dest_folder_id)

        if case_insensitive:
            file_name_lower = file_name.lower()
            for file in files:
                if file.name.lower() == file_name_lower:
                    logger.debug(
                        f"Case-insensitive conflict detected: {file_name} matches {file.name}"
                    )
                    return file
            return None

        for file in files:
            if file.name == file_name:
                logger.debug(f"Conflict detected: {file_name} already exists")
                return file

        return None

    @staticmethod
    async def check_conflicts_batch(
        dest_account: ConnectedAccount,
        file_names: list[str],
        dest_folder_id: str,
        case_insensitive: bool = False
    ) -> Dict[str, Optional[GoogleDriveFile]]:
        """
        Check multiple files for conflicts at once.

        Args:
            dest_account: Connected Google Drive account
            file_names: List of file names to check
            dest_folder_id: Destination folder ID
            case_insensitive: If True, perform case-insensitive comparison

        Returns:
            Dictionary mapping file names to GoogleDriveFile (if conflict) or None
        """
        results = {}

        # List all files in destination folder once
        existing_files = await GoogleDriveService.list_folder(dest_account, dest_folder_id)

        # Create lookup dictionaries for fast checking
        exact_match_lookup = {f.name: f for f in existing_files if f.type == "file"}

        if case_insensitive:
            case_insensitive_lookup = {f.name.lower(): f for f in existing_files if f.type == "file"}

        # Check each file name
        for file_name in file_names:
            # Check exact match
            if file_name in exact_match_lookup:
                results[file_name] = exact_match_lookup[file_name]
                logger.debug(f"Conflict detected: {file_name}")
            elif case_insensitive:
                # Check case-insensitive match
                file_name_lower = file_name.lower()
                if file_name_lower in case_insensitive_lookup:
                    results[file_name] = case_insensitive_lookup[file_name_lower]
                    logger.debug(f"Case-insensitive conflict detected: {file_name}")
                else:
                    results[file_name] = None
            else:
                results[file_name] = None

        logger.info(f"Checked {len(file_names)} files, found {sum(1 for v in results.values() if v)} conflicts")
        return results

    @staticmethod
    def generate_rename(original_name: str, existing_files: list[str]) -> str:
        """
        Generate a new filename to avoid conflicts.

        Args:
            original_name: Original filename
            existing_files: List of existing filenames

        Returns:
            New filename with suffix to avoid conflict
        """
        # Split name and extension
        if "." in original_name:
            name_parts = original_name.rsplit(".", 1)
            base_name = name_parts[0]
            extension = "." + name_parts[1]
        else:
            base_name = original_name
            extension = ""

        # Try numbered suffixes
        counter = 1
        while True:
            new_name = f"{base_name} ({counter}){extension}"
            if new_name not in existing_files:
                return new_name
            counter += 1

            # Safety limit
            if counter > 1000:
                raise Exception("Unable to generate unique filename after 1000 attempts")

    @staticmethod
    async def resolve_conflict(
        dest_account: ConnectedAccount,
        file_name: str,
        dest_folder_id: str,
        resolution: ConflictResolution
    ) -> str:
        """
        Resolve a file conflict based on the specified strategy.

        Args:
            dest_account: Connected Google Drive account
            file_name: Original filename
            dest_folder_id: Destination folder ID
            resolution: Conflict resolution strategy

        Returns:
            Final filename to use (may be renamed)

        Raises:
            Exception if conflict cannot be resolved
        """
        if resolution == ConflictResolution.SKIP:
            # Skip means don't upload, but this should be handled by caller
            raise Exception("SKIP resolution should be handled by caller")

        elif resolution == ConflictResolution.RENAME:
            # Generate a new name
            existing_files = await GoogleDriveService.list_folder(dest_account, dest_folder_id)
            existing_names = [f.name for f in existing_files if f.type == "file"]
            new_name = ConflictDetectionService.generate_rename(file_name, existing_names)
            logger.info(f"Renamed {file_name} to {new_name} to avoid conflict")
            return new_name

        elif resolution == ConflictResolution.OVERWRITE:
            # Keep the same name, but delete the existing file first
            existing_file = await GoogleDriveService.check_file_exists(
                dest_account, file_name, dest_folder_id
            )
            if existing_file:
                # Note: Google Drive API doesn't have a simple delete in the base service
                # The caller should handle deletion before upload
                logger.info(f"Will overwrite existing file: {file_name}")
            return file_name

        elif resolution == ConflictResolution.ASK:
            # ASK means pause and wait for user input
            # This should be handled by the transfer orchestrator
            raise Exception("ASK resolution requires user interaction")

        else:
            raise Exception(f"Unknown conflict resolution: {resolution}")
