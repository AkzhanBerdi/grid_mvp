# services/api_error_notifier.py - NEW FILE
"""
API Error Notification System
Sends immediate alerts for any API errors or critical issues
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict

from models.single_advanced_grid_config import SingleAdvancedGridConfig

try:
    from services.telegram_notifier import TelegramNotifier

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("TelegramNotifier not available for API error notifications")


class ErrorSeverity(Enum):
    LOW = "🟡"
    MEDIUM = "🟠"
    HIGH = "🔴"
    CRITICAL = "🚨"


@dataclass
class APIError:
    timestamp: float
    error_code: str
    error_message: str
    symbol: str
    operation: str
    severity: ErrorSeverity
    client_id: int
    context: Dict


class APIErrorNotifier:
    """
    Comprehensive API error notification system
    Sends immediate alerts for trading issues
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        if TELEGRAM_AVAILABLE:
            self.telegram = TelegramNotifier()
            self.notifications_enabled = self.telegram.enabled
        else:
            self.notifications_enabled = False

        # Error tracking
        self.error_history = []
        self.error_counts = {}
        self.last_notification = {}

        # Rate limiting (prevent spam)
        self.notification_cooldown = 300  # 5 minutes between similar errors

        # Critical error codes that need immediate attention
        self.critical_errors = {
            "-1013": "FILTER_FAILURE",  # Price/quantity precision
            "-2010": "INSUFFICIENT_BALANCE",
            "-1021": "TIMESTAMP_ERROR",
            "-1022": "SIGNATURE_ERROR",
            "-2013": "NO_SUCH_ORDER",
            "-2014": "BAD_API_KEY",
            "-1003": "TOO_MANY_REQUESTS",
            "-1015": "TOO_MANY_ORDERS",
        }

        self.logger.info("🚨 API Error Notifier initialized")
        if self.notifications_enabled:
            self.logger.info("   📱 Telegram notifications: ENABLED")
        else:
            self.logger.warning("   📱 Telegram notifications: DISABLED")

    async def notify_api_error(
        self,
        error_code: str,
        error_message: str,
        symbol: str,
        operation: str,
        client_id: int,
        context: Dict = None,
    ):
        """
        Send immediate notification for API errors
        """
        try:
            # Determine severity
            severity = self._get_error_severity(error_code, error_message)

            # Create error record
            api_error = APIError(
                timestamp=time.time(),
                error_code=error_code,
                error_message=error_message,
                symbol=symbol,
                operation=operation,
                severity=severity,
                client_id=client_id,
                context=context or {},
            )

            # Track error
            self.error_history.append(api_error)
            error_key = f"{error_code}_{symbol}_{operation}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

            # Log error
            self._log_error(api_error)

            # Send notification if enabled and not rate limited
            if self.notifications_enabled and self._should_notify(api_error):
                await self._send_error_notification(api_error)

        except Exception as e:
            self.logger.error(f"❌ Failed to notify API error: {e}")

    def _get_error_severity(self, error_code: str, error_message: str) -> ErrorSeverity:
        """Determine error severity based on code and message"""

        # Critical errors that break trading
        if error_code in ["-2014", "-1022", "-1021"]:  # Auth/signature issues
            return ErrorSeverity.CRITICAL

        # High priority errors
        if error_code in ["-1013", "-2010", "-1003", "-1015"]:
            return ErrorSeverity.HIGH

        # Medium priority
        if error_code in ["-2013", "-1121", "-1100"]:
            return ErrorSeverity.MEDIUM

        # Low priority for other errors
        return ErrorSeverity.LOW

    def _should_notify(self, api_error: APIError) -> bool:
        """Check if we should send notification (rate limiting)"""

        # Always notify critical errors
        if api_error.severity == ErrorSeverity.CRITICAL:
            return True

        # Rate limit other errors
        error_key = f"{api_error.error_code}_{api_error.symbol}"
        last_notification = self.last_notification.get(error_key, 0)

        if time.time() - last_notification > self.notification_cooldown:
            self.last_notification[error_key] = time.time()
            return True

        return False

    def _log_error(self, api_error: APIError):
        """Log error with appropriate severity"""

        count = self.error_counts.get(
            f"{api_error.error_code}_{api_error.symbol}_{api_error.operation}", 1
        )

        log_message = (
            f"{api_error.severity.value} API ERROR #{count}: "
            f"{api_error.operation} {api_error.symbol} - "
            f"Code {api_error.error_code}: {api_error.error_message}"
        )

        if api_error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif api_error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif api_error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    async def _send_error_notification(self, api_error: APIError):
        """Send Telegram notification for error"""
        try:
            # Get error description
            error_description = self.critical_errors.get(
                api_error.error_code, "Unknown error"
            )

            # Count occurrences
            error_key = (
                f"{api_error.error_code}_{api_error.symbol}_{api_error.operation}"
            )
            count = self.error_counts.get(error_key, 1)

            # Create notification message
            message = f"""{api_error.severity.value} **API Error Alert**

**Error Details:**
• Code: `{api_error.error_code}` ({error_description})
• Operation: {api_error.operation} {api_error.symbol}
• Client: {api_error.client_id}
• Count: {count} occurrence(s)

**Message:** {api_error.error_message}

**Time:** {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(api_error.timestamp))}"""

            # Add context if available
            if api_error.context:
                context_info = []
                for key, value in api_error.context.items():
                    if key in ["quantity", "price", "notional"]:
                        context_info.append(f"• {key.title()}: {value}")

                if context_info:
                    message += "\n\n**Context:**\n" + "\n".join(context_info)

            # Add recommended actions for common errors
            if api_error.error_code == "-1013":
                message += (
                    "\n\n**🔧 Recommended Action:** Check price/quantity precision"
                )
            elif api_error.error_code == "-2010":
                message += "\n\n**💰 Recommended Action:** Check account balance"
            elif api_error.error_code == "-1021":
                message += "\n\n**⏰ Recommended Action:** Check system time/sync"
            elif api_error.error_code == "-1003":
                message += "\n\n**⚠️ Recommended Action:** Reduce API call frequency"

            # Send notification
            await self.telegram.send_message(message)

            self.logger.info(f"📱 Sent error notification for {error_description}")

        except Exception as e:
            self.logger.error(f"❌ Failed to send Telegram notification: {e}")

    async def notify_grid_status(
        self,
        symbol: str,
        client_id: int,
        orders_placed: int,
        failed_orders: int,
        success_rate: float,
    ):
        """
        Send notification about grid setup results
        """
        try:
            if not self.notifications_enabled:
                return

            # Only notify if there are failures or critical issues
            if failed_orders == 0 and success_rate == 100.0:
                # Perfect success - send brief confirmation
                message = f"""✅ **Grid Setup Success**

**Symbol:** {symbol}
**Orders Placed:** {orders_placed}/10
**Success Rate:** {success_rate:.1f}%

Grid is now active and monitoring!"""

            elif failed_orders > 0:
                # Some failures - send detailed notification
                severity = "🟠" if success_rate >= 50 else "🔴"

                message = f"""{severity} **Grid Setup Alert**

**Symbol:** {symbol}
**Client:** {client_id}
**Orders Placed:** {orders_placed}
**Failed Orders:** {failed_orders}
**Success Rate:** {success_rate:.1f}%

**Status:** {"Partial Success" if orders_placed > 0 else "Setup Failed"}

Check logs for detailed error information."""

            else:
                return  # No notification needed

            await self.telegram.send_message(message)

        except Exception as e:
            self.logger.error(f"❌ Failed to send grid status notification: {e}")

    def get_error_summary(self, hours: int = 24) -> Dict:
        """Get error summary for the last N hours"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            recent_errors = [e for e in self.error_history if e.timestamp > cutoff_time]

            if not recent_errors:
                return {"period_hours": hours, "total_errors": 0, "error_breakdown": {}}

            # Group by error code
            error_breakdown = {}
            for error in recent_errors:
                code = error.error_code
                if code not in error_breakdown:
                    error_breakdown[code] = {
                        "count": 0,
                        "description": self.critical_errors.get(code, "Unknown"),
                        "symbols": set(),
                        "severity": error.severity.value,
                    }
                error_breakdown[code]["count"] += 1
                error_breakdown[code]["symbols"].add(error.symbol)

            # Convert sets to lists for JSON serialization
            for code_data in error_breakdown.values():
                code_data["symbols"] = list(code_data["symbols"])

            return {
                "period_hours": hours,
                "total_errors": len(recent_errors),
                "error_breakdown": error_breakdown,
                "most_recent": recent_errors[-1].__dict__ if recent_errors else None,
            }

        except Exception as e:
            self.logger.error(f"❌ Error generating summary: {e}")
            return {"error": str(e)}


# UPDATE your existing order execution methods to use the notifier

# ADD this to your single_advanced_grid_manager.py __init__ method:
"""
# Add to SingleAdvancedGridManager.__init__():
from services.api_error_notifier import APIErrorNotifier
self.error_notifier = APIErrorNotifier()
"""

# REPLACE your order execution error handling with this enhanced version:


async def _execute_inventory_aware_grid_setup_with_notifications(
    self, grid_config: SingleAdvancedGridConfig
) -> Dict:
    """
    ENHANCED: Execute grid setup with comprehensive error notifications
    """
    try:
        symbol = grid_config.symbol
        orders_placed = 0
        failed_orders = 0

        self.logger.info(f"🎯 Executing bulletproof grid setup for {symbol}")

        # Get exchange rules for formatting
        rules = await self._get_exchange_rules_simple(symbol)

        # Place BUY orders with error notifications
        for level in grid_config.buy_levels:
            try:
                # Format with exact precision
                quantity_str = (
                    f"{level['quantity']:.{rules['quantity_precision']}f}".rstrip(
                        "0"
                    ).rstrip(".")
                )
                price_str = f"{level['price']:.{rules['price_precision']}f}".rstrip(
                    "0"
                ).rstrip(".")

                # Ensure minimum decimal places
                if "." not in quantity_str and rules["quantity_precision"] > 0:
                    quantity_str += ".0"
                if "." not in price_str and rules["price_precision"] > 0:
                    price_str += ".0"

                self.logger.info(f"📤 Placing BUY: {quantity_str} @ {price_str}")

                order = self.binance_client.order_limit_buy(
                    symbol=symbol,
                    quantity=quantity_str,
                    price=price_str,
                    recvWindow=60000,
                )

                level["order_id"] = order["orderId"]
                orders_placed += 1
                self.logger.info(
                    f"✅ BUY Level {level['level']}: {order['origQty']} @ ${order['price']}"
                )

            except Exception as e:
                failed_orders += 1

                # Parse Binance API error
                error_code, error_message = self._parse_binance_error(e)

                # Send error notification
                await self.error_notifier.notify_api_error(
                    error_code=error_code,
                    error_message=error_message,
                    symbol=symbol,
                    operation="BUY_ORDER_PLACEMENT",
                    client_id=self.client_id,
                    context={
                        "level": level["level"],
                        "quantity": quantity_str,
                        "price": price_str,
                        "notional": level["order_size_usd"],
                    },
                )

                self.logger.error(f"❌ BUY Level {level['level']} failed: {e}")

        # Place SELL orders with error notifications
        for level in grid_config.sell_levels:
            try:
                # Format with exact precision
                quantity_str = (
                    f"{level['quantity']:.{rules['quantity_precision']}f}".rstrip(
                        "0"
                    ).rstrip(".")
                )
                price_str = f"{level['price']:.{rules['price_precision']}f}".rstrip(
                    "0"
                ).rstrip(".")

                # Ensure minimum decimal places
                if "." not in quantity_str and rules["quantity_precision"] > 0:
                    quantity_str += ".0"
                if "." not in price_str and rules["price_precision"] > 0:
                    price_str += ".0"

                self.logger.info(f"📤 Placing SELL: {quantity_str} @ {price_str}")

                order = self.binance_client.order_limit_sell(
                    symbol=symbol,
                    quantity=quantity_str,
                    price=price_str,
                    recvWindow=60000,
                )

                level["order_id"] = order["orderId"]
                orders_placed += 1
                self.logger.info(
                    f"✅ SELL Level {level['level']}: {order['origQty']} @ ${order['price']}"
                )

            except Exception as e:
                failed_orders += 1

                # Parse Binance API error
                error_code, error_message = self._parse_binance_error(e)

                # Send error notification
                await self.error_notifier.notify_api_error(
                    error_code=error_code,
                    error_message=error_message,
                    symbol=symbol,
                    operation="SELL_ORDER_PLACEMENT",
                    client_id=self.client_id,
                    context={
                        "level": level["level"],
                        "quantity": quantity_str,
                        "price": price_str,
                        "notional": level["order_size_usd"],
                    },
                )

                self.logger.error(f"❌ SELL Level {level['level']} failed: {e}")

        success_rate = (
            (orders_placed / (orders_placed + failed_orders) * 100)
            if (orders_placed + failed_orders) > 0
            else 0
        )

        # Send grid status notification
        await self.error_notifier.notify_grid_status(
            symbol=symbol,
            client_id=self.client_id,
            orders_placed=orders_placed,
            failed_orders=failed_orders,
            success_rate=success_rate,
        )

        self.logger.info("✅ Grid setup completed:")
        self.logger.info(f"   🎯 Orders placed: {orders_placed}")
        self.logger.info(f"   ❌ Failed orders: {failed_orders}")
        self.logger.info(f"   📊 Success rate: {success_rate:.1f}%")

        return {
            "success": orders_placed > 0,
            "orders_placed": orders_placed,
            "failed_orders": failed_orders,
            "success_rate": f"{success_rate:.1f}%",
        }

    except Exception as e:
        # Notify about critical setup failure
        await self.error_notifier.notify_api_error(
            error_code="SETUP_FAILURE",
            error_message=str(e),
            symbol=symbol,
            operation="GRID_SETUP",
            client_id=self.client_id,
            context={"total_capital": grid_config.total_capital},
        )

        self.logger.error(f"❌ Grid setup execution error: {e}")
        return {"success": False, "error": str(e)}


def _parse_binance_error(self, error) -> tuple:
    """Parse Binance API error to extract code and message"""
    try:
        error_str = str(error)

        # Extract error code (e.g., "APIError(code=-1013)")
        if "code=" in error_str:
            code_start = error_str.find("code=") + 5
            code_end = error_str.find(")", code_start)
            if code_end == -1:
                code_end = error_str.find(":", code_start)
            if code_end == -1:
                code_end = len(error_str)
            error_code = error_str[code_start:code_end].strip()
        else:
            error_code = "UNKNOWN"

        # Extract error message
        if ":" in error_str:
            error_message = error_str.split(":", 1)[1].strip()
        else:
            error_message = error_str

        return error_code, error_message

    except Exception:
        return "PARSE_ERROR", str(error)
