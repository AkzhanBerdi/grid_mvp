#!/usr/bin/env python3
"""
Complete Database Migration Script for GridTrader Pro
=====================================================

Safely migrates existing database to support user registry and performance optimizations.
Fixed indentation and completion issues.
"""

import logging
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from config import Config
except ImportError:
    # Fallback config for migration
    class Config:
        DATABASE_PATH = "data/gridtrader_clients.db"
        ADMIN_TELEGRAM_ID = None


class DatabaseMigrator:
    """Safe database migration with rollback capability"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.backup_path = (
            f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.logger = logging.getLogger(__name__)

        # Ensure database exists
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def create_backup(self) -> bool:
        """Create database backup before migration"""
        try:
            shutil.copy2(self.db_path, self.backup_path)
            self.logger.info(f"✅ Database backup created: {self.backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Backup creation failed: {e}")
            return False

    def check_current_schema(self) -> dict:
        """Check current database schema"""
        schema_info = {"tables": [], "clients_columns": [], "missing_features": []}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                schema_info["tables"] = [row[0] for row in cursor.fetchall()]

                # Get clients table columns
                if "clients" in schema_info["tables"]:
                    cursor.execute("PRAGMA table_info(clients)")
                    schema_info["clients_columns"] = [
                        row[1] for row in cursor.fetchall()
                    ]

                # Check for missing user registry features
                required_columns = [
                    "registration_status",
                    "registration_date",
                    "approved_by",
                    "registration_notes",
                ]

                for col in required_columns:
                    if col not in schema_info["clients_columns"]:
                        schema_info["missing_features"].append(f"clients.{col}")

                # Check for missing tables
                required_tables = ["admin_permissions", "user_activity"]
                for table in required_tables:
                    if table not in schema_info["tables"]:
                        schema_info["missing_features"].append(f"table.{table}")

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
                "name": "Add registration_status column",
                "sql": "ALTER TABLE clients ADD COLUMN registration_status TEXT DEFAULT 'approved'",
                "check": "registration_status",
                "check_type": "column",
            },
            {
                "name": "Add registration_date column",
                "sql": "ALTER TABLE clients ADD COLUMN registration_date DATETIME",
                "check": "registration_date",
                "check_type": "column",
            },
            {
                "name": "Add approved_by column",
                "sql": "ALTER TABLE clients ADD COLUMN approved_by INTEGER",
                "check": "approved_by",
                "check_type": "column",
            },
            {
                "name": "Add registration_notes column",
                "sql": "ALTER TABLE clients ADD COLUMN registration_notes TEXT",
                "check": "registration_notes",
                "check_type": "column",
            },
            # Create admin permissions table
            {
                "name": "Create admin_permissions table",
                "sql": """
                    CREATE TABLE IF NOT EXISTS admin_permissions (
                        telegram_id INTEGER PRIMARY KEY,
                        permission_level TEXT DEFAULT 'admin',
                        granted_by INTEGER,
                        granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (granted_by) REFERENCES admin_permissions (telegram_id)
                    )
                """,
                "check": "admin_permissions",
                "check_type": "table",
            },
            # Create user activity table
            {
                "name": "Create user_activity table",
                "sql": """
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
                "check": "user_activity",
                "check_type": "table",
            },
        ]

        success_count = 0

        for migration in migrations:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Check if migration is needed based on type
                    check_type = migration.get("check_type", "query")

                    if check_type == "column":
                        # Check if column exists in clients table
                        cursor = conn.execute("PRAGMA table_info(clients)")
                        columns = [row[1] for row in cursor.fetchall()]
                        if migration["check"] in columns:
                            self.logger.info(
                                f"⏭️  Skipping existing: {migration['name']}"
                            )
                            success_count += 1
                            continue
                    elif check_type == "table":
                        # Check if table exists
                        cursor = conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                            (migration["check"],),
                        )
                        if cursor.fetchone():
                            self.logger.info(
                                f"⏭️  Skipping existing: {migration['name']}"
                            )
                            success_count += 1
                            continue
                    else:
                        # Legacy query check
                        try:
                            conn.execute(migration["check"])
                            self.logger.info(
                                f"⏭️  Skipping existing: {migration['name']}"
                            )
                            success_count += 1
                            continue
                        except sqlite3.OperationalError:
                            # Migration needed
                            pass

                    # Execute migration
                    conn.execute(migration["sql"])
                    conn.commit()

                    # Verify migration worked
                    if check_type == "column":
                        cursor = conn.execute("PRAGMA table_info(clients)")
                        columns = [row[1] for row in cursor.fetchall()]
                        if migration["check"] not in columns:
                            raise Exception(f"Column {migration['check']} not created")
                    elif check_type == "table":
                        cursor = conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                            (migration["check"],),
                        )
                        if not cursor.fetchone():
                            raise Exception(f"Table {migration['check']} not created")
                    else:
                        conn.execute(migration["check"])

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

        self.logger.info(
            f"✅ User registry migration: {success_count}/{len(migrations)} successful"
        )
        return success_count == len(migrations)

    def create_indexes(self) -> bool:
        """Create performance indexes"""
        self.logger.info("🔄 Creating performance indexes...")

        indexes = [
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

        # Add user activity indexes only if table exists
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='user_activity'"
                )
                if cursor.fetchone():
                    indexes.extend(
                        [
                            "CREATE INDEX IF NOT EXISTS idx_user_activity_client_id ON user_activity(client_id)",
                            "CREATE INDEX IF NOT EXISTS idx_user_activity_type ON user_activity(activity_type)",
                            "CREATE INDEX IF NOT EXISTS idx_user_activity_timestamp ON user_activity(timestamp)",
                        ]
                    )
        except Exception:
            pass

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

        self.logger.info(
            f"✅ Performance indexes: {success_count}/{len(indexes)} created"
        )
        return success_count == len(indexes)

    def add_default_admin(self) -> bool:
        """Add default admin user if configured"""
        if not hasattr(Config, "ADMIN_TELEGRAM_ID") or not Config.ADMIN_TELEGRAM_ID:
            self.logger.warning(
                "⚠️  No ADMIN_TELEGRAM_ID configured, skipping default admin creation"
            )
            return True

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if admin already exists
                cursor = conn.execute(
                    "SELECT 1 FROM admin_permissions WHERE telegram_id = ?",
                    (Config.ADMIN_TELEGRAM_ID,),
                )

                if cursor.fetchone():
                    self.logger.info(
                        f"⏭️  Admin {Config.ADMIN_TELEGRAM_ID} already exists"
                    )
                    return True

                # Add default admin
                conn.execute(
                    """
                    INSERT INTO admin_permissions (telegram_id, permission_level, granted_at)
                    VALUES (?, 'admin', CURRENT_TIMESTAMP)
                """,
                    (Config.ADMIN_TELEGRAM_ID,),
                )

                conn.commit()
                self.logger.info(f"✅ Default admin added: {Config.ADMIN_TELEGRAM_ID}")
                return True

        except Exception as e:
            self.logger.error(f"❌ Error adding default admin: {e}")
            return False

    def migrate_existing_users(self) -> bool:
        """Migrate existing users to new registration system"""
        self.logger.info("🔄 Migrating existing users...")

        try:
            with sqlite3.connect(self.db_path) as conn:
                # First, update any NULL registration_date values
                conn.execute("""
                    UPDATE clients 
                    SET registration_date = COALESCE(created_at, CURRENT_TIMESTAMP)
                    WHERE registration_date IS NULL
                """)

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

                    conn.execute(
                        """
                        UPDATE clients 
                        SET registration_status = 'approved',
                            registration_date = COALESCE(registration_date, created_at, CURRENT_TIMESTAMP),
                            registration_notes = 'Migrated existing user'
                        WHERE telegram_id = ?
                    """,
                        (telegram_id,),
                    )

                conn.commit()
                self.logger.info(
                    f"✅ Migrated {len(existing_users)} existing users to approved status"
                )
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

        verification = {"success": True, "errors": [], "warnings": [], "stats": {}}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check required tables exist
                required_tables = [
                    "clients",
                    "admin_permissions",
                    "user_activity",
                    "trades",
                ]
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]

                for table in required_tables:
                    if table not in existing_tables:
                        verification["errors"].append(f"Missing table: {table}")
                        verification["success"] = False

                # Check required columns in clients table
                required_columns = [
                    "registration_status",
                    "registration_date",
                    "approved_by",
                    "registration_notes",
                ]

                cursor.execute("PRAGMA table_info(clients)")
                existing_columns = [row[1] for row in cursor.fetchall()]

                for column in required_columns:
                    if column not in existing_columns:
                        verification["errors"].append(
                            f"Missing column: clients.{column}"
                        )
                        verification["success"] = False

                # Get migration statistics
                cursor.execute("SELECT COUNT(*) FROM clients")
                verification["stats"]["total_clients"] = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM clients WHERE registration_status = 'approved'"
                )
                verification["stats"]["approved_clients"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM admin_permissions")
                verification["stats"]["admin_users"] = cursor.fetchone()[0]

                # Check for potential issues
                cursor.execute(
                    "SELECT COUNT(*) FROM clients WHERE registration_status IS NULL"
                )
                null_status_count = cursor.fetchone()[0]
                if null_status_count > 0:
                    verification["warnings"].append(
                        f"{null_status_count} clients with NULL registration_status"
                    )

                if verification["stats"]["admin_users"] == 0:
                    verification["warnings"].append("No admin users configured")

                return verification

        except Exception as e:
            verification["success"] = False
            verification["errors"].append(f"Verification failed: {e}")
            return verification

    def rollback_migration(self) -> bool:
        """Rollback migration using backup"""
        if not Path(self.backup_path).exists():
            self.logger.error("❌ No backup found for rollback")
            return False

        try:
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
        self.logger.info(
            f"📋 Current schema: {len(schema_info['tables'])} tables, "
            f"{len(schema_info['missing_features'])} missing features"
        )

        if not schema_info["missing_features"]:
            self.logger.info("✅ Database already up to date!")
            return True

        # Step 3: Run user registry migration
        if not self.migrate_user_registry():
            self.logger.error("❌ User registry migration failed")
            self.rollback_migration()
            return False

        # Step 4: Create performance indexes
        if not self.create_indexes():
            self.logger.warning("⚠️  Some performance indexes failed to create")

        # Step 5: Add default admin
        if not self.add_default_admin():
            self.logger.warning("⚠️  Default admin creation failed")

        # Step 6: Migrate existing users
        if not self.migrate_existing_users():
            self.logger.error("❌ User migration failed")
            self.rollback_migration()
            return False

        # Step 7: Optimize database
        if not self.optimize_database():
            self.logger.warning("⚠️  Database optimization failed")

        # Step 8: Verify migration
        verification = self.verify_migration()

        if verification["success"]:
            self.logger.info("🎉 Database migration completed successfully!")
            self.logger.info(f"📊 Migration stats: {verification['stats']}")

            if verification["warnings"]:
                self.logger.warning("⚠️  Warnings:")
                for warning in verification["warnings"]:
                    self.logger.warning(f"   - {warning}")

            return True
        else:
            self.logger.error("❌ Migration verification failed:")
            for error in verification["errors"]:
                self.logger.error(f"   - {error}")

            self.logger.info("Rolling back migration...")
            self.rollback_migration()
            return False


class MigrationValidator:
    """Additional validation and testing utilities"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

    def test_user_registry_features(self) -> bool:
        """Test user registry functionality after migration"""
        self.logger.info("🧪 Testing user registry features...")

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Test 1: Can we register a new user?
                test_user_id = 999999999  # Test telegram ID

                conn.execute(
                    """
                    INSERT OR REPLACE INTO clients 
                    (telegram_id, username, first_name, registration_status, registration_date)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (test_user_id, "test_user", "Test User", "pending"),
                )

                # Test 2: Can we approve the user?
                conn.execute(
                    """
                    UPDATE clients 
                    SET registration_status = 'approved', 
                        approved_by = ?,
                        registration_notes = 'Test approval'
                    WHERE telegram_id = ?
                """,
                    (
                        Config.ADMIN_TELEGRAM_ID
                        if hasattr(Config, "ADMIN_TELEGRAM_ID")
                        else None,
                        test_user_id,
                    ),
                )

                # Test 3: Can we log user activity?
                conn.execute(
                    """
                    INSERT INTO user_activity 
                    (client_id, activity_type, activity_data)
                    VALUES (?, ?, ?)
                """,
                    (test_user_id, "test_activity", "Migration test"),
                )

                # Test 4: Can we query user registration data?
                cursor = conn.execute(
                    """
                    SELECT registration_status, registration_date, approved_by, registration_notes
                    FROM clients WHERE telegram_id = ?
                """,
                    (test_user_id,),
                )

                user_data = cursor.fetchone()
                if not user_data:
                    raise Exception("Failed to retrieve user registration data")

                # Clean up test data
                conn.execute(
                    "DELETE FROM user_activity WHERE client_id = ?", (test_user_id,)
                )
                conn.execute(
                    "DELETE FROM clients WHERE telegram_id = ?", (test_user_id,)
                )
                conn.commit()

                self.logger.info("✅ User registry features test passed")
                return True

        except Exception as e:
            self.logger.error(f"❌ User registry test failed: {e}")
            return False

    def test_admin_permissions(self) -> bool:
        """Test admin permissions functionality"""
        self.logger.info("🧪 Testing admin permissions...")

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Test admin permissions query
                cursor = conn.execute("""
                    SELECT telegram_id, permission_level, granted_at
                    FROM admin_permissions
                    ORDER BY granted_at DESC
                """)

                admins = cursor.fetchall()
                self.logger.info(f"📋 Found {len(admins)} admin users")

                for admin in admins:
                    self.logger.info(f"   - Admin ID: {admin[0]}, Level: {admin[1]}")

                return True

        except Exception as e:
            self.logger.error(f"❌ Admin permissions test failed: {e}")
            return False

    def generate_migration_report(self) -> dict:
        """Generate comprehensive migration report"""
        self.logger.info("📊 Generating migration report...")

        report = {
            "migration_date": datetime.now().isoformat(),
            "database_path": self.db_path,
            "tables": {},
            "indexes": [],
            "statistics": {},
            "validation_results": {},
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get table information
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]

                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [row[1] for row in cursor.fetchall()]

                    report["tables"][table] = {"row_count": count, "columns": columns}

                # Get index information
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                report["indexes"] = [row[0] for row in cursor.fetchall()]

                # Generate statistics
                if "clients" in tables:
                    cursor.execute(
                        "SELECT registration_status, COUNT(*) FROM clients GROUP BY registration_status"
                    )
                    status_counts = dict(cursor.fetchall())
                    report["statistics"]["user_registration_status"] = status_counts

                if "admin_permissions" in tables:
                    cursor.execute("SELECT COUNT(*) FROM admin_permissions")
                    report["statistics"]["admin_count"] = cursor.fetchone()[0]

                # Run validation tests
                validator = MigrationValidator(self.db_path)
                report["validation_results"]["user_registry_test"] = (
                    validator.test_user_registry_features()
                )
                report["validation_results"]["admin_permissions_test"] = (
                    validator.test_admin_permissions()
                )

                return report

        except Exception as e:
            self.logger.error(f"❌ Report generation failed: {e}")
            report["error"] = str(e)
            return report


def setup_logging():
    """Configure logging for migration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("migration.log"),
        ],
    )


def create_migration_report():
    """Create and save detailed migration report"""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        validator = MigrationValidator()
        report = validator.generate_migration_report()

        # Save report to file
        report_path = (
            f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        import json

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"📊 Migration report saved: {report_path}")

        # Print summary
        logger.info("📋 Migration Summary:")
        logger.info(f"   - Tables: {len(report['tables'])}")
        logger.info(f"   - Indexes: {len(report['indexes'])}")

        if "statistics" in report:
            for key, value in report["statistics"].items():
                logger.info(f"   - {key}: {value}")

        return report_path

    except Exception as e:
        logger.error(f"❌ Report creation failed: {e}")
        return None


def main():
    """Main migration entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("GridTrader Pro Database Migration")
    logger.info("=" * 60)

    try:
        # Initialize migrator
        migrator = DatabaseMigrator()

        # Run migration
        success = migrator.run_full_migration()

        if success:
            logger.info("✅ Migration completed successfully!")
            logger.info(f"📁 Backup saved: {migrator.backup_path}")
            logger.info("🔧 GridTrader Pro is ready with user registry features!")
            return 0
        else:
            logger.error("❌ Migration failed!")
            logger.error("📁 Database restored from backup")
            return 1

    except FileNotFoundError as e:
        logger.error(f"❌ Database file not found: {e}")
        logger.error(
            "💡 Make sure GridTrader Pro has been run at least once to create the database"
        )
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error during migration: {e}")
        logger.error("💡 Check migration.log for detailed error information")
        return 1
    finally:
        logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GridTrader Pro Database Migration")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate migration report without running migration",
    )
    parser.add_argument(
        "--test-only", action="store_true", help="Run validation tests only"
    )
    parser.add_argument("--db-path", type=str, help="Custom database path")

    args = parser.parse_args()

    # Set custom database path if provided
    if args.db_path:
        Config.DATABASE_PATH = args.db_path

    if args.report_only:
        create_migration_report()
        sys.exit(0)
    elif args.test_only:
        setup_logging()
        validator = MigrationValidator()
        success = (
            validator.test_user_registry_features()
            and validator.test_admin_permissions()
        )
        sys.exit(0 if success else 1)
    else:
        sys.exit(main())
