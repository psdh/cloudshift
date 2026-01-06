"""
OneDrive file operations service.
Handles file listing, downloading, and interacting with OneDrive API.
"""

import logging
from typing import List, Dict, Any, Optional, AsyncIterator
import aiohttp
from datetime import datetime

from app.models.connected_account import ConnectedAccount
from app.services.oauth import OAuthService
from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class OneDriveFile:
    """Normalized file/folder object from OneDrive."""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data.get("id", "")
        self.name: str = data.get("name", "")
        self.type: str = "folder" if "folder" in data else "file"
        self.size: int = data.get("size", 0)
        self.modified_at: Optional[datetime] = None
        self.path: str = data.get("parentReference", {}).get("path", "")

        # Parse modified date
        if "lastModifiedDateTime" in data:
            try:
                self.modified_at = datetime.fromisoformat(data["lastModifiedDateTime"].replace("Z", "+00:00"))
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


class OneDriveService:
    """Service for interacting with OneDrive API."""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    @staticmethod
    async def _get_access_token(account: ConnectedAccount) -> str:
        """Get valid access token, refreshing if necessary."""
        return await OAuthService.get_valid_token(account, "onedrive")

    @staticmethod
    async def list_root_folder(account: ConnectedAccount) -> List[OneDriveFile]:
        """
        List contents of the root folder.

        Args:
            account: Connected OneDrive account

        Returns:
            List of OneDriveFile objects
        """
        return await OneDriveService.list_folder(account, "root")

    @staticmethod
    async def list_folder(
        account: ConnectedAccount,
        folder_id_or_path: str = "root",
        page_size: int = 200
    ) -> List[OneDriveFile]:
        """
        List contents of a specific folder with pagination support.

        Args:
            account: Connected OneDrive account
            folder_id_or_path: Folder ID or path (default: "root")
            page_size: Number of items per page (max 200)

        Returns:
            List of OneDriveFile objects
        """
        access_token = await OneDriveService._get_access_token(account)

        # Determine endpoint based on whether it's an ID or path
        if folder_id_or_path == "root" or folder_id_or_path.startswith("/"):
            # Use path-based endpoint
            if folder_id_or_path == "root":
                endpoint = f"{OneDriveService.BASE_URL}/me/drive/root/children"
            else:
                endpoint = f"{OneDriveService.BASE_URL}/me/drive/root:{folder_id_or_path}:/children"
        else:
            # Use ID-based endpoint
            endpoint = f"{OneDriveService.BASE_URL}/me/drive/items/{folder_id_or_path}/children"

        all_files = []
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"$top": page_size}

        async with aiohttp.ClientSession() as session:
            while endpoint:
                # Wait if rate limited
                await rate_limiter.wait_if_rate_limited("onedrive")

                # Record request
                await rate_limiter.record_request("onedrive")

                async with session.get(endpoint, headers=headers, params=params if params else None) as response:
                    # Handle rate limiting
                    if response.status == 429:
                        # Convert aiohttp response to httpx-like response for rate_limiter
                        import httpx
                        httpx_response = httpx.Response(
                            status_code=response.status,
                            headers=dict(response.headers),
                            request=httpx.Request("GET", endpoint)
                        )
                        await rate_limiter.handle_rate_limit_response("onedrive", httpx_response)
                        continue  # Retry after backoff

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OneDrive API error: {response.status} - {error_text}")
                        raise Exception(f"Failed to list OneDrive folder: {response.status}")

                    data = await response.json()

                    # Process items
                    for item in data.get("value", []):
                        all_files.append(OneDriveFile(item))

                    # Check for next page
                    endpoint = data.get("@odata.nextLink")
                    params = None  # nextLink already contains all params

                    logger.debug(f"Retrieved {len(data.get('value', []))} items from OneDrive")

        logger.info(f"Listed {len(all_files)} items from OneDrive folder {folder_id_or_path}")
        return all_files

    @staticmethod
    async def download_file(
        account: ConnectedAccount,
        file_id: str
    ) -> AsyncIterator[bytes]:
        """
        Download a file from OneDrive as a stream.

        Args:
            account: Connected OneDrive account
            file_id: File ID to download

        Yields:
            File content in chunks
        """
        access_token = await OneDriveService._get_access_token(account)

        # Get download URL
        endpoint = f"{OneDriveService.BASE_URL}/me/drive/items/{file_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            # First, get the file metadata to get download URL
            await rate_limiter.wait_if_rate_limited("onedrive")
            await rate_limiter.record_request("onedrive")

            async with session.get(endpoint, headers=headers) as response:
                if response.status == 429:
                    import httpx
                    httpx_response = httpx.Response(
                        status_code=response.status,
                        headers=dict(response.headers),
                        request=httpx.Request("GET", endpoint)
                    )
                    await rate_limiter.handle_rate_limit_response("onedrive", httpx_response)
                    raise Exception("Rate limit hit - retry required")

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OneDrive API error: {response.status} - {error_text}")
                    raise Exception(f"Failed to get OneDrive file info: {response.status}")

                data = await response.json()
                download_url = data.get("@microsoft.graph.downloadUrl")

                if not download_url:
                    raise Exception("No download URL available for file")

            # Now download the file (download URL doesn't count toward API rate limit)
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download file: {response.status}")

                # Stream the file in chunks
                chunk_size = 8192  # 8KB chunks
                while True:
                    chunk = await response.content.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

    @staticmethod
    async def get_file_info(
        account: ConnectedAccount,
        file_id: str
    ) -> OneDriveFile:
        """
        Get metadata for a specific file/folder.

        Args:
            account: Connected OneDrive account
            file_id: File or folder ID

        Returns:
            OneDriveFile object
        """
        access_token = await OneDriveService._get_access_token(account)

        endpoint = f"{OneDriveService.BASE_URL}/me/drive/items/{file_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OneDrive API error: {response.status} - {error_text}")
                    raise Exception(f"Failed to get file info: {response.status}")

                data = await response.json()
                return OneDriveFile(data)
