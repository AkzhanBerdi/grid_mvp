# services/working_fifo_integration.py
"""
Enhanced Working FIFO Integration with API Error Notifications
Uses FIFOProfitCalculator directly for accurate results
FIXED: Includes on_api_error method that grid_integration was trying to call
"""

import logging
from datetime import datetime

from analytics.fifo_profit_tracker import FIFOProfitCalculator
from services.telegram_notifier import TelegramNotifier


class WorkingFIFOIntegration:
    """Working integration with API error notifications and FIFO profit tracking"""

    def __init__(self, client_id: int):
        self.client_id = client_id
        self.calculator = FIFOProfitCalculator()  # Use working calculator
        self.telegram = TelegramNotifier()  # Use existing telegram notifier
        self.logger = logging.getLogger(__name__)

        # Milestone tracking
        self.milestones_reached = set()

        # Error tracking
        self.error_count = 0
        self.last_error_time = 0

    async def on_order_filled(
        self, symbol: str, side: str, quantity: float, price: float, level: int = None
    ):
        """Perfect order fill handler with working FIFO data"""
        try:
            # Get profit from working calculator
            performance = self.calculator.calculate_fifo_profit(self.client_id)
            total_profit = performance.get("total_profit", 0)

            order_value = quantity * price
            profit_estimate = 0
            if side == "SELL":
                profit_estimate = order_value * 0.025

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

            # Send notification
            success = await self.telegram.send_message(message)

            # Check milestones with working data
            if side == "SELL" and success:
                milestones = [25, 50, 100, 250, 500, 1000]
                for milestone in milestones:
                    if (
                        total_profit >= milestone
                        and milestone not in self.milestones_reached
                    ):
                        await self._notify_milestone(total_profit, milestone)
                        self.milestones_reached.add(milestone)
                        break

            return success

        except Exception as e:
            self.logger.error(f"Error in working FIFO integration: {e}")
            return False

    async def on_api_error(
        self,
        error_code: str,
        error_message: str,
        symbol: str = None,
        operation: str = "unknown",
        severity: str = "ERROR",
    ):
        """
        🚨 API Error Notification Handler
        This is the method that grid_integration was trying to call!
        """
        try:
            # Track error frequency
            current_time = datetime.now().timestamp()
            self.error_count += 1
            self.last_error_time = current_time

            # Get current profit for context
            try:
                performance = self.calculator.calculate_fifo_profit(self.client_id)
                total_profit = performance.get("total_profit", 0)
            except:
                total_profit = 0

            # Determine severity emoji
            severity_emoji = {
                "CRITICAL": "🚨",
                "ERROR": "❌",
                "WARNING": "⚠️",
                "INFO": "ℹ️",
            }.get(severity, "❌")

            # Create comprehensive error message
            message = f"""{severity_emoji} API ERROR DETECTED

🔍 Operation: {operation}
📊 Symbol: {symbol or "Unknown"}
🏷️ Error Code: {error_code}
📝 Message: {error_message[:100]}...

💰 Current Profit: ${total_profit:.2f}
👤 Client: {self.client_id}
🕐 Time: {datetime.now().strftime("%H:%M:%S")}

🔄 System will retry automatically"""

            # Add context for common errors
            if "insufficient balance" in error_message.lower():
                message += (
                    "\n\n💡 Note: Insufficient balance - normal during rapid trading"
                )
            elif "lot_size" in error_message.lower():
                message += "\n\n💡 Note: Order size too small - precision issue"
            elif "notional" in error_message.lower():
                message += "\n\n💡 Note: Order value too small - minimum $5 required"

            # Send error notification
            success = await self.telegram.send_message(message)

            if success:
                self.logger.info(f"✅ API error notification sent: {error_code}")
            else:
                self.logger.error("❌ Failed to send API error notification")

            # Log for debugging
            self.logger.error(
                f"API Error - {operation}: {error_code} - {error_message}"
            )

            return success

        except Exception as e:
            self.logger.error(f"Error in API error handler: {e}")
            return False

    async def on_order_placement_error(
        self, symbol: str, side: str, quantity: float, price: float, error: Exception
    ):
        """Specific handler for order placement errors"""
        try:
            error_code = str(getattr(error, "code", "UNKNOWN"))
            error_message = str(error)

            # Call the main API error handler
            await self.on_api_error(
                error_code=error_code,
                error_message=error_message,
                symbol=symbol,
                operation=f"order_placement_{side}",
                severity="ERROR",
            )

            # Additional order-specific context
            order_info = f"""
📤 Failed Order Details:
- Symbol: {symbol}
- Side: {side}
- Quantity: {quantity:.6f}
- Price: ${price:.6f}
- Value: ${quantity * price:.2f}"""

            await self.telegram.send_message(order_info)

        except Exception as e:
            self.logger.error(f"Error in order placement error handler: {e}")

    async def on_grid_setup_status(
        self, symbol: str, orders_placed: int, failed_orders: int, success_rate: str
    ):
        """Notify grid setup status"""
        try:
            if failed_orders == 0:
                # Perfect setup
                message = f"""✅ GRID SETUP COMPLETE

📊 Symbol: {symbol}
🎯 Orders Placed: {orders_placed}
📈 Success Rate: {success_rate}

🚀 Grid is active and trading!"""

            elif orders_placed > 0:
                # Partial setup
                message = f"""⚠️ GRID SETUP PARTIAL

📊 Symbol: {symbol}
✅ Orders Placed: {orders_placed}
❌ Failed Orders: {failed_orders}
📈 Success Rate: {success_rate}

🔄 Grid is operational but not complete"""

            else:
                # Failed setup
                message = f"""🚨 GRID SETUP FAILED

📊 Symbol: {symbol}
❌ All {failed_orders} orders failed
📈 Success Rate: {success_rate}

🔧 Check API keys and balance"""

            await self.telegram.send_message(message)

        except Exception as e:
            self.logger.error(f"Error in grid setup notification: {e}")

    async def _notify_milestone(self, total_profit: float, milestone: float):
        """Notify milestone with working data"""
        message = f"""🎉 PROFIT MILESTONE REACHED!

🎯 Milestone: ${milestone:.0f}
💰 Current Profit: ${total_profit:.2f}
👤 Client: {self.client_id}

🚀 Excellent trading performance!"""

        await self.telegram.send_message(message)

    def get_error_stats(self) -> dict:
        """Get error statistics"""
        return {
            "total_errors": self.error_count,
            "last_error_time": self.last_error_time,
            "client_id": self.client_id,
        }

    async def send_daily_summary(self):
        """Send daily profit summary"""
        try:
            performance = self.calculator.calculate_fifo_profit(self.client_id)

            message = f"""📊 DAILY TRADING SUMMARY

💰 Total Profit: ${performance.get("total_profit", 0):.2f}
🔄 Completed Cycles: {performance.get("completed_cycles", 0)}
📈 Win Rate: {performance.get("win_rate", 0):.1f}%
💵 Avg per Trade: ${performance.get("avg_profit_per_trade", 0):.2f}

👤 Client: {self.client_id}
📅 {datetime.now().strftime("%Y-%m-%d")}"""

            await self.telegram.send_message(message)

        except Exception as e:
            self.logger.error(f"Error sending daily summary: {e}")
