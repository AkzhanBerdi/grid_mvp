#!/usr/bin/env python3
"""Debug the encryption issue for client 485825055"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def debug_client_encryption():
    """Debug the specific client's encryption issue"""
    print("🔍 Debugging Client 485825055 Encryption Issue")
    print("=" * 60)
    
    try:
        from repositories.client_repository import ClientRepository
        from utils.crypto import CryptoUtils
        from config import Config
        
        # Show config info
        print(f"📋 Configuration:")
        print(f"   Encryption key length: {len(Config.ENCRYPTION_KEY)}")
        print(f"   Database path: {Config.DATABASE_PATH}")
        
        # Get client
        repo = ClientRepository()
        client = repo.get_client(485825055)
        
        if not client:
            print("❌ Client 485825055 not found")
            return
        
        print(f"\n👤 Client Info:")
        print(f"   Name: {client.first_name}")
        print(f"   API Key set: {bool(client.binance_api_key)}")
        print(f"   Secret Key set: {bool(client.binance_secret_key)}")
        
        # Show raw encrypted data (safely)
        if client.binance_api_key:
            print(f"\n🔐 Raw Encrypted API Key:")
            print(f"   Length: {len(client.binance_api_key)}")
            print(f"   First 50 chars: {client.binance_api_key[:50]}...")
            print(f"   Last 50 chars: ...{client.binance_api_key[-50:]}")
            
            # Check if it looks like base64
            import string
            b64_chars = string.ascii_letters + string.digits + '+/='
            is_b64_like = all(c in b64_chars for c in client.binance_api_key)
            print(f"   Looks like base64: {is_b64_like}")
        
        # Test crypto utils
        print(f"\n🔧 Testing CryptoUtils:")
        crypto = CryptoUtils()
        
        # Test basic encryption/decryption
        test_data = "test_string_12345"
        try:
            encrypted = crypto.encrypt(test_data)
            decrypted = crypto.decrypt(encrypted)
            basic_test = (test_data == decrypted)
            print(f"   Basic test: {'✅ PASS' if basic_test else '❌ FAIL'}")
            print(f"   Test encrypted: {encrypted[:50]}...")
        except Exception as e:
            print(f"   Basic test: ❌ FAIL - {e}")
            basic_test = False
        
        # Test with client's actual data
        if client.binance_api_key and basic_test:
            print(f"\n🔓 Attempting to decrypt client's API key:")
            try:
                decrypted_api = crypto.decrypt(client.binance_api_key)
                print(f"   ✅ SUCCESS!")
                print(f"   Decrypted length: {len(decrypted_api)}")
                print(f"   First 20 chars: {decrypted_api[:20]}...")
            except Exception as e:
                print(f"   ❌ FAILED: {e}")
                
                # Try manual debugging
                print(f"\n🔬 Manual debugging:")
                try:
                    import base64
                    decoded = base64.urlsafe_b64decode(client.binance_api_key)
                    print(f"   Base64 decode: ✅ SUCCESS ({len(decoded)} bytes)")
                    
                    # Try to decrypt the decoded data
                    try:
                        cipher_suite = crypto._cipher_suite
                        final_decrypt = cipher_suite.decrypt(decoded)
                        result = final_decrypt.decode('utf-8')
                        print(f"   Fernet decrypt: ✅ SUCCESS")
                        print(f"   Final result: {result[:20]}...")
                    except Exception as fernet_err:
                        print(f"   Fernet decrypt: ❌ FAILED - {fernet_err}")
                        
                except Exception as b64_err:
                    print(f"   Base64 decode: ❌ FAILED - {b64_err}")
        
        # Check database raw data
        print(f"\n🗄️ Checking database raw data:")
        try:
            import sqlite3
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.execute(
                    "SELECT binance_api_key, binance_secret_key FROM clients WHERE telegram_id = ?",
                    (485825055,)
                )
                row = cursor.fetchone()
                if row:
                    db_api_key = row[0]
                    db_secret_key = row[1]
                    print(f"   DB API key: {bool(db_api_key)} ({len(db_api_key) if db_api_key else 0} chars)")
                    print(f"   DB Secret key: {bool(db_secret_key)} ({len(db_secret_key) if db_secret_key else 0} chars)")
                    
                    # Compare with client object
                    if db_api_key == client.binance_api_key:
                        print(f"   ✅ Client object matches database")
                    else:
                        print(f"   ❌ Client object differs from database")
                        print(f"   DB first 50: {db_api_key[:50] if db_api_key else 'None'}...")
                        print(f"   Client first 50: {client.binance_api_key[:50] if client.binance_api_key else 'None'}...")
                else:
                    print(f"   ❌ No database record found")
        except Exception as db_err:
            print(f"   ❌ Database check failed: {db_err}")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_client_encryption()
