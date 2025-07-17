# services/fifo_service.py
"""
Unified FIFO Service - FIXED VERSION
Consolidates all FIFO-related functionality into single service
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional

from analytics.fifo_profit_tracker import FIFOProfitTracker
from config import Config


class FIFOService:
    """
    Unified FIFO calculation and monitoring service - FIXED VERSION
    Eliminates duplicate FIFO code across multiple files
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.profit_tracker = FIFOProfitTracker(self.db_path)
        self.logger = logging.getLogger(__name__)

        # Cache for performance metrics
        self._performance_cache = {}
        self._cache_timestamp = {}
        self._cache_ttl = 30  # 30 seconds cache

    def log_trade(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str,
    ) -> bool:
        """
        Single entry point for all trade logging with FIFO calculation
        Replaces duplicate logging methods across files
        """
        try:
            total_value = quantity * price

            with sqlite3.connect(self.db_path) as conn:
                # Log the trade
                conn.execute(
                    """
                    INSERT INTO trades (
                        client_id, symbol, side, quantity, price, 
                        total_value, order_id, executed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (client_id, symbol, side, quantity, price, total_value, order_id),
                )

                # Update grid order status if exists
                conn.execute(
                    """
                    UPDATE grid_orders 
                    SET status = 'FILLED', filled_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """,
                    (order_id,),
                )

                conn.commit()

            # Trigger FIFO calculation for this client
            self.calculate_fifo_performance(client_id, force_refresh=True)

            self.logger.info(
                f"📊 FIFO: Trade logged for client {client_id}: {side} {quantity} {symbol} @ ${price}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error logging trade for FIFO: {e}")
            return False

    def calculate_fifo_performance(
        self, client_id: int, force_refresh: bool = False
    ) -> Dict:
        """
        Single FIFO performance calculation - FIXED VERSION
        Uses the correct FIFOProfitTracker methods
        """
        cache_key = f"perf_{client_id}"
        current_time = datetime.now().timestamp()

        # Check cache unless forced refresh
        if not force_refresh and cache_key in self._performance_cache:
            if current_time - self._cache_timestamp.get(cache_key, 0) < self._cache_ttl:
                return self._performance_cache[cache_key]

        try:
            # FIXED: Use the correct method name from FIFOProfitTracker
            performance_metrics = self.profit_tracker.calculate_performance_metrics(
                client_id
            )

            # Convert PerformanceMetrics to dict format
            performance = {
                "total_trades": performance_metrics.total_trades,
                "total_profit": performance_metrics.total_realized_profit,
                "total_volume": performance_metrics.total_volume,
                "win_rate": performance_metrics.win_rate,
                "average_profit_per_trade": performance_metrics.average_profit_per_trade,
                "best_trade": performance_metrics.best_trade,
                "worst_trade": performance_metrics.worst_trade,
                "profit_factor": performance_metrics.profit_factor,
                "current_multiplier": performance_metrics.current_multiplier,
                "recent_24h_profit": performance_metrics.recent_24h_profit,
                "winning_trades": performance_metrics.winning_trades,
                "losing_trades": performance_metrics.losing_trades,
            }

            # Enhanced metrics calculation
            enhanced_metrics = self._calculate_enhanced_metrics(client_id)
            performance.update(enhanced_metrics)

            # Get recent trades for display
            recent_trades = self._get_recent_trades_formatted(client_id)
            performance["recent_trades"] = recent_trades

            # Cache the result
            self._performance_cache[cache_key] = performance
            self._cache_timestamp[cache_key] = current_time

            return performance

        except Exception as e:
            self.logger.error(
                f"Error calculating FIFO performance for client {client_id}: {e}"
            )
            return self._get_fallback_performance()

    def _get_recent_trades_formatted(self, client_id: int, limit: int = 10) -> list:
        """Get recent trades in formatted display format"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT executed_at, symbol, side, quantity, price, total_value
                    FROM trades 
                    WHERE client_id = ?
                    ORDER BY executed_at DESC
                    LIMIT ?
                """,
                    (client_id, limit),
                )

                trades = []
                for row in cursor.fetchall():
                    trades.append(
                        {
                            "executed_at": row[0],
                            "symbol": row[1],
                            "side": row[2],
                            "quantity": row[3],
                            "price": row[4],
                            "total_value": row[5],
                        }
                    )

                return trades

        except Exception as e:
            self.logger.error(f"Error getting recent trades: {e}")
            return []

    def _calculate_enhanced_metrics(self, client_id: int) -> Dict:
        """Calculate additional metrics for enhanced display"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Recent 24h performance
                cursor = conn.execute(
                    """
                    SELECT side, SUM(total_value) as volume
                    FROM trades 
                    WHERE client_id = ? AND executed_at > datetime('now', '-24 hours')
                    GROUP BY side
                """,
                    (client_id,),
                )

                daily_volume = {"BUY": 0.0, "SELL": 0.0}
                for row in cursor.fetchall():
                    daily_volume[row[0]] = row[1]

                # Active grid count
                cursor = conn.execute(
                    """
                    SELECT COUNT(DISTINCT symbol) as active_symbols
                    FROM grid_orders 
                    WHERE client_id = ? AND status = 'PENDING'
                """,
                    (client_id,),
                )

                active_grids = cursor.fetchone()[0] or 0

                return {
                    "daily_buy_volume": daily_volume["BUY"],
                    "daily_sell_volume": daily_volume["SELL"],
                    "daily_net_volume": daily_volume["SELL"] - daily_volume["BUY"],
                    "active_grids": active_grids,
                    "trading_efficiency": self._calculate_efficiency(daily_volume),
                }

        except Exception as e:
            self.logger.error(f"Error calculating enhanced metrics: {e}")
            return {
                "daily_buy_volume": 0.0,
                "daily_sell_volume": 0.0,
                "daily_net_volume": 0.0,
                "active_grids": 0,
                "trading_efficiency": 0.0,
            }

    def _calculate_efficiency(self, daily_volume: Dict) -> float:
        """Calculate trading efficiency score"""
        total_volume = daily_volume["BUY"] + daily_volume["SELL"]
        if total_volume == 0:
            return 0.0

        # Efficiency = how balanced the trading is (closer to 50/50 = better)
        buy_ratio = daily_volume["BUY"] / total_volume
        efficiency = 1.0 - abs(buy_ratio - 0.5) * 2  # 0-1 scale
        return efficiency * 100  # Convert to percentage

    def _get_fallback_performance(self) -> Dict:
        """Fallback performance data when calculation fails"""
        return {
            "total_trades": 0,
            "total_volume": 0.0,
            "total_profit": 0.0,
            "win_rate": 0.0,
            "recent_trades": [],
            "daily_buy_volume": 0.0,
            "daily_sell_volume": 0.0,
            "daily_net_volume": 0.0,
            "active_grids": 0,
            "trading_efficiency": 0.0,
            "average_profit_per_trade": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "profit_factor": 0.0,
            "current_multiplier": 1.0,
            "recent_24h_profit": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
        }

    def get_display_metrics(self, client_id: int) -> Dict:
        """
        Single method for getting formatted display metrics
        Replaces multiple formatting methods
        """
        performance = self.calculate_fifo_performance(client_id)

        # Format for display
        return {
            "total_profit_display": self._format_profit_display(
                performance["total_profit"]
            ),
            "volume_display": f"${performance['total_volume']:,.0f}",
            "win_rate_display": f"{performance['win_rate']:.1f}%",
            "efficiency_display": f"{performance.get('trading_efficiency', 0):.1f}%",
            "daily_volume_display": f"${performance.get('daily_buy_volume', 0) + performance.get('daily_sell_volume', 0):,.0f}",
            "active_grids_display": f"{performance.get('active_grids', 0)} grids",
            "performance_summary": self._generate_performance_summary(performance),
            "multiplier_display": f"{performance.get('current_multiplier', 1.0):.2f}x",
            "recent_profit_display": self._format_profit_display(
                performance.get("recent_24h_profit", 0)
            ),
        }

    def _format_profit_display(self, profit: float) -> str:
        """User-friendly profit display"""
        if profit < 0:
            return f"🔄 Building: ${abs(profit):.2f}"
        elif profit == 0:
            return "⚖️ Balanced: $0.00"
        else:
            return f"💰 Profit: ${profit:.2f}"

    def _generate_performance_summary(self, performance: Dict) -> str:
        """Generate human-readable performance summary"""
        total_trades = performance.get("total_trades", 0)
        profit = performance.get("total_profit", 0)
        efficiency = performance.get("trading_efficiency", 0)

        if total_trades == 0:
            return "🔄 Getting started - trades will appear soon"
        elif profit < 0:
            return f"📊 {total_trades} trades - Building positions strategically"
        elif efficiency > 80:
            return (
                f"🎯 {total_trades} trades - Excellent efficiency ({efficiency:.0f}%)"
            )
        elif efficiency > 60:
            return f"✅ {total_trades} trades - Good performance ({efficiency:.0f}%)"
        else:
            return f"📈 {total_trades} trades - Optimizing strategy"

    def get_all_clients_summary(self) -> Dict:
        """
        Get performance summary for all clients
        Used by monitoring dashboard
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT client_id FROM trades 
                    WHERE executed_at > datetime('now', '-7 days')
                """)

                active_clients = [row[0] for row in cursor.fetchall()]

                total_profit = 0.0
                total_volume = 0.0
                client_summaries = []

                for client_id in active_clients:
                    performance = self.calculate_fifo_performance(client_id)
                    total_profit += performance.get("total_profit", 0)
                    total_volume += performance.get("total_volume", 0)

                    client_summaries.append(
                        {
                            "client_id": client_id,
                            "profit": performance.get("total_profit", 0),
                            "volume": performance.get("total_volume", 0),
                            "trades": performance.get("total_trades", 0),
                            "win_rate": performance.get("win_rate", 0),
                            "efficiency": performance.get("trading_efficiency", 0),
                        }
                    )

                return {
                    "total_clients": len(active_clients),
                    "total_profit": total_profit,
                    "total_volume": total_volume,
                    "client_summaries": client_summaries,
                    "avg_profit": total_profit / len(active_clients)
                    if active_clients
                    else 0,
                }

        except Exception as e:
            self.logger.error(f"Error getting all clients summary: {e}")
            return {
                "total_clients": 0,
                "total_profit": 0.0,
                "total_volume": 0.0,
                "client_summaries": [],
                "avg_profit": 0.0,
            }

    # Additional convenience methods for integration
    def get_simple_profit(self, client_id: int) -> float:
        """Get simple profit value for quick checks"""
        try:
            performance = self.calculate_fifo_performance(client_id)
            return performance.get("total_profit", 0.0)
        except Exception as e:
            self.logger.error(f"Error getting simple profit: {e}")
            return 0.0

    def get_trade_count(self, client_id: int) -> int:
        """Get total trade count for client"""
        try:
            performance = self.calculate_fifo_performance(client_id)
            return performance.get("total_trades", 0)
        except Exception as e:
            self.logger.error(f"Error getting trade count: {e}")
            return 0

    def is_performing_well(self, client_id: int) -> bool:
        """Quick performance check"""
        try:
            performance = self.calculate_fifo_performance(client_id)
            win_rate = performance.get("win_rate", 0)
            efficiency = performance.get("trading_efficiency", 0)

            # Consider performing well if win rate > 50% and efficiency > 60%
            return win_rate > 50 and efficiency > 60
        except Exception as e:
            self.logger.error(f"Error checking performance: {e}")
            return False

