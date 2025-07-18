# models/single_advanced_grid_config.py
"""
Single Advanced Grid Configuration Model
========================================

Simplified grid configuration that eliminates dual-grid complexity
while maximizing advanced features integration.

Replaces: AdaptiveGridConfig (base_grid + enhanced_grid)
Benefits: Unified configuration, 100% capital allocation, simplified management
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class GridLevel:
    """Individual grid level configuration"""

    level: int  # Grid level number (-5 to +5, excluding 0)
    side: str  # "BUY" or "SELL"
    price: float  # Target price for this level
    quantity: float  # Quantity to trade
    order_size_usd: float  # USD value of the order
    order_id: Optional[str] = None  # Binance order ID when placed
    actual_price: Optional[float] = None  # Actual executed price
    actual_quantity: Optional[float] = None  # Actual executed quantity
    filled: bool = False  # Whether this level has been filled
    created_timestamp: float = field(default_factory=time.time)
    filled_timestamp: Optional[float] = None
    spacing_factor: float = 1.0  # Spacing multiplier for this level
    created_from_buy: Optional[int] = None  # If sell order, which buy level created it
    created_from_sell: Optional[int] = None  # If buy order, which sell level created it


class SingleAdvancedGridConfig:
    """
    Unified Advanced Grid Configuration

    Manages a single 10-level grid (5 buy + 5 sell) with ALL advanced features:
    - 100% capital allocation (no base/enhanced split)
    - Compound interest integration
    - Volatility-based adjustments
    - Kelly Criterion position sizing
    - Smart auto-reset capability
    - Market timing optimization
    """

    def __init__(self, symbol: str, total_capital: float, asset_config: Dict):
        # Basic configuration
        self.symbol = symbol
        self.total_capital = total_capital  # 100% allocation to single grid
        self.asset_config = asset_config

        # Grid structure - Fixed 10 levels for optimal balance
        self.grid_levels = 10
        self.buy_levels: List[GridLevel] = []  # 5 buy levels below center
        self.sell_levels: List[GridLevel] = []  # 5 sell levels above center

        # Dynamic parameters (adjusted by advanced features)
        self.base_order_size = 0.0  # Set by CompoundInterestManager
        self.grid_spacing = asset_config.get("grid_spacing_base", 0.025)  # 2.5% default
        self.center_price = 0.0  # Current center price of grid

        # Advanced features state
        self.compound_multiplier = 1.0  # Current compound multiplier
        self.volatility_regime = "moderate"  # Current volatility regime
        self.kelly_fraction = 0.1  # Kelly Criterion allocation fraction
        self.market_timing_score = 1.0  # Market timing adjustment factor

        # Grid lifecycle tracking
        self.created_timestamp = time.time()
        self.last_optimization = time.time()
        self.last_auto_reset = 0
        self.auto_reset_count = 0

        # Performance tracking
        self.total_orders_placed = 0
        self.total_orders_filled = 0
        self.total_profit_realized = 0.0
        self.total_volume_traded = 0.0

        # Risk management
        self.max_order_size_multiplier = asset_config.get(
            "max_order_size_multiplier", 3.0
        )
        self.volatility_threshold = asset_config.get("volatility_threshold", 1.0)
        self.compound_aggressiveness = asset_config.get("compound_aggressiveness", 0.7)

        # Configuration validation
        self._validate_configuration()

    def _validate_configuration(self):
        """Validate grid configuration parameters"""
        if self.total_capital <= 0:
            raise ValueError("Total capital must be positive")

        if self.grid_spacing <= 0 or self.grid_spacing > 0.1:
            raise ValueError("Grid spacing must be between 0 and 10%")

        if not self.symbol.endswith("USDT"):
            raise ValueError("Only USDT pairs are currently supported")

    def calculate_grid_levels(self, current_price: float) -> Dict:
        """
        Calculate optimal grid levels around current price

        Returns comprehensive grid layout with all levels defined
        """
        if current_price <= 0:
            raise ValueError("Current price must be positive")

        self.center_price = current_price
        spacing = self.grid_spacing

        # Clear existing levels
        self.buy_levels.clear()
        self.sell_levels.clear()

        # Calculate BUY LEVELS (below current price)
        for i in range(1, 6):  # Levels -1 to -5
            # Progressive spacing: farther levels have wider spacing
            level_spacing = spacing * (1 + i * 0.1)  # 1.1x, 1.2x, 1.3x, 1.4x, 1.5x
            price = current_price * (1 - level_spacing)

            # Progressive order sizing: larger orders at better prices
            size_multiplier = 1 + i * 0.05  # 5% increase per level down
            order_size_usd = self.base_order_size * size_multiplier
            quantity = order_size_usd / price

            buy_level = GridLevel(
                level=-i,
                side="BUY",
                price=price,
                quantity=quantity,
                order_size_usd=order_size_usd,
                spacing_factor=1 + i * 0.1,
            )

            self.buy_levels.append(buy_level)

        # Calculate SELL LEVELS (above current price)
        for i in range(1, 6):  # Levels +1 to +5
            level_spacing = spacing * (1 + i * 0.1)
            price = current_price * (1 + level_spacing)

            # Sell quantities will be set when corresponding buys are filled
            # Initial sell levels are placeholders for grid completeness
            size_multiplier = 1 + i * 0.05
            order_size_usd = self.base_order_size * size_multiplier
            quantity = order_size_usd / price

            sell_level = GridLevel(
                level=i,
                side="SELL",
                price=price,
                quantity=quantity,
                order_size_usd=order_size_usd,
                spacing_factor=1 + i * 0.1,
            )

            self.sell_levels.append(sell_level)

        # Sort levels for easy access
        self.buy_levels.sort(key=lambda x: x.level, reverse=True)  # -1, -2, -3, -4, -5
        self.sell_levels.sort(key=lambda x: x.level)  # +1, +2, +3, +4, +5

        # Calculate total capital allocation
        total_buy_allocation = sum(level.order_size_usd for level in self.buy_levels)

        return {
            "center_price": current_price,
            "total_levels": 10,
            "buy_levels": len(self.buy_levels),
            "sell_levels": len(self.sell_levels),
            "buy_price_range": (self.buy_levels[-1].price, self.buy_levels[0].price),
            "sell_price_range": (self.sell_levels[0].price, self.sell_levels[-1].price),
            "total_buy_allocation": total_buy_allocation,
            "grid_width": (self.sell_levels[-1].price - self.buy_levels[-1].price)
            / current_price,
            "average_spacing": spacing,
        }

    def get_level_by_id(self, level_id: int) -> Optional[GridLevel]:
        """Get grid level by its ID"""
        if level_id < 0:  # Buy level
            for level in self.buy_levels:
                if level.level == level_id:
                    return level
        else:  # Sell level
            for level in self.sell_levels:
                if level.level == level_id:
                    return level
        return None

    def get_level_by_order_id(self, order_id: str) -> Optional[GridLevel]:
        """Get grid level by Binance order ID"""
        for level in self.buy_levels + self.sell_levels:
            if level.order_id == order_id:
                return level
        return None

    def mark_level_filled(
        self, order_id: str, actual_price: float = None, actual_quantity: float = None
    ) -> Optional[GridLevel]:
        """Mark a level as filled and update statistics"""
        level = self.get_level_by_order_id(order_id)
        if level:
            level.filled = True
            level.filled_timestamp = time.time()
            if actual_price:
                level.actual_price = actual_price
            if actual_quantity:
                level.actual_quantity = actual_quantity

            # Update statistics
            self.total_orders_filled += 1
            self.total_volume_traded += level.order_size_usd

            return level
        return None

    def get_unfilled_levels(self, side: str = None) -> List[GridLevel]:
        """Get all unfilled levels, optionally filtered by side"""
        unfilled = []

        levels_to_check = []
        if side == "BUY":
            levels_to_check = self.buy_levels
        elif side == "SELL":
            levels_to_check = self.sell_levels
        else:
            levels_to_check = self.buy_levels + self.sell_levels

        for level in levels_to_check:
            if not level.filled and level.order_id:
                unfilled.append(level)

        return unfilled

    def get_filled_levels(self, side: str = None) -> List[GridLevel]:
        """Get all filled levels, optionally filtered by side"""
        filled = []

        levels_to_check = []
        if side == "BUY":
            levels_to_check = self.buy_levels
        elif side == "SELL":
            levels_to_check = self.sell_levels
        else:
            levels_to_check = self.buy_levels + self.sell_levels

        for level in levels_to_check:
            if level.filled:
                filled.append(level)

        return filled

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL for current positions"""
        unrealized_pnl = 0.0

        # Calculate PnL for filled buy orders (we own the asset)
        for level in self.get_filled_levels("BUY"):
            if level.actual_price and level.actual_quantity:
                position_pnl = (
                    current_price - level.actual_price
                ) * level.actual_quantity
                unrealized_pnl += position_pnl

        return unrealized_pnl

    def get_price_deviation_from_center(self, current_price: float) -> float:
        """Get price deviation from grid center as percentage"""
        if self.center_price <= 0:
            return 0.0

        return (current_price - self.center_price) / self.center_price

    def should_consider_reset(
        self, current_price: float, reset_threshold: float = 0.15
    ) -> bool:
        """Check if grid should be considered for reset"""
        deviation = abs(self.get_price_deviation_from_center(current_price))

        # Time-based reset prevention
        time_since_last_reset = time.time() - self.last_auto_reset
        min_reset_interval = 3600  # 1 hour

        # Daily reset limit
        reset_count_limit = 5

        return (
            deviation > reset_threshold
            and time_since_last_reset > min_reset_interval
            and self.auto_reset_count < reset_count_limit
        )

    def update_advanced_parameters(
        self,
        compound_multiplier: float = None,
        volatility_regime: str = None,
        kelly_fraction: float = None,
        market_timing_score: float = None,
    ):
        """Update parameters from advanced features"""
        if compound_multiplier is not None:
            self.compound_multiplier = compound_multiplier

        if volatility_regime is not None:
            self.volatility_regime = volatility_regime

        if kelly_fraction is not None:
            self.kelly_fraction = kelly_fraction

        if market_timing_score is not None:
            self.market_timing_score = market_timing_score

        self.last_optimization = time.time()

    def apply_volatility_adjustment(self, new_spacing: float):
        """Apply volatility-based spacing adjustment"""
        old_spacing = self.grid_spacing
        self.grid_spacing = new_spacing

        # Log the adjustment
        adjustment_factor = new_spacing / old_spacing if old_spacing > 0 else 1.0

        return {
            "old_spacing": old_spacing,
            "new_spacing": new_spacing,
            "adjustment_factor": adjustment_factor,
            "volatility_regime": self.volatility_regime,
        }

    def execute_auto_reset(self, new_center_price: float):
        """Execute auto-reset with new center price"""
        self.center_price = new_center_price
        self.last_auto_reset = time.time()
        self.auto_reset_count += 1

        # Clear existing levels (orders should be cancelled separately)
        for level in self.buy_levels + self.sell_levels:
            if not level.filled:
                level.order_id = None  # Clear order ID for unfilled orders

        # Recalculate grid levels will be done by the manager
        return {
            "reset_timestamp": self.last_auto_reset,
            "new_center_price": new_center_price,
            "reset_count": self.auto_reset_count,
            "reason": f"Price moved to ${new_center_price:.6f}",
        }

    def get_grid_status(self) -> Dict:
        """Get comprehensive grid status"""
        current_time = time.time()

        # Count order states
        total_orders = len(self.buy_levels) + len(self.sell_levels)
        filled_orders = len(self.get_filled_levels())
        unfilled_orders = len(self.get_unfilled_levels())
        active_orders = len(
            [
                l
                for l in self.buy_levels + self.sell_levels
                if l.order_id and not l.filled
            ]
        )

        # Calculate fill rate
        fill_rate = (filled_orders / total_orders * 100) if total_orders > 0 else 0

        # Get price ranges
        buy_range = (
            (self.buy_levels[-1].price, self.buy_levels[0].price)
            if self.buy_levels
            else (0, 0)
        )
        sell_range = (
            (self.sell_levels[0].price, self.sell_levels[-1].price)
            if self.sell_levels
            else (0, 0)
        )

        return {
            "symbol": self.symbol,
            "strategy": "Single Advanced Grid",
            "total_capital": self.total_capital,
            "capital_efficiency": "100%",
            # Grid structure
            "grid_details": {
                "total_levels": total_orders,
                "buy_levels": len(self.buy_levels),
                "sell_levels": len(self.sell_levels),
                "center_price": self.center_price,
                "grid_spacing": f"{self.grid_spacing * 100:.2f}%",
                "buy_price_range": buy_range,
                "sell_price_range": sell_range,
            },
            # Order status
            "order_status": {
                "total_orders": total_orders,
                "filled_orders": filled_orders,
                "unfilled_orders": unfilled_orders,
                "active_orders": active_orders,
                "fill_rate": f"{fill_rate:.1f}%",
            },
            # Advanced features
            "advanced_features": {
                "compound_multiplier": self.compound_multiplier,
                "volatility_regime": self.volatility_regime,
                "kelly_fraction": self.kelly_fraction,
                "market_timing_score": self.market_timing_score,
            },
            # Performance metrics
            "performance": {
                "total_volume_traded": self.total_volume_traded,
                "total_profit_realized": self.total_profit_realized,
                "orders_filled": self.total_orders_filled,
                "auto_reset_count": self.auto_reset_count,
            },
            # Lifecycle
            "lifecycle": {
                "created": self.created_timestamp,
                "age_hours": (current_time - self.created_timestamp) / 3600,
                "last_optimization": self.last_optimization,
                "last_auto_reset": self.last_auto_reset,
            },
            # Risk management
            "risk_management": {
                "max_order_multiplier": self.max_order_size_multiplier,
                "volatility_threshold": self.volatility_threshold,
                "compound_aggressiveness": self.compound_aggressiveness,
            },
        }

    def get_performance_summary(self, current_price: float = None) -> Dict:
        """Get performance summary with key metrics"""
        filled_buys = self.get_filled_levels("BUY")
        filled_sells = self.get_filled_levels("SELL")

        # Calculate realized profit from completed buy-sell cycles
        realized_profit = 0.0
        for sell_level in filled_sells:
            if sell_level.created_from_buy:
                buy_level = self.get_level_by_id(sell_level.created_from_buy)
                if buy_level and buy_level.filled:
                    if (
                        sell_level.actual_price
                        and buy_level.actual_price
                        and sell_level.actual_quantity
                    ):
                        cycle_profit = (
                            sell_level.actual_price - buy_level.actual_price
                        ) * sell_level.actual_quantity
                        realized_profit += cycle_profit

        # Calculate unrealized PnL if current price provided
        unrealized_pnl = 0.0
        if current_price:
            unrealized_pnl = self.calculate_unrealized_pnl(current_price)

        # Calculate grid efficiency
        total_possible_orders = 10  # 5 buy + 5 sell
        efficiency_score = (
            (len(filled_buys) + len(filled_sells)) / total_possible_orders * 100
        )

        return {
            "performance_summary": {
                "realized_profit": realized_profit,
                "unrealized_pnl": unrealized_pnl,
                "total_pnl": realized_profit + unrealized_pnl,
                "filled_buy_orders": len(filled_buys),
                "filled_sell_orders": len(filled_sells),
                "completed_cycles": min(len(filled_buys), len(filled_sells)),
                "efficiency_score": efficiency_score,
                "volume_traded": self.total_volume_traded,
                "capital_utilization": f"{(self.total_volume_traded / self.total_capital * 100):.1f}%"
                if self.total_capital > 0
                else "0%",
            },
            "advanced_optimization": {
                "compound_growth_factor": self.compound_multiplier,
                "volatility_adaptation": self.volatility_regime,
                "kelly_position_sizing": f"{self.kelly_fraction * 100:.1f}%",
                "market_timing_adjustment": self.market_timing_score,
                "total_optimizations": self.auto_reset_count
                + 1,  # Include initial setup
            },
        }

    def export_grid_data(self) -> Dict:
        """Export complete grid data for backup/analysis"""
        return {
            "metadata": {
                "symbol": self.symbol,
                "total_capital": self.total_capital,
                "created_timestamp": self.created_timestamp,
                "center_price": self.center_price,
                "grid_spacing": self.grid_spacing,
            },
            "buy_levels": [
                {
                    "level": level.level,
                    "price": level.price,
                    "quantity": level.quantity,
                    "order_size_usd": level.order_size_usd,
                    "order_id": level.order_id,
                    "filled": level.filled,
                    "actual_price": level.actual_price,
                    "actual_quantity": level.actual_quantity,
                    "created_timestamp": level.created_timestamp,
                    "filled_timestamp": level.filled_timestamp,
                }
                for level in self.buy_levels
            ],
            "sell_levels": [
                {
                    "level": level.level,
                    "price": level.price,
                    "quantity": level.quantity,
                    "order_size_usd": level.order_size_usd,
                    "order_id": level.order_id,
                    "filled": level.filled,
                    "actual_price": level.actual_price,
                    "actual_quantity": level.actual_quantity,
                    "created_timestamp": level.created_timestamp,
                    "filled_timestamp": level.filled_timestamp,
                    "created_from_buy": level.created_from_buy,
                }
                for level in self.sell_levels
            ],
            "advanced_features": {
                "compound_multiplier": self.compound_multiplier,
                "volatility_regime": self.volatility_regime,
                "kelly_fraction": self.kelly_fraction,
                "market_timing_score": self.market_timing_score,
            },
            "performance": {
                "total_orders_placed": self.total_orders_placed,
                "total_orders_filled": self.total_orders_filled,
                "total_profit_realized": self.total_profit_realized,
                "total_volume_traded": self.total_volume_traded,
                "auto_reset_count": self.auto_reset_count,
            },
        }

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"SingleAdvancedGridConfig({self.symbol}, "
            f"${self.total_capital:,.2f}, "
            f"{len(self.buy_levels)}B+{len(self.sell_levels)}S, "
            f"center=${self.center_price:.4f})"
        )

    def __str__(self) -> str:
        """Human-readable string representation"""
        filled_count = len(self.get_filled_levels())
        total_count = len(self.buy_levels) + len(self.sell_levels)

        return (
            f"Single Advanced Grid: {self.symbol}\n"
            f"Capital: ${self.total_capital:,.2f} (100% allocation)\n"
            f"Levels: {total_count} total ({len(self.buy_levels)} buy + {len(self.sell_levels)} sell)\n"
            f"Filled: {filled_count}/{total_count} ({filled_count / total_count * 100:.1f}%)\n"
            f"Center: ${self.center_price:.6f}\n"
            f"Spacing: {self.grid_spacing * 100:.2f}%\n"
            f"Compound: {self.compound_multiplier:.2f}x\n"
            f"Volatility: {self.volatility_regime}"
        )


# Utility functions for grid management


def create_optimized_grid_config(
    symbol: str,
    total_capital: float,
    current_price: float,
    asset_config: Dict,
    compound_multiplier: float = 1.0,
    volatility_regime: str = "moderate",
) -> SingleAdvancedGridConfig:
    """
    Create an optimized grid configuration with advanced features pre-configured

    This is a convenience function for creating grids with optimal settings
    """
    # Create base configuration
    config = SingleAdvancedGridConfig(symbol, total_capital, asset_config)

    # Set advanced parameters
    config.compound_multiplier = compound_multiplier
    config.volatility_regime = volatility_regime

    # Calculate base order size (will be adjusted by compound multiplier)
    base_allocation = total_capital / 10  # Divide across 10 levels initially
    config.base_order_size = base_allocation * compound_multiplier

    # Apply volatility adjustments to spacing
    volatility_adjustments = {
        "low": 0.8,  # Tighter spacing in low volatility
        "moderate": 1.0,  # Standard spacing
        "high": 1.3,  # Wider spacing in high volatility
        "extreme": 1.6,  # Much wider spacing
    }

    spacing_multiplier = volatility_adjustments.get(volatility_regime, 1.0)
    config.grid_spacing = (
        asset_config.get("grid_spacing_base", 0.025) * spacing_multiplier
    )

    # Calculate grid levels
    config.calculate_grid_levels(current_price)

    return config


def validate_grid_integrity(config: SingleAdvancedGridConfig) -> Dict:
    """
    Validate grid configuration integrity and return validation report
    """
    issues = []
    warnings = []

    # Check basic configuration
    if config.total_capital <= 0:
        issues.append("Total capital must be positive")

    if config.center_price <= 0:
        issues.append("Center price must be set")

    if not config.buy_levels:
        issues.append("No buy levels configured")

    if len(config.buy_levels) != 5:
        warnings.append(f"Expected 5 buy levels, found {len(config.buy_levels)}")

    if len(config.sell_levels) != 5:
        warnings.append(f"Expected 5 sell levels, found {len(config.sell_levels)}")

    # Check level ordering
    if config.buy_levels:
        buy_prices = [level.price for level in config.buy_levels]
        if buy_prices != sorted(buy_prices, reverse=True):
            issues.append("Buy levels are not properly ordered (should be descending)")

    if config.sell_levels:
        sell_prices = [level.price for level in config.sell_levels]
        if sell_prices != sorted(sell_prices):
            issues.append("Sell levels are not properly ordered (should be ascending)")

    # Check price relationships
    if config.buy_levels and config.sell_levels:
        highest_buy = max(level.price for level in config.buy_levels)
        lowest_sell = min(level.price for level in config.sell_levels)

        if highest_buy >= lowest_sell:
            issues.append("Buy levels overlap with sell levels")

        if lowest_sell < config.center_price:
            issues.append("Sell levels below center price")

        if highest_buy > config.center_price:
            issues.append("Buy levels above center price")

    # Check capital allocation
    total_buy_allocation = sum(level.order_size_usd for level in config.buy_levels)
    if total_buy_allocation > config.total_capital * 1.1:  # 10% tolerance
        warnings.append(
            f"Buy allocation (${total_buy_allocation:.2f}) exceeds total capital"
        )

    # Check advanced features
    if config.compound_multiplier < 0.5 or config.compound_multiplier > 5.0:
        warnings.append(
            f"Compound multiplier ({config.compound_multiplier}) outside normal range"
        )

    if config.grid_spacing < 0.005 or config.grid_spacing > 0.1:
        warnings.append(
            f"Grid spacing ({config.grid_spacing * 100:.2f}%) outside recommended range"
        )

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "summary": f"Grid validation: {len(issues)} issues, {len(warnings)} warnings",
    }
