from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import httpx

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.services.oauth import OAuthService
from app.services.audit import AuditService
from app.models.connected_account import CloudProvider
from pydantic import BaseModel


router = APIRouter(prefix="/api/oauth", tags=["oauth"])


class AuthorizeResponse(BaseModel):
    """Response schema for OAuth authorization URL."""

    auth_url: str
    state: str


class OAuthCallbackParams(BaseModel):
    """Query parameters for OAuth callback."""

    code: str
    state: str
    error: Optional[str] = None
    error_description: Optional[str] = None


class ConnectedAccountResponse(BaseModel):
    """Response schema for connected account."""

    id: int
    provider: str
    account_email: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/onedrive/authorize", response_model=AuthorizeResponse)
async def onedrive_authorize(
    request: Request,
    user_id: int = Depends(get_current_user_id)
):
    """
    Initiate OneDrive OAuth authorization flow.

    Returns authorization URL with state parameter for CSRF protection.

    Args:
        request: FastAPI request object to get base URL
        user_id: Current user ID from JWT token

    Returns:
        AuthorizeResponse: Authorization URL and state parameter
    """
    # Generate state for CSRF protection
    state = OAuthService.generate_state()

    # Build redirect URI
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/oauth/onedrive/callback"

    # Get authorization URL
    auth_url = OAuthService.get_onedrive_auth_url(state, redirect_uri)

    # Store state in session/cache for validation (simplified for now)
    # In production, store state in Redis with user_id and expiry
    # For now, we'll validate state exists in the callback

    return AuthorizeResponse(auth_url=auth_url, state=state)


@router.get("/onedrive/callback")
async def onedrive_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle OneDrive OAuth callback.

    Exchanges authorization code for tokens and stores them encrypted.

    Args:
        code: Authorization code from OneDrive
        state: State parameter for CSRF validation
        error: Error code if authorization failed
        error_description: Error description if authorization failed
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        Dict with success message and account info

    Raises:
        HTTPException 400: If OAuth flow failed or state invalid
    """
    # Check for OAuth errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description or 'No description'}"
        )

    # Validate required parameters
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )

    # TODO: Validate state parameter against stored value in Redis
    # For now, we'll accept any state (simplified for development)

    try:
        # Build redirect URI (same as in authorize)
        # In production, this should be from settings
        redirect_uri = f"{settings.APP_URL or 'http://localhost:8000'}/api/oauth/onedrive/callback"

        # Exchange code for tokens
        token_response = await OAuthService.exchange_onedrive_code(code, redirect_uri)

        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )

        # Fetch user info to get email
        user_info = await OAuthService.get_onedrive_user_info(access_token)
        account_email = user_info.get("userPrincipalName") or user_info.get("mail")

        # Save connected account with encrypted tokens
        account = await OAuthService.save_connected_account(
            db=db,
            user_id=user_id,
            provider=CloudProvider.ONEDRIVE,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            account_email=account_email
        )

        # Log account connection
        await AuditService.log_account_connected(
            db, user_id, "onedrive", account_email or "unknown", request
        )

        return {
            "success": True,
            "message": "OneDrive account connected successfully",
            "account": ConnectedAccountResponse(
                id=account.id,
                provider=account.provider.value,
                account_email=account.account_email,
                created_at=account.created_at.isoformat()
            )
        }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during OAuth flow: {str(e)}"
        )


@router.get("/google/authorize", response_model=AuthorizeResponse)
async def google_authorize(
    request: Request,
    user_id: int = Depends(get_current_user_id)
):
    """
    Initiate Google Drive OAuth authorization flow.

    Returns authorization URL with state parameter for CSRF protection.

    Args:
        request: FastAPI request object to get base URL
        user_id: Current user ID from JWT token

    Returns:
        AuthorizeResponse: Authorization URL and state parameter
    """
    # Generate state for CSRF protection
    state = OAuthService.generate_state()

    # Build redirect URI
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/oauth/google/callback"

    # Get authorization URL
    auth_url = OAuthService.get_google_auth_url(state, redirect_uri)

    return AuthorizeResponse(auth_url=auth_url, state=state)


@router.get("/google/callback")
async def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google Drive OAuth callback.

    Exchanges authorization code for tokens and stores them encrypted.

    Args:
        code: Authorization code from Google
        state: State parameter for CSRF validation
        error: Error code if authorization failed
        error_description: Error description if authorization failed
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        Dict with success message and account info

    Raises:
        HTTPException 400: If OAuth flow failed or state invalid
    """
    # Check for OAuth errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description or 'No description'}"
        )

    # Validate required parameters
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )

    # TODO: Validate state parameter against stored value in Redis

    try:
        # Build redirect URI (same as in authorize)
        redirect_uri = f"{settings.APP_URL or 'http://localhost:8000'}/api/oauth/google/callback"

        # Exchange code for tokens
        token_response = await OAuthService.exchange_google_code(code, redirect_uri)

        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )

        # Fetch user info to get email
        user_info = await OAuthService.get_google_user_info(access_token)
        account_email = user_info.get("email")

        # Save connected account with encrypted tokens
        account = await OAuthService.save_connected_account(
            db=db,
            user_id=user_id,
            provider=CloudProvider.GOOGLE_DRIVE,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            account_email=account_email
        )

        return {
            "success": True,
            "message": "Google Drive account connected successfully",
            "account": ConnectedAccountResponse(
                id=account.id,
                provider=account.provider.value,
                account_email=account.account_email,
                created_at=account.created_at.isoformat()
            )
        }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange authorization code: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during OAuth flow: {str(e)}"
        )


# Import settings at the end to avoid circular imports
from app.core.config import settings
