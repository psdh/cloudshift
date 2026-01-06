import pytest
from app.models.connected_account import ConnectedAccount, CloudProvider
from app.services.encryption import EncryptionService


def test_cloud_provider_enum():
    """Test CloudProvider enum values."""
    assert CloudProvider.ONEDRIVE.value == "onedrive"
    assert CloudProvider.GOOGLE_DRIVE.value == "google_drive"


def test_encryption_service():
    """Test token encryption and decryption."""
    plaintext = "test_oauth_token_12345"

    # Encrypt the token
    encrypted = EncryptionService.encrypt(plaintext)

    # Verify encrypted token is different from plaintext
    assert encrypted != plaintext
    assert len(encrypted) > 0

    # Decrypt the token
    decrypted = EncryptionService.decrypt(encrypted)

    # Verify decryption works
    assert decrypted == plaintext


def test_encryption_decryption_failure():
    """Test that invalid ciphertext returns None."""
    invalid_ciphertext = "invalid_token_data"
    decrypted = EncryptionService.decrypt(invalid_ciphertext)
    assert decrypted is None


def test_connected_account_model_structure():
    """Test that ConnectedAccount model has required attributes."""
    # This tests the model structure without database
    account = ConnectedAccount(
        user_id=1,
        provider=CloudProvider.ONEDRIVE,
        access_token="encrypted_access_token",
        refresh_token="encrypted_refresh_token",
        account_email="test@onedrive.com"
    )

    assert account.user_id == 1
    assert account.provider == CloudProvider.ONEDRIVE
    assert account.access_token == "encrypted_access_token"
    assert account.refresh_token == "encrypted_refresh_token"
    assert account.account_email == "test@onedrive.com"
