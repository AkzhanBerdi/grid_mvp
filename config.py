# config.py
"""Configuration management for Right Bastard Client Service"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Production configuration for Right Bastard Client Service"""

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
    DEFAULT_GRID_LEVELS = 8
    MIN_CAPITAL = 200.0  # Minimum capital to start trading

    # Risk Management
    MAX_BUY_PREMIUM = 0.02  # 2%

    # Performance Settings
    UPDATE_INTERVAL = 30  # seconds between grid updates
    PRICE_CACHE_TIMEOUT = 5  # seconds to cache prices

    # Client Limits
    MAX_CONCURRENT_GRIDS = 5  # Maximum grids per client
    MAX_CLIENTS = 100  # Maximum total clients

    # Monitoring
    PERFORMANCE_LOG_INTERVAL = 300  # Log performance every 5 minutes
    BACKUP_INTERVAL = 86400  # Backup database daily (seconds)

    # DEFAULT_ORDER_SIZE removed - calculated dynamically
    BASE_ORDER_SIZE = 50.0  # Starting point only, not used in calculations
    DEFAULT_GRID_LEVELS = 8
    MIN_ORDER_SIZE = 10.0  # Minimum for exchange compliance
    MAX_ORDER_SIZE_RATIO = 0.1  # Max 10% of capital per order

    # Static risk parameters removed - calculated dynamically
    BASE_GRID_SPACING = 0.025  # Starting point only
    MIN_GRID_SPACING = 0.01  # 1% minimum for safety
    MAX_GRID_SPACING = 0.05  # 5% maximum for effectiveness

    BASE_MAX_LOSS = 0.01  # Starting point only
    MIN_MAX_LOSS = 0.005  # 0.5% minimum
    MAX_MAX_LOSS = 0.02  # 2% maximum

    BASE_RESET_THRESHOLD = 0.15  # Starting point only
    MIN_RESET_THRESHOLD = 0.1  # 10% minimum
    MAX_RESET_THRESHOLD = 0.25  # 25% maximum

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


# FUTURE IMPLEMENTATIONS
class DynamicOrderSizerInterface:
    """Interface for dynamic order sizing - will be implemented by CompoundManager"""

    async def get_current_order_size(
        self, client_id: int, symbol: str, base_capital: float
    ) -> float:
        """Calculate current optimal order size"""
        raise NotImplementedError("Will be implemented by CompoundManager")

    async def get_grid_allocation(self, client_id: int, total_capital: float) -> dict:
        """Calculate dynamic base/enhanced allocation"""
        raise NotImplementedError("Will be implemented by CompoundManager")


class MarketTimingInterface:
    """Interface for dynamic timing - will be implemented by MarketTimer"""

    async def get_next_check_interval(
        self, operation_type: str, symbol: str = None
    ) -> float:
        """Calculate optimal next check interval"""
        raise NotImplementedError("Will be implemented by MarketTimer")

    async def get_api_call_delay(
        self, last_call_time: float, operation_type: str
    ) -> float:
        """Calculate optimal delay between API calls"""
        raise NotImplementedError("Will be implemented by MarketTimer")


class VolatilityRiskInterface:
    """Interface for volatility-based risk - will be implemented by VolatilityOrderSizer"""

    async def get_volatility_adjusted_spacing(
        self, symbol: str, base_spacing: float
    ) -> float:
        """Calculate volatility-adjusted grid spacing"""
        raise NotImplementedError("Will be implemented by VolatilityOrderSizer")

    async def get_volatility_adjusted_order_size(
        self, symbol: str, base_size: float
    ) -> float:
        """Calculate volatility-adjusted order size"""
        raise NotImplementedError("Will be implemented by VolatilityOrderSizer")


class AutoResetInterface:
    """Interface for auto-reset - will be implemented by SmartGridAutoReset"""

    async def should_reset_grid(
        self,
        symbol: str,
        current_price: float,
        grid_config: dict,
        market_conditions: dict,
    ) -> bool:
        """Determine if grid should be automatically reset"""
        raise NotImplementedError("Will be implemented by SmartGridAutoReset")

    async def calculate_new_grid_parameters(
        self, symbol: str, current_price: float
    ) -> dict:
        """Calculate optimal parameters for grid reset"""
        raise NotImplementedError("Will be implemented by SmartGridAutoReset")
