# delete_test_user.py - Quick script to remove test user 999999999

import sqlite3
from config import Config

def delete_test_user():
    """Delete test user 999999999 and all associated data"""
    
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT telegram_id, status FROM clients WHERE telegram_id = ?", (999999999,))
            user = cursor.fetchone()
            
            if not user:
                print("✅ Test user 999999999 not found - already deleted")
                return
                
            print(f"📋 Found test user: {user[0]} (status: {user[1]})")
            
            # Delete all related data
            tables_to_clean = [
                ("trades", "client_id"),
                ("grid_orders", "client_id"), 
                ("grid_positions", "client_id"),
                ("fifo_cost_basis", "client_id"),
                ("client_performance", "client_id"),
                ("clients", "telegram_id")  # Delete client record last
            ]
            
            total_deleted = 0
            
            for table, column in tables_to_clean:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = ?", (999999999,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        cursor.execute(f"DELETE FROM {table} WHERE {column} = ?", (999999999,))
                        deleted = cursor.rowcount
                        total_deleted += deleted
                        print(f"🗑️ Deleted {deleted} records from {table}")
                    else:
                        print(f"✅ No records found in {table}")
                        
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        print(f"⚠️ Table {table} doesn't exist - skipping")
                    else:
                        print(f"❌ Error cleaning {table}: {e}")
            
            # Commit all deletions
            conn.commit()
            
            print(f"\n✅ SUCCESS: Deleted test user 999999999")
            print(f"📊 Total records deleted: {total_deleted}")
            print(f"🎯 You should now only receive FIFO status for user 485825055")
            
    except Exception as e:
        print(f"❌ Error deleting test user: {e}")

def verify_remaining_users():
    """Verify which users remain in the database"""
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT telegram_id, status, total_capital FROM clients ORDER BY telegram_id")
            users = cursor.fetchall()
            
            print(f"\n📋 Remaining users in database:")
            print("-" * 50)
            
            if users:
                for user_id, status, capital in users:
                    print(f"👤 User: {user_id}")
                    print(f"   Status: {status}")
                    print(f"   Capital: ${capital}")
                    print()
            else:
                print("No users found in database")
                
    except Exception as e:
        print(f"❌ Error checking users: {e}")

if __name__ == "__main__":
    print("🗑️ DELETING TEST USER 999999999")
    print("=" * 50)
    
    # Show current users
    print("Before deletion:")
    verify_remaining_users()
    
    # Delete test user
    delete_test_user()
    
    # Show remaining users
    print("After deletion:")
    verify_remaining_users()
    
    print("\n💡 Next steps:")
    print("1. Restart your bot service")
    print("2. You should only receive FIFO status for user 485825055")
    print("3. No more duplicate status messages!")

# ALTERNATIVE: Direct SQL commands you can run manually
"""
-- Run these SQL commands directly in your database:

-- Check current users
SELECT telegram_id, status, total_capital FROM clients;

-- Delete test user and all data
DELETE FROM trades WHERE client_id = 999999999;
DELETE FROM grid_orders WHERE client_id = 999999999;
DELETE FROM grid_positions WHERE client_id = 999999999; 
DELETE FROM fifo_cost_basis WHERE client_id = 999999999;
DELETE FROM client_performance WHERE client_id = 999999999;
DELETE FROM clients WHERE telegram_id = 999999999;

-- Verify deletion
SELECT telegram_id, status, total_capital FROM clients;
"""
