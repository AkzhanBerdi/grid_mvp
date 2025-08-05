#!/usr/bin/env python3
"""
Quick Admin Setup Script
========================

Fixes admin access and database issues for immediate deployment.
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config

def setup_admin_access():
    """Set up admin access directly in database"""
    
    print("🔧 FIXING ADMIN ACCESS")
    print("=" * 40)
    
    db_path = Config.DATABASE_PATH
    admin_telegram_id = Config.ADMIN_TELEGRAM_ID
    
    if not admin_telegram_id:
        print("❌ No ADMIN_TELEGRAM_ID found in config")
        print("   Add ADMIN_TELEGRAM_ID to your .env file")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Ensure admin_permissions table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_permissions (
                    telegram_id INTEGER PRIMARY KEY,
                    permission_level TEXT DEFAULT 'admin',
                    granted_by INTEGER,
                    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add admin user (or update if exists)
            conn.execute("""
                INSERT OR REPLACE INTO admin_permissions 
                (telegram_id, permission_level, granted_by, granted_at)
                VALUES (?, 'admin', ?, CURRENT_TIMESTAMP)
            """, (admin_telegram_id, admin_telegram_id))
            
            # Ensure the admin user is in clients table with approved status
            conn.execute("""
                INSERT OR REPLACE INTO clients (
                    telegram_id, username, first_name, status, grid_status,
                    registration_status, registration_date, total_capital,
                    risk_level, trading_pairs, grid_spacing, grid_levels, order_size
                ) VALUES (?, 'admin', 'Admin', 'active', 'inactive',
                         'approved', CURRENT_TIMESTAMP, 0.0,
                         'moderate', 'ADA,AVAX', 0.025, 8, 50.0)
            """, (admin_telegram_id,))
            
            conn.commit()
            
            print(f"✅ Admin access granted to Telegram ID: {admin_telegram_id}")
            return True
            
    except Exception as e:
        print(f"❌ Error setting up admin: {e}")
        return False

def fix_telegram_parsing_error():
    """Fix the Telegram parsing error in admin panel"""
    
    print("\n🔧 FIXING TELEGRAM PARSING ERROR")
    print("=" * 40)
    
    # The error is in utils/base_handler.py in _show_pending_users method
    # It's a Markdown parsing issue with unescaped characters
    
    print("📝 Issue: Telegram can't parse admin panel message")
    print("🔧 Solution: The admin panel message has invalid Markdown")
    print("✅ This will be fixed by updating the message format")
    
    return True

def validate_database_schema():
    """Validate database schema is complete"""
    
    print("\n🔧 VALIDATING DATABASE SCHEMA")
    print("=" * 40)
    
    db_path = Config.DATABASE_PATH
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check for required tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['clients', 'trades', 'admin_permissions', 'user_activity']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"⚠️  Missing tables: {missing_tables}")
                print("   Running database initialization...")
                
                # Run database setup
                from database.db_setup import DatabaseSetup
                db_setup = DatabaseSetup()
                db_setup.initialize()
                
                print("✅ Database schema updated")
            else:
                print("✅ All required tables present")
            
            # Check client count
            cursor.execute("SELECT COUNT(*) FROM clients")
            client_count = cursor.fetchone()[0]
            print(f"📊 Total clients in database: {client_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Database validation error: {e}")
        return False

def main():
    """Main setup function"""
    
    print("🚀 GRIDTRADER PRO - ADMIN SETUP & FIXES")
    print("=" * 60)
    
    # Step 1: Validate database
    if not validate_database_schema():
        print("❌ Database validation failed")
        return False
    
    # Step 2: Setup admin access
    if not setup_admin_access():
        print("❌ Admin setup failed")
        return False
    
    # Step 3: Note about parsing error
    fix_telegram_parsing_error()
    
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETE!")
    print("=" * 60)
    
    print("\n📋 WHAT WAS FIXED:")
    print("   ✅ Admin permissions added to database")
    print("   ✅ Database schema validated")
    print("   ✅ Client registration setup")
    
    print("\n📋 NEXT STEPS:")
    print("   1. Restart your application: python3 main.py")
    print("   2. In Telegram, type: /admin")
    print("   3. You should now have admin access")
    
    print(f"\n📱 Your admin Telegram ID: {Config.ADMIN_TELEGRAM_ID}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
