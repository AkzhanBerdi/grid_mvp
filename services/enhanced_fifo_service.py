# services/enhanced_fifo_service.py
"""
Enhanced FIFO Service for Pure USDT Grid Initialization
======================================================

Adds support for recording initial cost basis from pure USDT initialization
Ensures perfect profit tracking from the first trade
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from services.telegram_notifier import TelegramNotifier


class EnhancedFIFOService:
    """
    Enhanced FIFO Service that supports pure USDT grid initialization
    Extends existing FIFO functionality with cost basis management
    """

    def __init__(self, db_path: Optional[str] = None):
        # Your existing __init__ code...
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

        # Add notification support
        try:
            self.telegram = TelegramNotifier()
            self.notifications_enabled = self.telegram.enabled
        except ImportError:
            self.notifications_enabled = False
            self.logger.warning("Telegram notifications not available")

        # Add startup suppression (prevents spam during service startup)
        self.startup_mode = True
        asyncio.get_event_loop().call_later(60, self._disable_startup_mode)

        # Milestone tracking for profit notifications
        self.milestones_reached = set()

        # Error tracking
        self.error_count = 0
        self.last_error_time = 0

    def _disable_startup_mode(self):
        """Disable startup mode to allow normal notifications"""
        self.startup_mode = False
        self.logger.info("📢 FIFO notifications enabled (startup suppression ended)")

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

    async def record_initial_cost_basis(
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
        Record initial asset purchase as FIFO cost basis

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

    def calculate_fifo_profit_with_cost_basis(
        self, client_id: int, symbol: Optional[str] = None
    ) -> Dict:
        """
        Calculate FIFO profit using proper cost basis from initialization

        This ensures accurate profit calculations that account for the initial
        asset purchase during grid setup
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

                return self._calculate_enhanced_fifo_profit(trades, cost_basis_records)

        except Exception as e:
            self.logger.error(f"❌ Enhanced FIFO calculation error: {e}")
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

    def get_cost_basis_summary(
        self, client_id: int, symbol: Optional[str] = None
    ) -> Dict:
        """Get summary of cost basis records for a client"""
        try:
            with sqlite3.connect(self.db_path) as conn:
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

                cursor = conn.execute(query, params)
                records = cursor.fetchall()

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
            self.logger.error(f"❌ Error getting cost basis summary: {e}")
            return {"error": str(e)}

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
            cost_basis_summary = self.get_cost_basis_summary(client_id)

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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT symbol, COUNT(*) as sell_count
                    FROM trades
                    WHERE client_id = ? AND side = 'SELL'
                    GROUP BY symbol
                """,
                    (client_id,),
                )

                sell_counts = dict(cursor.fetchall())

                cursor = conn.execute(
                    """
                    SELECT symbol, COUNT(*) as buy_count
                    FROM trades
                    WHERE client_id = ? AND side = 'BUY'
                    GROUP BY symbol
                """,
                    (client_id,),
                )

                buy_counts = dict(cursor.fetchall())

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
            fifo_profit = self.calculate_fifo_profit_with_cost_basis(client_id)

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

    def log_trade(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str,
    ) -> bool:
        """Compatibility method for legacy FIFOService.log_trade()"""
        # Delegate to your existing trade logging method
        return self.record_trade_execution(
            client_id, symbol, side, quantity, price, order_id
        )

    def get_client_performance(self, client_id: int) -> Dict:
        """Compatibility method for legacy performance calls"""
        return self.calculate_fifo_profit_with_cost_basis(client_id)

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
        Handle order fill with FIFO tracking and notifications
        This replaces the working_fifo_integration.on_order_filled method
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

            # Record the trade in FIFO system
            trade_recorded = await self._record_trade_with_fifo(
                client_id, symbol, side, quantity, price, order_id
            )

            if not trade_recorded:
                self.logger.error("❌ Failed to record trade in FIFO system")
                return False

            # Calculate current profit using FIFO
            profit_data = self.calculate_fifo_profit_with_cost_basis(client_id)
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

    # ========================================================================
    # METHOD 2: on_api_error - Essential for error handling
    # ========================================================================
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
        Handle API errors with intelligent notifications
        This replaces the working_fifo_integration.on_api_error method
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

            # Get current profit for context
            try:
                profit_data = self.calculate_fifo_profit_with_cost_basis(client_id)
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

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def _record_trade_with_fifo(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str = None,
    ) -> bool:
        """Record trade in FIFO system"""
        try:
            # Use your existing trade recording logic
            # This should integrate with your cost basis tracking

            # For BUY orders: record as cost basis
            if side == "BUY":
                cost_basis_id = await self.record_initial_cost_basis(
                    client_id=client_id,
                    symbol=symbol,
                    quantity=quantity,
                    cost_per_unit=price,
                    total_cost=quantity * price,
                    timestamp=time.time(),
                    trade_id=order_id or f"trade_{int(time.time())}",
                )
                return cost_basis_id is not None

            # For SELL orders: record as trade execution
            else:
                # Record in trades table and calculate FIFO profit
                with sqlite3.connect(self.db_path) as conn:
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
                            quantity * price,
                            order_id,
                        ),
                    )
                return True

        except Exception as e:
            self.logger.error(f"❌ Failed to record trade: {e}")
            return False

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
            await self._record_trade_with_fifo(
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

    # ========================================================================
    # COMPATIBILITY METHODS (for legacy code)
    # ========================================================================

    def log_trade(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str,
    ) -> bool:
        """Legacy compatibility method"""
        try:
            # Convert to async call
            return asyncio.create_task(
                self._record_trade_with_fifo(
                    client_id, symbol, side, quantity, price, order_id
                )
            )
        except Exception as e:
            self.logger.error(f"❌ Legacy log_trade error: {e}")
            return False

    # Add to EnhancedFIFOService class:


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
        Replaces APIErrorNotifier.notify_api_error()
        """
        try:
            # Skip during startup to prevent spam
            if self.startup_mode:
                if "CRITICAL" in operation.upper():
                    self.logger.error(
                        f"🚨 CRITICAL API Error: {error_code} - {error_message}"
                    )
                return True

            # Get current profit for context
            try:
                profit_data = self.calculate_fifo_profit_with_cost_basis(client_id)
                total_profit = profit_data.get("total_profit", 0)
            except:
                total_profit = 0

            # Determine severity emoji
            severity_emoji = self._get_error_severity_emoji(error_code)

            # Create comprehensive error message
            message = f"""{severity_emoji} **API Error Alert**

    **Error Details:**
    - Code: `{error_code}`
    - Operation: {operation} {symbol}
    - Client: {client_id}

    **Message:** {error_message[:150]}...

    **Trading Context:**
    - Current Profit: ${total_profit:.2f}
    - Symbol: {symbol}
    - Time: {datetime.now().strftime("%H:%M:%S")}

    🔄 System will retry automatically"""

            # Add helpful context for common errors
            if "insufficient balance" in error_message.lower():
                message += (
                    "\n\n💡 **Note:** Insufficient balance - normal during rapid trading"
                )
            elif "lot_size" in error_message.lower():
                message += "\n\n💡 **Note:** Order size too small - precision issue"
            elif "notional" in error_message.lower():
                message += "\n\n💡 **Note:** Order value too small - minimum $5 required"
            elif error_code in ["-2014", "-1022"]:
                message += "\n\n🚨 **CRITICAL:** Authentication issue - check API keys"

            # Send notification
            success = True
            if self.notifications_enabled:
                success = await self.telegram.send_message(message)

            # Log error appropriately
            if error_code in ["-2014", "-1022", "-1021"]:  # Critical auth errors
                self.logger.critical(
                    f"🚨 CRITICAL API Error: {error_code} - {error_message}"
                )
            else:
                self.logger.error(
                    f"❌ API Error - {operation}: {error_code} - {error_message}"
                )

            return success

        except Exception as e:
            self.logger.error(f"❌ Error in API error handler: {e}")
            return False


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
        Replaces APIErrorNotifier.notify_grid_status()
        """
        try:
            # Skip during startup
            if self.startup_mode:
                self.logger.debug(f"🔇 Grid status notification suppressed: {symbol}")
                return True

            # Get current profit for context
            try:
                profit_data = self.calculate_fifo_profit_with_cost_basis(client_id)
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


    def _get_error_severity_emoji(self, error_code: str) -> str:
        """Get appropriate emoji for error severity"""
        critical_errors = ["-2014", "-1022", "-1021"]  # Auth/signature issues
        high_errors = ["-1013", "-2010", "-1003", "-1015"]  # Trading issues

        if error_code in critical_errors:
            return "🚨"
        elif error_code in high_errors:
            return "❌"
        else:
            return "⚠️"
    
# Integration helper functions
def create_enhanced_fifo_service(db_path: Optional[str] = None) -> EnhancedFIFOService:
    """Factory function to create enhanced FIFO service"""
    return EnhancedFIFOService(db_path)


async def migrate_existing_client_to_enhanced_fifo(
    client_id: int,
    symbol: str,
    current_asset_holdings: float,
    estimated_cost_basis: float,
    fifo_service: EnhancedFIFOService,
) -> Dict:
    """
    Helper function to migrate existing clients to enhanced FIFO tracking

    For clients who already have assets but unknown cost basis
    """
    try:
        # Record estimated cost basis for existing holdings
        total_cost = current_asset_holdings * estimated_cost_basis

        cost_basis_id = await fifo_service.record_initial_cost_basis(
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
