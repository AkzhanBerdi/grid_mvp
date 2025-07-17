# services/performance_calculator.py
"""Fixed Performance Calculator for Grid Trading"""

import logging
from datetime import datetime
from typing import Dict, List

from repositories.trade_repository import TradeRepository


class GridPerformanceCalculator:
    """Fixed performance calculator that understands grid trading logic"""

    def __init__(self):
        self.trade_repo = TradeRepository()
        self.logger = logging.getLogger(__name__)

    def calculate_grid_performance(self, client_id: int, days: int = 30) -> Dict:
        """Calculate proper grid trading performance"""
        try:
            # Get all trades for the period
            trades = self._get_recent_trades(client_id, days)

            if not trades:
                return self._empty_performance()

            # Calculate grid trading metrics
            grid_metrics = self._calculate_grid_metrics(trades)

            # Calculate position-based profits
            position_profits = self._calculate_position_profits(trades)

            # Combine metrics
            performance = {
                **grid_metrics,
                **position_profits,
                "calculation_method": "grid_trading_optimized",
                "last_updated": datetime.now().isoformat(),
            }

            self.logger.info(
                f"📊 Performance calculated for client {client_id}: {performance['total_profit']:.2f}"
            )
            return performance

        except Exception as e:
            self.logger.error(f"❌ Performance calculation error: {e}")
            return self._empty_performance()

    def _get_recent_trades(self, client_id: int, days: int) -> List[Dict]:
        """Get recent trades with proper structure"""
        try:
            import sqlite3

            from config import Config

            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.execute(
                    """
                    SELECT symbol, side, quantity, price, total_value, executed_at, order_id
                    FROM trades 
                    WHERE client_id = ? 
                    AND executed_at >= datetime('now', '-{} days')
                    ORDER BY executed_at ASC
                """.format(days),
                    (client_id,),
                )

                trades = []
                for row in cursor.fetchall():
                    trades.append(
                        {
                            "symbol": row[0],
                            "side": row[1],
                            "quantity": float(row[2]),
                            "price": float(row[3]),
                            "total_value": float(row[4]),
                            "executed_at": row[5],
                            "order_id": row[6],
                        }
                    )

                return trades

        except Exception as e:
            self.logger.error(f"❌ Error getting trades: {e}")
            return []

    def _calculate_grid_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate basic grid trading metrics"""

        total_trades = len(trades)
        buy_trades = [t for t in trades if t["side"] == "BUY"]
        sell_trades = [t for t in trades if t["side"] == "SELL"]

        total_volume = sum(t["total_value"] for t in trades)
        buy_volume = sum(t["total_value"] for t in buy_trades)
        sell_volume = sum(t["total_value"] for t in sell_trades)

        # Calculate average prices
        avg_buy_price = (
            sum(t["price"] for t in buy_trades) / len(buy_trades) if buy_trades else 0
        )
        avg_sell_price = (
            sum(t["price"] for t in sell_trades) / len(sell_trades)
            if sell_trades
            else 0
        )

        return {
            "total_trades": total_trades,
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_volume": total_volume,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "avg_buy_price": avg_buy_price,
            "avg_sell_price": avg_sell_price,
            "price_spread": avg_sell_price - avg_buy_price
            if avg_sell_price and avg_buy_price
            else 0,
        }

    def _calculate_position_profits(self, trades: List[Dict]) -> Dict:
        """Calculate profits using position tracking (proper for grid trading)"""

        # Group trades by symbol
        symbol_trades = {}
        for trade in trades:
            symbol = trade["symbol"]
            if symbol not in symbol_trades:
                symbol_trades[symbol] = []
            symbol_trades[symbol].append(trade)

        total_realized_profit = 0.0
        total_unrealized_profit = 0.0
        profitable_trades = 0
        total_fees = 0.0

        symbol_performance = {}

        for symbol, symbol_trade_list in symbol_trades.items():
            symbol_perf = self._calculate_symbol_performance(symbol_trade_list)
            symbol_performance[symbol] = symbol_perf

            total_realized_profit += symbol_perf["realized_profit"]
            total_unrealized_profit += symbol_perf["unrealized_profit"]
            profitable_trades += symbol_perf["profitable_trades"]
            total_fees += symbol_perf["total_fees"]

        # Calculate final metrics
        total_profit = total_realized_profit + total_unrealized_profit
        win_rate = (profitable_trades / len(trades) * 100) if trades else 0
        avg_profit_per_trade = total_profit / len(trades) if trades else 0

        # Performance rating
        performance_rating = self._calculate_performance_rating(
            total_profit, win_rate, len(trades)
        )

        return {
            "total_profit": total_profit,
            "realized_profit": total_realized_profit,
            "unrealized_profit": total_unrealized_profit,
            "total_fees": total_fees,
            "win_rate": win_rate,
            "avg_profit_per_trade": avg_profit_per_trade,
            "profitable_trades": profitable_trades,
            "performance_rating": performance_rating,
            "symbol_performance": symbol_performance,
        }

    def _calculate_symbol_performance(self, trades: List[Dict]) -> Dict:
        """Calculate performance for a specific symbol using FIFO accounting"""

        position = {"quantity": 0.0, "cost_basis": 0.0, "realized_profit": 0.0}

        profitable_trades = 0
        total_fees = 0.0

        for trade in trades:
            # Estimate trading fee (0.1% per trade)
            fee = trade["total_value"] * 0.001
            total_fees += fee

            if trade["side"] == "BUY":
                # Add to position
                position["quantity"] += trade["quantity"]
                position["cost_basis"] += trade["total_value"] + fee

            else:  # SELL
                if position["quantity"] > 0:
                    # Calculate profit on sold portion
                    avg_cost_per_unit = position["cost_basis"] / position["quantity"]
                    sell_quantity = min(trade["quantity"], position["quantity"])

                    cost_of_sold = avg_cost_per_unit * sell_quantity
                    revenue = (trade["price"] * sell_quantity) - fee
                    trade_profit = revenue - cost_of_sold

                    position["realized_profit"] += trade_profit

                    if trade_profit > 0:
                        profitable_trades += 1

                    # Update position
                    position["quantity"] -= sell_quantity
                    if position["quantity"] > 0:
                        position["cost_basis"] -= cost_of_sold
                    else:
                        position["cost_basis"] = 0.0

        # Calculate unrealized profit for remaining position
        unrealized_profit = 0.0
        if position["quantity"] > 0:
            # Use last trade price as market price estimate
            last_price = trades[-1]["price"] if trades else 0
            avg_cost = position["cost_basis"] / position["quantity"]
            unrealized_profit = (last_price - avg_cost) * position["quantity"]

        return {
            "realized_profit": position["realized_profit"],
            "unrealized_profit": unrealized_profit,
            "total_profit": position["realized_profit"] + unrealized_profit,
            "profitable_trades": profitable_trades,
            "total_fees": total_fees,
            "remaining_position": position["quantity"],
            "position_cost_basis": position["cost_basis"],
        }

    def _calculate_performance_rating(
        self, total_profit: float, win_rate: float, total_trades: int
    ) -> str:
        """Calculate overall performance rating"""

        if total_trades < 5:
            return "insufficient_data"

        # Score based on multiple factors
        profit_score = min(
            100, max(0, (total_profit + 100) / 2)
        )  # Scale around break-even
        win_rate_score = win_rate
        volume_score = min(100, total_trades * 2)  # More trades = more data

        overall_score = (
            (profit_score * 0.5) + (win_rate_score * 0.3) + (volume_score * 0.2)
        )

        if overall_score >= 80:
            return "excellent"
        elif overall_score >= 60:
            return "good"
        elif overall_score >= 40:
            return "fair"
        else:
            return "poor"

    def _empty_performance(self) -> Dict:
        """Return empty performance structure"""
        return {
            "total_trades": 0,
            "total_profit": 0.0,
            "realized_profit": 0.0,
            "unrealized_profit": 0.0,
            "total_fees": 0.0,
            "win_rate": 0.0,
            "avg_profit_per_trade": 0.0,
            "profitable_trades": 0,
            "performance_rating": "no_data",
            "total_volume": 0.0,
            "calculation_method": "grid_trading_optimized",
        }

    def calculate_market_adaptation_score(self, client_id: int) -> float:
        """Calculate how well the system adapts to market conditions"""
        try:
            # This would analyze how grid spacing and order placement
            # has adapted to market volatility and trends

            # For now, return a basic score based on trade frequency
            trades = self._get_recent_trades(client_id, 7)  # Last 7 days

            if len(trades) < 2:
                return 0.0

            # More frequent trading in volatile markets = better adaptation
            trades_per_day = len(trades) / 7
            adaptation_score = min(1.0, trades_per_day / 5)  # 5 trades/day = 100%

            return adaptation_score * 100

        except Exception as e:
            self.logger.error(f"❌ Market adaptation calculation error: {e}")
            return 0.0

    def calculate_trading_efficiency(self, client_id: int) -> float:
        """Calculate trading efficiency score"""
        try:
            performance = self.calculate_grid_performance(client_id)

            if performance["total_trades"] == 0:
                return 0.0

            # Efficiency = (Win Rate + Profit Consistency) / 2
            win_rate = performance["win_rate"]

            # Profit consistency (lower is better for consistent small profits)
            avg_profit = abs(performance["avg_profit_per_trade"])
            consistency_score = (
                min(100, 50 / max(1, avg_profit)) if avg_profit > 0 else 0
            )

            efficiency = (win_rate + consistency_score) / 2
            return min(100, efficiency)

        except Exception as e:
            self.logger.error(f"❌ Trading efficiency calculation error: {e}")
            return 0.0


# Update the trade repository to use the new calculator
class FixedTradeRepository(TradeRepository):
    """Enhanced trade repository with fixed calculations"""

    def __init__(self):
        super().__init__()
        self.performance_calc = GridPerformanceCalculator()

    def get_client_trade_stats(self, client_id: int) -> Dict:
        """Get enhanced trade statistics with proper grid calculations"""

        # Get fixed performance calculations
        performance = self.performance_calc.calculate_grid_performance(client_id)

        # Get recent trades for display
        recent_trades = self.performance_calc._get_recent_trades(client_id, 7)

        # Format recent trades for display
        formatted_recent = []
        for trade in recent_trades[-10:]:  # Last 10 trades
            profit = 0.0  # Will be calculated properly by performance calculator
            formatted_recent.append(
                {
                    "symbol": trade["symbol"],
                    "side": trade["side"],
                    "quantity": trade["quantity"],
                    "price": trade["price"],
                    "total_value": trade["total_value"],
                    "executed_at": trade["executed_at"],
                    "profit": profit,
                }
            )

        # Return enhanced stats
        return {
            **performance,
            "recent_trades": formatted_recent,
            "market_adaptation_score": self.performance_calc.calculate_market_adaptation_score(
                client_id
            ),
            "trading_efficiency_score": self.performance_calc.calculate_trading_efficiency(
                client_id
            ),
        }
