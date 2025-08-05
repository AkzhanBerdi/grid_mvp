#!/usr/bin/env python3
"""
Quick API Key Debug Script
==========================
Check what's actually stored in the database
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from repositories.client_repository import ClientRepository

def debug_api_keys():
    """Debug API key storage"""
    
    client_repo = ClientRepository()
    client_id = 485825055  # Your Telegram ID from logs
    
    print("🔍 API KEY DEBUG")
    print("=" * 40)
    
    try:
        client = client_repo.get_client(client_id)
        
        if not client:
            print(f"❌ No client found for ID: {client_id}")
            return
        
        print(f"✅ Client found: {client_id}")
        print(f"   Username: {client.username}")
        print(f"   Status: {client.status}")
        print(f"   Capital: ${client.total_capital}")
        
        # Check API keys
        has_api = bool(client.binance_api_key)
        has_secret = bool(client.binance_secret_key)
        
        print(f"\n🔑 API Key Status:")
        print(f"   API Key exists: {has_api}")
        print(f"   Secret Key exists: {has_secret}")
        
        if has_api:
            print(f"   API Key length: {len(client.binance_api_key)}")
            print(f"   API Key preview: {client.binance_api_key[:20]}...")
        
        if has_secret:
            print(f"   Secret length: {len(client.binance_secret_key)}")
            print(f"   Secret preview: {client.binance_secret_key[:20]}...")
        
        # Test decryption
        print(f"\n🔓 Testing Decryption:")
        try:
            api_key, secret_key = client_repo.get_decrypted_api_keys(client)
            
            print(f"   Decryption successful: {bool(api_key and secret_key)}")
            
            if api_key:
                print(f"   Decrypted API starts with: {api_key[:10]}...")
            if secret_key:
                print(f"   Decrypted secret starts with: {secret_key[:10]}...")
                
        except Exception as e:
            print(f"   ❌ Decryption failed: {e}")
        
        # Check trading readiness
        can_trade = bool(client.binance_api_key and client.binance_secret_key and client.total_capital > 0)
        print(f"\n🚀 Trading Ready: {can_trade}")
        
        if not can_trade:
            issues = []
            if not client.binance_api_key:
                issues.append("Missing API key")
            if not client.binance_secret_key:
                issues.append("Missing secret key")
            if client.total_capital <= 0:
                issues.append("No capital set")
            
            print(f"   Issues: {', '.join(issues)}")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    debug_api_keys()
