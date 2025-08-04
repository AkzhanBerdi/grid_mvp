#!/usr/bin/env python3
# scripts/migrate_database.py
"""
Database Migration Script for GridTrader Pro
Safely migrates existing database to support user registry and performance optimizations
"""

import logging
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config


class DatabaseMigrator:
    """Safe database migration with rollback capability"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger = logging.getLogger(__name__)
        
        # Ensure database exists
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    def create_backup(self) -> bool:
        """Create database backup before migration"""
        try:
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            self.logger.info(f"✅ Database backup created: {self.backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error adding default admin: {e}")
            return False
    
    def migrate_existing_users(self) -> bool:
        """Migrate existing users to new registration system"""
        self.logger.info("🔄 Migrating existing users...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all existing clients without registration status
                cursor = conn.execute("""
                    SELECT telegram_id, username, first_name, created_at 
                    FROM clients 
                    WHERE registration_status IS NULL OR registration_status = ''
                """)
                
                existing_users = cursor.fetchall()
                
                if not existing_users:
                    self.logger.info("⏭️  No existing users to migrate")
                    return True
                
                # Update existing users to approved status
                for user in existing_users:
                    telegram_id, username, first_name, created_at = user
                    
                    conn.execute("""
                        UPDATE clients 
                        SET registration_status = 'approved',
                            registration_date = COALESCE(created_at, CURRENT_TIMESTAMP),
                            registration_notes = 'Migrated existing user'
                        WHERE telegram_id = ?
                    """, (telegram_id,))
                
                conn.commit()
                self.logger.info(f"✅ Migrated {len(existing_users)} existing users to approved status")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error migrating existing users: {e}")
            return False
    
    def optimize_database(self) -> bool:
        """Optimize database performance"""
        self.logger.info("🔄 Optimizing database performance...")
        
        optimizations = [
            "PRAGMA optimize",
            "VACUUM",
            "ANALYZE",
        ]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for optimization in optimizations:
                    self.logger.debug(f"Running: {optimization}")
                    conn.execute(optimization)
                    conn.commit()
                
                self.logger.info("✅ Database optimization completed")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Database optimization failed: {e}")
            return False
    
    def verify_migration(self) -> dict:
        """Verify migration was successful"""
        self.logger.info("🔍 Verifying migration...")
        
        verification = {
            'success': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check required tables exist
                required_tables = ['clients', 'admin_permissions', 'user_activity', 'trades']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                for table in required_tables:
                    if table not in existing_tables:
                        verification['errors'].append(f"Missing table: {table}")
                        verification['success'] = False
                
                # Check required columns in clients table
                required_columns = [
                    'registration_status', 'registration_date', 
                    'approved_by', 'registration_notes'
                ]
                
                cursor.execute("PRAGMA table_info(clients)")
                existing_columns = [row[1] for row in cursor.fetchall()]
                
                for column in required_columns:
                    if column not in existing_columns:
                        verification['errors'].append(f"Missing column: clients.{column}")
                        verification['success'] = False
                
                # Get migration statistics
                cursor.execute("SELECT COUNT(*) FROM clients")
                verification['stats']['total_clients'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM clients WHERE registration_status = 'approved'")
                verification['stats']['approved_clients'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM admin_permissions")
                verification['stats']['admin_users'] = cursor.fetchone()[0]
                
                # Check for potential issues
                cursor.execute("SELECT COUNT(*) FROM clients WHERE registration_status IS NULL")
                null_status_count = cursor.fetchone()[0]
                if null_status_count > 0:
                    verification['warnings'].append(f"{null_status_count} clients with NULL registration_status")
                
                if verification['stats']['admin_users'] == 0:
                    verification['warnings'].append("No admin users configured")
                
                return verification
                
        except Exception as e:
            verification['success'] = False
            verification['errors'].append(f"Verification failed: {e}")
            return verification
    
    def rollback_migration(self) -> bool:
        """Rollback migration using backup"""
        if not Path(self.backup_path).exists():
            self.logger.error("❌ No backup found for rollback")
            return False
        
        try:
            import shutil
            shutil.copy2(self.backup_path, self.db_path)
            self.logger.info(f"✅ Database rolled back from: {self.backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Rollback failed: {e}")
            return False
    
    def run_full_migration(self) -> bool:
        """Run complete migration process"""
        self.logger.info("🚀 Starting database migration for GridTrader Pro...")
        
        # Step 1: Create backup
        if not self.create_backup():
            self.logger.error("❌ Migration aborted: Backup creation failed")
            return False
        
        # Step 2: Check current schema
        schema_info = self.check_current_schema()
        self.logger.info(f"📋 Current schema: {len(schema_info['tables'])} tables, "
                        f"{len(schema_info['missing_features'])} missing features")
        
        if not schema_info['missing_features']:
            self.logger.info("✅ Database already up to date!")
            return True
        
        # Step 3: Run migrations
        migration_steps = [
            ("User Registry", self.migrate_user_registry),
            ("Performance Indexes", self.create_indexes),
            ("Default Admin", self.add_default_admin),
            ("Existing Users", self.migrate_existing_users),
            ("Database Optimization", self.optimize_database)
        ]
        
        for step_name, step_function in migration_steps:
            self.logger.info(f"🔄 Running: {step_name}")
            if not step_function():
                self.logger.error(f"❌ Migration failed at: {step_name}")
                
                # Ask for rollback
                rollback = input(f"\n❌ Migration failed at {step_name}. Rollback? (y/N): ").lower()
                if rollback == 'y':
                    self.rollback_migration()
                return False
        
        # Step 4: Verify migration
        verification = self.verify_migration()
        
        if verification['success']:
            self.logger.info("🎉 Migration completed successfully!")
            self.logger.info(f"📊 Migration stats: {verification['stats']}")
            
            if verification['warnings']:
                self.logger.warning("⚠️  Warnings:")
                for warning in verification['warnings']:
                    self.logger.warning(f"  • {warning}")
            
            return True
        else:
            self.logger.error("❌ Migration verification failed!")
            for error in verification['errors']:
                self.logger.error(f"  • {error}")
            
            # Ask for rollback
            rollback = input("\n❌ Verification failed. Rollback? (y/N): ").lower()
            if rollback == 'y':
                self.rollback_migration()
            return False


class PerformanceAnalyzer:
    """Analyze database performance and suggest optimizations"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
    
    def analyze_performance(self) -> dict:
        """Analyze current database performance"""
        analysis = {
            'database_size_mb': 0,
            'table_sizes': {},
            'index_usage': {},
            'slow_queries': [],
            'recommendations': []
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                analysis['database_size_mb'] = round(db_size / (1024 * 1024), 2)
                
                # Table sizes
                tables = ['clients', 'trades', 'grid_instances', 'grid_orders', 'user_activity']
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        analysis['table_sizes'][table] = count
                    except sqlite3.OperationalError:
                        analysis['table_sizes'][table] = 0
                
                # Check for missing indexes
                if analysis['table_sizes']['trades'] > 1000:
                    analysis['recommendations'].append("Consider partitioning trades table by date")
                
                if analysis['table_sizes']['user_activity'] > 10000:
                    analysis['recommendations'].append("Implement user_activity cleanup policy")
                
                if analysis['database_size_mb'] > 100:
                    analysis['recommendations'].append("Consider implementing database archiving")
                
                # Performance recommendations
                if analysis['table_sizes']['trades'] > 500:
                    analysis['recommendations'].append("Enable async trade recording for better performance")
                
                return analysis
                
        except Exception as e:
            self.logger.error(f"❌ Performance analysis failed: {e}")
            return analysis
    
    def generate_performance_report(self) -> str:
        """Generate human-readable performance report"""
        analysis = self.analyze_performance()
        
        report = f"""
📊 Database Performance Analysis
================================

📁 Database Size: {analysis['database_size_mb']} MB

📋 Table Sizes:
"""
        
        for table, size in analysis['table_sizes'].items():
            report += f"  • {table}: {size:,} records\n"
        
        if analysis['recommendations']:
            report += f"\n💡 Recommendations:\n"
            for rec in analysis['recommendations']:
                report += f"  • {rec}\n"
        else:
            report += f"\n✅ Performance looks good!\n"
        
        return report


def main():
    """Main migration script"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('migration.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    print("🚀 GridTrader Pro Database Migration Tool")
    print("=" * 50)
    
    try:
        # Initialize migrator
        migrator = DatabaseMigrator()
        
        # Show current status
        schema_info = migrator.check_current_schema()
        print(f"📋 Current Database:")
        print(f"  • Tables: {len(schema_info['tables'])}")
        print(f"  • Missing Features: {len(schema_info['missing_features'])}")
        
        if schema_info['missing_features']:
            print("\n🔧 Missing Features:")
            for feature in schema_info['missing_features']:
                print(f"  • {feature}")
        
        # Performance analysis
        analyzer = PerformanceAnalyzer()
        performance_report = analyzer.generate_performance_report()
        print(performance_report)
        
        # Ask for confirmation
        if schema_info['missing_features']:
            proceed = input(f"\n🚀 Proceed with migration? (y/N): ").lower()
            if proceed != 'y':
                print("❌ Migration cancelled by user")
                return
        else:
            print("✅ Database is already up to date!")
            return
        
        # Run migration
        success = migrator.run_full_migration()
        
        if success:
            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. Update your handlers to use EnhancedClientHandler")
            print("2. Configure ADMIN_TELEGRAM_ID in your environment")
            print("3. Test the registration flow")
            print("4. Consider implementing async database operations")
        else:
            print("\n❌ Migration failed!")
            print("Check the logs for details")
    
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
            self.logger.error(f"❌ Backup creation failed: {e}")
            return False
    
    def check_current_schema(self) -> dict:
        """Check current database schema"""
        schema_info = {
            'tables': [],
            'clients_columns': [],
            'missing_features': []
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                schema_info['tables'] = [row[0] for row in cursor.fetchall()]
                
                # Get clients table columns
                if 'clients' in schema_info['tables']:
                    cursor.execute("PRAGMA table_info(clients)")
                    schema_info['clients_columns'] = [row[1] for row in cursor.fetchall()]
                
                # Check for missing user registry features
                required_columns = [
                    'registration_status', 'registration_date', 
                    'approved_by', 'registration_notes'
                ]
                
                for col in required_columns:
                    if col not in schema_info['clients_columns']:
                        schema_info['missing_features'].append(f"clients.{col}")
                
                # Check for missing tables
                required_tables = ['admin_permissions', 'user_activity']
                for table in required_tables:
                    if table not in schema_info['tables']:
                        schema_info['missing_features'].append(f"table.{table}")
                
                return schema_info
                
        except Exception as e:
            self.logger.error(f"❌ Schema check failed: {e}")
            return schema_info
    
    def migrate_user_registry(self) -> bool:
        """Migrate database to support user registry"""
        self.logger.info("🔄 Migrating user registry features...")
        
        migrations = [
            # Add registration fields to clients table
            {
                'name': 'Add registration_status column',
                'sql': "ALTER TABLE clients ADD COLUMN registration_status TEXT DEFAULT 'approved'",
                'check': "SELECT registration_status FROM clients LIMIT 1"
            },
            {
                'name': 'Add registration_date column',
                'sql': "ALTER TABLE clients ADD COLUMN registration_date DATETIME DEFAULT CURRENT_TIMESTAMP",
                'check': "SELECT registration_date FROM clients LIMIT 1"
            },
            {
                'name': 'Add approved_by column',
                'sql': "ALTER TABLE clients ADD COLUMN approved_by INTEGER",
                'check': "SELECT approved_by FROM clients LIMIT 1"
            },
            {
                'name': 'Add registration_notes column',
                'sql': "ALTER TABLE clients ADD COLUMN registration_notes TEXT",
                'check': "SELECT registration_notes FROM clients LIMIT 1"
            },
            
            # Create admin permissions table
            {
                'name': 'Create admin_permissions table',
                'sql': """
                    CREATE TABLE IF NOT EXISTS admin_permissions (
                        telegram_id INTEGER PRIMARY KEY,
                        permission_level TEXT DEFAULT 'admin',
                        granted_by INTEGER,
                        granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (granted_by) REFERENCES admin_permissions (telegram_id)
                    )
                """,
                'check': "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_permissions'"
            },
            
            # Create user activity table
            {
                'name': 'Create user_activity table',
                'sql': """
                    CREATE TABLE IF NOT EXISTS user_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER NOT NULL,
                        activity_type TEXT NOT NULL,
                        activity_data TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (client_id) REFERENCES clients (telegram_id)
                    )
                """,
                'check': "SELECT name FROM sqlite_master WHERE type='table' AND name='user_activity'"
            }
        ]
        
        success_count = 0
        
        for migration in migrations:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # First check if migration is needed
                    try:
                        conn.execute(migration['check'])
                        self.logger.info(f"⏭️  Skipping existing: {migration['name']}")
                        success_count += 1
                        continue
                    except sqlite3.OperationalError:
                        # Migration needed
                        pass
                    
                    # Execute migration
                    conn.execute(migration['sql'])
                    conn.commit()
                    
                    # Verify migration worked
                    conn.execute(migration['check'])
                    
                    self.logger.info(f"✅ {migration['name']}")
                    success_count += 1
                    
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e) or "already exists" in str(e):
                    self.logger.info(f"⏭️  Already exists: {migration['name']}")
                    success_count += 1
                else:
                    self.logger.error(f"❌ {migration['name']}: {e}")
            except Exception as e:
                self.logger.error(f"❌ {migration['name']}: {e}")
        
        self.logger.info(f"✅ User registry migration: {success_count}/{len(migrations)} successful")
        return success_count == len(migrations)
    
    def create_indexes(self) -> bool:
        """Create performance indexes"""
        self.logger.info("🔄 Creating performance indexes...")
        
        indexes = [
            # User activity indexes
            "CREATE INDEX IF NOT EXISTS idx_user_activity_client_id ON user_activity(client_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_activity_type ON user_activity(activity_type)",
            "CREATE INDEX IF NOT EXISTS idx_user_activity_timestamp ON user_activity(timestamp)",
            
            # Enhanced client indexes
            "CREATE INDEX IF NOT EXISTS idx_clients_registration_status ON clients(registration_status)",
            "CREATE INDEX IF NOT EXISTS idx_clients_registration_date ON clients(registration_date)",
            "CREATE INDEX IF NOT EXISTS idx_clients_approved_by ON clients(approved_by)",
            
            # Existing performance indexes (if missing)
            "CREATE INDEX IF NOT EXISTS idx_trades_client_symbol ON trades(client_id, symbol)",
            "CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side)",
            "CREATE INDEX IF NOT EXISTS idx_trades_is_initialization ON trades(is_initialization)",
            
            # Grid performance indexes
            "CREATE INDEX IF NOT EXISTS idx_grid_instances_client_symbol ON grid_instances(client_id, symbol)",
            "CREATE INDEX IF NOT EXISTS idx_grid_orders_status ON grid_orders(status)",
        ]
        
        success_count = 0
        
        for index_sql in indexes:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(index_sql)
                    conn.commit()
                    success_count += 1
                    self.logger.debug(f"✅ Index created: {index_sql[:50]}...")
            except Exception as e:
                self.logger.error(f"❌ Index creation failed: {e}")
        
        self.logger.info(f"✅ Performance indexes: {success_count}/{len(indexes)} created")
        return success_count == len(indexes)
    
    def add_default_admin(self) -> bool:
        """Add default admin user if configured"""
        if not hasattr(Config, 'ADMIN_TELEGRAM_ID') or not Config.ADMIN_TELEGRAM_ID:
            self.logger.warning("⚠️  No ADMIN_TELEGRAM_ID configured, skipping default admin creation")
            return True
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if admin already exists
                cursor = conn.execute(
                    "SELECT 1 FROM admin_permissions WHERE telegram_id = ?",
                    (Config.ADMIN_TELEGRAM_ID,)
                )
                
                if cursor.fetchone():
                    self.logger.info(f"⏭️  Admin {Config.ADMIN_TELEGRAM_ID} already exists")
                    return True
                
                # Add default admin
                conn.execute("""
                    INSERT INTO admin_permissions (telegram_id, permission_level, granted_at)
                    VALUES (?, 'admin', CURRENT_TIMESTAMP)
                """, (Config.ADMIN_TELEGRAM_ID,))
                
                conn.commit()
                self.logger.info(f"✅ Default admin added: {Config.ADMIN_TELEGRAM_ID}")
                return True
                
        except Exception as e:
