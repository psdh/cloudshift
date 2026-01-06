"""
Tests for email notification service.
"""

import pytest
from datetime import datetime, timedelta
from app.services.email import EmailService


def test_format_file_size():
    """Test file size formatting."""
    email_service = EmailService()

    assert "500.0 B" in email_service._format_file_size(500)
    assert "1.0 KB" in email_service._format_file_size(1024)
    assert "1.5 KB" in email_service._format_file_size(1536)
    assert "1.0 MB" in email_service._format_file_size(1024 * 1024)
    assert "1.5 GB" in email_service._format_file_size(int(1.5 * 1024 * 1024 * 1024))


def test_format_duration():
    """Test duration formatting."""
    email_service = EmailService()

    start = datetime(2026, 1, 1, 10, 0, 0)

    # Test various durations
    end = start + timedelta(hours=2, minutes=15)
    assert "2 hours 15 minutes" == email_service._format_duration(start, end)

    end = start + timedelta(minutes=45)
    assert "45 minutes" == email_service._format_duration(start, end)

    end = start + timedelta(hours=1)
    assert "1 hour" == email_service._format_duration(start, end)

    end = start + timedelta(seconds=30)
    assert "30 seconds" == email_service._format_duration(start, end)


def test_generate_completion_email_html():
    """Test completion email HTML generation."""
    email_service = EmailService()

    html = email_service._generate_completion_email_html(
        user_name="testuser",
        job_id=123,
        total_files=100,
        total_size=1024 * 1024 * 500,  # 500 MB
        files_transferred=95,
        files_failed=5,
        duration="2 hours 15 minutes",
        source_provider="onedrive",
        dest_provider="google"
    )

    # Check that key elements are present
    assert "Transfer Complete" in html
    assert "Job #123" in html
    assert "testuser" in html
    assert "95" in html  # files transferred
    assert "500.0 MB" in html  # formatted size
    assert "95.0%" in html  # success rate
    assert "2 hours 15 minutes" in html
    assert "Onedrive" in html
    assert "Google" in html
    assert "Failed Files:" in html  # Shows failed count when > 0


def test_generate_completion_email_html_no_failures():
    """Test completion email HTML without failures."""
    email_service = EmailService()

    html = email_service._generate_completion_email_html(
        user_name="testuser",
        job_id=123,
        total_files=100,
        total_size=1024 * 1024 * 100,
        files_transferred=100,
        files_failed=0,
        duration="1 hour 30 minutes",
        source_provider="onedrive",
        dest_provider="google"
    )

    # Should not show failed files section when count is 0
    assert "Failed Files:" not in html
    assert "100.0%" in html  # 100% success rate


def test_generate_failure_email_html():
    """Test failure email HTML generation."""
    email_service = EmailService()

    html = email_service._generate_failure_email_html(
        user_name="testuser",
        job_id=456,
        total_files=100,
        files_attempted=50,
        files_failed=50,
        error_message="Connection timeout to destination provider",
        source_provider="onedrive",
        dest_provider="google"
    )

    # Check that key elements are present
    assert "Transfer Failed" in html
    assert "Job #456" in html
    assert "testuser" in html
    assert "Connection timeout" in html
    assert "100" in html  # total files
    assert "50" in html  # attempted and failed
    assert "Onedrive" in html
    assert "Google" in html
    assert "What to do next:" in html


@pytest.mark.asyncio
async def test_send_email_without_ses_client():
    """Test that send methods return False when SES client not configured."""
    email_service = EmailService()
    # Force SES client to None to simulate missing credentials
    email_service.ses_client = None

    result = await email_service.send_transfer_completion_email(
        to_email="test@example.com",
        job_id=1,
        total_files=10,
        total_size=1024,
        files_transferred=10,
        files_failed=0,
        started_at=datetime.now(),
        completed_at=datetime.now(),
        source_provider="onedrive",
        dest_provider="google"
    )

    assert result is False

    result = await email_service.send_transfer_failure_email(
        to_email="test@example.com",
        job_id=1,
        total_files=10,
        files_attempted=5,
        files_failed=5,
        error_message="Test error",
        source_provider="onedrive",
        dest_provider="google"
    )

    assert result is False
