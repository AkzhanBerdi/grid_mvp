# database/db_setup.py
"""Simplified database setup for client grid trading service"""

import logging
import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from config import Config


class DatabaseSetup:
    """Database initialization for simplified grid trading service"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Initialize all database tables"""
        self.logger.info("Initializing database...")

        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")

            # Create clients table
            self._create_clients_table(conn)

            # Create trading tables
            self._create_trading_tables(conn)

            # Create analytics tables
            self._create_analytics_tables(conn)

            # Create indexes for performance
            self._create_indexes(conn)

        self.logger.info("Database initialized successfully")

    def _create_clients_table(self, conn):
        """Create clients table"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                status TEXT DEFAULT 'active',
                grid_status TEXT DEFAULT 'inactive',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- Trading Configuration
                total_capital REAL DEFAULT 0.0,
                risk_level TEXT DEFAULT 'moderate',
                trading_pairs TEXT DEFAULT 'ADA,AVAX',
                
                -- API Credentials (encrypted)
                binance_api_key TEXT,
                binance_secret_key TEXT,
                
                -- Grid Settings
                grid_spacing REAL DEFAULT 0.025,
                grid_levels INTEGER DEFAULT 8,
                order_size REAL DEFAULT 50.0
            )
        """)

    def _create_trading_tables(self, conn):
        """Create trading-related tables"""

        # Grid orders table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS grid_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                order_id TEXT NOT NULL,
                grid_level INTEGER NOT NULL,
                status TEXT DEFAULT 'PLACED',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                filled_at DATETIME,
                FOREIGN KEY (client_id) REFERENCES clients (telegram_id)
            )
        """)

        # Executed trades table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                total_value REAL NOT NULL,
                order_id TEXT,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                profit REAL DEFAULT 0.0,
                FOREIGN KEY (client_id) REFERENCES clients (telegram_id)
            )
        """)

        # Grid instances tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS grid_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                status TEXT DEFAULT 'inactive',
                center_price REAL,
                grid_spacing REAL,
                grid_levels INTEGER,
                order_size REAL,
                started_at DATETIME,
                stopped_at DATETIME,
                total_trades INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0.0,
                UNIQUE(client_id, symbol),
                FOREIGN KEY (client_id) REFERENCES clients (telegram_id)
            )
        """)

    def _create_analytics_tables(self, conn):
        """Create analytics and monitoring tables"""

        # Client events for activity tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS client_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (telegram_id)
            )
        """)

        # System performance metrics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Daily summary statistics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                active_clients INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                total_volume REAL DEFAULT 0.0,
                total_profit REAL DEFAULT 0.0,
                active_grids INTEGER DEFAULT 0,
                UNIQUE(date)
            )
        """)

    def _create_indexes(self, conn):
        """Create database indexes for performance"""
        indexes = [
            # Client indexes
            "CREATE INDEX IF NOT EXISTS idx_clients_telegram_id ON clients(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status)",
            # Grid orders indexes
            "CREATE INDEX IF NOT EXISTS idx_grid_orders_client_id ON grid_orders(client_id)",
            "CREATE INDEX IF NOT EXISTS idx_grid_orders_symbol ON grid_orders(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_grid_orders_order_id ON grid_orders(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_grid_orders_status ON grid_orders(status)",
            # Trades indexes
            "CREATE INDEX IF NOT EXISTS idx_trades_client_id ON trades(client_id)",
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at)",
            # Grid instances indexes
            "CREATE INDEX IF NOT EXISTS idx_grid_instances_client_id ON grid_instances(client_id)",
            "CREATE INDEX IF NOT EXISTS idx_grid_instances_symbol ON grid_instances(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_grid_instances_status ON grid_instances(status)",
            # Events indexes
            "CREATE INDEX IF NOT EXISTS idx_client_events_client_id ON client_events(client_id)",
            "CREATE INDEX IF NOT EXISTS idx_client_events_type ON client_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_client_events_timestamp ON client_events(timestamp)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

    def add_sample_data(self):
        """Add sample data for testing (development only)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Add sample client (for testing)
                conn.execute("""
                    INSERT OR IGNORE INTO clients (
                        telegram_id, username, first_name, total_capital,
                        trading_pairs, grid_spacing, grid_levels, order_size
                    ) VALUES (
                        123456789, 'testuser', 'Test User', 1000.0,
                        'ADA,AVAX', 0.025, 8, 50.0
                    )
                """)

                self.logger.info("Sample data added for testing")

        except Exception as e:
            self.logger.error(f"Error adding sample data: {e}")

    def get_database_stats(self):
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # Count clients
                cursor = conn.execute("SELECT COUNT(*) FROM clients")
                stats["total_clients"] = cursor.fetchone()[0]

                # Count active clients
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM clients WHERE status = 'active'"
                )
                stats["active_clients"] = cursor.fetchone()[0]

                # Count total trades
                cursor = conn.execute("SELECT COUNT(*) FROM trades")
                stats["total_trades"] = cursor.fetchone()[0]

                # Count active grids
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM grid_instances WHERE status = 'active'"
                )
                stats["active_grids"] = cursor.fetchone()[0]

                return stats

        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}

    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to maintain performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Clean old events
                conn.execute(
                    """
                    DELETE FROM client_events 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep)
                )

                # Clean old system metrics
                conn.execute(
                    """
                    DELETE FROM system_metrics 
                    WHERE recorded_at < datetime('now', '-{} days')
                """.format(days_to_keep)
                )

                # Keep trades but clean very old ones
                conn.execute(
                    """
                    DELETE FROM trades 
                    WHERE executed_at < datetime('now', '-{} days')
                """.format(days_to_keep * 2)
                )  # Keep trades longer

                self.logger.info(f"Cleaned up data older than {days_to_keep} days")

        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")

    def backup_database(self, backup_path: str = None):
        """Create database backup"""
        try:
            if not backup_path:
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"data/backups/gridtrader_backup_{timestamp}.db"

            # Ensure backup directory exists
            Path(backup_path).parent.mkdir(parents=True, exist_ok=True)

            # Create backup
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)

            self.logger.info(f"Database backed up to {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"Error backing up database: {e}")
            return None


# Initialize database on import
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Database management for GridTrader Pro"
    )
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--backup", action="store_true", help="Backup database")
    parser.add_argument(
        "--cleanup", type=int, metavar="DAYS", help="Cleanup data older than DAYS"
    )
    parser.add_argument(
        "--sample", action="store_true", help="Add sample data for testing"
    )

    args = parser.parse_args()

    db_setup = DatabaseSetup()

    if args.init:
        db_setup.initialize()
        print("✅ Database initialized")

    if args.stats:
        stats = db_setup.get_database_stats()
        print("📊 Database Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")

    if args.backup:
        backup_path = db_setup.backup_database()
        if backup_path:
            print(f"✅ Database backed up to {backup_path}")

    if args.cleanup:
        db_setup.cleanup_old_data(args.cleanup)
        print(f"✅ Cleaned up data older than {args.cleanup} days")

    if args.sample:
        db_setup.add_sample_data()
        print("✅ Sample data added")

    if not any(vars(args).values()):
        # Default action
        db_setup.initialize()
        print("✅ Database initialized (default action)")
