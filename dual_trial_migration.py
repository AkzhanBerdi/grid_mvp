#!/usr/bin/env python3
"""Database migration for dual trial system"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config


def migrate_to_dual_trial_system():
    """Migrate existing database to support dual trial system"""
    
    print("🔄 MIGRATING TO DUAL TRIAL SYSTEM")
    print("=" * 50)
    
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            # Check if new columns already exist
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            migration_needed = False
            
            # Add new trial columns if they don't exist
            new_columns = [
                ('demo_trial_started', 'DATETIME'),
                ('demo_trial_expires', 'DATETIME'),
                ('real_trial_started', 'DATETIME'),
                ('real_trial_expires', 'DATETIME')
            ]
            
            for column_name, column_type in new_columns:
                if column_name not in columns:
                    print(f"➕ Adding column: {column_name}")
                    conn.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                    migration_needed = True
                else:
                    print(f"✅ Column exists: {column_name}")
            
            if migration_needed:
                print("\n🔄 Migrating existing user data...")
                
                # Migrate existing users with trials to new system
                cursor = conn.execute("""
                    SELECT telegram_id, subscription_status, trial_started, trial_expires,
                           binance_api_key
                    FROM users 
                    WHERE subscription_status = 'trial'
                """)
                
                users_to_migrate = cursor.fetchall()
                
                for user_data in users_to_migrate:
                    telegram_id, sub_status, trial_started, trial_expires, api_key = user_data
                    
                    # Determine if this was demo or real trial
                    is_demo = api_key and 'demo' in api_key.lower()
                    
                    if is_demo:
                        # Migrate to demo trial
                        conn.execute("""
                            UPDATE users SET 
                                subscription_status = 'demo_trial',
                                demo_trial_started = ?,
                                demo_trial_expires = ?
                            WHERE telegram_id = ?
                        """, (trial_started, trial_expires, telegram_id))
                        print(f"📱 Migrated user {telegram_id} to demo trial")
                    else:
                        # Migrate to real trial
                        conn.execute("""
                            UPDATE users SET 
                                subscription_status = 'real_trial',
                                real_trial_started = ?,
                                real_trial_expires = ?
                            WHERE telegram_id = ?
                        """, (trial_started, trial_expires, telegram_id))
                        print(f"💰 Migrated user {telegram_id} to real trial")
                
                print(f"✅ Migrated {len(users_to_migrate)} existing trial users")
                
                # Set up any users with no subscription to be ready for demo trial
                cursor = conn.execute("""
                    UPDATE users SET subscription_status = 'none'
                    WHERE subscription_status IS NULL OR subscription_status = ''
                """)
                
                affected_rows = cursor.rowcount
                if affected_rows > 0:
                    print(f"🔧 Fixed {affected_rows} users with missing subscription status")
                
                print("\n✅ Database migration completed successfully!")
            else:
                print("\n✅ Database already up to date!")
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    return True

def verify_migration():
    """Verify the migration was successful"""
    
    print("\n🔍 VERIFYING MIGRATION")
    print("=" * 30)
    
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            # Check column structure
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            required_columns = [
                'demo_trial_started', 'demo_trial_expires',
                'real_trial_started', 'real_trial_expires'
            ]
            
            for column in required_columns:
                if column in columns:
                    print(f"✅ Column present: {column}")
                else:
                    print(f"❌ Column missing: {column}")
                    return False
            
            # Check subscription statuses
            cursor = conn.execute("""
                SELECT subscription_status, COUNT(*) 
                FROM users 
                GROUP BY subscription_status
            """)
            
            print("\n📊 User distribution by subscription status:")
            for status, count in cursor.fetchall():
                print(f"  {status}: {count} users")
            
            # Check for users ready for demo trial
            cursor = conn.execute("""
                SELECT COUNT(*) FROM users 
                WHERE subscription_status = 'none'
            """)
            
            none_count = cursor.fetchone()[0]
            print(f"\n🎮 Users ready for demo trial: {none_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def create_test_user():
    """Create a test user to verify the system works"""
    
    print("\n🧪 CREATING TEST USER")
    print("=" * 25)
    
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            test_telegram_id = 999999999  # Test user ID
            
            # Check if test user already exists
            cursor = conn.execute(
                "SELECT telegram_id FROM users WHERE telegram_id = ?", 
                (test_telegram_id,)
            )
            
            if cursor.fetchone():
                print(f"🔧 Test user {test_telegram_id} already exists, updating...")
                conn.execute("""
                    UPDATE users SET 
                        subscription_status = 'none',
                        demo_trial_started = NULL,
                        demo_trial_expires = NULL,
                        real_trial_started = NULL,
                        real_trial_expires = NULL,
                        binance_api_key = NULL,
                        binance_secret_key = NULL
                    WHERE telegram_id = ?
                """, (test_telegram_id,))
            else:
                print(f"➕ Creating test user {test_telegram_id}...")
                conn.execute("""
                    INSERT INTO users (
                        telegram_id, username, first_name, subscription_status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    test_telegram_id, "test_user", "Test User", "none",
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
            
            print(f"✅ Test user {test_telegram_id} ready for testing dual trial system")
            print("💡 You can test with this user ID in your bot")
            
    except Exception as e:
        print(f"❌ Test user creation failed: {e}")

if __name__ == "__main__":
    print("🚀 DUAL TRIAL SYSTEM MIGRATION")
    print("=" * 40)
    print("This will upgrade your database to support:")
    print("• 7-day demo trials")
    print("• 7-day real trading trials") 
    print("• Automatic trial progression")
    print("• Auto-stop on expiry")
    print()
    
    # Run migration
    if migrate_to_dual_trial_system():
        # Verify it worked
        if verify_migration():
            print("\n🎉 MIGRATION SUCCESSFUL!")
            
            # Create test user
            create_test_user()
            
            print("\n📋 NEXT STEPS:")
            print("1. Update your handler to use DualTrialHandler")
            print("2. Update your main bot to include trial monitor")
            print("3. Test with the test user (ID: 999999999)")
            print("4. Deploy to production")
            print("\n🚀 Your dual trial system is ready!")
        else:
            print("\n❌ Migration verification failed!")
    else:
        print("\n❌ Migration failed!")
