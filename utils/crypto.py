# utils/crypto.py - Fixed version with better error handling

"""Enhanced encryption utilities with detailed error handling"""

import base64
import logging
import traceback

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CryptoUtils:
    """Enhanced encryption utilities for API keys with better error handling"""

    def __init__(self, encryption_key: str = None):
        self.logger = logging.getLogger(__name__)

        if encryption_key:
            self.encryption_key = encryption_key
        else:
            from config import Config

            self.encryption_key = Config.ENCRYPTION_KEY

        self._cipher_suite = self._get_cipher_suite()

    def _get_cipher_suite(self):
        """Generate cipher suite from encryption key"""
        try:
            # Use the encryption key to generate Fernet key
            password = self.encryption_key.encode()

            # Use a fixed salt for consistency
            salt = b"gridtrader_salt_2024"

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
                self.logger.debug("Empty data provided for encryption")
                return data

            self.logger.debug(f"Encrypting data of length: {len(data)}")
            encrypted_data = self._cipher_suite.encrypt(data.encode("utf-8"))
            result = base64.urlsafe_b64encode(encrypted_data).decode("utf-8")
            self.logger.debug(f"Encryption successful, result length: {len(result)}")
            return result

        except Exception as e:
            self.logger.error(f"Encryption error: {e}")
            self.logger.error(f"Encryption traceback: {traceback.format_exc()}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data with detailed error handling"""
        try:
            if not encrypted_data:
                self.logger.debug("Empty encrypted data provided for decryption")
                return encrypted_data

            self.logger.debug(f"Decrypting data of length: {len(encrypted_data)}")
            self.logger.debug(
                f"Encrypted data first 50 chars: {encrypted_data[:50]}..."
            )

            # Step 1: Decode from base64
            try:
                decoded_data = base64.urlsafe_b64decode(encrypted_data.encode("utf-8"))
                self.logger.debug(
                    f"Base64 decode successful, length: {len(decoded_data)}"
                )
            except Exception as decode_error:
                self.logger.error(f"Base64 decode error: {decode_error}")
                raise ValueError(f"Invalid base64 data: {decode_error}")

            # Step 2: Decrypt with Fernet
            try:
                decrypted_data = self._cipher_suite.decrypt(decoded_data)
                self.logger.debug(
                    f"Fernet decrypt successful, length: {len(decrypted_data)}"
                )
            except Exception as fernet_error:
                self.logger.error(f"Fernet decrypt error: {fernet_error}")
                raise ValueError(f"Fernet decryption failed: {fernet_error}")

            # Step 3: Decode to string
            try:
                result = decrypted_data.decode("utf-8")
                self.logger.debug(
                    f"Final decode successful, result length: {len(result)}"
                )
                return result
            except Exception as utf8_error:
                self.logger.error(f"UTF-8 decode error: {utf8_error}")
                raise ValueError(f"UTF-8 decoding failed: {utf8_error}")

        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            self.logger.error(f"Decryption traceback: {traceback.format_exc()}")
            self.logger.error(
                f"Input data: {encrypted_data[:100] if encrypted_data else 'None'}..."
            )
            raise

    def safe_decrypt(self, encrypted_data: str) -> tuple:
        """Safe decryption that returns (success, result, error)"""
        try:
            result = self.decrypt(encrypted_data)
            return True, result, None
        except Exception as e:
            error_msg = str(e)
            self.logger.warning(f"Safe decrypt failed: {error_msg}")
            return False, None, error_msg

    def test_encryption_cycle(self, test_data: str = "test_api_key_12345") -> bool:
        """Test complete encryption/decryption cycle"""
        try:
            self.logger.info(f"Testing encryption cycle with: {test_data}")

            # Encrypt
            encrypted = self.encrypt(test_data)
            self.logger.info(f"Encrypted: {encrypted[:50]}...")

            # Decrypt
            decrypted = self.decrypt(encrypted)
            self.logger.info(f"Decrypted: {decrypted}")

            # Compare
            success = test_data == decrypted
            self.logger.info(f"Encryption cycle test: {'PASS' if success else 'FAIL'}")
            return success

        except Exception as e:
            self.logger.error(f"Encryption cycle test failed: {e}")
            return False


# Create a debug function to test the current client's encrypted data
def debug_client_encryption(client_id: int):
    """Debug function to test client's encrypted data"""
    print(f"🔍 Debugging encryption for client {client_id}")
    print("=" * 50)

    try:
        # Import required modules
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent))

        from repositories.client_repository import ClientRepository
        from utils.crypto import CryptoUtils

        # Get client
        repo = ClientRepository()
        client = repo.get_client(client_id)

        if not client:
            print(f"❌ Client {client_id} not found")
            return

        print(f"✅ Client found: {client.first_name}")
        print(f"   API Key set: {bool(client.binance_api_key)}")
        print(f"   Secret Key set: {bool(client.binance_secret_key)}")

        if client.binance_api_key:
            print(f"   Encrypted API Key (first 50): {client.binance_api_key[:50]}...")
            print(f"   Encrypted API Key length: {len(client.binance_api_key)}")

        # Test crypto utils
        crypto = CryptoUtils()

        # Test basic encryption first
        test_success = crypto.test_encryption_cycle()
        print(f"✅ Basic encryption test: {'PASS' if test_success else 'FAIL'}")

        if client.binance_api_key:
            print("\n🔓 Testing client API key decryption...")
            success, result, error = crypto.safe_decrypt(client.binance_api_key)

            if success:
                print("✅ API Key decryption successful!")
                print(f"   Decrypted length: {len(result)}")
                print(f"   First 20 chars: {result[:20]}...")
            else:
                print(f"❌ API Key decryption failed: {error}")

                # Try to understand the format
                try:
                    import base64

                    decoded = base64.urlsafe_b64decode(client.binance_api_key)
                    print(f"   Base64 decode successful, length: {len(decoded)}")
                except Exception as decode_err:
                    print(f"   Base64 decode failed: {decode_err}")

        if client.binance_secret_key:
            print("\n🔓 Testing client secret key decryption...")
            success, result, error = crypto.safe_decrypt(client.binance_secret_key)

            if success:
                print("✅ Secret Key decryption successful!")
                print(f"   Decrypted length: {len(result)}")
            else:
                print(f"❌ Secret Key decryption failed: {error}")

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Test with the specific client ID from the logs
    debug_client_encryption(485825055)
