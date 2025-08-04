# config.py
# root directory
"""Configuration management for Right Bastard Client Service"""

import os
from typing import Dict

from dotenv import load_dotenv

load_dotenv()
import logging


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

    # ✅ USER REGISTRY SETTINGS
    AUTO_APPROVE_USERS = os.getenv("AUTO_APPROVE_USERS", "false").lower() == "true"
    REQUIRE_ADMIN_APPROVAL = not AUTO_APPROVE_USERS  # Inverse of auto_approve
    MAX_PENDING_USERS = int(os.getenv("MAX_PENDING_USERS", "50"))
    USER_REGISTRATION_ENABLED = (
        os.getenv("USER_REGISTRATION_ENABLED", "true").lower() == "true"
    )
    ADMIN_NOTIFICATION_ON_REGISTRATION = (
        os.getenv("ADMIN_NOTIFICATION_ON_REGISTRATION", "true").lower() == "true"
    )

    # Registration messages
    REGISTRATION_WELCOME_MESSAGE = os.getenv(
        "REGISTRATION_WELCOME_MESSAGE",
        "Welcome to GridTrader Pro! Your registration is pending approval. You will be notified once approved.",
    )
    REGISTRATION_APPROVED_MESSAGE = os.getenv(
        "REGISTRATION_APPROVED_MESSAGE",
        "🎉 Congratulations! Your GridTrader Pro account has been approved. You can now start trading!",
    )
    REGISTRATION_DENIED_MESSAGE = os.getenv(
        "REGISTRATION_DENIED_MESSAGE",
        "Sorry, your GridTrader Pro registration was not approved. Please contact support for more information.",
    )

    @classmethod
    def get_setting(cls, setting_name: str, default_value=None):
        """
        Get a configuration setting with a default value
        This method provides a unified way to access configuration values
        """
        # Check if the setting exists as a class attribute
        if hasattr(cls, setting_name):
            return getattr(cls, setting_name)

        # Check environment variables (useful for deployment flexibility)
        env_value = os.getenv(setting_name)
        if env_value is not None:
            # Try to convert to appropriate type based on default value
            if isinstance(default_value, bool):
                return env_value.lower() in ("true", "1", "yes", "on")
            elif isinstance(default_value, int):
                try:
                    return int(env_value)
                except ValueError:
                    return default_value
            elif isinstance(default_value, float):
                try:
                    return float(env_value)
                except ValueError:
                    return default_value
            else:
                return env_value

        # Return default value if setting not found
        return default_value

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


class SingleGridPortfolioManager:
    """
    Updated Portfolio Manager for Single Advanced Grid Architecture
    Handles ETH (40%), SOL (35%), ADA (25%) allocation with inventory management
    """

    def __init__(self, total_capital: float = 2400.0):
        self.total_capital = total_capital
        self.logger = logging.getLogger(__name__)

        # Updated allocation strategy with inventory management
        self.portfolio_allocation = {
            "ETHUSDT": {
                "allocation_pct": 0.40,  # 40% = $960 for $2400
                "total_capital": total_capital * 0.40,
                "usdt_reserve": total_capital * 0.20,  # 50% of allocation in USDT
                "asset_reserve": total_capital * 0.20,  # 50% of allocation in ETH
                "grid_levels": 10,  # 5 buy + 5 sell
                "grid_spacing": 0.025,  # 2.5% - ETH less volatile
                "order_size_base": total_capital * 0.04,  # $96 per order for $2400
                "risk_level": "conservative",
                "volatility_threshold": 1.20,
                "rationale": "Blue chip crypto - ETF inflows, institutional adoption, lowest volatility",
                "expected_annual_return": "60-100%",
            },
            "SOLUSDT": {
                "allocation_pct": 0.35,  # 35% = $840 for $2400
                "total_capital": total_capital * 0.35,
                "usdt_reserve": total_capital * 0.175,  # 50% of allocation in USDT
                "asset_reserve": total_capital * 0.175,  # 50% of allocation in SOL
                "grid_levels": 10,  # 5 buy + 5 sell
                "grid_spacing": 0.030,  # 3.0% - SOL more volatile
                "order_size_base": total_capital * 0.035,  # $84 per order for $2400
                "risk_level": "moderate-aggressive",
                "volatility_threshold": 1.40,
                "rationale": "Growth driver - High-performance blockchain, DeFi ecosystem, memecoin platform",
                "expected_annual_return": "80-120%",
            },
            "ADAUSDT": {
                "allocation_pct": 0.25,  # 25% = $600 for $2400
                "total_capital": total_capital * 0.25,
                "usdt_reserve": total_capital * 0.125,  # 50% of allocation in USDT
                "asset_reserve": total_capital * 0.125,  # 50% of allocation in ADA
                "grid_levels": 10,  # 5 buy + 5 sell
                "grid_spacing": 0.028,  # 2.8% - ADA moderate volatility
                "order_size_base": total_capital * 0.025,  # $60 per order for $2400
                "risk_level": "moderate",
                "volatility_threshold": 1.30,
                "rationale": "Stability + upside - Academic blockchain, PoS pioneer, sustainable development",
                "expected_annual_return": "70-110%",
            },
        }

        # Validate allocation adds to 100%
        total_allocation = sum(
            asset["allocation_pct"] for asset in self.portfolio_allocation.values()
        )
        assert abs(total_allocation - 1.0) < 0.001, (
            f"Total allocation must be 100%, got {total_allocation:.1%}"
        )

        self.logger.info(f"💼 Single Grid Portfolio initialized: ${total_capital:,.2f}")
        self.logger.info(
            f"   🔷 ETH: ${self.portfolio_allocation['ETHUSDT']['total_capital']:,.2f} (40%) - Conservative anchor"
        )
        self.logger.info(
            f"   🟣 SOL: ${self.portfolio_allocation['SOLUSDT']['total_capital']:,.2f} (35%) - Growth driver"
        )
        self.logger.info(
            f"   🔵 ADA: ${self.portfolio_allocation['ADAUSDT']['total_capital']:,.2f} (25%) - Stability + upside"
        )

    def get_asset_configuration(self, symbol: str) -> Dict:
        """
        Get configuration for specific asset compatible with GridManager
        """
        asset_config = self.portfolio_allocation.get(symbol)

        if not asset_config:
            raise ValueError(f"Unsupported symbol: {symbol}. Supported: ETH, SOL, ADA")

        # Ensure minimum order size for NOTIONAL compliance
        min_order_size = 25.0  # $25 minimum
        final_order_size = max(asset_config["order_size_base"], min_order_size)

        return {
            "symbol": symbol,
            "total_capital": asset_config["total_capital"],
            "allocation_percentage": asset_config["allocation_pct"] * 100,
            "usdt_reserve": asset_config["usdt_reserve"],
            "asset_reserve": asset_config["asset_reserve"],
            "order_size": final_order_size,
            "grid_levels": asset_config["grid_levels"],
            "grid_spacing": asset_config["grid_spacing"],
            "volatility_threshold": asset_config["volatility_threshold"],
            "risk_level": asset_config["risk_level"],
            "expected_return": asset_config["expected_annual_return"],
            "rationale": asset_config["rationale"],
            # Additional config for GridManager compatibility
            "grid_spacing_base": asset_config["grid_spacing"],
            "compound_aggressiveness": self._get_compound_aggressiveness(
                asset_config["risk_level"]
            ),
            "max_order_size_multiplier": self._get_order_size_multiplier(
                asset_config["risk_level"]
            ),
        }

    def _get_compound_aggressiveness(self, risk_level: str) -> float:
        """Get compound aggressiveness based on risk level"""
        mapping = {
            "conservative": 0.6,
            "moderate": 0.7,
            "moderate-aggressive": 0.8,
            "aggressive": 0.9,
        }
        return mapping.get(risk_level, 0.7)

    def _get_order_size_multiplier(self, risk_level: str) -> float:
        """Get order size multiplier based on risk level"""
        mapping = {
            "conservative": 2.5,
            "moderate": 2.8,
            "moderate-aggressive": 3.0,
            "aggressive": 3.5,
        }
        return mapping.get(risk_level, 2.8)

    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        summary = {
            "total_capital": self.total_capital,
            "architecture": "Single Advanced Grid with Inventory Management",
            "total_grids": 3,  # One grid per asset
            "total_levels": 30,  # 10 levels per grid
            "assets": {},
            "risk_profile": "Balanced growth with risk-adjusted allocation",
            "expected_annual_return": "60-120% (weighted average: ~80%)",
            "max_drawdown_estimate": "20-30%",
            "allocation_strategy": "40% ETH (anchor) + 35% SOL (growth) + 25% ADA (stability)",
        }

        for symbol in ["ETHUSDT", "SOLUSDT", "ADAUSDT"]:
            config = self.get_asset_configuration(symbol)
            summary["assets"][symbol] = {
                "allocation": f"{config['allocation_percentage']:.0f}%",
                "capital": f"${config['total_capital']:,.2f}",
                "usdt_reserve": f"${config['usdt_reserve']:,.2f}",
                "asset_reserve": f"${config['asset_reserve']:,.2f}",
                "grid_levels": config["grid_levels"],
                "order_size": f"${config['order_size']:.2f}",
                "grid_spacing": f"{config['grid_spacing'] * 100:.1f}%",
                "expected_return": config["expected_return"],
                "rationale": config["rationale"],
            }

        return summary

    def get_allocation_reasoning(self) -> Dict:
        """
        Get detailed reasoning behind the asset allocation strategy
        """
        return {
            "strategy_name": "Balanced Growth with Risk-Adjusted Allocation",
            "total_capital": f"${self.total_capital:,.2f}",
            "allocation_philosophy": [
                "Conservative anchor (ETH) for stability and institutional confidence",
                "Growth driver (SOL) for high returns and ecosystem expansion",
                "Stability + upside (ADA) for academic rigor and long-term value",
            ],
            "risk_management": [
                "Diversification across different blockchain paradigms",
                "Volatility-adjusted grid spacing (2.5% ETH, 3.0% SOL, 2.8% ADA)",
                "Conservative position sizing with inventory management",
                "50/50 USDT/Asset split enables consistent order replacement",
            ],
            "asset_details": {
                "ETHUSDT": {
                    "allocation": "40% ($960)",
                    "reasoning": [
                        "Largest allocation due to lowest risk profile",
                        "Strong institutional adoption and ETF inflows",
                        "Network effects and established ecosystem",
                        "Most liquid crypto asset",
                        "Conservative 2.5% grid spacing",
                    ],
                    "market_position": "Conservative anchor - stability with upside",
                },
                "SOLUSDT": {
                    "allocation": "35% ($840)",
                    "reasoning": [
                        "High growth potential with expanding ecosystem",
                        "Leading DeFi and memecoin platform",
                        "Strong developer activity and innovation",
                        "Higher volatility = more grid trading opportunities",
                        "3.0% grid spacing captures SOL's price movements",
                    ],
                    "market_position": "Growth driver - highest return potential",
                },
                "ADAUSDT": {
                    "allocation": "25% ($600)",
                    "reasoning": [
                        "Academic research-driven development",
                        "Proof-of-Stake pioneer with governance focus",
                        "Sustainable and methodical approach",
                        "Lower correlation with ETH/SOL during market stress",
                        "2.8% grid spacing balances stability and opportunity",
                    ],
                    "market_position": "Stability + upside - long-term value creation",
                },
            },
            "expected_outcomes": {
                "low_volatility_market": "ETH grid captures steady gains, portfolio stability maintained",
                "high_volatility_market": "SOL grid maximizes opportunities, ADA provides balance",
                "bear_market": "Conservative allocation and spacing limit downside exposure",
                "bull_market": "SOL allocation captures maximum upside, ETH provides steady gains",
            },
        }


# UPDATE: Replace this section in your existing asset configs
# In your GridManager.__init__, UPDATE the asset_configs to use this:


def get_updated_asset_configs(total_capital: float = 2400.0) -> Dict:
    """
    REPLACE your existing asset_configs in GridManager with this
    """
    portfolio_manager = SingleGridPortfolioManager(total_capital)

    return {
        "ETHUSDT": {
            "allocation": portfolio_manager.portfolio_allocation["ETHUSDT"][
                "total_capital"
            ],
            "risk_profile": "conservative",
            "grid_spacing_base": 0.025,  # 2.5%
            "volatility_threshold": 0.8,
            "compound_aggressiveness": 0.6,
            "max_order_size_multiplier": 2.5,
        },
        "SOLUSDT": {
            "allocation": portfolio_manager.portfolio_allocation["SOLUSDT"][
                "total_capital"
            ],
            "risk_profile": "moderate-aggressive",
            "grid_spacing_base": 0.03,  # 3.0%
            "volatility_threshold": 1.2,
            "compound_aggressiveness": 0.8,
            "max_order_size_multiplier": 3.0,
        },
        "ADAUSDT": {
            "allocation": portfolio_manager.portfolio_allocation["ADAUSDT"][
                "total_capital"
            ],
            "risk_profile": "moderate",
            "grid_spacing_base": 0.025,  # 2.5%
            "volatility_threshold": 1.0,
            "compound_aggressiveness": 0.7,
            "max_order_size_multiplier": 2.8,
        },
    }
