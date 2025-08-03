# repositories/trade_repository.py
"""
Consolidated Trade Repository
============================

Unified repository combining all trade logging, analytics, and enhanced features.
Consolidates functionality from both trade_repository.py and enhanced_trade_repository.py
"""

import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional

from config import Config


class TradeRepository:
    """
    Consolidated Trade Repository for all trade operations

    Features:
    - Basic trade logging and analytics
    - Enhanced FIFO support with initialization tracking
    - Comprehensive performance metrics
    - Grid order management
    - Database schema validation
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure database schema supports all features"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if trades table has required columns
                cursor.execute("PRAGMA table_info(trades)")
                columns = [col[1] for col in cursor.fetchall()]

                if "is_initialization" not in columns:
                    self.logger.warning(
                        "⚠️ Database schema missing enhanced columns. Some features may be limited."
                    )

        except Exception as e:
            self.logger.error(f"❌ Schema check failed: {e}")

    # ==============================================
    # BASIC TRADE LOGGING (from original repository)
    # ==============================================

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

    # ==============================================
    # ENHANCED TRADE CREATION (from enhanced repository)
    # ==============================================

    async def create_trade(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        total_value: Optional[float] = None,
        executed_at: Optional[float] = None,
        is_initialization: bool = False,
        trade_id: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> str:
        """
        Enhanced trade creation with initialization flag support

        Args:
            client_id: Client identifier
            symbol: Trading pair (e.g., "ADAUSDT")
            side: "BUY" or "SELL"
            quantity: Amount of asset traded
            price: Price per unit
            total_value: Total USD value (calculated if not provided)
            executed_at: Timestamp (defaults to now)
            is_initialization: Whether this is an initialization trade
            trade_id: Optional external trade ID
            order_id: Optional order ID for linking

        Returns:
            Database trade ID as string
        """
        try:
            # Calculate total value if not provided
            if total_value is None:
                total_value = quantity * price

            executed_timestamp = executed_at or time.time()
            executed_datetime = datetime.fromtimestamp(executed_timestamp)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if enhanced schema is available
                cursor.execute("PRAGMA table_info(trades)")
                columns = [col[1] for col in cursor.fetchall()]

                if "is_initialization" in columns:
                    # Use enhanced schema
                    cursor.execute(
                        """
                        INSERT INTO trades 
                        (client_id, symbol, side, quantity, price, total_value, 
                         executed_at, is_initialization, order_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            client_id,
                            symbol,
                            side,
                            quantity,
                            price,
                            total_value,
                            executed_datetime,
                            is_initialization,
                            order_id,
                        ),
                    )
                else:
                    # Fallback to basic schema
                    cursor.execute(
                        """
                        INSERT INTO trades 
                        (client_id, symbol, side, quantity, price, total_value, 
                         executed_at, order_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            client_id,
                            symbol,
                            side,
                            quantity,
                            price,
                            total_value,
                            executed_datetime,
                            order_id,
                        ),
                    )

                db_trade_id = cursor.lastrowid

                self.logger.info(
                    f"✅ Trade created: ID={db_trade_id}, {side} {quantity:.4f} {symbol} @ ${price:.4f}"
                )
                if is_initialization:
                    self.logger.info("   🏁 Marked as initialization trade")

                return str(db_trade_id)

        except Exception as e:
            self.logger.error(f"❌ Error creating trade: {e}")
            raise

    # ==============================================
    # TRADE RETRIEVAL AND ANALYTICS
    # ==============================================

    def get_client_trades(
        self,
        client_id: int,
        symbol: Optional[str] = None,
        include_initialization: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get trades for a client with optional filtering

        Args:
            client_id: Client identifier
            symbol: Optional symbol filter
            include_initialization: Whether to include initialization trades
            limit: Optional limit on results

        Returns:
            List of trade dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Build query
                base_query = """
                    SELECT id, client_id, symbol, side, quantity, price, total_value, 
                           executed_at, order_id,
                           COALESCE(is_initialization, 0) as is_initialization
                    FROM trades 
                    WHERE client_id = ?
                """
                params = [client_id]

                # Add symbol filter
                if symbol:
                    base_query += " AND symbol = ?"
                    params.append(symbol)

                # Add initialization filter
                if not include_initialization:
                    base_query += " AND COALESCE(is_initialization, 0) = 0"

                # Add ordering and limit
                base_query += " ORDER BY executed_at ASC"
                if limit:
                    base_query += f" LIMIT {limit}"

                cursor = conn.execute(base_query, params)
                rows = cursor.fetchall()

                # Convert to dictionaries
                trades = []
                for row in rows:
                    trade = {
                        "id": row[0],
                        "client_id": row[1],
                        "symbol": row[2],
                        "side": row[3],
                        "quantity": row[4],
                        "price": row[5],
                        "total_value": row[6],
                        "executed_at": row[7],
                        "order_id": row[8],
                        "is_initialization": bool(row[9]),
                    }
                    trades.append(trade)

                return trades

        except Exception as e:
            self.logger.error(f"❌ Error getting client trades: {e}")
            return []

    def get_fifo_trade_sequence(self, client_id: int, symbol: str) -> List[Dict]:
        """
        Get trades in FIFO order for profit calculation

        Returns trades ordered by execution time for accurate FIFO processing
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, symbol, side, quantity, price, total_value, executed_at,
                           order_id, COALESCE(is_initialization, 0) as is_initialization
                    FROM trades 
                    WHERE client_id = ? AND symbol = ?
                    ORDER BY executed_at ASC
                """,
                    (client_id, symbol),
                )

                rows = cursor.fetchall()

                trades = []
                for row in rows:
                    trade = {
                        "id": row[0],
                        "symbol": row[1],
                        "side": row[2],
                        "quantity": row[3],
                        "price": row[4],
                        "total_value": row[5],
                        "executed_at": row[6],
                        "order_id": row[7],
                        "is_initialization": bool(row[8]),
                    }
                    trades.append(trade)

                return trades

        except Exception as e:
            self.logger.error(f"❌ Error getting FIFO trade sequence: {e}")
            return []

    def get_initialization_trades(self, client_id: int) -> List[Dict]:
        """Get all initialization trades for a client"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, symbol, side, quantity, price, total_value, executed_at, order_id
                    FROM trades 
                    WHERE client_id = ? AND COALESCE(is_initialization, 0) = 1
                    ORDER BY executed_at ASC
                """,
                    (client_id,),
                )

                rows = cursor.fetchall()

                trades = []
                for row in rows:
                    trade = {
                        "id": row[0],
                        "symbol": row[1],
                        "side": row[2],
                        "quantity": row[3],
                        "price": row[4],
                        "total_value": row[5],
                        "executed_at": row[6],
                        "order_id": row[7],
                        "is_initialization": True,
                    }
                    trades.append(trade)

                return trades

        except Exception as e:
            self.logger.error(f"❌ Error getting initialization trades: {e}")
            return []

    # ==============================================
    # COMPREHENSIVE ANALYTICS
    # ==============================================

    def get_client_trade_stats(self, client_id: int) -> Dict:
        """Get comprehensive trade statistics for a client (original method)"""
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
                        "profit": (row[4] * 0.01) if row[1] == "SELL" else 0,
                    }
                    for row in cursor.fetchall()
                ]

                # Calculate metrics
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

    def get_trade_statistics(
        self, client_id: int, symbol: Optional[str] = None
    ) -> Dict:
        """Get enhanced trade statistics with initialization tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                base_query = """
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN side = 'BUY' THEN 1 END) as buy_trades,
                        COUNT(CASE WHEN side = 'SELL' THEN 1 END) as sell_trades,
                        SUM(CASE WHEN side = 'BUY' THEN total_value ELSE 0 END) as total_bought,
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE 0 END) as total_sold,
                        AVG(total_value) as avg_trade_size,
                        MIN(executed_at) as first_trade,
                        MAX(executed_at) as last_trade,
                        COUNT(CASE WHEN COALESCE(is_initialization, 0) = 1 THEN 1 END) as initialization_trades
                    FROM trades 
                    WHERE client_id = ?
                """

                params = [client_id]
                if symbol:
                    base_query += " AND symbol = ?"
                    params.append(symbol)

                cursor = conn.execute(base_query, params)
                row = cursor.fetchone()

                if row:
                    stats = {
                        "total_trades": row[0] or 0,
                        "buy_trades": row[1] or 0,
                        "sell_trades": row[2] or 0,
                        "total_bought": row[3] or 0.0,
                        "total_sold": row[4] or 0.0,
                        "avg_trade_size": row[5] or 0.0,
                        "first_trade": row[6],
                        "last_trade": row[7],
                        "initialization_trades": row[8] or 0,
                        "simple_profit": (row[4] or 0.0) - (row[3] or 0.0),
                        "has_initialization": (row[8] or 0) > 0,
                    }

                    return stats
                else:
                    return self._empty_statistics()

        except Exception as e:
            self.logger.error(f"❌ Error getting trade statistics: {e}")
            return self._empty_statistics()

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

    # ==============================================
    # DATABASE MANAGEMENT
    # ==============================================

    def verify_database_schema(self) -> Dict:
        """Verify that database schema supports all features"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check trades table
                cursor.execute("PRAGMA table_info(trades)")
                trades_columns = [col[1] for col in cursor.fetchall()]

                # Check FIFO cost basis table
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='fifo_cost_basis'
                """)
                fifo_table_exists = cursor.fetchone() is not None

                fifo_columns = []
                if fifo_table_exists:
                    cursor.execute("PRAGMA table_info(fifo_cost_basis)")
                    fifo_columns = [col[1] for col in cursor.fetchall()]

                required_trades_columns = [
                    "id",
                    "client_id",
                    "symbol",
                    "side",
                    "quantity",
                    "price",
                    "total_value",
                    "executed_at",
                    "is_initialization",
                ]

                required_fifo_columns = [
                    "id",
                    "client_id",
                    "symbol",
                    "quantity",
                    "cost_per_unit",
                    "total_cost",
                    "remaining_quantity",
                    "is_initialization",
                ]

                missing_trades_columns = [
                    col for col in required_trades_columns if col not in trades_columns
                ]

                missing_fifo_columns = (
                    [col for col in required_fifo_columns if col not in fifo_columns]
                    if fifo_table_exists
                    else required_fifo_columns
                )

                schema_valid = (
                    len(missing_trades_columns) == 0
                    and fifo_table_exists
                    and len(missing_fifo_columns) == 0
                )

                return {
                    "schema_valid": schema_valid,
                    "trades_table_ok": len(missing_trades_columns) == 0,
                    "fifo_table_exists": fifo_table_exists,
                    "fifo_table_ok": len(missing_fifo_columns) == 0,
                    "missing_trades_columns": missing_trades_columns,
                    "missing_fifo_columns": missing_fifo_columns,
                    "current_trades_columns": trades_columns,
                    "current_fifo_columns": fifo_columns,
                    "recommendation": "Run database migration script"
                    if not schema_valid
                    else "Schema is ready",
                }

        except Exception as e:
            return {
                "schema_valid": False,
                "error": str(e),
                "recommendation": "Check database connectivity and run migration script",
            }

    def delete_test_trades(self, client_id: int) -> bool:
        """Delete test trades for a specific client (for testing only)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM trades WHERE client_id = ?",
                    (client_id,),
                )

                deleted_count = cursor.rowcount
                self.logger.info(
                    f"🗑️ Deleted {deleted_count} test trades for client {client_id}"
                )

                return True

        except Exception as e:
            self.logger.error(f"❌ Error deleting test trades: {e}")
            return False

    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            "total_trades": 0,
            "buy_trades": 0,
            "sell_trades": 0,
            "total_bought": 0.0,
            "total_sold": 0.0,
            "avg_trade_size": 0.0,
            "first_trade": None,
            "last_trade": None,
            "initialization_trades": 0,
            "simple_profit": 0.0,
            "has_initialization": False,
        }


# ==============================================
# CONVENIENCE FUNCTIONS
# ==============================================


def create_trade_repository(db_path: Optional[str] = None) -> TradeRepository:
    """Factory function to create trade repository"""
    return TradeRepository(db_path)


# Backward compatibility aliases
# EnhancedTradeRepository = TradeRepository
create_enhanced_trade_repository = create_trade_repository
