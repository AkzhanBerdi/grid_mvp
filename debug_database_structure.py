#!/usr/bin/env python3
"""Debug database structure and client data"""

import sys
from pathlib import Path
import sqlite3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def debug_database():
    """Debug the database structure and client data"""
    print("🗄️ Database Structure Debug")
    print("=" * 50)
    
    try:
        from config import Config
        
        db_path = Config.DATABASE_PATH
        print(f"Database path: {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            # Check if clients table exists
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("❌ Clients table does not exist!")
                return
            
            print("✅ Clients table exists")
            
            # Get table structure
            cursor = conn.execute("PRAGMA table_info(clients)")
            columns = cursor.fetchall()
            
            print(f"\n📋 Table Structure ({len(columns)} columns):")
            for i, (cid, name, type_, notnull, default, pk) in enumerate(columns):
                print(f"   {i:2d}: {name:20s} {type_:10s} {'NOT NULL' if notnull else ''}")
            
            # Check specific client
            client_id = 485825055
            cursor = conn.execute("SELECT * FROM clients WHERE telegram_id = ?", (client_id,))
            row = cursor.fetchone()
            
            if row:
                print(f"\n👤 Client {client_id} Data ({len(row)} fields):")
                for i, value in enumerate(row):
                    if i < len(columns):
                        col_name = columns[i][1]  # Column name is at index 1
                        if col_name in ['binance_api_key', 'binance_secret_key'] and value:
                            display_value = f"{str(value)[:30]}... (length: {len(str(value))})"
                        else:
                            display_value = str(value)[:50]
                        print(f"   {i:2d}: {col_name:20s} = {display_value}")
                    else:
                        print(f"   {i:2d}: UNKNOWN_COLUMN      = {str(value)[:50]}")
            else:
                print(f"\n❌ No data found for client {client_id}")
            
            # Test the expected query
            print(f"\n🔍 Testing Repository Query:")
            cursor = conn.execute(
                """
                SELECT telegram_id, username, first_name, status, grid_status,
                       created_at, updated_at, total_capital, risk_level,
                       trading_pairs, binance_api_key, binance_secret_key,
                       grid_spacing, grid_levels, order_size
                FROM clients WHERE telegram_id = ?
            """,
                (client_id,)
            )
            
            row = cursor.fetchone()
            if row:
                print(f"✅ Query successful, returned {len(row)} fields")
                expected_fields = [
                    'telegram_id', 'username', 'first_name', 'status', 'grid_status',
                    'created_at', 'updated_at', 'total_capital', 'risk_level',
                    'trading_pairs', 'binance_api_key', 'binance_secret_key',
                    'grid_spacing', 'grid_levels', 'order_size'
                ]
                
                for i, field_name in enumerate(expected_fields):
                    if i < len(row):
                        value = row[i]
                        if field_name in ['binance_api_key', 'binance_secret_key'] and value:
                            display = f"{str(value)[:30]}... (len: {len(str(value))})"
                        else:
                            display = str(value)[:50] if value is not None else "NULL"
                        print(f"   {i:2d}: {field_name:20s} = {display}")
                    else:
                        print(f"   {i:2d}: {field_name:20s} = MISSING!")
            else:
                print("❌ Repository query returned no results")
                
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_database()
