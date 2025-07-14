# config.py
"""Configuration management for GridTrader Pro Client Service"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Production configuration for GridTrader Pro Client Service"""

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    IS_PRODUCTION = ENVIRONMENT == "production"

    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/gridtrader_clients.db")

    # Security
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "change-this-in-production-32chars")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "data/logs/gridtrader_service.log"

    # Trading Configuration
    DEFAULT_TRADING_PAIRS = ["ADA", "AVAX"]

    # Supported symbols with their configurations
    SYMBOL_CONFIG = {
        "ADAUSDT": {
            "min_quantity": 10,
            "quantity_precision": 0,  # Whole numbers
            "price_precision": 8,
            "min_order_value": 10.0,
        },
        "AVAXUSDT": {
            "min_quantity": 0.1,
            "quantity_precision": 3,
            "price_precision": 4,
            "min_order_value": 10.0,
        },
        "BTCUSDT": {
            "min_quantity": 0.00001,
            "quantity_precision": 5,
            "price_precision": 2,
            "min_order_value": 10.0,
        },
        "ETHUSDT": {
            "min_quantity": 0.001,
            "quantity_precision": 3,
            "price_precision": 2,
            "min_order_value": 10.0,
        },
    }

    # Grid Trading Defaults
    DEFAULT_GRID_SPACING = 0.025  # 2.5%
    DEFAULT_GRID_LEVELS = 8
    DEFAULT_ORDER_SIZE = 50.0  # USD per order
    MIN_CAPITAL = 100.0  # Minimum capital to start trading

    # Risk Management
    MAX_LOSS_PER_TRADE = 0.01  # 1%
    MAX_BUY_PREMIUM = 0.02  # 2%
    GRID_RESET_THRESHOLD = 0.15  # 15% price deviation triggers reset

    # Performance Settings
    UPDATE_INTERVAL = 30  # seconds between grid updates
    PRICE_CACHE_TIMEOUT = 5  # seconds to cache prices

    # Client Limits
    MAX_CONCURRENT_GRIDS = 5  # Maximum grids per client
    MAX_CLIENTS = 100  # Maximum total clients

    # Monitoring
    PERFORMANCE_LOG_INTERVAL = 300  # Log performance every 5 minutes
    BACKUP_INTERVAL = 86400  # Backup database daily (seconds)

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_vars = [
            cls.TELEGRAM_BOT_TOKEN,
            cls.ENCRYPTION_KEY,
        ]

        # Check required variables
        if not all(var for var in required_vars):
            return False

        # Validate encryption key length
        if len(cls.ENCRYPTION_KEY) < 16:
            return False

        return True

    @classmethod
    def get_symbol_config(cls, symbol: str) -> dict:
        """Get configuration for a specific symbol"""
        return cls.SYMBOL_CONFIG.get(
            symbol,
            {
                "min_quantity": 0.001,
                "quantity_precision": 3,
                "price_precision": 4,
                "min_order_value": 10.0,
            },
        )
