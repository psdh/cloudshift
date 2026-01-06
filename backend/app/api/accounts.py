from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.connected_account import ConnectedAccount, CloudProvider
from app.services.oauth import OAuthService
from pydantic import BaseModel


router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class ConnectedAccountListResponse(BaseModel):
    """Response schema for connected account in list."""

    provider: str
    account_email: str | None
    connected_at: str
    token_expires_at: str | None

    class Config:
        from_attributes = True


class AccountStatusResponse(BaseModel):
    """Response schema for account status check."""

    provider: str
    is_connected: bool
    is_token_valid: bool
    account_email: str | None
    expires_at: str | None


@router.get("", response_model=List[ConnectedAccountListResponse])
async def list_connected_accounts(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all connected cloud storage accounts for the current user.

    Returns list of connected accounts without sensitive token information.

    Args:
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        List[ConnectedAccountListResponse]: List of connected accounts
    """
    # Fetch all connected accounts for user
    result = await db.execute(
        select(ConnectedAccount)
        .where(ConnectedAccount.user_id == user_id)
        .order_by(ConnectedAccount.created_at.desc())
    )
    accounts = result.scalars().all()

    # Format response without exposing tokens
    response = []
    for account in accounts:
        response.append(
            ConnectedAccountListResponse(
                provider=account.provider.value,
                account_email=account.account_email,
                connected_at=account.created_at.isoformat(),
                token_expires_at=account.token_expiry.isoformat() if account.token_expiry else None
            )
        )

    return response


@router.delete("/{provider}")
async def disconnect_account(
    provider: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect a cloud storage account and delete its tokens.

    Args:
        provider: Cloud provider name ("onedrive" or "google_drive")
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        Dict with success message

    Raises:
        HTTPException 400: If provider is invalid
        HTTPException 404: If account not found
    """
    # Validate provider
    try:
        provider_enum = CloudProvider(provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Must be 'onedrive' or 'google_drive'"
        )

    # Find and delete the account
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == provider_enum
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} account connected"
        )

    # Delete the account
    await db.delete(account)
    await db.commit()

    return {
        "success": True,
        "message": f"{provider} account disconnected successfully"
    }


@router.get("/{provider}/status", response_model=AccountStatusResponse)
async def get_account_status(
    provider: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Check the status and validity of a connected account.

    Args:
        provider: Cloud provider name ("onedrive" or "google_drive")
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        AccountStatusResponse: Account status information

    Raises:
        HTTPException 400: If provider is invalid
    """
    # Validate provider
    try:
        provider_enum = CloudProvider(provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Must be 'onedrive' or 'google_drive'"
        )

    # Find the account
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == provider_enum
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        # Account not connected
        return AccountStatusResponse(
            provider=provider,
            is_connected=False,
            is_token_valid=False,
            account_email=None,
            expires_at=None
        )

    # Check if token is valid (not expired)
    is_valid = not OAuthService.is_token_expired(account.token_expiry)

    return AccountStatusResponse(
        provider=provider,
        is_connected=True,
        is_token_valid=is_valid,
        account_email=account.account_email,
        expires_at=account.token_expiry.isoformat() if account.token_expiry else None
    )
