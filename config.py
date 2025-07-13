# config.py
"""Configuration management for GridTrader Pro MVP"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))

    # Binance Configuration (for admin testing)
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    IS_PRODUCTION = ENVIRONMENT == "production"
    IS_TESTNET = not IS_PRODUCTION

    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/gridtrader.db")

    # Security
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "default-key-change-in-production")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "data/logs/gridtrader.log"

    # Trading Configuration
    DEFAULT_TRADING_PAIRS = {
        "ADA": {"symbol": "ADAUSDT", "precision": 0, "min_order_size": 10.0},
        "AVAX": {"symbol": "AVAXUSDT", "precision": 2, "min_order_size": 0.1},
    }

    # Risk Management
    RISK_LEVELS = {
        "conservative": {"grid_spacing": 0.01, "grid_levels": 5},
        "moderate": {"grid_spacing": 0.02, "grid_levels": 8},
        "aggressive": {"grid_spacing": 0.03, "grid_levels": 10},
    }

    # Subscription Plans
    SUBSCRIPTION_PLANS = {
        "trial": {"duration_days": 7, "price": 0},
        "starter": {"price": 29, "features": ["2_pairs", "basic_support"]},
        "pro": {
            "price": 49,
            "features": ["unlimited_pairs", "priority_support", "analytics"],
        },
        "enterprise": {
            "price": 99,
            "features": ["multiple_bots", "custom_strategies", "dedicated_support"],
        },
    }

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_vars = [
            cls.TELEGRAM_BOT_TOKEN,
        ]
        return all(var is not None for var in required_vars)
