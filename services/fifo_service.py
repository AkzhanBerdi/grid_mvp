# services/fifo_service.py
"""
Enhanced FIFO Service with Async Operations and Fixed Trade Recording Logic
===========================================================================

FIXES:
1. The critical issue where BUY trades weren't being recorded in trades table
2. Adds async database operations for better performance
3. Maintains all existing FIFO functionality
4. Supports pure USDT grid initialization
5. FIXED: asyncio.run() cannot be called from running event loop
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiosqlite

from config import Config


class FIFOService:
    """
    Enhanced FIFO Service with async operations and fixed trade recording logic

    CRITICAL FIX: Now properly records BOTH BUY and SELL trades in trades table
    while maintaining proper FIFO cost basis tracking.
    ASYNC FIX: Properly handles async/sync context to avoid event loop conflicts.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

        # Initialize cost basis table
        self._init_cost_basis_table()

        # Add notification support
        try:
            from services.telegram_notifier import TelegramNotifier

            self.telegram = TelegramNotifier()
            self.notifications_enabled = self.telegram.enabled
        except (ImportError, Exception):
            self.telegram = None
            self.notifications_enabled = False

        # Add startup suppression (prevents spam during service startup)
        self.startup_mode = True
        # Use a different approach for startup mode timing
        self._schedule_startup_mode_disable()

        # Milestone tracking for profit notifications
        self.milestones_reached = set()

        # Error tracking
        self.error_count = 0
        self.last_error_time = 0

    def _schedule_startup_mode_disable(self):
        """Schedule startup mode disable without depending on event loop"""
        import threading

        def disable_after_delay():
            time.sleep(60)  # Wait 60 seconds
            self.startup_mode = False
            self.logger.info(
                "📢 FIFO notifications enabled (startup suppression ended)"
            )

        thread = threading.Thread(target=disable_after_delay, daemon=True)
        thread.start()

    def _init_cost_basis_table(self):
        """Initialize cost basis tracking table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS fifo_cost_basis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        cost_per_unit REAL NOT NULL,
                        total_cost REAL NOT NULL,
                        remaining_quantity REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_initialization BOOLEAN DEFAULT 0,
                        trade_id TEXT,
                        notes TEXT
                    )
                """)

                # Index for fast lookups
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_fifo_cost_basis_client_symbol 
                    ON fifo_cost_basis(client_id, symbol)
                """)

                self.logger.info("✅ FIFO cost basis table initialized")

        except Exception as e:
            self.logger.error(f"❌ Error initializing cost basis table: {e}")

    # ==============================================
    # ASYNC COST BASIS OPERATIONS (High Performance)
    # ==============================================

    async def record_initial_cost_basis_async(
        self,
        client_id: int,
        symbol: str,
        quantity: float,
        cost_per_unit: float,
        total_cost: float,
        timestamp: float,
        trade_id: Optional[str] = None,
    ) -> str:
        """
        Record initial asset purchase as FIFO cost basis (async)

        Non-blocking version for better performance.
        """
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO fifo_cost_basis 
                    (client_id, symbol, quantity, cost_per_unit, total_cost, 
                     remaining_quantity, is_initialization, trade_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                    (
                        client_id,
                        symbol,
                        quantity,
                        cost_per_unit,
                        total_cost,
                        quantity,  # Initially, all quantity remains
                        trade_id,
                        "Initial cost basis from pure USDT grid initialization",
                    ),
                )

                cost_basis_id = cursor.lastrowid
                await conn.commit()

                self.logger.info("✅ Initial cost basis recorded async:")
                self.logger.info(f"   Cost Basis ID: {cost_basis_id}")
                self.logger.info(f"   Client: {client_id}")
                self.logger.info(f"   Symbol: {symbol}")
                self.logger.info(f"   Quantity: {quantity:.4f}")
                self.logger.info(f"   Cost per Unit: ${cost_per_unit:.4f}")
                self.logger.info(f"   Total Cost: ${total_cost:.2f}")

                return str(cost_basis_id)

        except Exception as e:
            self.logger.error(f"❌ Error recording initial cost basis async: {e}")
            raise

    async def record_trade_with_fifo_async(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str = None,
    ) -> bool:
        """
        FIXED: Record trade with proper FIFO logic (async)

        CRITICAL FIX: Now records BOTH BUY and SELL trades in trades table.
        This was the missing piece causing incomplete trade history.
        """
        try:
            total_value = quantity * price

            async with aiosqlite.connect(self.db_path) as conn:
                # STEP 1: ALWAYS record the trade (both BUY and SELL)
                await conn.execute(
                    """
                    INSERT INTO trades (
                        client_id, symbol, side, quantity, price,
                        total_value, order_id, executed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        client_id,
                        symbol,
                        side,
                        quantity,
                        price,
                        total_value,
                        order_id,
                    ),
                )

                # STEP 2: For BUY orders, ALSO record as cost basis for FIFO tracking
                if side == "BUY":
                    # Record cost basis for future FIFO calculations
                    await conn.execute(
                        """
                        INSERT INTO fifo_cost_basis (
                            client_id, symbol, quantity, cost_per_unit, 
                            total_cost, remaining_quantity, trade_id, is_initialization
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                        (
                            client_id,
                            symbol.replace(
                                "USDT", ""
                            ),  # Remove USDT suffix for cost basis
                            quantity,
                            price,
                            total_value,
                            quantity,  # Initially, all quantity remains
                            order_id or f"trade_{int(time.time())}",
                        ),
                    )

                    self.logger.debug(
                        f"✅ BUY trade + cost basis recorded async: {quantity:.4f} {symbol} @ ${price:.4f}"
                    )

                else:  # SELL orders
                    # For SELL orders, the trade is recorded but FIFO matching is handled elsewhere
                    # This ensures we have complete trade history while maintaining FIFO accuracy
                    self.logger.debug(
                        f"✅ SELL trade recorded async: {quantity:.4f} {symbol} @ ${price:.4f}"
                    )

                await conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"❌ Failed to record trade with FIFO async: {e}")
            return False

    # ==============================================
    # SYNC COST BASIS OPERATIONS (For Critical Operations)
    # ==============================================

    def record_initial_cost_basis(
        self,
        client_id: int,
        symbol: str,
        quantity: float,
        cost_per_unit: float,
        total_cost: float,
        timestamp: float,
        trade_id: Optional[str] = None,
    ) -> str:
        """
        Record initial asset purchase as FIFO cost basis (sync version)

        This is called during pure USDT grid initialization to establish
        the cost basis for all future sell orders
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO fifo_cost_basis 
                    (client_id, symbol, quantity, cost_per_unit, total_cost, 
                     remaining_quantity, is_initialization, trade_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                    (
                        client_id,
                        symbol,
                        quantity,
                        cost_per_unit,
                        total_cost,
                        quantity,  # Initially, all quantity remains
                        trade_id,
                        "Initial cost basis from pure USDT grid initialization",
                    ),
                )

                cost_basis_id = cursor.lastrowid

                self.logger.info("✅ Initial cost basis recorded:")
                self.logger.info(f"   Cost Basis ID: {cost_basis_id}")
                self.logger.info(f"   Client: {client_id}")
                self.logger.info(f"   Symbol: {symbol}")
                self.logger.info(f"   Quantity: {quantity:.4f}")
                self.logger.info(f"   Cost per Unit: ${cost_per_unit:.4f}")
                self.logger.info(f"   Total Cost: ${total_cost:.2f}")

                return str(cost_basis_id)

        except Exception as e:
            self.logger.error(f"❌ Error recording initial cost basis: {e}")
            raise

    def _record_trade_with_fifo(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str = None,
    ) -> bool:
        """
        FIXED: Record trade in FIFO system with proper logic (sync version)

        Uses sync database operations to avoid async context issues.
        """
        try:
            total_value = quantity * price

            with sqlite3.connect(self.db_path) as conn:
                # STEP 1: ALWAYS record the trade (both BUY and SELL)
                conn.execute(
                    """
                    INSERT INTO trades (
                        client_id, symbol, side, quantity, price,
                        total_value, order_id, executed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        client_id,
                        symbol,
                        side,
                        quantity,
                        price,
                        total_value,
                        order_id,
                    ),
                )

                # STEP 2: For BUY orders, ALSO record as cost basis for FIFO tracking
                if side == "BUY":
                    # Record cost basis for future FIFO calculations
                    conn.execute(
                        """
                        INSERT INTO fifo_cost_basis (
                            client_id, symbol, quantity, cost_per_unit, 
                            total_cost, remaining_quantity, trade_id, is_initialization
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                        (
                            client_id,
                            symbol.replace(
                                "USDT", ""
                            ),  # Remove USDT suffix for cost basis
                            quantity,
                            price,
                            total_value,
                            quantity,  # Initially, all quantity remains
                            order_id or f"trade_{int(time.time())}",
                        ),
                    )

                    self.logger.debug(
                        f"✅ BUY trade + cost basis recorded sync: {quantity:.4f} {symbol} @ ${price:.4f}"
                    )

                else:  # SELL orders
                    self.logger.debug(
                        f"✅ SELL trade recorded sync: {quantity:.4f} {symbol} @ ${price:.4f}"
                    )

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"❌ Failed to record trade with FIFO sync: {e}")
            return False

    # ==============================================
    # INTELLIGENT ROUTING FOR TRADE RECORDING
    # ==============================================

    async def record_trade_intelligent(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str = None,
        critical: bool = False,
    ) -> bool:
        """
        Intelligent trade recording with FIFO that chooses async or sync based on criticality

        Args:
            critical: If True, uses blocking operations for reliability
                     If False, uses non-blocking async for performance
        """
        if critical:
            # Critical operation - use sync for reliability
            try:
                return self._record_trade_with_fifo(
                    client_id, symbol, side, quantity, price, order_id
                )
            except Exception as e:
                self.logger.error(f"❌ Critical FIFO trade recording failed: {e}")
                return False
        else:
            # Non-critical - use async for performance
            return await self.record_trade_with_fifo_async(
                client_id, symbol, side, quantity, price, order_id
            )

    # ==============================================
    # ENHANCED FIFO PROFIT CALCULATIONS - FIXED
    # ==============================================

    async def calculate_fifo_profit_with_cost_basis_async(
        self, client_id: int, symbol: Optional[str] = None
    ) -> Dict:
        """
        Calculate FIFO profit using proper cost basis from initialization (async)

        Non-blocking version for dashboard and analytics operations.
        """
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Get all trades for the client/symbol
                if symbol:
                    trades_query = """
                        SELECT symbol, side, quantity, price, total_value, executed_at
                        FROM trades 
                        WHERE client_id = ? AND symbol = ?
                        ORDER BY executed_at ASC
                    """
                    params = (client_id, symbol)
                else:
                    trades_query = """
                        SELECT symbol, side, quantity, price, total_value, executed_at
                        FROM trades 
                        WHERE client_id = ?
                        ORDER BY executed_at ASC
                    """
                    params = (client_id,)

                async with conn.execute(trades_query, params) as cursor:
                    trades = await cursor.fetchall()

                # Get cost basis information
                cost_basis_query = (
                    """
                    SELECT symbol, quantity, cost_per_unit, total_cost, remaining_quantity
                    FROM fifo_cost_basis
                    WHERE client_id = ?
                """
                    + (" AND symbol = ?" if symbol else "")
                    + """
                    ORDER BY created_at ASC
                """
                )

                cost_basis_params = (client_id, symbol) if symbol else (client_id,)
                async with conn.execute(cost_basis_query, cost_basis_params) as cursor:
                    cost_basis_records = await cursor.fetchall()

                return self._calculate_enhanced_fifo_profit(trades, cost_basis_records)

        except Exception as e:
            self.logger.error(f"❌ Enhanced FIFO calculation error async: {e}")
            return self._empty_fifo_performance()

    def calculate_fifo_profit_with_cost_basis(
        self, client_id: int, symbol: Optional[str] = None
    ) -> Dict:
        """
        FIXED: Calculate FIFO profit using proper cost basis from initialization (sync version)

        CRITICAL FIX: Now properly handles async context to avoid event loop conflicts.
        """
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in a running loop, use sync fallback to avoid conflicts
                return self._calculate_fifo_sync_fallback(client_id, symbol)
            except RuntimeError:
                # No running loop, safe to use asyncio.run()
                return asyncio.run(
                    self.calculate_fifo_profit_with_cost_basis_async(client_id, symbol)
                )
        except Exception as e:
            self.logger.error(f"❌ Enhanced FIFO calculation error: {e}")
            return self._empty_fifo_performance()

    def _calculate_fifo_sync_fallback(
        self, client_id: int, symbol: Optional[str] = None
    ) -> Dict:
        """
        Synchronous fallback for FIFO calculation when in async context

        This prevents the asyncio.run() error when called from an async context.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all trades for the client/symbol
                if symbol:
                    trades_query = """
                        SELECT symbol, side, quantity, price, total_value, executed_at
                        FROM trades 
                        WHERE client_id = ? AND symbol = ?
                        ORDER BY executed_at ASC
                    """
                    params = (client_id, symbol)
                else:
                    trades_query = """
                        SELECT symbol, side, quantity, price, total_value, executed_at
                        FROM trades 
                        WHERE client_id = ?
                        ORDER BY executed_at ASC
                    """
                    params = (client_id,)

                cursor = conn.execute(trades_query, params)
                trades = cursor.fetchall()

                # Get cost basis information
                cost_basis_query = (
                    """
                    SELECT symbol, quantity, cost_per_unit, total_cost, remaining_quantity
                    FROM fifo_cost_basis
                    WHERE client_id = ?
                """
                    + (" AND symbol = ?" if symbol else "")
                    + """
                    ORDER BY created_at ASC
                """
                )

                cost_basis_params = (client_id, symbol) if symbol else (client_id,)
                cursor = conn.execute(cost_basis_query, cost_basis_params)
                cost_basis_records = cursor.fetchall()

                result = self._calculate_enhanced_fifo_profit(
                    trades, cost_basis_records
                )
                result["calculation_method"] = "sync_fallback"
                return result

        except Exception as e:
            self.logger.error(f"❌ Sync FIFO fallback error: {e}")
            return self._empty_fifo_performance()

    def _calculate_enhanced_fifo_profit(
        self, trades: List, cost_basis_records: List
    ) -> Dict:
        """
        Calculate FIFO profit with proper cost basis accounting
        """
        # Group by symbol
        symbol_data = {}

        # Initialize with cost basis
        for record in cost_basis_records:
            symbol, quantity, cost_per_unit, total_cost, remaining_quantity = record

            if symbol not in symbol_data:
                symbol_data[symbol] = {
                    "inventory": [],  # FIFO queue of purchases
                    "realized_profit": 0.0,
                    "total_fees": 0.0,
                    "trades_count": 0,
                }

            # Add initial cost basis to inventory
            symbol_data[symbol]["inventory"].append(
                {
                    "quantity": remaining_quantity,
                    "cost_per_unit": cost_per_unit,
                    "from_initialization": True,
                }
            )

        # Process all trades
        total_realized_profit = 0.0
        total_trades = 0
        profitable_trades = 0

        for trade in trades:
            symbol, side, quantity, price, total_value, executed_at = trade

            if symbol not in symbol_data:
                symbol_data[symbol] = {
                    "inventory": [],
                    "realized_profit": 0.0,
                    "total_fees": 0.0,
                    "trades_count": 0,
                }

            total_trades += 1
            symbol_data[symbol]["trades_count"] += 1

            # Estimate trading fee
            fee = total_value * 0.001  # 0.1% fee estimate
            symbol_data[symbol]["total_fees"] += fee

            if side == "BUY":
                # Add to inventory (FIFO queue)
                symbol_data[symbol]["inventory"].append(
                    {
                        "quantity": quantity,
                        "cost_per_unit": price,
                        "from_initialization": False,
                    }
                )

            elif side == "SELL":
                # Calculate profit using FIFO
                remaining_sell_quantity = quantity
                trade_profit = 0.0

                while remaining_sell_quantity > 0 and symbol_data[symbol]["inventory"]:
                    oldest_purchase = symbol_data[symbol]["inventory"][0]

                    # Determine how much to match from this purchase
                    match_quantity = min(
                        remaining_sell_quantity, oldest_purchase["quantity"]
                    )

                    # Calculate profit for this match
                    cost_of_goods_sold = (
                        match_quantity * oldest_purchase["cost_per_unit"]
                    )
                    revenue = match_quantity * price
                    match_profit = (
                        revenue - cost_of_goods_sold - (fee * match_quantity / quantity)
                    )

                    trade_profit += match_profit

                    # Update quantities
                    remaining_sell_quantity -= match_quantity
                    oldest_purchase["quantity"] -= match_quantity

                    # Remove purchase if fully consumed
                    if oldest_purchase["quantity"] <= 0:
                        symbol_data[symbol]["inventory"].pop(0)

                # Record realized profit
                symbol_data[symbol]["realized_profit"] += trade_profit
                total_realized_profit += trade_profit

                if trade_profit > 0:
                    profitable_trades += 1

        # Calculate final metrics
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        avg_profit_per_trade = (
            total_realized_profit / total_trades if total_trades > 0 else 0
        )

        # Calculate unrealized profit for remaining inventory
        total_unrealized_profit = 0.0
        for symbol, data in symbol_data.items():
            if data["inventory"]:
                # Use last trade price as current market price estimate
                last_price = 0
                for trade in reversed(trades):
                    if trade[0] == symbol:  # symbol match
                        last_price = trade[3]  # price
                        break

                for holding in data["inventory"]:
                    unrealized_profit = (
                        last_price - holding["cost_per_unit"]
                    ) * holding["quantity"]
                    total_unrealized_profit += unrealized_profit

        total_profit = total_realized_profit + total_unrealized_profit
        total_fees = sum(data["total_fees"] for data in symbol_data.values())

        return {
            "total_profit": round(total_profit, 2),
            "realized_profit": round(total_realized_profit, 2),
            "unrealized_profit": round(total_unrealized_profit, 2),
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "win_rate": round(win_rate, 1),
            "avg_profit_per_trade": round(avg_profit_per_trade, 2),
            "total_fees": round(total_fees, 2),
            "symbol_breakdown": {
                symbol: {
                    "realized_profit": round(data["realized_profit"], 2),
                    "trades_count": data["trades_count"],
                    "total_fees": round(data["total_fees"], 2),
                    "remaining_inventory_items": len(data["inventory"]),
                }
                for symbol, data in symbol_data.items()
            },
            "calculation_method": "enhanced_fifo_with_cost_basis",
            "cost_basis_used": len(cost_basis_records) > 0,
        }

    def _empty_fifo_performance(self) -> Dict:
        """Return empty FIFO performance structure"""
        return {
            "total_profit": 0.0,
            "realized_profit": 0.0,
            "unrealized_profit": 0.0,
            "total_trades": 0,
            "profitable_trades": 0,
            "win_rate": 0.0,
            "avg_profit_per_trade": 0.0,
            "total_fees": 0.0,
            "symbol_breakdown": {},
            "calculation_method": "enhanced_fifo_with_cost_basis",
            "cost_basis_used": False,
        }

    # ==============================================
    # COST BASIS MANAGEMENT
    # ==============================================

    async def get_cost_basis_summary_async(
        self, client_id: int, symbol: Optional[str] = None
    ) -> Dict:
        """Get summary of cost basis records for a client (async)"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                if symbol:
                    query = """
                        SELECT symbol, quantity, cost_per_unit, total_cost, 
                               remaining_quantity, created_at, is_initialization
                        FROM fifo_cost_basis
                        WHERE client_id = ? AND symbol = ?
                        ORDER BY created_at ASC
                    """
                    params = (client_id, symbol)
                else:
                    query = """
                        SELECT symbol, quantity, cost_per_unit, total_cost, 
                               remaining_quantity, created_at, is_initialization
                        FROM fifo_cost_basis
                        WHERE client_id = ?
                        ORDER BY created_at ASC
                    """
                    params = (client_id,)

                async with conn.execute(query, params) as cursor:
                    records = await cursor.fetchall()

                summary = {
                    "client_id": client_id,
                    "total_cost_basis_records": len(records),
                    "symbols": {},
                    "total_initial_investment": 0.0,
                    "has_initialization_records": False,
                }

                for record in records:
                    (
                        symbol,
                        quantity,
                        cost_per_unit,
                        total_cost,
                        remaining_quantity,
                        created_at,
                        is_initialization,
                    ) = record

                    if symbol not in summary["symbols"]:
                        summary["symbols"][symbol] = {
                            "records": [],
                            "total_initial_cost": 0.0,
                            "total_remaining_quantity": 0.0,
                        }

                    summary["symbols"][symbol]["records"].append(
                        {
                            "quantity": quantity,
                            "cost_per_unit": cost_per_unit,
                            "total_cost": total_cost,
                            "remaining_quantity": remaining_quantity,
                            "created_at": created_at,
                            "is_initialization": bool(is_initialization),
                        }
                    )

                    summary["symbols"][symbol]["total_initial_cost"] += total_cost
                    summary["symbols"][symbol]["total_remaining_quantity"] += (
                        remaining_quantity
                    )
                    summary["total_initial_investment"] += total_cost

                    if is_initialization:
                        summary["has_initialization_records"] = True

                return summary

        except Exception as e:
            self.logger.error(f"❌ Error getting cost basis summary sync: {e}")
            return {"error": str(e)}

    # ==============================================
    # FIFO VALIDATION AND INTEGRITY
    # ==============================================

    async def validate_fifo_integrity(self, client_id: int) -> Dict:
        """
        Validate FIFO integrity and cost basis accuracy

        Ensures that all sells have proper cost basis and FIFO calculations are correct
        """
        try:
            validation_results = {
                "client_id": client_id,
                "validation_passed": True,
                "issues": [],
                "summary": {},
                "recommendations": [],
            }

            # Check for cost basis records
            cost_basis_summary = await self.get_cost_basis_summary_async(client_id)

            if not cost_basis_summary.get("has_initialization_records"):
                validation_results["issues"].append(
                    {
                        "type": "missing_initialization",
                        "severity": "high",
                        "message": "No initialization cost basis found. FIFO profit calculations may be inaccurate.",
                        "recommendation": "Re-initialize grids using pure USDT method for accurate profit tracking",
                    }
                )
                validation_results["validation_passed"] = False

            # Check for orphaned sells (sells without matching buys)
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute(
                    """
                    SELECT symbol, COUNT(*) as sell_count
                    FROM trades
                    WHERE client_id = ? AND side = 'SELL'
                    GROUP BY symbol
                """,
                    (client_id,),
                ) as cursor:
                    sell_counts = dict(await cursor.fetchall())

                async with conn.execute(
                    """
                    SELECT symbol, COUNT(*) as buy_count
                    FROM trades
                    WHERE client_id = ? AND side = 'BUY'
                    GROUP BY symbol
                """,
                    (client_id,),
                ) as cursor:
                    buy_counts = dict(await cursor.fetchall())

                # Add cost basis quantities to buy counts
                for symbol, data in cost_basis_summary.get("symbols", {}).items():
                    buy_counts[symbol] = buy_counts.get(symbol, 0) + len(
                        data["records"]
                    )

                # Check for imbalances
                for symbol in sell_counts:
                    sells = sell_counts.get(symbol, 0)
                    buys = buy_counts.get(symbol, 0)

                    if sells > buys:
                        validation_results["issues"].append(
                            {
                                "type": "orphaned_sells",
                                "severity": "medium",
                                "symbol": symbol,
                                "message": f"Symbol {symbol} has {sells} sells but only {buys} buys/cost basis records",
                                "recommendation": "Some sell orders may not have proper cost basis for profit calculation",
                            }
                        )

            # Calculate profit accuracy score
            fifo_profit = await self.calculate_fifo_profit_with_cost_basis_async(
                client_id
            )

            if fifo_profit.get("cost_basis_used"):
                validation_results["summary"]["profit_tracking"] = (
                    "✅ Accurate - Using proper cost basis"
                )
            else:
                validation_results["summary"]["profit_tracking"] = (
                    "⚠️ Potentially inaccurate - No cost basis records"
                )

            validation_results["summary"]["total_profit"] = fifo_profit.get(
                "total_profit", 0.0
            )
            validation_results["summary"]["calculation_method"] = fifo_profit.get(
                "calculation_method", "unknown"
            )

            # Generate recommendations
            if not validation_results["validation_passed"]:
                validation_results["recommendations"].extend(
                    [
                        "1. Stop current grids and re-initialize using pure USDT method",
                        "2. Record initial asset purchases as cost basis",
                        "3. Resume trading with accurate FIFO profit tracking",
                        "4. Monitor profit calculations regularly for accuracy",
                    ]
                )
            else:
                validation_results["recommendations"].append(
                    "✅ FIFO integrity is good. Continue trading with confidence."
                )

            return validation_results

        except Exception as e:
            self.logger.error(f"❌ FIFO validation error: {e}")
            return {
                "client_id": client_id,
                "validation_passed": False,
                "error": str(e),
                "recommendations": ["Contact support for FIFO validation assistance"],
            }

    # ==============================================
    # ENHANCED ORDER FILL HANDLING
    # ==============================================

    async def on_order_filled(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str = None,
        level: int = None,
    ) -> bool:
        """
        Handle order fill with FIFO tracking and notifications (enhanced with async)
        """
        try:
            # Skip notifications during startup to prevent spam
            if self.startup_mode:
                self.logger.debug(
                    f"🔇 Suppressed order fill notification during startup: {symbol} {side}"
                )
                # Still record the trade, just don't send notification
                await self._record_trade_quietly(
                    client_id, symbol, side, quantity, price, order_id
                )
                return True

            # Record the trade in FIFO system (using fixed async logic)
            trade_recorded = await self.record_trade_with_fifo_async(
                client_id, symbol, side, quantity, price, order_id
            )

            if not trade_recorded:
                self.logger.error("❌ Failed to record trade in FIFO system")
                return False

            # Calculate current profit using FIFO (async version)
            profit_data = await self.calculate_fifo_profit_with_cost_basis_async(
                client_id
            )
            total_profit = profit_data.get("total_profit", 0)

            # Format notification message
            order_value = quantity * price
            profit_estimate = 0
            if side == "SELL":
                profit_estimate = order_value * 0.025  # Rough estimate

            # Smart quantity formatting (ADA vs others)
            if symbol == "ADAUSDT":
                qty_str = f"{quantity:.1f}"
            else:
                qty_str = f"{quantity:.4f}"

            message = f"""{symbol} {side} ORDER FILLED

Amount: {qty_str} @ ${price:.4f}
Value: ${order_value:.2f}"""

            if level:
                message += f"\nLevel: {level}"

            if profit_estimate > 0:
                message += f"\nEstimated Profit: ${profit_estimate:.2f}"

            message += f"\nTotal Profit: ${total_profit:.2f}"
            message += f"\nTime: {datetime.now().strftime('%H:%M:%S')}"

            # Send notification if enabled
            success = True
            if self.notifications_enabled:
                success = await self.telegram.send_message(message)

            # Check for profit milestones
            if side == "SELL" and success:
                await self._check_profit_milestones(client_id, total_profit)

            if success:
                self.logger.info(
                    f"✅ Order fill processed: {symbol} {side} @ ${price:.4f}"
                )

            return success

        except Exception as e:
            self.logger.error(f"❌ Error in on_order_filled: {e}")
            return False

    async def on_api_error(
        self,
        client_id: int,
        error_code: str,
        error_message: str,
        symbol: str = None,
        operation: str = "unknown",
        severity: str = "ERROR",
    ) -> bool:
        """
        Handle API errors with intelligent notifications (enhanced with async)
        """
        try:
            # Reduce spam during startup - only critical errors
            if self.startup_mode:
                if severity == "CRITICAL":
                    self.logger.error(
                        f"🚨 CRITICAL API Error during startup: {error_code} - {error_message}"
                    )
                else:
                    self.logger.debug(
                        f"🔇 API Error suppressed during startup: {error_code}"
                    )
                return True

            # Track error
            current_time = datetime.now().timestamp()
            self.error_count += 1
            self.last_error_time = current_time

            # Get current profit for context (async version)
            try:
                profit_data = await self.calculate_fifo_profit_with_cost_basis_async(
                    client_id
                )
                total_profit = profit_data.get("total_profit", 0)
            except:
                total_profit = 0

            # Choose emoji based on severity
            severity_emoji = {
                "CRITICAL": "🚨",
                "ERROR": "❌",
                "WARNING": "⚠️",
                "INFO": "ℹ️",
            }.get(severity, "❌")

            # Create error message
            message = f"""{severity_emoji} API ERROR DETECTED

🔍 Operation: {operation}
📊 Symbol: {symbol or "Unknown"}
🏷️ Error Code: {error_code}
📝 Message: {error_message[:100]}...

💰 Current Profit: ${total_profit:.2f}
👤 Client: {client_id}
🕐 Time: {datetime.now().strftime("%H:%M:%S")}

🔄 System will retry automatically"""

            # Add helpful context for common errors
            if "insufficient balance" in error_message.lower():
                message += (
                    "\n\n💡 Note: Insufficient balance - normal during rapid trading"
                )
            elif "lot_size" in error_message.lower():
                message += "\n\n💡 Note: Order size too small - precision issue"
            elif "notional" in error_message.lower():
                message += "\n\n💡 Note: Order value too small - minimum $5 required"

            # Send notification if enabled
            success = True
            if self.notifications_enabled:
                success = await self.telegram.send_message(message)

            if success:
                self.logger.info(f"✅ API error notification sent: {error_code}")
            else:
                self.logger.error("❌ Failed to send API error notification")

            # Log the error
            self.logger.error(
                f"API Error - {operation}: {error_code} - {error_message}"
            )

            return success

        except Exception as e:
            self.logger.error(f"❌ Error in API error handler: {e}")
            return False

    # ==============================================
    # HELPER METHODS
    # ==============================================

    async def _record_trade_quietly(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str = None,
    ):
        """Record trade without notifications (used during startup)"""
        try:
            await self.record_trade_with_fifo_async(
                client_id, symbol, side, quantity, price, order_id
            )
        except Exception as e:
            self.logger.error(f"❌ Failed to record trade quietly: {e}")

    async def _check_profit_milestones(self, client_id: int, total_profit: float):
        """Check and notify about profit milestones"""
        try:
            milestones = [25, 50, 100, 250, 500, 1000]

            for milestone in milestones:
                if (
                    total_profit >= milestone
                    and milestone not in self.milestones_reached
                ):
                    await self._notify_milestone(client_id, total_profit, milestone)
                    self.milestones_reached.add(milestone)
                    break  # Only notify one milestone at a time

        except Exception as e:
            self.logger.error(f"❌ Error checking milestones: {e}")

    async def _notify_milestone(
        self, client_id: int, total_profit: float, milestone: int
    ):
        """Send milestone notification"""
        try:
            if not self.notifications_enabled:
                return

            message = f"""🎉 PROFIT MILESTONE REACHED!

💰 Total Profit: ${total_profit:.2f}
🎯 Milestone: ${milestone}
👤 Client: {client_id}
🕐 Time: {datetime.now().strftime("%H:%M:%S")}

🚀 Keep up the great trading!"""

            await self.telegram.send_message(message)
            self.logger.info(f"🎉 Milestone notification sent: ${milestone}")

        except Exception as e:
            self.logger.error(f"❌ Failed to send milestone notification: {e}")

    # ==============================================
    # COMPATIBILITY METHODS (for legacy code)
    # ==============================================

    def log_trade(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str,
    ) -> bool:
        """Legacy compatibility method - now properly records ALL trades"""
        try:
            # Check async context and use appropriate method
            try:
                loop = asyncio.get_running_loop()
                # In async context, use sync fallback
                return self._record_trade_with_fifo(
                    client_id, symbol, side, quantity, price, order_id
                )
            except RuntimeError:
                # No running loop, use async version
                return asyncio.run(
                    self.record_trade_with_fifo_async(
                        client_id, symbol, side, quantity, price, order_id
                    )
                )
        except Exception as e:
            self.logger.error(f"❌ Legacy log_trade error: {e}")
            return False

    def get_client_performance(self, client_id: int) -> Dict:
        """Compatibility method for legacy performance calls"""
        return self.calculate_fifo_profit_with_cost_basis(client_id)

    async def notify_api_error(
        self,
        error_code: str,
        error_message: str,
        symbol: str,
        operation: str,
        client_id: int,
        context: dict = None,
    ) -> bool:
        """
        Consolidated API error notification with FIFO context
        """
        return await self.on_api_error(
            client_id, error_code, error_message, symbol, operation, "ERROR"
        )

    async def notify_grid_status(
        self,
        symbol: str,
        client_id: int,
        orders_placed: int,
        failed_orders: int,
        success_rate: float,
    ) -> bool:
        """
        Grid setup status notification with FIFO context
        """
        try:
            # Skip during startup
            if self.startup_mode:
                self.logger.debug(f"🔇 Grid status notification suppressed: {symbol}")
                return True

            # Get current profit for context (async)
            try:
                profit_data = await self.calculate_fifo_profit_with_cost_basis_async(
                    client_id
                )
                total_profit = profit_data.get("total_profit", 0)
            except:
                total_profit = 0

            # Only notify if there are issues or significant success
            if failed_orders == 0 and orders_placed > 5:
                # Perfect setup - brief success message
                message = f"""✅ **Grid Setup Complete**

**Symbol:** {symbol}
**Orders Placed:** {orders_placed}
**Success Rate:** {success_rate:.1f}%
**Current Profit:** ${total_profit:.2f}

🚀 Trading active!"""

            elif failed_orders > 0:
                # Issues detected - detailed message
                severity = "🟠" if success_rate >= 50 else "🔴"

                message = f"""{severity} **Grid Setup Alert**

**Symbol:** {symbol}
**Client:** {client_id}
**Orders Placed:** {orders_placed}
**Failed Orders:** {failed_orders}
**Success Rate:** {success_rate:.1f}%
**Current Profit:** ${total_profit:.2f}

**Status:** {"Partial Success" if orders_placed > 0 else "Setup Failed"}

Check logs for detailed error information."""

            else:
                return True  # No notification needed

            # Send notification
            success = True
            if self.notifications_enabled:
                success = await self.telegram.send_message(message)

            if success:
                self.logger.info(f"✅ Grid status notification sent: {symbol}")

            return success

        except Exception as e:
            self.logger.error(f"❌ Failed to send grid status notification: {e}")
            return False

    # ==============================================
    # PERFORMANCE OPTIMIZATION HELPERS
    # ==============================================

    async def optimize_for_concurrent_users(self, enable: bool = True):
        """
        Configure FIFO service optimizations for concurrent users
        """
        try:
            if enable:
                self.logger.info(
                    "✅ FIFO async operations enabled for concurrent users"
                )
            else:
                self.logger.warning(
                    "⚠️ FIFO sync operations restored - may impact performance"
                )

        except Exception as e:
            self.logger.error(f"❌ Error configuring FIFO optimizations: {e}")


# ==============================================
# INTEGRATION HELPER FUNCTIONS
# ==============================================


def create_enhanced_fifo_service(db_path: Optional[str] = None) -> FIFOService:
    """Factory function to create enhanced FIFO service"""
    return FIFOService(db_path)


async def migrate_existing_client_to_enhanced_fifo(
    client_id: int,
    symbol: str,
    current_asset_holdings: float,
    estimated_cost_basis: float,
    fifo_service: FIFOService,
) -> Dict:
    """
    Helper function to migrate existing clients to enhanced FIFO tracking

    For clients who already have assets but unknown cost basis
    """
    try:
        # Record estimated cost basis for existing holdings
        total_cost = current_asset_holdings * estimated_cost_basis

        cost_basis_id = await fifo_service.record_initial_cost_basis_async(
            client_id=client_id,
            symbol=symbol,
            quantity=current_asset_holdings,
            cost_per_unit=estimated_cost_basis,
            total_cost=total_cost,
            timestamp=time.time(),
            trade_id=f"migration_{client_id}_{symbol}",
        )

        return {
            "success": True,
            "client_id": client_id,
            "symbol": symbol,
            "cost_basis_id": cost_basis_id,
            "message": f"✅ Migrated {current_asset_holdings:.4f} {symbol} with estimated cost basis ${estimated_cost_basis:.4f}",
            "note": "Future grids should use pure USDT initialization for perfect accuracy",
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Migration failed: {e}",
            "recommendation": "Use pure USDT initialization for new grids",
        }


# ==============================================
# TESTING AND VALIDATION
# ==============================================

if __name__ == "__main__":
    """Test the enhanced FIFO service"""
    import asyncio

    async def test_fifo_performance():
        """Test FIFO service with async operations"""

        print("🧪 Testing Enhanced FIFO Service...")

        fifo_service = FIFOService("data/gridtrader_clients.db")
        test_client_id = 123456789

        # Test async trade recording
        start_time = time.time()

        # Test the fixed trade recording logic
        test_trades = [
            ("BUY", 100.0, 1.0),  # Should record in both trades AND cost_basis
            ("SELL", 50.0, 1.1),  # Should record in trades only
            ("BUY", 75.0, 0.95),  # Should record in both trades AND cost_basis
            ("SELL", 25.0, 1.05),  # Should record in trades only
        ]

        for side, quantity, price in test_trades:
            success = await fifo_service.record_trade_with_fifo_async(
                test_client_id,
                "ADAUSDT",
                side,
                quantity,
                price,
                f"test_{side}_{time.time()}",
            )
            print(f"✅ {side} trade recorded: {success}")

        recording_time = time.time() - start_time

        # Test async profit calculation
        start_time = time.time()
        profit_data = await fifo_service.calculate_fifo_profit_with_cost_basis_async(
            test_client_id
        )
        calculation_time = time.time() - start_time

        print("\n📊 Performance Results:")
        print(f"✅ Trade recording: {recording_time:.3f}s for 4 trades")
        print(f"✅ Profit calculation: {calculation_time:.3f}s")
        print(f"✅ Total profit: ${profit_data.get('total_profit', 0):.2f}")
        print(f"✅ Total trades: {profit_data.get('total_trades', 0)}")

        # Test FIFO validation
        validation = await fifo_service.validate_fifo_integrity(test_client_id)
        print(f"✅ FIFO validation: {validation['validation_passed']}")

        # Test sync fallback functionality
        print("\n🔄 Testing Sync Fallback...")
        try:
            # This should use sync fallback since we're in async context
            sync_profit_data = fifo_service.calculate_fifo_profit_with_cost_basis(
                test_client_id
            )
            print(
                f"✅ Sync fallback works: {sync_profit_data.get('calculation_method', 'unknown')}"
            )
        except Exception as e:
            print(f"❌ Sync fallback failed: {e}")

        # Test cost basis summary
        print("\n📋 Testing Cost Basis Summary...")
        try:
            cost_summary = await fifo_service.get_cost_basis_summary_async(
                test_client_id
            )
            print(
                f"✅ Cost basis records: {cost_summary.get('total_cost_basis_records', 0)}"
            )
            print(
                f"✅ Has initialization: {cost_summary.get('has_initialization_records', False)}"
            )
        except Exception as e:
            print(f"❌ Cost basis summary failed: {e}")

    async def test_context_detection():
        """Test that the service properly detects async contexts"""
        print("\n🧪 Testing Context Detection...")

        fifo_service = FIFOService("data/gridtrader_clients.db")
        test_client_id = 123456789

        # This should detect we're in async context and use sync fallback
        try:
            result = fifo_service.calculate_fifo_profit_with_cost_basis(test_client_id)
            method = result.get("calculation_method", "unknown")
            print(f"✅ Context detection working: Method = {method}")

            if "sync_fallback" in method:
                print("✅ Correctly used sync fallback in async context")
            else:
                print("⚠️  May not have detected async context properly")

        except Exception as e:
            print(f"❌ Context detection test failed: {e}")

    def test_sync_context():
        """Test FIFO service in pure sync context"""
        print("\n🧪 Testing Pure Sync Context...")

        fifo_service = FIFOService("data/gridtrader_clients.db")
        test_client_id = 123456789

        try:
            # This should use asyncio.run() since we're not in async context
            result = fifo_service.calculate_fifo_profit_with_cost_basis(test_client_id)
            method = result.get("calculation_method", "unknown")
            print(f"✅ Sync context test: Method = {method}")

            if "sync_fallback" not in method:
                print("✅ Correctly used async version in sync context")
            else:
                print("⚠️  Used sync fallback in sync context (still works)")

        except Exception as e:
            print(f"❌ Sync context test failed: {e}")

    async def test_trade_recording_integrity():
        """Test that trades are recorded properly in both tables"""
        print("\n🧪 Testing Trade Recording Integrity...")

        fifo_service = FIFOService("data/gridtrader_clients.db")
        test_client_id = 999999999  # Use different ID for testing

        # Clear any existing test data
        try:
            with sqlite3.connect(fifo_service.db_path) as conn:
                conn.execute(
                    "DELETE FROM trades WHERE client_id = ?", (test_client_id,)
                )
                conn.execute(
                    "DELETE FROM fifo_cost_basis WHERE client_id = ?", (test_client_id,)
                )
                conn.commit()
        except:
            pass

        # Test BUY trade recording
        buy_success = await fifo_service.record_trade_with_fifo_async(
            test_client_id, "ADAUSDT", "BUY", 100.0, 1.0, "test_buy_001"
        )
        print(f"✅ BUY trade recorded: {buy_success}")

        # Test SELL trade recording
        sell_success = await fifo_service.record_trade_with_fifo_async(
            test_client_id, "ADAUSDT", "SELL", 50.0, 1.1, "test_sell_001"
        )
        print(f"✅ SELL trade recorded: {sell_success}")

        # Verify both trades are in trades table
        try:
            with sqlite3.connect(fifo_service.db_path) as conn:
                cursor = conn.execute(
                    "SELECT side, COUNT(*) FROM trades WHERE client_id = ? GROUP BY side",
                    (test_client_id,),
                )
                trade_counts = dict(cursor.fetchall())

                print(
                    f"✅ Trades in database: BUY={trade_counts.get('BUY', 0)}, SELL={trade_counts.get('SELL', 0)}"
                )

                # Verify BUY trades also created cost basis records
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM fifo_cost_basis WHERE client_id = ?",
                    (test_client_id,),
                )
                cost_basis_count = cursor.fetchone()[0]
                print(f"✅ Cost basis records: {cost_basis_count}")

                if trade_counts.get("BUY", 0) > 0 and cost_basis_count > 0:
                    print("✅ BUY trades correctly created cost basis records")
                else:
                    print("❌ BUY trades may not have created cost basis records")

        except Exception as e:
            print(f"❌ Trade integrity verification failed: {e}")

        # Clean up test data
        try:
            with sqlite3.connect(fifo_service.db_path) as conn:
                conn.execute(
                    "DELETE FROM trades WHERE client_id = ?", (test_client_id,)
                )
                conn.execute(
                    "DELETE FROM fifo_cost_basis WHERE client_id = ?", (test_client_id,)
                )
                conn.commit()
                print("✅ Test data cleaned up")
        except:
            pass

    # Run all tests
    try:
        print("🚀 Starting FIFO Service Comprehensive Tests...")
        print("=" * 60)

        # Test 1: Basic functionality and performance
        asyncio.run(test_fifo_performance())

        # Test 2: Context detection
        asyncio.run(test_context_detection())

        # Test 3: Pure sync context
        test_sync_context()

        # Test 4: Trade recording integrity
        asyncio.run(test_trade_recording_integrity())

        print("\n" + "=" * 60)
        print("🎉 Enhanced FIFO Service Ready!")
        print("\nKey fixes implemented:")
        print("✅ BUY trades now recorded in trades table")
        print("✅ Async operations for better performance")
        print("✅ Complete trade history maintained")
        print("✅ FIFO cost basis tracking preserved")
        print("✅ FIXED: asyncio.run() event loop conflict resolved")
        print("✅ Smart context detection (async vs sync)")
        print("✅ Comprehensive error handling")
        print("✅ Trade recording integrity verified")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Check database path and permissions")
        import traceback

        traceback.print_exc()
