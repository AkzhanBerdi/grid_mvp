# config.py
"""Configuration management for Right Bastard Client Service"""

import logging
import os
from typing import Dict

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
        # ✅ ADD ETH CONFIGURATION
        "ETHUSDT": {
            "min_quantity": 0.001,
            "quantity_precision": 5,
            "price_precision": 2,  # ETH usually 2 decimals ($3456.78)
            "min_order_value": 10.0,
        },
        # ✅ ADD SOL CONFIGURATION
        "SOLUSDT": {
            "min_quantity": 0.01,
            "quantity_precision": 3,
            "price_precision": 4,  # SOL usually 4 decimals ($123.4567)
            "min_order_value": 10.0,
        },
        "BTCUSDT": {
            "min_quantity": 0.00001,
            "quantity_precision": 5,
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


class ThreeAssetPortfolioManager:
    """Manages ETH (40%), SOL (30%), ADA (30%) portfolio strategy"""

    def __init__(self, total_capital: float):
        self.total_capital = total_capital
        self.logger = logging.getLogger(__name__)

        # Portfolio allocation - Total 30 grids (10 per asset)
        self.portfolio_allocation = {
            "ETHUSDT": {
                "allocation": 0.40,  # 40% of capital
                "capital": total_capital * 0.40,
                "max_grids": 10,  # 10 grids for ETH
                "risk_level": "moderate",
                "rationale": "Blue chip crypto, stable growth",
                "expected_annual_return": "60-100%",
                "order_size_multiplier": 1.0,
            },
            "SOLUSDT": {
                "allocation": 0.30,  # 30% of capital
                "capital": total_capital * 0.30,
                "max_grids": 10,  # 10 grids for SOL
                "risk_level": "moderate-high",
                "rationale": "High-performance blockchain, growth potential",
                "expected_annual_return": "80-120%",
                "order_size_multiplier": 1.1,  # Slightly larger orders
            },
            "ADAUSDT": {
                "allocation": 0.30,  # 30% of capital
                "capital": total_capital * 0.30,
                "max_grids": 10,  # 10 grids for ADA
                "risk_level": "moderate",
                "rationale": "Academic blockchain, steady development",
                "expected_annual_return": "70-110%",
                "order_size_multiplier": 0.9,  # Slightly smaller orders
            },
        }

        # Validate total allocation is 100%
        total_allocation = sum(
            asset["allocation"] for asset in self.portfolio_allocation.values()
        )
        assert abs(total_allocation - 1.0) < 0.001, (
            f"Total allocation must be 100%, got {total_allocation:.1%}"
        )

        self.logger.info(f"💼 Portfolio initialized: ${total_capital:,.2f}")
        self.logger.info(
            f"   🔷 ETH: ${self.portfolio_allocation['ETHUSDT']['capital']:,.2f} (40%)"
        )
        self.logger.info(
            f"   🟣 SOL: ${self.portfolio_allocation['SOLUSDT']['capital']:,.2f} (30%)"
        )
        self.logger.info(
            f"   🔵 ADA: ${self.portfolio_allocation['ADAUSDT']['capital']:,.2f} (30%)"
        )

    def get_asset_configuration(self, symbol: str) -> Dict:
        """Get optimized configuration for specific asset"""
        asset_config = self.portfolio_allocation.get(symbol)

        if not asset_config:
            raise ValueError(f"Unsupported symbol: {symbol}. Supported: ETH, SOL, ADA")

        # Calculate order size per grid (capital / number of grids)
        base_order_size = asset_config["capital"] / asset_config["max_grids"]
        adjusted_order_size = base_order_size * asset_config["order_size_multiplier"]

        # Ensure minimum order size for NOTIONAL compliance
        min_order_size = 25.0  # $25 minimum to avoid NOTIONAL errors
        final_order_size = max(adjusted_order_size, min_order_size)

        # Grid configuration based on asset characteristics
        grid_configs = {
            "ETHUSDT": {
                "grid_levels": 5,  # 5 buy + 5 sell = 10 total
                "grid_spacing": 0.035,  # 3.5% spacing (ETH less volatile)
                "volatility_threshold": 1.20,  # 120% volatility threshold
            },
            "SOLUSDT": {
                "grid_levels": 5,  # 5 buy + 5 sell = 10 total
                "grid_spacing": 0.045,  # 4.5% spacing (SOL more volatile)
                "volatility_threshold": 1.40,  # 140% volatility threshold
            },
            "ADAUSDT": {
                "grid_levels": 5,  # 5 buy + 5 sell = 10 total
                "grid_spacing": 0.040,  # 4.0% spacing (ADA moderate volatility)
                "volatility_threshold": 1.30,  # 130% volatility threshold
            },
        }

        grid_config = grid_configs[symbol]

        return {
            "symbol": symbol,
            "capital": asset_config["capital"],
            "allocation_percentage": asset_config["allocation"] * 100,
            "order_size": final_order_size,
            "grid_levels": grid_config["grid_levels"],
            "grid_spacing": grid_config["grid_spacing"],
            "max_grids": asset_config["max_grids"],
            "volatility_threshold": grid_config["volatility_threshold"],
            "risk_level": asset_config["risk_level"],
            "expected_return": asset_config["expected_annual_return"],
            "rationale": asset_config["rationale"],
        }

    def get_portfolio_summary(self) -> Dict:
        """Get complete portfolio summary"""
        summary = {
            "total_capital": self.total_capital,
            "total_grids": 30,  # 10 per asset
            "assets": {},
            "risk_profile": "Balanced growth with blue-chip focus",
            "expected_annual_return": "70-110%",
            "max_drawdown_estimate": "25-35%",
        }

        for symbol in ["ETHUSDT", "SOLUSDT", "ADAUSDT"]:
            config = self.get_asset_configuration(symbol)
            summary["assets"][symbol] = {
                "allocation": f"{config['allocation_percentage']:.0f}%",
                "capital": f"${config['capital']:,.2f}",
                "grids": config["max_grids"],
                "order_size": f"${config['order_size']:.2f}",
                "expected_return": config["expected_return"],
            }

        return summary
