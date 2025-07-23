# Add this migration script: scripts/migrate_to_enhanced_fifo.py

import sqlite3

from config import Config


def migrate_database():
    """Add initialization flag to trades table"""
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            # Add is_initialization column if it doesn't exist
            try:
                conn.execute(
                    "ALTER TABLE trades ADD COLUMN is_initialization BOOLEAN DEFAULT 0"
                )
                print("✅ Added is_initialization column to trades table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print("✅ is_initialization column already exists")
                else:
                    raise

            print("✅ Database migration completed")

    except Exception as e:
        print(f"❌ Migration error: {e}")


if __name__ == "__main__":
    migrate_database()
