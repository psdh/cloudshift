"""Integration tests for transfer API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.models.transfer import TransferJob, TransferItem, JobStatus
from app.core.security import create_access_token


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYxKxNzYZqy"  # 'password'
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create an auth token for the test user."""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def connected_accounts(db_session, test_user):
    """Create connected accounts for test user."""
    onedrive_account = ConnectedAccount(
        user_id=test_user.id,
        provider="onedrive",
        access_token="fake_onedrive_token",
        refresh_token="fake_refresh",
        token_expiry=datetime.utcnow() + timedelta(hours=1),
        account_email="user@onedrive.com"
    )
    google_account = ConnectedAccount(
        user_id=test_user.id,
        provider="google_drive",
        access_token="fake_google_token",
        refresh_token="fake_refresh",
        token_expiry=datetime.utcnow() + timedelta(hours=1),
        account_email="user@gmail.com"
    )
    db_session.add(onedrive_account)
    db_session.add(google_account)
    db_session.commit()
    return {
        "onedrive": onedrive_account,
        "google": google_account
    }


class TestTransferCRUD:
    """Test transfer CRUD operations."""

    def test_create_transfer(self, client: TestClient, auth_headers, connected_accounts):
        """Test creating a new transfer job."""
        response = client.post(
            "/api/transfers",
            headers=auth_headers,
            json={
                "source_provider": "onedrive",
                "dest_provider": "google",
                "source_folder_id": "root",
                "dest_folder_id": "root",
                "config": {
                    "conflict_strategy": "ask",
                    "file_types": [".pdf", ".docx"]
                }
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["source_provider"] == "onedrive"
        assert data["dest_provider"] == "google_drive"
        assert data["status"] == "draft"
        assert data["config"]["conflict_strategy"] == "ask"
        assert "id" in data

    def test_list_transfers(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test listing user's transfers."""
        # Create some test transfers
        for i in range(3):
            job = TransferJob(
                user_id=test_user.id,
                status=JobStatus.COMPLETED if i == 0 else JobStatus.PENDING,
                source_provider="onedrive",
                dest_provider="google",
                config={}
            )
            db_session.add(job)
        db_session.commit()

        response = client.get("/api/transfers", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1

    def test_list_transfers_pagination(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test transfer list pagination."""
        # Create 25 test transfers
        for i in range(25):
            job = TransferJob(
                user_id=test_user.id,
                status=JobStatus.PENDING,
                source_provider="onedrive",
                dest_provider="google",
                config={}
            )
            db_session.add(job)
        db_session.commit()

        # Get first page
        response = client.get("/api/transfers?page=1&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["total_pages"] == 3

        # Get second page
        response = client.get("/api/transfers?page=2&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10

    def test_get_transfer_details(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test getting transfer details."""
        job = TransferJob(
            user_id=test_user.id,
            status=JobStatus.COMPLETED,
            source_provider="onedrive",
            dest_provider="google",
            config={"conflict_strategy": "skip_all"}
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/transfers/{job.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job.id
        assert data["status"] == "completed"
        assert data["config"]["conflict_strategy"] == "skip_all"

    def test_get_transfer_not_found(self, client: TestClient, auth_headers):
        """Test getting non-existent transfer."""
        response = client.get("/api/transfers/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_transfer_unauthorized(self, client: TestClient, auth_headers, db_session):
        """Test getting transfer owned by another user."""
        # Create another user
        other_user = User(email="other@example.com", password_hash="hash")
        db_session.add(other_user)
        db_session.commit()

        # Create transfer for other user
        job = TransferJob(
            user_id=other_user.id,
            status=JobStatus.PENDING,
            source_provider="onedrive",
            dest_provider="google",
            config={}
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/transfers/{job.id}", headers=auth_headers)
        assert response.status_code == 404

    def test_cancel_transfer(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test cancelling a transfer."""
        job = TransferJob(
            user_id=test_user.id,
            status=JobStatus.RUNNING,
            source_provider="onedrive",
            dest_provider="google",
            config={}
        )
        db_session.add(job)
        db_session.commit()

        response = client.post(f"/api/transfers/{job.id}/cancel", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify in database
        db_session.refresh(job)
        assert job.status == JobStatus.CANCELLED

    def test_delete_transfer(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test deleting a completed transfer."""
        job = TransferJob(
            user_id=test_user.id,
            status=JobStatus.COMPLETED,
            source_provider="onedrive",
            dest_provider="google",
            config={}
        )
        db_session.add(job)
        db_session.commit()
        job_id = job.id

        response = client.delete(f"/api/transfers/{job_id}", headers=auth_headers)

        assert response.status_code == 200

        # Verify deletion
        deleted_job = db_session.query(TransferJob).filter_by(id=job_id).first()
        assert deleted_job is None


class TestTransferConfiguration:
    """Test transfer configuration endpoints."""

    def test_update_transfer_config(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test updating transfer configuration."""
        job = TransferJob(
            user_id=test_user.id,
            status=JobStatus.DRAFT,
            source_provider="onedrive",
            dest_provider="google",
            config={}
        )
        db_session.add(job)
        db_session.commit()

        response = client.patch(
            f"/api/transfers/{job.id}/config",
            headers=auth_headers,
            json={
                "file_types": [".pdf", ".docx"],
                "conflict_strategy": "rename_all",
                "folder_exclude": ["temp", "cache"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["config"]["conflict_strategy"] == "rename_all"
        assert ".pdf" in data["config"]["file_types"]

    def test_update_config_invalid_strategy(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test updating config with invalid strategy."""
        job = TransferJob(
            user_id=test_user.id,
            status=JobStatus.DRAFT,
            source_provider="onedrive",
            dest_provider="google",
            config={}
        )
        db_session.add(job)
        db_session.commit()

        response = client.patch(
            f"/api/transfers/{job.id}/config",
            headers=auth_headers,
            json={
                "conflict_strategy": "invalid_strategy"
            }
        )

        assert response.status_code == 422  # Validation error


class TestTransferScheduling:
    """Test transfer scheduling endpoints."""

    def test_schedule_transfer(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test scheduling a transfer."""
        job = TransferJob(
            user_id=test_user.id,
            status=JobStatus.PENDING,
            source_provider="onedrive",
            dest_provider="google",
            config={}
        )
        # Add a test item
        item = TransferItem(
            job_id=job.id,
            source_file_id="file123",
            source_path="test.pdf",
            dest_path="test.pdf",
            status=JobStatus.PENDING,
            size=1024
        )
        job.items.append(item)
        db_session.add(job)
        db_session.commit()

        scheduled_time = datetime.utcnow() + timedelta(hours=2)

        response = client.post(
            f"/api/transfers/{job.id}/schedule",
            headers=auth_headers,
            json={
                "scheduled_for": scheduled_time.isoformat()
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "scheduled"
        assert "scheduled_for" in data

        # Verify in database
        db_session.refresh(job)
        assert job.status == JobStatus.SCHEDULED
        assert job.scheduled_for is not None

    def test_schedule_transfer_no_items(self, client: TestClient, auth_headers, db_session, test_user, connected_accounts):
        """Test scheduling a transfer with no items."""
        job = TransferJob(
            user_id=test_user.id,
            status=JobStatus.PENDING,
            source_provider="onedrive",
            dest_provider="google",
            config={}
        )
        db_session.add(job)
        db_session.commit()

        scheduled_time = datetime.utcnow() + timedelta(hours=2)

        response = client.post(
            f"/api/transfers/{job.id}/schedule",
            headers=auth_headers,
            json={
                "scheduled_for": scheduled_time.isoformat()
            }
        )

        assert response.status_code == 400
        assert "no items" in response.json()["detail"].lower()


class TestAuthFlow:
    """Test complete authentication flow."""

    def test_complete_auth_flow(self, client: TestClient):
        """Test registration -> login -> token refresh flow."""
        # Step 1: Register
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123"
            }
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["email"] == "newuser@example.com"

        # Step 2: Login
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123"
            }
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data

        # Step 3: Access protected endpoint
        access_token = login_data["access_token"]
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == "newuser@example.com"

        # Step 4: Refresh token
        refresh_token = login_data["refresh_token"]
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data

        # New access token should work
        new_access_token = refresh_data["access_token"]
        me_response2 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert me_response2.status_code == 200

    def test_invalid_login(self, client: TestClient, test_user):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    def test_duplicate_registration(self, client: TestClient, test_user):
        """Test registering with existing email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
