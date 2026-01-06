"""
Tests for SSE progress streaming endpoint.
"""

import pytest
import json
from httpx import AsyncClient
from app.main import app
from app.services.progress_tracker import progress_tracker


@pytest.mark.asyncio
async def test_sse_stream_sends_progress_updates():
    """Test that SSE stream sends progress updates for a job."""
    # This is a basic test to verify the SSE endpoint is accessible
    # A full test would require setting up a job and mocking Redis

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a test user and get auth token
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "test_sse@example.com",
                "password": "TestPass123!"
            }
        )
        assert register_response.status_code == 201

        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "test_sse@example.com",
                "password": "TestPass123!"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create a transfer job
        transfer_response = await client.post(
            "/api/transfers",
            json={
                "source_provider": "onedrive",
                "dest_provider": "google"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert transfer_response.status_code == 201
        job_id = transfer_response.json()["id"]

        # Initialize progress in Redis
        await progress_tracker.initialize_progress(
            job_id=job_id,
            total_files=10,
            total_size=1000000
        )

        # Update progress to simulate a file being transferred
        await progress_tracker.update_file_start(job_id, "test.txt", 1000)
        await progress_tracker.update_file_complete(job_id, success=True, bytes_transferred=1000)

        # Connect to SSE stream (use streaming for testing)
        # Note: This will only read the first event, then close
        async with client.stream(
            "GET",
            f"/api/transfers/{job_id}/progress/stream",
            headers={"Authorization": f"Bearer {token}"}
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # Read first event
            event_data = None
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event_data = json.loads(line[6:])  # Remove "data: " prefix
                    break

            # Verify event structure
            assert event_data is not None
            assert event_data["job_id"] == job_id
            assert event_data["total_files"] == 10
            assert event_data["total_size"] == 1000000
            assert event_data["files_completed"] == 1
            assert "percent_complete" in event_data

        # Cleanup
        await progress_tracker.delete_progress(job_id)


@pytest.mark.asyncio
async def test_sse_stream_requires_auth():
    """Test that SSE stream requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/transfers/999/progress/stream")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_sse_stream_validates_job_ownership():
    """Test that SSE stream validates job ownership."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create first user
        await client.post(
            "/api/auth/register",
            json={
                "email": "user1@example.com",
                "password": "TestPass123!"
            }
        )
        login1 = await client.post(
            "/api/auth/login",
            json={
                "email": "user1@example.com",
                "password": "TestPass123!"
            }
        )
        token1 = login1.json()["access_token"]

        # Create second user
        await client.post(
            "/api/auth/register",
            json={
                "email": "user2@example.com",
                "password": "TestPass123!"
            }
        )
        login2 = await client.post(
            "/api/auth/login",
            json={
                "email": "user2@example.com",
                "password": "TestPass123!"
            }
        )
        token2 = login2.json()["access_token"]

        # Create job as user1
        transfer_response = await client.post(
            "/api/transfers",
            json={
                "source_provider": "onedrive",
                "dest_provider": "google"
            },
            headers={"Authorization": f"Bearer {token1}"}
        )
        job_id = transfer_response.json()["id"]

        # Try to stream as user2 (should fail)
        response = await client.get(
            f"/api/transfers/{job_id}/progress/stream",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response.status_code == 404
