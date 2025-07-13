# Fix for database/db_setup.py
"""Database setup with fixed imports"""

import logging
import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from config import Config


class DatabaseSetup:
    """Database initialization and schema management"""

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

            # Create users table
            self._create_users_table(conn)

            # Create analytics tables
            self._create_analytics_tables(conn)

            # Create trading tables
            self._create_trading_tables(conn)

            # Create indexes for performance
            self._create_indexes(conn)

        self.logger.info("Database initialized successfully")

    def _create_users_table(self, conn):
        """Create users table"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                subscription_status TEXT DEFAULT 'none',
                bot_status TEXT DEFAULT 'inactive',
                trial_started DATETIME,
                trial_expires DATETIME,
                total_capital REAL DEFAULT 0.0,
                risk_level TEXT DEFAULT 'moderate',
                trading_pairs TEXT DEFAULT 'ADA',
                binance_api_key TEXT,
                binance_secret_key TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _create_analytics_tables(self, conn):
        """Create analytics tables"""
        # User events for conversion tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        """)

        # Conversion funnel tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversion_funnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, step_name),
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        """)

    def _create_trading_tables(self, conn):
        """Create trading-related tables"""
        # Individual trades
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                value REAL NOT NULL,
                profit REAL DEFAULT 0.0,
                order_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        """)

        # Bot instances tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                status TEXT DEFAULT 'inactive',
                config TEXT,
                started_at DATETIME,
                stopped_at DATETIME,
                error_message TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        """)

    def _create_indexes(self, conn):
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_telegram_id ON user_events(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_type ON user_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_trades_telegram_id ON trades(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_funnel_telegram_id ON conversion_funnel(telegram_id)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)


# Initialize database on import
if __name__ == "__main__":
    db_setup = DatabaseSetup()
    db_setup.initialize()
