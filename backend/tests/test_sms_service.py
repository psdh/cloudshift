"""
Tests for SMS notification service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.sms import SMSService


def test_sms_service_disabled_without_credentials():
    """Test that SMS service is disabled without Twilio credentials."""
    with patch('app.services.sms.settings') as mock_settings:
        mock_settings.TWILIO_ACCOUNT_SID = None

        service = SMSService()
        assert service.enabled is False


def test_sms_service_disabled_on_import_error():
    """Test that SMS service handles missing Twilio package gracefully."""
    with patch('app.services.sms.settings') as mock_settings:
        mock_settings.TWILIO_ACCOUNT_SID = "test_sid"
        mock_settings.TWILIO_AUTH_TOKEN = "test_token"
        mock_settings.TWILIO_PHONE_NUMBER = "+1234567890"

        # Mock import to raise ImportError
        with patch('builtins.__import__', side_effect=ImportError("No module named 'twilio'")):
            service = SMSService()
            # Service should catch ImportError and remain disabled
            assert service.enabled is False


def test_validate_phone_number_valid():
    """Test phone number validation with valid numbers."""
    service = SMSService()

    # Valid formats
    assert service._validate_phone_number("+12345678901") is True
    assert service._validate_phone_number("+44 1234 567890") is True
    assert service._validate_phone_number("+1-234-567-8901") is True
    assert service._validate_phone_number("+1 (234) 567-8901") is True


def test_validate_phone_number_invalid():
    """Test phone number validation with invalid numbers."""
    service = SMSService()

    # Invalid formats
    assert service._validate_phone_number("") is False
    assert service._validate_phone_number(None) is False
    assert service._validate_phone_number("1234567890") is False  # Missing +
    assert service._validate_phone_number("+123") is False  # Too short
    assert service._validate_phone_number("+12345678901234567890") is False  # Too long
    assert service._validate_phone_number("+1234abc5678") is False  # Contains letters


@pytest.mark.asyncio
async def test_send_completion_sms_disabled():
    """Test that SMS is skipped when service is disabled."""
    service = SMSService()
    service.enabled = False

    result = await service.send_transfer_completion_sms(
        to_phone="+12345678901",
        job_id=1,
        total_files=10,
        files_transferred=10,
        files_failed=0,
        source_provider="onedrive",
        dest_provider="google"
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_completion_sms_invalid_phone():
    """Test that SMS fails with invalid phone number."""
    service = SMSService()
    service.enabled = True

    result = await service.send_transfer_completion_sms(
        to_phone="invalid",
        job_id=1,
        total_files=10,
        files_transferred=10,
        files_failed=0,
        source_provider="onedrive",
        dest_provider="google"
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_completion_sms_success():
    """Test successful SMS sending for completion."""
    service = SMSService()
    service.enabled = True

    # Mock Twilio client
    mock_message = Mock()
    mock_message.sid = "SM123456"

    mock_client = Mock()
    mock_client.messages.create.return_value = mock_message
    service.client = mock_client
    service.from_number = "+10987654321"

    result = await service.send_transfer_completion_sms(
        to_phone="+12345678901",
        job_id=1,
        total_files=10,
        files_transferred=10,
        files_failed=0,
        source_provider="onedrive",
        dest_provider="google"
    )

    assert result is True
    mock_client.messages.create.assert_called_once()
    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs['to'] == "+12345678901"
    assert call_args.kwargs['from_'] == "+10987654321"
    assert "Transfer #1 complete" in call_args.kwargs['body']
    assert "10/10 files transferred" in call_args.kwargs['body']


@pytest.mark.asyncio
async def test_send_completion_sms_with_failures():
    """Test SMS content when some files failed."""
    service = SMSService()
    service.enabled = True

    # Mock Twilio client
    mock_message = Mock()
    mock_message.sid = "SM123456"

    mock_client = Mock()
    mock_client.messages.create.return_value = mock_message
    service.client = mock_client
    service.from_number = "+10987654321"

    result = await service.send_transfer_completion_sms(
        to_phone="+12345678901",
        job_id=1,
        total_files=10,
        files_transferred=8,
        files_failed=2,
        source_provider="onedrive",
        dest_provider="google"
    )

    assert result is True
    call_args = mock_client.messages.create.call_args
    assert "complete with errors" in call_args.kwargs['body']
    assert "8 transferred" in call_args.kwargs['body']
    assert "2 failed" in call_args.kwargs['body']


@pytest.mark.asyncio
async def test_send_failure_sms_success():
    """Test successful SMS sending for failure."""
    service = SMSService()
    service.enabled = True

    # Mock Twilio client
    mock_message = Mock()
    mock_message.sid = "SM123456"

    mock_client = Mock()
    mock_client.messages.create.return_value = mock_message
    service.client = mock_client
    service.from_number = "+10987654321"

    result = await service.send_transfer_failure_sms(
        to_phone="+12345678901",
        job_id=1,
        error_reason="Network timeout",
        source_provider="onedrive",
        dest_provider="google"
    )

    assert result is True
    mock_client.messages.create.assert_called_once()
    call_args = mock_client.messages.create.call_args
    assert "Transfer #1 failed" in call_args.kwargs['body']
    assert "Network timeout" in call_args.kwargs['body']


@pytest.mark.asyncio
async def test_send_failure_sms_truncates_long_error():
    """Test that long error messages are truncated in SMS."""
    service = SMSService()
    service.enabled = True

    # Mock Twilio client
    mock_message = Mock()
    mock_message.sid = "SM123456"

    mock_client = Mock()
    mock_client.messages.create.return_value = mock_message
    service.client = mock_client
    service.from_number = "+10987654321"

    long_error = "A" * 150  # 150 character error message

    result = await service.send_transfer_failure_sms(
        to_phone="+12345678901",
        job_id=1,
        error_reason=long_error,
        source_provider="onedrive",
        dest_provider="google"
    )

    assert result is True
    call_args = mock_client.messages.create.call_args
    body = call_args.kwargs['body']
    # Error should be truncated to 100 chars + "..."
    assert "A" * 100 + "..." in body


@pytest.mark.asyncio
async def test_send_sms_handles_twilio_error():
    """Test that Twilio errors are handled gracefully."""
    service = SMSService()
    service.enabled = True

    # Mock Twilio client to raise exception
    mock_client = Mock()
    mock_client.messages.create.side_effect = Exception("Twilio API error")
    service.client = mock_client
    service.from_number = "+10987654321"

    result = await service.send_transfer_completion_sms(
        to_phone="+12345678901",
        job_id=1,
        total_files=10,
        files_transferred=10,
        files_failed=0,
        source_provider="onedrive",
        dest_provider="google"
    )

    # Should return False but not raise exception
    assert result is False
