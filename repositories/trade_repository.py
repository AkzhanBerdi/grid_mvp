# repositories/trade_repository.py
"""Trade repository for logging and analytics"""

import logging
import sqlite3
from typing import Dict, List

from config import Config


class TradeRepository:
    """Repository for trade data and analytics"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

    def log_grid_order(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str,
        grid_level: int,
    ):
        """Log a grid order placement"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO grid_orders (
                        client_id, symbol, side, quantity, price, 
                        order_id, grid_level, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PLACED', CURRENT_TIMESTAMP)
                """,
                    (client_id, symbol, side, quantity, price, order_id, grid_level),
                )

        except Exception as e:
            self.logger.error(f"Error logging grid order: {e}")

    def log_trade_execution(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str,
    ):
        """Log a trade execution"""
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

                # Update grid order status
                conn.execute(
                    """
                    UPDATE grid_orders 
                    SET status = 'FILLED', filled_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """,
                    (order_id,),
                )

        except Exception as e:
            self.logger.error(f"Error logging trade execution: {e}")

    def get_client_trade_stats(self, client_id: int) -> Dict:
        """Get comprehensive trade statistics for a client"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Basic stats
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(total_value) as total_volume,
                        AVG(total_value) as avg_trade_size
                    FROM trades 
                    WHERE client_id = ?
                """,
                    (client_id,),
                )

                basic_stats = cursor.fetchone()

                # Calculate profit (simplified: sell_total - buy_total)
                cursor = conn.execute(
                    """
                    SELECT 
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE 0 END) as sell_total,
                        SUM(CASE WHEN side = 'BUY' THEN total_value ELSE 0 END) as buy_total,
                        COUNT(CASE WHEN side = 'SELL' THEN 1 END) as sell_count,
                        COUNT(CASE WHEN side = 'BUY' THEN 1 END) as buy_count
                    FROM trades 
                    WHERE client_id = ?
                """,
                    (client_id,),
                )

                profit_stats = cursor.fetchone()

                # Recent trades
                cursor = conn.execute(
                    """
                    SELECT symbol, side, quantity, price, total_value, executed_at
                    FROM trades 
                    WHERE client_id = ?
                    ORDER BY executed_at DESC
                    LIMIT 10
                """,
                    (client_id,),
                )

                recent_trades = [
                    {
                        "symbol": row[0],
                        "side": row[1],
                        "quantity": row[2],
                        "price": row[3],
                        "total_value": row[4],
                        "executed_at": row[5],
                        "profit": (row[4] * 0.01)
                        if row[1] == "SELL"
                        else 0,  # Simplified profit calc
                    }
                    for row in cursor.fetchall()
                ]

                # Calculate win rate and profit
                total_trades = basic_stats[0] or 0
                total_volume = basic_stats[1] or 0.0
                avg_trade_size = basic_stats[2] or 0.0

                sell_total = profit_stats[0] or 0.0
                buy_total = profit_stats[1] or 0.0
                sell_count = profit_stats[2] or 0

                total_profit = sell_total - buy_total
                win_rate = (sell_count / total_trades * 100) if total_trades > 0 else 0

                return {
                    "total_trades": total_trades,
                    "total_volume": total_volume,
                    "avg_trade_size": avg_trade_size,
                    "total_profit": total_profit,
                    "win_rate": win_rate,
                    "recent_trades": recent_trades,
                }

        except Exception as e:
            self.logger.error(f"Error getting trade stats for client {client_id}: {e}")
            return {
                "total_trades": 0,
                "total_volume": 0.0,
                "avg_trade_size": 0.0,
                "total_profit": 0.0,
                "win_rate": 0.0,
                "recent_trades": [],
            }

    def get_daily_performance(self, client_id: int, days: int = 30) -> List[Dict]:
        """Get daily performance over specified period"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        DATE(executed_at) as trade_date,
                        COUNT(*) as trades_count,
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE -total_value END) as daily_pnl,
                        SUM(total_value) as daily_volume
                    FROM trades 
                    WHERE client_id = ? 
                    AND executed_at >= datetime('now', '-{} days')
                    GROUP BY DATE(executed_at)
                    ORDER BY trade_date DESC
                """.format(days),
                    (client_id,),
                )

                return [
                    {
                        "date": row[0],
                        "trades": row[1],
                        "pnl": row[2],
                        "volume": row[3],
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            self.logger.error(f"Error getting daily performance: {e}")
            return []

    def get_symbol_performance(self, client_id: int) -> Dict:
        """Get performance breakdown by trading symbol"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        symbol,
                        COUNT(*) as trades,
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE -total_value END) as pnl,
                        SUM(total_value) as volume
                    FROM trades 
                    WHERE client_id = ?
                    GROUP BY symbol
                """,
                    (client_id,),
                )

                return {
                    row[0]: {
                        "trades": row[1],
                        "pnl": row[2],
                        "volume": row[3],
                    }
                    for row in cursor.fetchall()
                }

        except Exception as e:
            self.logger.error(f"Error getting symbol performance: {e}")
            return {}


# repositories/__init__.py
"""Repositories package initialization"""

from services.performance_calculator import FixedTradeRepository

from .client_repository import ClientRepository

__all__ = ["ClientRepository", "FixedTradeRepository"]
