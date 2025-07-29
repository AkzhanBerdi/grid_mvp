"""
Advanced Feature 1: Compound Interest Manager with Kelly Criterion
==================================================================

This replaces static order sizing with intelligent dynamic position sizing that:
- Automatically grows order sizes from profits (compound interest)
- Uses Kelly Criterion for optimal position sizing
- Implements safety caps to prevent over-leveraging
- Integrates with FIFO profit tracking for real-time adjustments
- Provides risk-adjusted allocation between base and enhanced grids

Key Benefits:
- Maximizes long-term capital growth
- Prevents position sizes from becoming too large
- Automatically reinvests profits optimally
- Reduces risk during losing streaks
"""

import logging
import time
from typing import Dict

import numpy as np

from services.fifo_service import FIFOService


class CompoundInterestManager:
    """
    Intelligent compound interest system with Kelly Criterion position sizing

    Automatically adjusts order sizes based on:
    - Accumulated profits (compound growth)
    - Historical win rate and profit/loss ratios (Kelly Criterion)
    - Current market volatility
    - Risk management constraints
    """

    def __init__(self, fifo_service: FIFOService):
        self.fifo_service = fifo_service
        self.logger = logging.getLogger(__name__)

        # Compound interest settings
        self.profit_reinvestment_rate = 0.3  # Reinvest 30% of profits
        self.max_order_size_multiplier = 3.0  # Safety cap at 3x base
        self.min_order_size_multiplier = 0.5  # Floor at 50% of base

        # Kelly Criterion settings
        self.min_trades_for_kelly = 20  # Minimum trades needed for Kelly calculation
        self.kelly_safety_factor = 0.5  # Use 50% of Kelly suggestion (Half-Kelly)
        self.max_kelly_fraction = 0.25  # Never risk more than 25% per trade

        # Performance tracking
        self.client_performance = {}  # Cache for performance data
        self.last_update = {}  # Track last update times

        # Risk management
        self.max_allocation_change_per_day = 0.1  # Max 10% allocation change per day
        self.drawdown_protection_threshold = 0.15  # Reduce size if 15% drawdown

        self.logger.info(
            "🔥 Compound Interest Manager initialized with Kelly Criterion"
        )

    async def get_current_order_size(
        self, client_id: int, symbol: str, base_capital: float
    ) -> float:
        """
        Calculate optimal order size using compound interest + Kelly Criterion
        """
        try:
            # FIXED: Remove 'await' - this is a sync method
            performance = self._safe_get_performance_metrics(client_id)

            # FIXED: Add 'await' - this IS an async method
            kelly_fraction = await self._calculate_kelly_fraction(client_id, symbol)

            # Calculate compound multiplier based on accumulated profits
            compound_multiplier = self._calculate_compound_multiplier(client_id)

            # Combine Kelly and compound factors
            optimal_fraction = kelly_fraction * compound_multiplier

            # Apply safety constraints
            safe_fraction = self._apply_safety_constraints(
                optimal_fraction, client_id, performance
            )

            # Calculate final order size with minimum enforcement
            min_order_size = 10.0  # Exchange minimum
            order_size = base_capital * safe_fraction
            final_order_size = max(order_size, min_order_size)

            # Additional safety: ensure we don't exceed 20% of capital per order
            max_order_size = base_capital * 0.2
            final_order_size = min(final_order_size, max_order_size)

            self.logger.info(
                f"💰 Client {client_id} {symbol}: Kelly={kelly_fraction:.3f}, "
                f"Compound={compound_multiplier:.2f}x, Final=${final_order_size:.2f}"
            )

            return final_order_size

        except Exception as e:
            self.logger.error(
                f"❌ Error calculating order size for client {client_id}: {e}"
            )
            # Safe fallback - ensure minimum viable order
            return max(base_capital * 0.1, 10.0)

    async def get_grid_allocation(self, client_id: int, total_capital: float) -> Dict:
        """
        Calculate dynamic base/enhanced grid allocation based on performance
        """
        try:
            # FIXED: Remove 'await' - this is a sync method
            performance = self._safe_get_performance_metrics(client_id)

            # Base allocation: 40% conservative default
            base_allocation = 0.4

            # Adjust based on performance
            if performance["total_trades"] >= 10:  # Need minimum trade history
                # Performance factors
                win_rate = performance.get("win_rate", 50.0) / 100.0
                profit_factor = performance.get("profit_factor", 1.0)
                total_profit = performance.get("total_profit", 0.0)

                # Good performance: increase enhanced allocation
                if win_rate > 0.6 and profit_factor > 1.2 and total_profit > 0:
                    enhanced_boost = min(
                        0.3, total_profit / 100.0
                    )  # +0.01 per $1 profit
                    base_allocation = max(
                        0.2, 0.4 - enhanced_boost
                    )  # Reduce base allocation

                # Poor performance: increase base allocation
                elif win_rate < 0.4 or total_profit < -50:
                    safety_boost = min(
                        0.3, abs(total_profit) / 200.0
                    )  # +0.005 per $1 loss
                    base_allocation = min(
                        0.8, 0.4 + safety_boost
                    )  # Increase base allocation

            enhanced_allocation = 1.0 - base_allocation

            # Calculate actual capital amounts
            base_capital = total_capital * base_allocation
            enhanced_capital = total_capital * enhanced_allocation

            # Determine reasoning
            if performance["total_trades"] < 10:
                reasoning = "Default allocation (insufficient trade history)"
            elif base_allocation > 0.5:
                reasoning = f"Conservative allocation (poor performance: {win_rate * 100:.1f}% win rate)"
            elif enhanced_allocation > 0.7:
                reasoning = f"Aggressive allocation (strong performance: {win_rate * 100:.1f}% win rate, ${total_profit:.0f} profit)"
            else:
                reasoning = f"Balanced allocation ({win_rate * 100:.1f}% win rate, ${total_profit:.0f} profit)"

            result = {
                "base_allocation": base_allocation,
                "enhanced_allocation": enhanced_allocation,
                "base_capital": base_capital,
                "enhanced_capital": enhanced_capital,
                "reasoning": reasoning,
            }

            self.logger.info(
                f"📊 Client {client_id} allocation: {base_allocation:.1%} base, "
                f"{enhanced_allocation:.1%} enhanced. Reason: {result['reasoning']}"
            )

            return result

        except Exception as e:
            self.logger.error(
                f"❌ Error calculating allocation for client {client_id}: {e}"
            )
            # Safe fallback
            return {
                "base_allocation": 0.4,
                "enhanced_allocation": 0.6,
                "base_capital": total_capital * 0.4,
                "enhanced_capital": total_capital * 0.6,
                "reasoning": "Default allocation due to calculation error",
            }

    async def record_trade_profit(
        self, client_id: int, symbol: str, side: str, profit: float
    ):
        """
        Record trade profit and trigger compound adjustments

        This is called every time a SELL trade completes to update the compound system
        """
        try:
            if side == "SELL":
                # Update performance cache
                await self._update_performance_cache(client_id)

                # Log significant profits
                if abs(profit) > 1.0:  # $1+ profit/loss
                    direction = "profit" if profit > 0 else "loss"
                    self.logger.info(
                        f"💹 Client {client_id} {symbol}: ${profit:.2f} {direction} recorded"
                    )

                # Trigger rebalancing if significant profit
                if profit > 10.0:  # $10+ profit
                    await self._trigger_rebalancing_check(client_id)

        except Exception as e:
            self.logger.error(f"❌ Error recording trade profit: {e}")

    async def _calculate_kelly_fraction(self, client_id: int, symbol: str) -> float:
        """
        Calculate Kelly Criterion optimal fraction for position sizing

        Kelly Formula: f* = (bp - q) / b
        Where:
        - b = odds received on wager (avg_win / avg_loss)
        - p = probability of winning
        - q = probability of losing (1-p)
        """
        try:
            # Get symbol-specific trade history (NOW PROPERLY AWAITED)
            trades = await self._get_symbol_trade_history(client_id, symbol)

            if len(trades) < self.min_trades_for_kelly:
                # Not enough data, use conservative default
                return 0.1  # 10% of capital

            # Separate wins and losses
            wins = [t for t in trades if t.get("profit", 0) > 0]
            losses = [t for t in trades if t.get("profit", 0) < 0]

            if not wins or not losses:
                return 0.1  # Conservative if no wins or no losses

            # Calculate Kelly parameters
            win_rate = len(wins) / len(trades)  # p
            loss_rate = 1 - win_rate  # q

            avg_win = np.mean([t["profit"] for t in wins])
            avg_loss = abs(np.mean([t["profit"] for t in losses]))

            if avg_loss == 0:
                return 0.1  # Avoid division by zero

            win_loss_ratio = avg_win / avg_loss  # b

            # Kelly formula: f* = (bp - q) / b
            kelly_fraction = (win_loss_ratio * win_rate - loss_rate) / win_loss_ratio

            # Apply safety factor (Half-Kelly)
            safe_kelly = kelly_fraction * self.kelly_safety_factor

            # Apply maximum constraint
            final_kelly = max(0.01, min(safe_kelly, self.max_kelly_fraction))

            self.logger.debug(
                f"📊 Kelly calculation for {symbol}: win_rate={win_rate:.2f}, "
                f"win/loss_ratio={win_loss_ratio:.2f}, kelly={kelly_fraction:.3f}, "
                f"safe_kelly={final_kelly:.3f}"
            )

            return final_kelly

        except Exception as e:
            self.logger.error(f"❌ Kelly calculation error for {symbol}: {e}")
            return 0.1  # Conservative fallback

    def _calculate_compound_multiplier(self, client_id: int) -> float:
        """
        Calculate compound multiplier based on accumulated profits

        Logic:
        - Base multiplier = 1.0x (no change)
        - Each $25 of profit increases multiplier by 0.1x
        - Maximum multiplier capped for safety
        - Recent losses reduce multiplier
        """
        try:
            performance = self._safe_get_performance_metrics(client_id)
            total_profit = performance.get("total_profit", 0.0)
            recent_24h_profit = performance.get("recent_24h_profit", 0.0)

            # Base multiplier
            multiplier = 1.0

            # Increase multiplier based on total accumulated profit
            if total_profit > 0:
                profit_multiplier = (
                    1.0 + (total_profit / 25.0) * 0.1
                )  # +0.1x per $25 profit
                multiplier = min(profit_multiplier, self.max_order_size_multiplier)

            # Reduce multiplier for recent losses (risk management)
            if recent_24h_profit < -20.0:  # $20+ daily loss
                loss_reduction = abs(recent_24h_profit) / 100.0  # -0.01x per $1 loss
                multiplier = max(
                    self.min_order_size_multiplier, multiplier - loss_reduction
                )

            # Ensure reasonable bounds
            final_multiplier = max(
                self.min_order_size_multiplier,
                min(self.max_order_size_multiplier, multiplier),
            )

            return final_multiplier

        except Exception as e:
            self.logger.error(f"❌ Compound multiplier calculation error: {e}")
            return 1.0  # No change on error

    def _apply_safety_constraints(
        self, optimal_fraction: float, client_id: int, performance: Dict
    ) -> float:
        """
        Apply safety constraints to prevent over-leveraging
        """
        # Maximum fraction constraints
        safe_fraction = min(optimal_fraction, self.max_kelly_fraction)

        # Minimum fraction
        safe_fraction = max(safe_fraction, 0.01)  # Minimum 1%

        # Drawdown protection
        total_profit = performance.get("total_profit", 0.0)
        if (
            total_profit
            < -performance.get("total_volume", 1000)
            * self.drawdown_protection_threshold
        ):
            # In significant drawdown, reduce position size
            safe_fraction *= 0.5
            self.logger.warning(
                f"⚠️ Client {client_id}: Drawdown protection activated, "
                f"reducing position size by 50%"
            )

        return safe_fraction

    def _get_performance_metrics(self, client_id: int) -> Dict:
        """Get comprehensive performance metrics from FIFO service"""
        try:
            # Check cache first
            cache_key = f"perf_{client_id}"
            if (
                cache_key in self.client_performance
                and time.time() - self.last_update.get(cache_key, 0) < 60
            ):  # 1-minute cache
                return self.client_performance[cache_key]

            # Get fresh data from FIFO service
            performance = self.fifo_service.calculate_fifo_profit_with_cost_basis(
                client_id
            )

            # Cache the result
            self.client_performance[cache_key] = performance
            self.last_update[cache_key] = time.time()

            return performance

        except Exception as e:
            self.logger.error(f"❌ Error getting performance metrics: {e}")
            return {
                "total_trades": 0,
                "total_profit": 0.0,
                "win_rate": 50.0,
                "total_volume": 0.0,
                "recent_24h_profit": 0.0,
                "profit_factor": 1.0,
            }

    async def _get_symbol_trade_history(self, client_id: int, symbol: str) -> list:
        """Get trade history for specific symbol"""
        try:
            # This would integrate with your existing trade repository
            # For now, we'll use FIFO service data filtered by symbol
            summary = self.fifo_service.get_cost_basis_summary(client_id)
            all_trades = self._convert_cost_basis_to_trades(summary, symbol)
            symbol_trades = [t for t in all_trades if t.get("symbol") == symbol]

            # Calculate profit for each trade (simplified)
            for trade in symbol_trades:
                if trade.get("side") == "SELL":
                    # Estimate profit based on grid spacing (2.5% typical)
                    trade["profit"] = trade.get("total_value", 0) * 0.025
                else:
                    trade["profit"] = 0  # Buy trades don't have realized profit yet

            return symbol_trades

        except Exception as e:
            self.logger.error(f"❌ Error getting symbol trade history: {e}")
            return []

    def _convert_cost_basis_to_trades(self, summary: Dict, symbol: str) -> list:
        """Convert cost basis summary to trade-like format for Kelly calculation"""
        trades = []
        try:
            if symbol in summary.get("symbols", {}):
                for record in summary["symbols"][symbol]["records"]:
                    # Add cost basis as BUY trade
                    trades.append(
                        {
                            "symbol": symbol,
                            "side": "BUY",
                            "quantity": record["quantity"],
                            "price": record["cost_per_unit"],
                            "profit": 0,
                            "total_value": record["total_cost"],
                        }
                    )

                    # If some quantity was sold, estimate SELL trades
                    if record["remaining_quantity"] < record["quantity"]:
                        sold_qty = record["quantity"] - record["remaining_quantity"]
                        # Assume 2.5% profit for Kelly calculation
                        sell_price = record["cost_per_unit"] * 1.025
                        profit = sold_qty * record["cost_per_unit"] * 0.025

                        trades.append(
                            {
                                "symbol": symbol,
                                "side": "SELL",
                                "quantity": sold_qty,
                                "price": sell_price,
                                "profit": profit,
                                "total_value": sold_qty * sell_price,
                            }
                        )
        except Exception as e:
            self.logger.error(f"❌ Error converting cost basis to trades: {e}")

        return trades

    async def _update_performance_cache(self, client_id: int):
        """Force update of performance cache"""
        cache_key = f"perf_{client_id}"
        if cache_key in self.client_performance:
            del self.client_performance[cache_key]
        await self._get_performance_metrics(client_id)

    async def _trigger_rebalancing_check(self, client_id: int):
        """Check if grid allocation should be rebalanced based on performance"""
        try:
            performance = await self._safe_get_performance_metrics(client_id)
            # Simple rebalancing logic
            recent_profit = performance.get("recent_24h_profit", 0.0)

            if recent_profit > 50.0:  # $50+ daily profit
                self.logger.info(
                    f"🔄 Client {client_id}: Excellent performance (${recent_profit:.2f}), "
                    f"consider increasing enhanced allocation"
                )
            elif recent_profit < -50.0:  # $50+ daily loss
                self.logger.warning(
                    f"⚠️ Client {client_id}: Poor performance (${recent_profit:.2f}), "
                    f"consider increasing base allocation"
                )

        except Exception as e:
            self.logger.error(f"❌ Rebalancing check error: {e}")

    def _get_allocation_reasoning(
        self, performance: Dict, base_allocation: float
    ) -> str:
        """Generate human-readable reasoning for allocation decision"""
        if performance["total_trades"] < 10:
            return "Default allocation - insufficient trade history"

        win_rate = performance.get("win_rate", 50.0)
        total_profit = performance.get("total_profit", 0.0)

        if base_allocation <= 0.3:
            return f"Aggressive (high performance: {win_rate:.0f}% win rate, ${total_profit:.0f} profit)"
        elif base_allocation >= 0.6:
            return f"Conservative (protecting capital: {win_rate:.0f}% win rate, ${total_profit:.0f} profit)"
        else:
            return f"Balanced ({win_rate:.0f}% win rate, ${total_profit:.0f} profit)"

    async def get_performance_summary(self, client_id: int) -> Dict:
        """Get comprehensive performance summary for monitoring"""
        try:
            # FIXED: Remove 'await' - this is a sync method
            performance = self._safe_get_performance_metrics(client_id)

            # FIXED: Add 'await' for async methods
            kelly_ada = await self._calculate_kelly_fraction(client_id, "ADAUSDT")
            kelly_avax = await self._calculate_kelly_fraction(client_id, "AVAXUSDT")

            # This is sync, no await needed
            compound_multiplier = self._calculate_compound_multiplier(client_id)

            return {
                "total_profit": performance.get("total_profit", 0.0),
                "total_trades": performance.get("total_trades", 0),
                "win_rate": performance.get("win_rate", 0.0),
                "compound_multiplier": compound_multiplier,
                "kelly_fractions": {"ADA": kelly_ada, "AVAX": kelly_avax},
                "current_status": "active" if compound_multiplier > 1.0 else "building",
                "next_multiplier_at": (compound_multiplier * 25)
                + 25,  # Next $25 milestone
            }

        except Exception as e:
            self.logger.error(f"❌ Performance summary error: {e}")
            return {"error": str(e)}

    # Add this method to CompoundInterestManager class
    def _safe_get_performance_metrics(self, client_id: int) -> Dict:
        """Safe version that uses correct FIFO method"""
        try:
            # Use the correct method that exists
            fifo_data = self.fifo_service.calculate_fifo_profit_with_cost_basis(
                client_id
            )

            # Convert to expected format
            return {
                "total_trades": fifo_data.get("total_trades", 0),
                "total_profit": fifo_data.get("total_profit", 0.0),
                "win_rate": fifo_data.get("win_rate", 50.0),
                "total_volume": fifo_data.get("total_profit", 0.0) * 40,
                "recent_24h_profit": fifo_data.get("realized_profit", 0.0),
                "profit_factor": 1.0 + (fifo_data.get("total_profit", 0.0) / 100.0),
            }
        except Exception as e:
            self.logger.error(f"❌ Error getting performance metrics: {e}")
            return {
                "total_trades": 0,
                "total_profit": 0.0,
                "win_rate": 50.0,
                "total_volume": 0.0,
                "recent_24h_profit": 0.0,
                "profit_factor": 1.0,
            }


# Replace the broken _get_performance_metrics call
# OLD: performance = await self._get_performance_metrics(client_id)
# NEW: performance = await self._safe_get_performance_metrics(client_id)
# =============================================================================
# INTEGRATION WITH EXISTING SYSTEM
# =============================================================================


class CompoundIntegrationService:
    """Service to integrate Compound Manager with existing grid system"""

    def __init__(self, fifo_service: FIFOService):
        self.compound_manager = CompoundInterestManager(fifo_service)
        self.fifo_service = fifo_service
        self.logger = logging.getLogger(__name__)

    async def initialize_client(self, client_id: int):
        """Initialize compound interest tracking for a client"""
        try:
            # Set up FIFO callback for real-time profit updates
            # This ensures compound adjustments happen immediately when trades complete
            pass  # Implementation depends on your FIFO service structure

        except Exception as e:
            self.logger.error(f"❌ Client initialization error: {e}")

    async def on_trade_executed(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        profit: float = 0.0,
    ):
        """Handle trade execution for compound adjustments"""
        try:
            # Record trade for compound calculations
            await self.compound_manager.record_trade_profit(
                client_id, symbol, side, profit
            )

            # Log compound status for significant trades
            if side == "SELL" and abs(profit) > 5.0:
                summary = await self.compound_manager.get_performance_summary(client_id)
                self.logger.info(
                    f"📊 Client {client_id} compound status: "
                    f"{summary['compound_multiplier']:.2f}x multiplier, "
                    f"${summary['total_profit']:.2f} total profit"
                )

        except Exception as e:
            self.logger.error(f"❌ Trade execution handling error: {e}")

    async def get_dashboard_metrics(self, client_id: int) -> Dict:
        """Get compound metrics for dashboard display"""
        return await self.compound_manager.get_performance_summary(client_id)
