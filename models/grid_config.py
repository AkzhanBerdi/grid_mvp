# models/grid_config.py
"""Grid trading configuration with anti-corruption protection"""

import logging
from typing import Dict, List

from .client import Client, ClientStatus, GridStatus


class GridConfig:
    """
    🔧 FIXED: Grid trading configuration that CANNOT become a dictionary
    Removed @dataclass to prevent automatic dict serialization
    """

    def __init__(
        self,
        symbol: str,
        client_id: int,
        grid_spacing: float = 0.025,  # 2.5%
        total_capital: float = 0.0,
        grid_levels: int = 8,
        order_size: float = 50.0,  # USD per order
        center_price: float = 0.0,
    ):
        self.symbol = symbol
        self.client_id = client_id
        self.grid_spacing = grid_spacing
        self.total_capital = total_capital
        self.grid_levels = grid_levels
        self.order_size = order_size
        self.center_price = center_price

        # Risk management
        self.max_loss_per_trade: float = 0.01  # 1%
        self.max_buy_premium: float = 0.02  # 2%

        # Grid state
        self.active: bool = False
        self.buy_levels: List[Dict] = []
        self.sell_levels: List[Dict] = []

        # 🔧 CRITICAL: Anti-corruption markers
        self._is_grid_config = True
        self._grid_config_version = "2.0"

        # Additional attributes that get added by GridManager
        self.base_order_size: float = order_size
        self.compound_multiplier: float = 1.0
        self.volatility_regime: str = "moderate"

        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"✅ GridConfig created for {symbol} - ID: {id(self)}")

    def __setattr__(self, name, value):
        """Override setattr to prevent corruption"""
        if (
            name.startswith("_")
            or hasattr(self, name)
            or name
            in [
                "symbol",
                "client_id",
                "grid_spacing",
                "total_capital",
                "grid_levels",
                "order_size",
                "center_price",
                "max_loss_per_trade",
                "max_buy_premium",
                "active",
                "buy_levels",
                "sell_levels",
                "base_order_size",
                "compound_multiplier",
                "volatility_regime",
                "logger",
            ]
        ):
            super().__setattr__(name, value)
        else:
            self.logger.warning(f"⚠️ Attempted to set unknown attribute: {name}")
            super().__setattr__(name, value)

    def validate_integrity(self) -> bool:
        """Validate that this object hasn't been corrupted"""
        try:
            # Check required attributes exist
            required_attrs = [
                "symbol",
                "client_id",
                "grid_spacing",
                "total_capital",
                "grid_levels",
                "order_size",
                "buy_levels",
                "sell_levels",
            ]

            for attr in required_attrs:
                if not hasattr(self, attr):
                    self.logger.error(f"❌ GridConfig missing attribute: {attr}")
                    return False

            # Check anti-corruption markers
            if not hasattr(self, "_is_grid_config") or not self._is_grid_config:
                self.logger.error("❌ GridConfig missing anti-corruption marker")
                return False

            # Check types
            if not isinstance(self.buy_levels, list) or not isinstance(
                self.sell_levels, list
            ):
                self.logger.error("❌ GridConfig levels are not lists")
                return False

            return True

        except Exception as e:
            self.logger.error(f"❌ GridConfig validation error: {e}")
            return False

    def calculate_grid_levels(self, current_price: float):
        """Calculate buy and sell grid levels - FIXED ORDER SIZING"""
        try:
            self.center_price = current_price
            self.buy_levels = []
            self.sell_levels = []

            # FIXED: Use the order_size directly (this is now the correct USD amount per order)
            order_size_usd = self.order_size

            self.logger.debug("🔧 GridConfig calculation:")
            self.logger.debug(f"   Current price: ${current_price:.4f}")
            self.logger.debug(f"   Order size USD: ${order_size_usd:.2f}")
            self.logger.debug(f"   Grid spacing: {self.grid_spacing * 100:.1f}%")
            self.logger.debug(f"   Grid levels: {self.grid_levels}")

            # Calculate buy levels (below current price)
            for i in range(1, self.grid_levels + 1):
                price = current_price * (1 - self.grid_spacing * i)
                quantity = (
                    order_size_usd / price
                )  # Calculate quantity based on USD amount

                self.buy_levels.append(
                    {
                        "level": -i,  # 🔧 FIXED: Negative for buy levels
                        "side": "BUY",
                        "price": price,
                        "quantity": quantity,
                        "order_size_usd": order_size_usd,
                        "filled": False,
                        "order_id": None,
                    }
                )

                self.logger.debug(
                    f"   Buy Level -{i}: {quantity:.4f} {self.symbol.replace('USDT', '')} at ${price:.4f} = ${order_size_usd:.2f}"
                )

            # Calculate sell levels (above current price)
            for i in range(1, self.grid_levels + 1):
                price = current_price * (1 + self.grid_spacing * i)
                quantity = (
                    order_size_usd / price
                )  # Calculate quantity based on USD amount

                self.sell_levels.append(
                    {
                        "level": i,  # Positive for sell levels
                        "side": "SELL",
                        "price": price,
                        "quantity": quantity,
                        "order_size_usd": order_size_usd,
                        "filled": False,
                        "order_id": None,
                    }
                )

                self.logger.debug(
                    f"   Sell Level {i}: {quantity:.4f} {self.symbol.replace('USDT', '')} at ${price:.4f} = ${order_size_usd:.2f}"
                )

            self.logger.info(
                f"✅ Grid calculated: {len(self.buy_levels)} buy + {len(self.sell_levels)} sell levels"
            )

        except Exception as e:
            self.logger.error(f"❌ Error calculating grid levels: {e}")
            raise

    def get_next_buy_level(self, current_price: float) -> Dict:
        """Get the next buy level that should trigger"""
        for level in self.buy_levels:
            if not level["filled"] and current_price <= level["price"]:
                return level
        return None

    def get_next_sell_level(self, current_price: float) -> Dict:
        """Get the next sell level that should trigger"""
        for level in self.sell_levels:
            if not level["filled"] and current_price >= level["price"]:
                return level
        return None

    def should_reset_grid(
        self, current_price: float, time_threshold: int = 3600
    ) -> bool:
        """Check if grid should be reset due to price deviation"""
        if not self.center_price:
            return False

        # Check if price has moved more than 15% from center
        price_deviation = abs(current_price - self.center_price) / self.center_price
        return price_deviation > 0.15

    def reset_grid(self, new_price: float):
        """Reset grid with new center price"""
        self.calculate_grid_levels(new_price)
        self.active = True

    def mark_level_filled(self, side: str, level: int, order_id: str):
        """Mark a grid level as filled"""
        levels = self.buy_levels if side == "BUY" else self.sell_levels

        for grid_level in levels:
            if grid_level["level"] == level:
                grid_level["filled"] = True
                grid_level["order_id"] = order_id
                break

    def get_grid_status(self) -> Dict:
        """Get current grid status"""
        buy_filled = sum(1 for level in self.buy_levels if level["filled"])
        sell_filled = sum(1 for level in self.sell_levels if level["filled"])

        return {
            "symbol": self.symbol,
            "active": self.active,
            "center_price": self.center_price,
            "total_levels": self.grid_levels * 2,
            "buy_levels_filled": buy_filled,
            "sell_levels_filled": sell_filled,
            "buy_levels_active": len(self.buy_levels) - buy_filled,
            "sell_levels_active": len(self.sell_levels) - sell_filled,
            "object_id": id(self),
            "is_valid": self.validate_integrity(),
        }

    def to_dict(self) -> Dict:
        """
        🔧 CONTROLLED serialization - only use when explicitly needed
        Marks the dict so we can detect and recover from it
        """
        return {
            "symbol": self.symbol,
            "client_id": self.client_id,
            "grid_spacing": self.grid_spacing,
            "total_capital": self.total_capital,
            "grid_levels": self.grid_levels,
            "order_size": self.order_size,
            "center_price": self.center_price,
            "active": self.active,
            "buy_levels": self.buy_levels,
            "sell_levels": self.sell_levels,
            "base_order_size": getattr(self, "base_order_size", self.order_size),
            "compound_multiplier": getattr(self, "compound_multiplier", 1.0),
            "volatility_regime": getattr(self, "volatility_regime", "moderate"),
            # 🔧 CRITICAL: Recovery markers
            "_type": "GridConfig",
            "_version": self._grid_config_version,
            "_serialized": True,
            "_original_id": id(self),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GridConfig":
        """
        🔧 CONTROLLED deserialization with validation
        """
        try:
            # Validate this is actually a serialized GridConfig
            if data.get("_type") != "GridConfig":
                raise ValueError(f"Not a serialized GridConfig: {data.get('_type')}")

            # Create new instance
            obj = cls(
                symbol=data["symbol"],
                client_id=data["client_id"],
                grid_spacing=data["grid_spacing"],
                total_capital=data["total_capital"],
                grid_levels=data["grid_levels"],
                order_size=data["order_size"],
                center_price=data.get("center_price", 0.0),
            )

            # Restore state
            obj.active = data.get("active", False)
            obj.buy_levels = data.get("buy_levels", [])
            obj.sell_levels = data.get("sell_levels", [])
            obj.base_order_size = data.get("base_order_size", obj.order_size)
            obj.compound_multiplier = data.get("compound_multiplier", 1.0)
            obj.volatility_regime = data.get("volatility_regime", "moderate")

            obj.logger.info(
                f"✅ GridConfig recovered from dict - Original ID: {data.get('_original_id')}, New ID: {id(obj)}"
            )

            return obj

        except Exception as e:
            logging.error(f"❌ Failed to recover GridConfig from dict: {e}")
            raise

    def __repr__(self):
        return f"GridConfig({self.symbol}, client={self.client_id}, levels={self.grid_levels}, id={id(self)})"

    def __str__(self):
        return f"GridConfig for {self.symbol} (ID: {id(self)})"


# 🔧 CRITICAL: Add validation functions for your grid trading engine


def validate_grid_config(grid_config, context: str = "unknown") -> bool:
    """
    Validate that grid_config is a proper GridConfig object, not a dict
    """
    logger = logging.getLogger(__name__)

    if grid_config is None:
        logger.error(f"❌ {context}: grid_config is None")
        return False

    if isinstance(grid_config, dict):
        logger.error(
            f"❌ {context}: grid_config is dict with keys: {list(grid_config.keys())}"
        )

        # Check if it's a recoverable serialized GridConfig
        if grid_config.get("_type") == "GridConfig":
            logger.warning(
                f"🔧 {context}: Found serialized GridConfig - needs recovery"
            )
            return False  # Still invalid, but recoverable
        else:
            logger.error(f"🚨 {context}: Unknown dict format - cannot recover")
            return False

    if isinstance(grid_config, GridConfig):
        # Validate integrity
        if grid_config.validate_integrity():
            logger.debug(f"✅ {context}: GridConfig is valid")
            return True
        else:
            logger.error(f"❌ {context}: GridConfig failed integrity check")
            return False

    logger.error(f"❌ {context}: grid_config is wrong type: {type(grid_config)}")
    return False


def recover_grid_config(grid_config, context: str = "unknown"):
    """
    Attempt to recover a GridConfig from a serialized dict
    Returns recovered GridConfig or None if impossible
    """
    logger = logging.getLogger(__name__)

    if not isinstance(grid_config, dict):
        logger.debug(f"✅ {context}: No recovery needed - already proper object")
        return grid_config

    if grid_config.get("_type") != "GridConfig":
        logger.error(f"❌ {context}: Cannot recover - not a serialized GridConfig")
        return None

    try:
        recovered = GridConfig.from_dict(grid_config)
        logger.info(f"✅ {context}: Successfully recovered GridConfig")
        return recovered
    except Exception as e:
        logger.error(f"❌ {context}: Recovery failed: {e}")
        return None


# models/__init__.py - UPDATE THIS
"""Models package initialization"""

__all__ = [
    "Client",
    "ClientStatus",
    "GridStatus",
    "GridConfig",
    "validate_grid_config",
    "recover_grid_config",
]
