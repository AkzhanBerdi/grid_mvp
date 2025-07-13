#!/usr/bin/env python3
"""Fix database schema issues"""

import sqlite3
import sys
from pathlib import Path

def check_and_fix_database():
    """Check and fix database schema"""
    db_path = "data/gridtrader.db"
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    print(f"🔍 Checking database: {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if trades table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("✅ Trades table exists")
                
                # Check table structure
                cursor.execute("PRAGMA table_info(trades)")
                columns = cursor.fetchall()
                
                print("📋 Current table structure:")
                for col in columns:
                    print(f"   {col[1]} ({col[2]}) - NULL: {not col[3]}")
                
                # Check if telegram_id column exists and is nullable
                column_names = [col[1] for col in columns]
                
                if 'telegram_id' in column_names:
                    # Check if telegram_id allows NULL
                    telegram_id_info = next((col for col in columns if col[1] == 'telegram_id'), None)
                    if telegram_id_info and telegram_id_info[3]:  # NOT NULL constraint
                        print("⚠️  telegram_id column has NOT NULL constraint - fixing...")
                        
                        # Create new table without NOT NULL constraint on telegram_id
                        cursor.execute("""
                            CREATE TABLE trades_new (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                                symbol TEXT NOT NULL,
                                side TEXT NOT NULL,
                                quantity REAL NOT NULL,
                                price REAL NOT NULL,
                                value REAL NOT NULL,
                                telegram_id INTEGER,
                                profit REAL DEFAULT 0
                            )
                        """)
                        
                        # Copy data from old table
                        cursor.execute("""
                            INSERT INTO trades_new (id, timestamp, symbol, side, quantity, price, value, telegram_id, profit)
                            SELECT id, timestamp, symbol, side, quantity, price, value, NULL, profit
                            FROM trades
                        """)
                        
                        # Drop old table and rename new one
                        cursor.execute("DROP TABLE trades")
                        cursor.execute("ALTER TABLE trades_new RENAME TO trades")
                        
                        print("✅ Fixed telegram_id column constraint")
                    else:
                        print("✅ telegram_id column is properly nullable")
                else:
                    print("✅ No telegram_id column - trades table is compatible")
            else:
                print("⚠️  Trades table doesn't exist - creating...")
                
                # Create proper trades table
                cursor.execute("""
                    CREATE TABLE trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        value REAL NOT NULL,
                        telegram_id INTEGER,
                        profit REAL DEFAULT 0
                    )
                """)
                
                print("✅ Created trades table")
            
            # Verify final structure
            cursor.execute("PRAGMA table_info(trades)")
            final_columns = cursor.fetchall()
            
            print("\n📋 Final table structure:")
            for col in final_columns:
                not_null = "NOT NULL" if col[3] else "NULL"
                print(f"   {col[1]} ({col[2]}) - {not_null}")
            
            print("\n✅ Database schema is now correct!")
            return True
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    """Main function"""
    print("🔧 GridTrader Database Fix")
    print("=" * 40)
    
    if check_and_fix_database():
        print("\n✅ Database is ready!")
        return 0
    else:
        print("\n❌ Database fix failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
