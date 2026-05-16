"""
Google Drive file operations service.
Handles file listing, uploading, folder creation, and interacting with Google Drive API.
"""

import logging
from typing import List, Dict, Any, Optional, AsyncIterator, Callable
import aiohttp
import io
from datetime import datetime

from app.models.connected_account import ConnectedAccount
from app.services.oauth import OAuthService
from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class GoogleDriveFile:
    """Normalized file/folder object from Google Drive."""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.mime_type: str = data.get("mimeType", "")
        self.type: str = "folder" if self.mime_type == "application/vnd.google-apps.folder" else "file"
        self.size: int = int(data.get("size", 0)) if "size" in data else 0
        self.modified_at: Optional[datetime] = None
        self.path: str = ""  # Google Drive doesn't provide full paths easily

        # Parse modified date
        if "modifiedTime" in data:
            try:
                self.modified_at = datetime.fromisoformat(data["modifiedTime"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "path": self.path
        }


class GoogleDriveService:
    """Service for interacting with Google Drive API."""

    BASE_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3"

    @staticmethod
    async def _get_access_token(account: ConnectedAccount) -> str:
        """Get valid access token, refreshing if necessary."""
        return await OAuthService.get_valid_token(account)

    @staticmethod
    async def list_root_folder(account: ConnectedAccount) -> List[GoogleDriveFile]:
        """
        List contents of the root folder (My Drive).

        Args:
            account: Connected Google Drive account

        Returns:
            List of GoogleDriveFile objects
        """
        return await GoogleDriveService.list_folder(account, "root")

    @staticmethod
    async def list_folder(
        account: ConnectedAccount,
        folder_id: str = "root",
        page_size: int = 100
    ) -> List[GoogleDriveFile]:
        """
        List contents of a specific folder with pagination support.

        Args:
            account: Connected Google Drive account
            folder_id: Folder ID (default: "root" for My Drive)
            page_size: Number of items per page (max 1000)

        Returns:
            List of GoogleDriveFile objects
        """
        access_token = await GoogleDriveService._get_access_token(account)

        endpoint = f"{GoogleDriveService.BASE_URL}/files"
        all_files = []
        page_token = None

        headers = {"Authorization": f"Bearer {access_token}"}

        # Query for files in this folder, excluding trashed items
        query = f"'{folder_id}' in parents and trashed = false"

        async with aiohttp.ClientSession() as session:
            while True:
                # Wait if rate limited
                await rate_limiter.wait_if_rate_limited("google")

                # Record request
                await rate_limiter.record_request("google")

                params = {
                    "q": query,
                    "pageSize": page_size,
                    "fields": "nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                }
                if page_token:
                    params["pageToken"] = page_token

                async with session.get(endpoint, headers=headers, params=params) as response:
                    # Handle rate limiting
                    if response.status == 429:
                        import httpx
                        httpx_response = httpx.Response(
                            status_code=response.status,
                            headers=dict(response.headers),
                            request=httpx.Request("GET", endpoint)
                        )
                        await rate_limiter.handle_rate_limit_response("google", httpx_response)
                        continue  # Retry after backoff

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Google Drive API error: {response.status} - {error_text}")
                        raise Exception(f"Failed to list Google Drive folder: {response.status}")

                    data = await response.json()

                    # Process items
                    for item in data.get("files", []):
                        all_files.append(GoogleDriveFile(item))

                    # Check for next page
                    page_token = data.get("nextPageToken")
                    logger.debug(f"Retrieved {len(data.get('files', []))} items from Google Drive")

                    if not page_token:
                        break

        logger.info(f"Listed {len(all_files)} items from Google Drive folder {folder_id}")
        return all_files

    @staticmethod
    async def upload_file(
        account: ConnectedAccount,
        file_name: str,
        file_stream: AsyncIterator[bytes],
        parent_folder_id: str = "root",
        mime_type: str = "application/octet-stream",
        total_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> GoogleDriveFile:
        """
        Upload a file to Google Drive via a resumable session, streaming the
        source iterator. At most one ~8 MiB (256 KiB-aligned) buffer is held
        in memory, so files of any size can be uploaded without buffering the
        whole object.

        Args:
            account: Connected Google Drive account
            file_name: Name of the file to create
            file_stream: Async iterator yielding file content chunks
            parent_folder_id: Parent folder ID (default: "root")
            mime_type: MIME type of the file
            total_size: Total size in bytes (required for the streaming
                Content-Range; the transfer pipeline always knows this)
            progress_callback: Optional callback (bytes uploaded so far)

        Returns:
            GoogleDriveFile object for the uploaded file
        """
        access_token = await GoogleDriveService._get_access_token(account)
        metadata = {"name": file_name, "parents": [parent_folder_id]}

        # Initiate the resumable session.
        init_endpoint = (
            f"{GoogleDriveService.UPLOAD_URL}/files"
            "?uploadType=resumable&fields=id,name,mimeType,size,modifiedTime"
        )
        init_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        await rate_limiter.wait_if_rate_limited("google_drive")
        await rate_limiter.record_request("google_drive")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                init_endpoint, headers=init_headers, json=metadata
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to initiate resumable upload: {response.status} - {error_text}"
                    )
                    raise Exception(
                        f"Failed to initiate resumable upload: {response.status}"
                    )
                upload_url = response.headers.get("Location")
                if not upload_url:
                    raise Exception("No upload URL received from Google Drive")

            # Google requires every non-final chunk to be a multiple of 256 KiB.
            block = 256 * 1024
            flush_at = 32 * block  # 8 MiB
            buffer = bytearray()
            uploaded = 0

            async def _put(chunk: bytes, is_final: bool):
                nonlocal uploaded
                start = uploaded
                end = uploaded + len(chunk) - 1
                # Use the known total when available; otherwise '*' until the
                # final chunk, where the total becomes the final byte count.
                if total_size is not None:
                    total = str(total_size)
                elif is_final:
                    total = str(uploaded + len(chunk))
                else:
                    total = "*"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{total}",
                }
                async with session.put(upload_url, headers=headers, data=chunk) as resp:
                    uploaded = end + 1
                    if resp.status in (200, 201):
                        return GoogleDriveFile(await resp.json())
                    if resp.status == 308:
                        if progress_callback:
                            progress_callback(uploaded)
                        return None
                    error_text = await resp.text()
                    raise Exception(
                        f"Resumable upload failed: {resp.status} - {error_text}"
                    )

            result = None
            async for chunk in file_stream:
                buffer.extend(chunk)
                while len(buffer) >= flush_at:
                    part = bytes(buffer[:flush_at])
                    del buffer[:flush_at]
                    result = await _put(part, is_final=False)

            # Final chunk (the remainder; may be empty for a 0-byte file).
            result = await _put(bytes(buffer), is_final=True)
            if result is None:
                raise Exception("Resumable upload did not return file metadata")

            logger.info(
                f"Uploaded {file_name} to Google Drive ({uploaded} bytes streamed)"
            )
            if progress_callback:
                progress_callback(uploaded)
            return result

    @staticmethod
    async def delete_file(account: ConnectedAccount, file_id: str) -> bool:
        """Delete a file by ID (used to implement conflict 'overwrite')."""
        access_token = await GoogleDriveService._get_access_token(account)
        endpoint = f"{GoogleDriveService.BASE_URL}/files/{file_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.delete(endpoint, headers=headers) as response:
                if response.status not in (200, 204):
                    error_text = await response.text()
                    logger.error(
                        f"Failed to delete Google Drive file {file_id}: "
                        f"{response.status} - {error_text}"
                    )
                    return False
        logger.info(f"Deleted Google Drive file {file_id}")
        return True

    @staticmethod
    async def create_folder(
        account: ConnectedAccount,
        folder_name: str,
        parent_folder_id: str = "root"
    ) -> GoogleDriveFile:
        """
        Create a single folder in Google Drive.

        Args:
            account: Connected Google Drive account
            folder_name: Name of the folder to create
            parent_folder_id: Parent folder ID (default: "root")

        Returns:
            GoogleDriveFile object for the created folder
        """
        access_token = await GoogleDriveService._get_access_token(account)

        endpoint = f"{GoogleDriveService.BASE_URL}/files?fields=id,name,mimeType,modifiedTime"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=headers, json=metadata) as response:
                if response.status not in (200, 201):
                    error_text = await response.text()
                    logger.error(f"Google Drive folder creation error: {response.status} - {error_text}")
                    raise Exception(f"Failed to create folder in Google Drive: {response.status}")

                data = await response.json()
                logger.info(f"Created folder {folder_name} in Google Drive")
                return GoogleDriveFile(data)

    @staticmethod
    async def create_folder_path(
        account: ConnectedAccount,
        folder_path: str,
        parent_folder_id: str = "root"
    ) -> GoogleDriveFile:
        """
        Create a nested folder path, creating all intermediate folders.
        Idempotent: returns existing folder if already exists.

        Args:
            account: Connected Google Drive account
            folder_path: Path like "folder1/folder2/folder3"
            parent_folder_id: Starting parent folder ID (default: "root")

        Returns:
            GoogleDriveFile object for the final folder in the path
        """
        # Split path into parts
        parts = [p for p in folder_path.split("/") if p]

        current_parent = parent_folder_id

        for folder_name in parts:
            # Check if folder already exists
            existing = await GoogleDriveService._find_folder_by_name(
                account, folder_name, current_parent
            )

            if existing:
                current_parent = existing.id
                logger.debug(f"Folder {folder_name} already exists with ID {current_parent}")
            else:
                # Create the folder
                folder = await GoogleDriveService.create_folder(
                    account, folder_name, current_parent
                )
                current_parent = folder.id
                logger.debug(f"Created folder {folder_name} with ID {current_parent}")

        # Return the final folder
        return await GoogleDriveService.get_file_info(account, current_parent)

    @staticmethod
    async def _find_folder_by_name(
        account: ConnectedAccount,
        folder_name: str,
        parent_folder_id: str
    ) -> Optional[GoogleDriveFile]:
        """Find a folder by name within a parent folder."""
        access_token = await GoogleDriveService._get_access_token(account)

        endpoint = f"{GoogleDriveService.BASE_URL}/files"
        headers = {"Authorization": f"Bearer {access_token}"}

        query = (
            f"name = '{folder_name}' and "
            f"'{parent_folder_id}' in parents and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )

        params = {
            "q": query,
            "pageSize": 1,
            "fields": "files(id, name, mimeType, modifiedTime)"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                files = data.get("files", [])

                if files:
                    return GoogleDriveFile(files[0])
                return None

    @staticmethod
    async def get_file_info(
        account: ConnectedAccount,
        file_id: str
    ) -> GoogleDriveFile:
        """
        Get metadata for a specific file/folder.

        Args:
            account: Connected Google Drive account
            file_id: File or folder ID

        Returns:
            GoogleDriveFile object
        """
        access_token = await GoogleDriveService._get_access_token(account)

        endpoint = f"{GoogleDriveService.BASE_URL}/files/{file_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"fields": "id, name, mimeType, size, modifiedTime"}

        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Google Drive API error: {response.status} - {error_text}")
                    raise Exception(f"Failed to get file info: {response.status}")

                data = await response.json()
                return GoogleDriveFile(data)

    @staticmethod
    async def check_file_exists(
        account: ConnectedAccount,
        file_name: str,
        parent_folder_id: str
    ) -> Optional[GoogleDriveFile]:
        """
        Check if a file with the given name exists in a folder.

        Args:
            account: Connected Google Drive account
            file_name: Name of the file to check
            parent_folder_id: Parent folder ID to search in

        Returns:
            GoogleDriveFile object if found, None otherwise
        """
        access_token = await GoogleDriveService._get_access_token(account)

        endpoint = f"{GoogleDriveService.BASE_URL}/files"
        headers = {"Authorization": f"Bearer {access_token}"}

        query = (
            f"name = '{file_name}' and "
            f"'{parent_folder_id}' in parents and "
            f"trashed = false"
        )

        params = {
            "q": query,
            "pageSize": 1,
            "fields": "files(id, name, mimeType, size, modifiedTime)"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                files = data.get("files", [])

                if files:
                    return GoogleDriveFile(files[0])
                return None
