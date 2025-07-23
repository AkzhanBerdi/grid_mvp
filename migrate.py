# scripts/migrate_database_for_pure_usdt.py
"""
Database Migration Script for Pure USDT Grid Integration
=======================================================

This script safely updates your existing database to support:
1. FIFO cost basis tracking
2. Initialization trade flags
3. Enhanced profit calculation tables

Run this BEFORE implementing the Pure USDT system.
"""

import sqlite3
import logging
import os
from datetime import datetime
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handles safe database migration for Pure USDT integration"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def run_complete_migration(self):
        """Run complete database migration with backup"""
        try:
            logger.info("🚀 Starting Database Migration for Pure USDT Integration")
            logger.info("=" * 60)
            
            # Step 1: Create backup
            self._create_backup()
            
            # Step 2: Check current schema
            self._analyze_current_schema()
            
            # Step 3: Run migrations
            self._migrate_trades_table()
            self._create_fifo_cost_basis_table()
            self._create_indexes()
            
            # Step 4: Validate migration
            self._validate_migration()
            
            logger.info("✅ Database migration completed successfully!")
            logger.info(f"📁 Backup created at: {self.backup_path}")
            logger.info("🚀 Ready for Pure USDT Grid Integration!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            logger.info(f"🔄 Restore from backup: {self.backup_path}")
            return False
    
    def _create_backup(self):
        """Create backup of current database"""
        try:
            if os.path.exists(self.db_path):
                import shutil
                shutil.copy2(self.db_path, self.backup_path)
                logger.info(f"✅ Database backup created: {self.backup_path}")
            else:
                logger.info("ℹ️ No existing database found - creating fresh")
                
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            raise
    
    def _analyze_current_schema(self):
        """Analyze current database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if trades table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='trades'
                """)
                
                trades_exists = cursor.fetchone() is not None
                logger.info(f"📊 Trades table exists: {trades_exists}")
                
                if trades_exists:
                    # Get current trades table schema
                    cursor.execute("PRAGMA table_info(trades)")
                    columns = cursor.fetchall()
                    
                    logger.info("📋 Current trades table columns:")
                    for col in columns:
                        logger.info(f"   - {col[1]} ({col[2]})")
                    
                    # Check if is_initialization column exists
                    has_init_column = any(col[1] == 'is_initialization' for col in columns)
                    logger.info(f"🔍 has is_initialization column: {has_init_column}")
                    
                    return {
                        "trades_exists": trades_exists,
                        "has_init_column": has_init_column,
                        "columns": [col[1] for col in columns]
                    }
                else:
                    return {"trades_exists": False}
                    
        except Exception as e:
            logger.error(f"❌ Schema analysis failed: {e}")
            raise
    
    def _migrate_trades_table(self):
        """Migrate trades table to include initialization flag"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if trades table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='trades'
                """)
                
                if not cursor.fetchone():
                    # Create new trades table with all columns
                    logger.info("📋 Creating new trades table...")
                    cursor.execute("""
                        CREATE TABLE trades (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            client_id INTEGER NOT NULL,
                            symbol TEXT NOT NULL,
                            side TEXT NOT NULL,
                            quantity REAL NOT NULL,
                            price REAL NOT NULL,
                            total_value REAL NOT NULL,
                            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            is_initialization BOOLEAN DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    logger.info("✅ Trades table created with all columns")
                else:
                    # Check if is_initialization column exists
                    cursor.execute("PRAGMA table_info(trades)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'is_initialization' not in columns:
                        logger.info("📋 Adding is_initialization column to trades table...")
                        cursor.execute("""
                            ALTER TABLE trades 
                            ADD COLUMN is_initialization BOOLEAN DEFAULT 0
                        """)
                        logger.info("✅ is_initialization column added")
                    else:
                        logger.info("✅ is_initialization column already exists")
                
                # Create index on client_id and symbol for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_client_symbol 
                    ON trades(client_id, symbol)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_executed_at 
                    ON trades(executed_at)
                """)
                
                logger.info("✅ Trades table migration completed")
                
        except Exception as e:
            logger.error(f"❌ Trades table migration failed: {e}")
            raise
    
    def _create_fifo_cost_basis_table(self):
        """Create FIFO cost basis tracking table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                logger.info("📋 Creating FIFO cost basis table...")
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS fifo_cost_basis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        cost_per_unit REAL NOT NULL,
                        total_cost REAL NOT NULL,
                        remaining_quantity REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_initialization BOOLEAN DEFAULT 0,
                        trade_id TEXT,
                        notes TEXT,
                        
                        FOREIGN KEY (client_id) REFERENCES clients(id)
                    )
                """)
                
                logger.info("✅ FIFO cost basis table created")
                
        except Exception as e:
            logger.error(f"❌ FIFO cost basis table creation failed: {e}")
            raise
    
    def _create_indexes(self):
        """Create performance indexes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                logger.info("📋 Creating performance indexes...")
                
                # FIFO cost basis indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_fifo_cost_basis_client_symbol 
                    ON fifo_cost_basis(client_id, symbol)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_fifo_cost_basis_created_at 
                    ON fifo_cost_basis(created_at)
                """)
                
                # Additional trades indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_side 
                    ON trades(side)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_is_initialization 
                    ON trades(is_initialization)
                """)
                
                logger.info("✅ Performance indexes created")
                
        except Exception as e:
            logger.error(f"❌ Index creation failed: {e}")
            raise
    
    def _validate_migration(self):
        """Validate that migration was successful"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                logger.info("🔍 Validating migration...")
                
                # Validate trades table structure
                cursor.execute("PRAGMA table_info(trades)")
                trades_columns = [col[1] for col in cursor.fetchall()]
                
                required_columns = [
                    'id', 'client_id', 'symbol', 'side', 'quantity', 
                    'price', 'total_value', 'executed_at', 'is_initialization'
                ]
                
                missing_columns = [col for col in required_columns if col not in trades_columns]
                if missing_columns:
                    raise Exception(f"Missing columns in trades table: {missing_columns}")
                
                logger.info("✅ Trades table structure validated")
                
                # Validate FIFO cost basis table
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='fifo_cost_basis'
                """)
                
                if not cursor.fetchone():
                    raise Exception("FIFO cost basis table not found")
                
                logger.info("✅ FIFO cost basis table validated")
                
                # Test basic operations
                cursor.execute("SELECT COUNT(*) FROM trades")
                trades_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM fifo_cost_basis")
                cost_basis_count = cursor.fetchone()[0]
                
                logger.info(f"📊 Current data:")
                logger.info(f"   - Trades: {trades_count}")
                logger.info(f"   - Cost basis records: {cost_basis_count}")
                
                logger.info("✅ Migration validation passed")
                
        except Exception as e:
            logger.error(f"❌ Migration validation failed: {e}")
            raise
    
    def rollback_migration(self):
        """Rollback migration using backup"""
        try:
            if os.path.exists(self.backup_path):
                import shutil
                shutil.copy2(self.backup_path, self.db_path)
                logger.info(f"✅ Database rolled back from: {self.backup_path}")
            else:
                logger.error("❌ No backup file found for rollback")
                
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")


def run_migration():
    """Main migration function"""
    print("🚀 GridTrader Pro Database Migration")
    print("=" * 50)
    print("This will update your database for Pure USDT Grid Integration")
    print()
    
    # Get confirmation
    confirm = input("Continue with migration? (y/N): ").lower().strip()
    if confirm != 'y':
        print("❌ Migration cancelled")
        return False
    
    # Run migration
    migrator = DatabaseMigrator()
    success = migrator.run_complete_migration()
    
    if success:
        print()
        print("🎉 Migration completed successfully!")
        print("✅ Your database is ready for Pure USDT Grid Integration")
        print()
        print("Next steps:")
        print("1. Test the updated database")
        print("2. Implement Pure USDT Grid code")
        print("3. Update your handlers and services")
        print("4. Test with small amounts first")
    else:
        print()
        print("❌ Migration failed!")
        print("Check the logs above for details")
        print("Your original database backup is available")
    
    return success


def test_migration():
    """Test the migrated database"""
    try:
        print("🧪 Testing migrated database...")
        
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Test trades table
            cursor.execute("""
                INSERT INTO trades 
                (client_id, symbol, side, quantity, price, total_value, is_initialization)
                VALUES (99999, 'TESTUSDT', 'BUY', 100.0, 1.0, 100.0, 1)
            """)
            
            cursor.execute("""
                SELECT * FROM trades WHERE client_id = 99999
            """)
            test_trade = cursor.fetchone()
            
            if test_trade:
                print("✅ Trades table working correctly")
                
                # Clean up test data
                cursor.execute("DELETE FROM trades WHERE client_id = 99999")
            else:
                print("❌ Trades table test failed")
                return False
            
            # Test FIFO cost basis table
            cursor.execute("""
                INSERT INTO fifo_cost_basis 
                (client_id, symbol, quantity, cost_per_unit, total_cost, remaining_quantity, is_initialization)
                VALUES (99999, 'TESTUSDT', 100.0, 1.0, 100.0, 100.0, 1)
            """)
            
            cursor.execute("""
                SELECT * FROM fifo_cost_basis WHERE client_id = 99999
            """)
            test_cost_basis = cursor.fetchone()
            
            if test_cost_basis:
                print("✅ FIFO cost basis table working correctly")
                
                # Clean up test data
                cursor.execute("DELETE FROM fifo_cost_basis WHERE client_id = 99999")
            else:
                print("❌ FIFO cost basis table test failed")
                return False
            
            print("✅ All database tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


if __name__ == "__main__":
    # Run migration
    success = run_migration()
    
    if success:
        # Test the migration
        print()
        test_success = test_migration()
        
        if test_success:
            print()
            print("🎯 Ready for Pure USDT Grid Integration!")
            print("You can now implement the Pure USDT Grid system.")
        else:
            print()
            print("⚠️ Migration completed but tests failed")
            print("Check database permissions and integrity")
