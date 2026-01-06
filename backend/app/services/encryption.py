from cryptography.fernet import Fernet
from typing import Optional
from app.core.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data like OAuth tokens."""

    @staticmethod
    def _get_cipher() -> Fernet:
        """
        Get Fernet cipher instance using the encryption key from settings.

        Returns:
            Fernet: Cipher instance for encryption/decryption
        """
        # Use the encryption key from settings
        # In production, this should be a 32-byte URL-safe base64-encoded key
        # Generate one with: from cryptography.fernet import Fernet; Fernet.generate_key()
        key = settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY
        return Fernet(key)

    @staticmethod
    def encrypt(plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            str: Encrypted string (base64 encoded)
        """
        cipher = EncryptionService._get_cipher()
        encrypted_bytes = cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    @staticmethod
    def decrypt(ciphertext: str) -> Optional[str]:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: The encrypted string to decrypt

        Returns:
            Optional[str]: Decrypted string, or None if decryption fails
        """
        try:
            cipher = EncryptionService._get_cipher()
            decrypted_bytes = cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception:
            # Decryption failed - token may be corrupted or key changed
            return None
