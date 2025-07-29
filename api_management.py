#!/usr/bin/env python3
"""
API Key Management Script for GridTrader Bot
Safely removes old API keys and adds new ones
"""

import logging
import sqlite3
import sys
from pathlib import Path

from config import Config
from repositories.client_repository import ClientRepository
from utils.crypto import CryptoUtils

INVALID_ID = "❌ Invalid Telegram ID"
CANCELLED_OPERATION = "❌ Operation cancelled"

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class APIKeyManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.crypto_utils = CryptoUtils()
        self.client_repo = ClientRepository()
        self.logger = logging.getLogger(__name__)
        
        # Ensure database exists
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    def list_clients_with_api_keys(self):
        """List all clients that have API keys"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT telegram_id, username, first_name, 
                           binance_api_key IS NOT NULL as has_api_key,
                           binance_secret_key IS NOT NULL as has_secret_key,
                           status, created_at
                    FROM clients 
                    ORDER BY telegram_id
                """)
                
                clients = cursor.fetchall()
                
                print("\n" + "="*80)
                print("CLIENTS WITH API KEYS")
                print("="*80)
                print(f"{'ID':<12} {'Username':<15} {'Name':<15} {'API':<5} {'Secret':<6} {'Status':<10} {'Created'}")
                print("-"*80)
                
                for client in clients:
                    telegram_id, username, first_name, has_api, has_secret, status, created = client
                    api_status = "✅" if has_api else "❌"
                    secret_status = "✅" if has_secret else "❌"
                    created_date = created[:10] if created else "Unknown"
                    
                    print(f"{telegram_id:<12} {username or 'N/A':<15} {first_name or 'N/A':<15} "
                          f"{api_status:<5} {secret_status:<6} {status:<10} {created_date}")
                
                return clients
                
        except Exception as e:
            self.logger.error(f"Error listing clients: {e}")
            return []
    
    def remove_api_keys(self, telegram_id: int = None):
        """Remove API keys for specific client or all clients"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if telegram_id:
                    # Remove for specific client
                    cursor = conn.execute(
                        "SELECT username, first_name FROM clients WHERE telegram_id = ?",
                        (telegram_id,)
                    )
                    client_info = cursor.fetchone()
                    
                    if not client_info:
                        print(f"❌ Client {telegram_id} not found")
                        return False
                    
                    username, first_name = client_info
                    print(f"\n🗑️  Removing API keys for: {first_name} (@{username}) - ID: {telegram_id}")
                    
                    conn.execute("""
                        UPDATE clients 
                        SET binance_api_key = NULL, 
                            binance_secret_key = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE telegram_id = ?
                    """, (telegram_id,))
                    
                    print(f"✅ API keys removed for client {telegram_id}")
                    
                else:
                    # Remove for all clients
                    print("\n🗑️  Removing ALL API keys from database...")
                    
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM clients WHERE binance_api_key IS NOT NULL"
                    )
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        print("ℹ️  No API keys found to remove")
                        return True
                    
                    confirm = input(f"⚠️  This will remove API keys from {count} clients. Continue? (yes/no): ")
                    if confirm.lower() != 'yes':
                        print(CANCELLED_OPERATION)
                        return False
                    
                    conn.execute("""
                        UPDATE clients 
                        SET binance_api_key = NULL, 
                            binance_secret_key = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE binance_api_key IS NOT NULL OR binance_secret_key IS NOT NULL
                    """)
                    
                    print(f"✅ API keys removed from {count} clients")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error removing API keys: {e}")
            print(f"❌ Error removing API keys: {e}")
            return False
    
    def add_api_keys(self, telegram_id: int, api_key: str, secret_key: str):
        """Add new API keys for a client"""
        try:
            # Validate inputs
            if not api_key or len(api_key) < 20:
                print("❌ Invalid API key format")
                return False
            
            if not secret_key or len(secret_key) < 20:
                print("❌ Invalid secret key format")
                return False
            
            # Check if client exists
            client = self.client_repo.get_client(telegram_id)
            if not client:
                print(f"❌ Client {telegram_id} not found")
                return False
            
            # Encrypt the keys
            print("🔐 Encrypting API keys...")
            encrypted_api_key = self.crypto_utils.encrypt(api_key)
            encrypted_secret_key = self.crypto_utils.encrypt(secret_key)
            
            # Test decryption to ensure keys work
            print("🧪 Testing encryption/decryption...")
            test_api = self.crypto_utils.decrypt(encrypted_api_key)
            test_secret = self.crypto_utils.decrypt(encrypted_secret_key)
            
            if test_api != api_key or test_secret != secret_key:
                print("❌ Encryption test failed")
                return False
            
            print("✅ Encryption test passed")
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE clients 
                    SET binance_api_key = ?, 
                        binance_secret_key = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """, (encrypted_api_key, encrypted_secret_key, telegram_id))
            
            print(f"✅ API keys successfully added for client {telegram_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding API keys: {e}")
            print(f"❌ Error adding API keys: {e}")
            return False
    
    def verify_api_keys(self, telegram_id: int = None):
        """Verify API keys can be decrypted properly"""
        try:
            clients_to_check = []
            
            if telegram_id:
                client = self.client_repo.get_client(telegram_id)
                if client:
                    clients_to_check = [client]
            else:
                # Check all clients with API keys
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT telegram_id FROM clients 
                        WHERE binance_api_key IS NOT NULL
                    """)
                    client_ids = [row[0] for row in cursor.fetchall()]
                    clients_to_check = [self.client_repo.get_client(cid) for cid in client_ids]
                    clients_to_check = [c for c in clients_to_check if c]  # Filter None
            
            print("\n🔍 VERIFYING API KEYS")
            print("="*50)
            
            for client in clients_to_check:
                print(f"\nClient: {client.first_name} (ID: {client.telegram_id})")
                
                if not client.binance_api_key or not client.binance_secret_key:
                    print("  ❌ No API keys found")
                    continue
                
                try:
                    # Test decryption
                    decrypted_api = self.crypto_utils.decrypt(client.binance_api_key)
                    decrypted_secret = self.crypto_utils.decrypt(client.binance_secret_key)
                    
                    if decrypted_api and decrypted_secret:
                        print(f"  ✅ API keys valid (lengths: {len(decrypted_api)}, {len(decrypted_secret)})")
                    else:
                        print("  ❌ Decryption returned empty keys")
                        
                except Exception as e:
                    print(f"  ❌ Decryption failed: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying API keys: {e}")
            print(f"❌ Error verifying API keys: {e}")
            return False
    
    def purge_database(self):
        """Completely purge all API keys and optionally reset database"""
        print("\n🚨 DATABASE PURGE OPTIONS")
        print("="*40)
        print("1. Remove API keys only")
        print("2. Remove API keys + reset all client settings")
        print("3. Remove API keys + delete all clients")
        print("4. Cancel")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "4":
            print(CANCELLED_OPERATION)
            return False
        
        # Final confirmation
        confirm = input("\n⚠️  This is irreversible! Type 'PURGE' to confirm: ")
        if confirm != "PURGE":
            print(CANCELLED_OPERATION)
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                if choice == "1":
                    # Remove API keys only
                    conn.execute("""
                        UPDATE clients 
                        SET binance_api_key = NULL, 
                            binance_secret_key = NULL,
                            updated_at = CURRENT_TIMESTAMP
                    """)
                    print("✅ All API keys removed")
                    
                elif choice == "2":
                    # Reset all client settings
                    conn.execute("""
                        UPDATE clients 
                        SET binance_api_key = NULL, 
                            binance_secret_key = NULL,
                            total_capital = 0.0,
                            trading_pairs = 'ADA,AVAX',
                            grid_status = 'inactive',
                            updated_at = CURRENT_TIMESTAMP
                    """)
                    print("✅ All API keys and settings reset")
                    
                elif choice == "3":
                    # Delete all clients
                    conn.execute("DELETE FROM clients")
                    print("✅ All clients deleted")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error purging database: {e}")
            print(f"❌ Error purging database: {e}")
            return False


def main():
    """Interactive CLI for API key management"""
    print("🔑 GridTrader API Key Manager")
    print("="*40)
    
    try:
        manager = APIKeyManager()
        
        while True:
            print("\n📋 MENU:")
            print("1. List clients with API keys")
            print("2. Remove API keys (specific client)")
            print("3. Remove ALL API keys")
            print("4. Add new API keys")
            print("5. Verify API keys")
            print("6. Purge database")
            print("7. Exit")
            
            choice = input("\nSelect option (1-7): ").strip()
            
            if choice == "1":
                manager.list_clients_with_api_keys()
                
            elif choice == "2":
                telegram_id = input("Enter Telegram ID: ").strip()
                try:
                    telegram_id = int(telegram_id)
                    manager.remove_api_keys(telegram_id)
                except ValueError:
                    print(INVALID_ID)
                    
            elif choice == "3":
                manager.remove_api_keys()
                
            elif choice == "4":
                telegram_id = input("Enter Telegram ID: ").strip()
                api_key = input("Enter API Key: ").strip()
                secret_key = input("Enter Secret Key: ").strip()
                
                try:
                    telegram_id = int(telegram_id)
                    manager.add_api_keys(telegram_id, api_key, secret_key)
                except ValueError:
                    print(INVALID_ID)
                    
            elif choice == "5":
                telegram_id_input = input("Enter Telegram ID (or press Enter for all): ").strip()
                telegram_id = None
                if telegram_id_input:
                    try:
                        telegram_id = int(telegram_id_input)
                    except ValueError:
                        print(INVALID_ID)
                        continue
                manager.verify_api_keys(telegram_id)
                
            elif choice == "6":
                manager.purge_database()
                
            elif choice == "7":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid option")
                
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    main()
