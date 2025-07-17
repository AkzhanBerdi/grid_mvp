# models/grid_config.py
"""Grid trading configuration"""

from typing import Dict, List

from dataclasses import dataclass


@dataclass
class GridConfig:
    """Grid trading configuration for a specific pair"""

    symbol: str
    client_id: int
    grid_spacing: float = 0.025  # 2.5%
    grid_levels: int = 8
    order_size: float = 50.0  # USD per order
    center_price: float = 0.0

    # Risk management
    max_loss_per_trade: float = 0.01  # 1%
    max_buy_premium: float = 0.02  # 2%

    # Grid state
    active: bool = False
    buy_levels: List[Dict] = None
    sell_levels: List[Dict] = None

    def __post_init__(self):
        if self.buy_levels is None:
            self.buy_levels = []
        if self.sell_levels is None:
            self.sell_levels = []

    def calculate_grid_levels(self, current_price: float):
        """Calculate buy and sell grid levels - FIXED ORDER SIZING"""
        self.center_price = current_price
        self.buy_levels = []
        self.sell_levels = []

        # FIXED: Use the order_size directly (this is now the correct USD amount per order)
        order_size_usd = self.order_size

        print("🔧 GridConfig calculation:")
        print(f"   Current price: ${current_price:.4f}")
        print(f"   Order size USD: ${order_size_usd:.2f}")
        print(f"   Grid spacing: {self.grid_spacing * 100:.1f}%")
        print(f"   Grid levels: {self.grid_levels}")

        # Calculate buy levels (below current price)
        for i in range(1, self.grid_levels + 1):
            price = current_price * (1 - self.grid_spacing * i)
            quantity = order_size_usd / price  # Calculate quantity based on USD amount

            self.buy_levels.append(
                {
                    "level": i,
                    "price": price,
                    "quantity": quantity,
                    "filled": False,
                    "order_id": None,
                }
            )

            print(
                f"   Buy Level {i}: {quantity:.3f} {self.symbol.replace('USDT', '')} at ${price:.4f} = ${order_size_usd:.2f}"
            )

        # Calculate sell levels (above current price)
        for i in range(1, self.grid_levels + 1):
            price = current_price * (1 + self.grid_spacing * i)
            quantity = order_size_usd / price  # Calculate quantity based on USD amount

            self.sell_levels.append(
                {
                    "level": i,
                    "price": price,
                    "quantity": quantity,
                    "filled": False,
                    "order_id": None,
                }
            )

            print(
                f"   Sell Level {i}: {quantity:.3f} {self.symbol.replace('USDT', '')} at ${price:.4f} = ${order_size_usd:.2f}"
            )

        print(
            f"✅ Grid calculated: {len(self.buy_levels)} buy + {len(self.sell_levels)} sell levels"
        )

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
        }


# models/__init__.py
"""Models package initialization"""

from .client import Client, ClientStatus, GridStatus
from .grid_config import GridConfig

__all__ = ["Client", "ClientStatus", "GridStatus", "GridConfig"]
