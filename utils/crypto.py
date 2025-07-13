# utils/crypto.py
"""Encryption utilities for secure data storage"""

import base64
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import Config


class CryptoUtils:
    """Encryption utilities for sensitive data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cipher_suite = self._get_cipher_suite()

    def _get_cipher_suite(self):
        """Generate cipher suite from config key"""
        try:
            # Use config key to generate Fernet key
            password = Config.ENCRYPTION_KEY.encode()
            salt = b"salt_1234567890"  # In production, use random salt per user
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            return Fernet(key)
        except Exception as e:
            self.logger.error(f"Error initializing encryption: {e}")
            raise

    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        try:
            if not data:
                return data

            encrypted_data = self._cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            self.logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        try:
            if not encrypted_data:
                return encrypted_data

            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            raise
