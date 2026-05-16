"""
Tests for SSE progress streaming endpoint.

The streaming happy-path is an integration test (needs Redis-backed
progress_tracker and a worker) and is skipped here; the auth/ownership
guards are unit-testable against the in-memory test DB via async_client.
"""

import pytest


@pytest.mark.skip(
    reason="Integration-only: requires Redis-backed progress_tracker and a "
    "running worker. Covered by the e2e suite, not the unit suite."
)
@pytest.mark.asyncio
async def test_sse_stream_sends_progress_updates():
    """Streaming happy-path — integration only (see skip reason)."""


@pytest.mark.asyncio
async def test_sse_stream_requires_auth(async_client):
    """SSE stream must reject unauthenticated requests with 401."""
    response = await async_client.get("/api/transfers/999/progress/stream")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sse_stream_validates_job_ownership(async_client):
    """A user must not be able to stream another user's job (404)."""
    # User 1
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        },
    )
    login1 = await async_client.post(
        "/api/auth/login",
        json={"email": "user1@example.com", "password": "TestPass123!"},
    )
    token1 = login1.json()["access_token"]

    # User 2
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "user2@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        },
    )
    login2 = await async_client.post(
        "/api/auth/login",
        json={"email": "user2@example.com", "password": "TestPass123!"},
    )
    token2 = login2.json()["access_token"]

    # Job owned by user 1
    transfer_response = await async_client.post(
        "/api/transfers",
        json={"source_provider": "onedrive", "dest_provider": "google_drive"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    job_id = transfer_response.json()["id"]

    # User 2 must not see it
    response = await async_client.get(
        f"/api/transfers/{job_id}/progress/stream",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert response.status_code == 404
