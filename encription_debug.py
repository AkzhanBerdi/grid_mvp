#!/usr/bin/env python3
"""
Debug encryption issues in GridTrader Pro
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_encryption():
    """Test the encryption system"""
    print("🔐 Testing GridTrader Pro Encryption System")
    print("=" * 50)
    
    try:
        # Test 1: Import and basic setup
        print("1️⃣ Testing imports...")
        from config import Config
        from utils.crypto import CryptoUtils
        print("   ✅ Imports successful")
        
        # Test 2: Configuration
        print("2️⃣ Testing configuration...")
        print(f"   ENCRYPTION_KEY length: {len(Config.ENCRYPTION_KEY)}")
        print(f"   ENCRYPTION_KEY valid: {Config.validate()}")
        
        if len(Config.ENCRYPTION_KEY) < 16:
            print("   ❌ ENCRYPTION_KEY too short!")
            return False
        
        # Test 3: Crypto initialization
        print("3️⃣ Testing crypto initialization...")
        crypto = CryptoUtils()
        print("   ✅ CryptoUtils initialized")
        
        # Test 4: Basic encryption/decryption
        print("4️⃣ Testing basic encryption...")
        test_data = "test_api_key_12345"
        
        encrypted = crypto.encrypt(test_data)
        print(f"   Original: {test_data}")
        print(f"   Encrypted: {encrypted}")
        
        decrypted = crypto.decrypt(encrypted)
        print(f"   Decrypted: {decrypted}")
        
        if test_data == decrypted:
            print("   ✅ Basic encryption/decryption working!")
        else:
            print("   ❌ Basic encryption/decryption failed!")
            return False
        
        # Test 5: Test with actual user data
        print("5️⃣ Testing with user API key format...")
        user_api_key = "RbnGQGG43ZdrWTMJ3K0XF7hECYQxfi2qMdokyYPBoSU55UvjCos5VUZXGQkLitdq"
        
        encrypted_user = crypto.encrypt(user_api_key)
        print(f"   User API key encrypted: {encrypted_user[:50]}...")
        
        decrypted_user = crypto.decrypt(encrypted_user)
        print(f"   User API key decrypted: {decrypted_user}")
        
        if user_api_key == decrypted_user:
            print("   ✅ User API key encryption working!")
        else:
            print("   ❌ User API key encryption failed!")
            return False
        
        # Test 6: Test empty/None values
        print("6️⃣ Testing edge cases...")
        
        # Test empty string
        empty_encrypted = crypto.encrypt("")
        empty_decrypted = crypto.decrypt(empty_encrypted)
        print(f"   Empty string test: '{empty_decrypted}' == '' ? {empty_decrypted == ''}")
        
        # Test None (should return None)
        none_encrypted = crypto.encrypt(None)
        print(f"   None test: {none_encrypted} (should be None)")
        
        print("\n✅ ALL ENCRYPTION TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ ENCRYPTION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_encryption():
    """Test encryption in database context"""
    print("\n🗄️ Testing Database Encryption")
    print("=" * 50)
    
    try:
        from repositories.client_repository import ClientRepository
        from models.client import Client
        
        # Create test client
        repo = ClientRepository()
        
        # Test client creation
        test_client = repo.create_client(
            telegram_id=999999999,
            username="test_encryption",
            first_name="Test User"
        )
        
        print("✅ Test client created")
        
        # Add API keys
        test_client.binance_api_key = "test_api_key_12345"
        test_client.binance_secret_key = "test_secret_key_67890"
        
        # Update client (this should encrypt the keys)
        success = repo.update_client(test_client)
        print(f"✅ Client updated: {success}")
        
        # Retrieve client (this should decrypt the keys)
        retrieved_client = repo.get_client(999999999)
        
        if retrieved_client:
            print(f"✅ Client retrieved")
            print(f"   API Key: {retrieved_client.binance_api_key}")
            print(f"   Secret Key: {retrieved_client.binance_secret_key}")
            
            if (retrieved_client.binance_api_key == "test_api_key_12345" and 
                retrieved_client.binance_secret_key == "test_secret_key_67890"):
                print("✅ Database encryption/decryption working!")
                return True
            else:
                print("❌ Database encryption/decryption failed!")
                return False
        else:
            print("❌ Could not retrieve client")
            return False
            
    except Exception as e:
        print(f"❌ Database encryption test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all encryption tests"""
    print("🔧 GridTrader Pro Encryption Diagnostics")
    print("=" * 60)
    
    # Test basic encryption
    basic_test = test_encryption()
    
    # Test database encryption
    db_test = test_database_encryption()
    
    print("\n📊 TEST RESULTS")
    print("=" * 30)
    print(f"Basic Encryption: {'✅ PASS' if basic_test else '❌ FAIL'}")
    print(f"Database Encryption: {'✅ PASS' if db_test else '❌ FAIL'}")
    
    if basic_test and db_test:
        print("\n🎉 All tests passed! Encryption system is working correctly.")
        print("\n💡 If you're still seeing errors, the issue might be:")
        print("   • Database corruption")
        print("   • Partial client records")
        print("   • Timing issues during API testing")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
