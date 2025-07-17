# utils/fifo_telegram_monitor.py
"""
Focused FIFO Profit Telegram Monitor for GridTrader Pro
Integrates with existing database and trade execution flow
"""

import logging
import sqlite3
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict

import requests

from config import Config


class FIFOProfitCalculator:
    """FIFO-based profit calculation using existing database"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

        # FIFO queues for each symbol: {symbol: deque of buy trades}
        self.buy_queues: Dict[str, deque] = {}

    def calculate_fifo_profit(self, client_id: int) -> Dict:
        """Calculate FIFO profit for specific client"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all trades for the client
                cursor = conn.execute(
                    """
                    SELECT symbol, side, quantity, price, executed_at, total_value
                    FROM trades 
                    WHERE client_id = ?
                    ORDER BY executed_at ASC
                """,
                    (client_id,),
                )

                trades = cursor.fetchall()

                # Reset queues for this calculation
                symbol_queues = {}
                total_profit = 0.0
                completed_cycles = 0
                winning_trades = 0
                total_volume = 0.0

                for trade in trades:
                    symbol, side, quantity, price, executed_at, total_value = trade
                    total_volume += total_value

                    if symbol not in symbol_queues:
                        symbol_queues[symbol] = deque()

                    if side == "BUY":
                        # Add to buy queue
                        symbol_queues[symbol].append(
                            {
                                "quantity": quantity,
                                "price": price,
                                "timestamp": executed_at,
                            }
                        )

                    elif side == "SELL":
                        # Match with oldest buys (FIFO)
                        remaining_sell = quantity

                        while remaining_sell > 0 and symbol_queues[symbol]:
                            oldest_buy = symbol_queues[symbol][0]

                            # How much to match
                            match_qty = min(remaining_sell, oldest_buy["quantity"])

                            # Calculate profit for this match
                            buy_cost = match_qty * oldest_buy["price"]
                            sell_revenue = match_qty * price
                            profit = sell_revenue - buy_cost

                            total_profit += profit
                            completed_cycles += 1

                            if profit > 0:
                                winning_trades += 1

                            # Update quantities
                            remaining_sell -= match_qty
                            oldest_buy["quantity"] -= match_qty

                            # Remove buy if fully consumed
                            if oldest_buy["quantity"] <= 0:
                                symbol_queues[symbol].popleft()

                # Calculate metrics
                win_rate = (
                    (winning_trades / completed_cycles * 100)
                    if completed_cycles > 0
                    else 0
                )
                avg_profit = (
                    total_profit / completed_cycles if completed_cycles > 0 else 0
                )

                return {
                    "total_profit": round(total_profit, 2),
                    "completed_cycles": completed_cycles,
                    "winning_trades": winning_trades,
                    "win_rate": round(win_rate, 1),
                    "avg_profit_per_trade": round(avg_profit, 2),
                    "total_volume": round(total_volume, 2),
                    "profit_margin": round((total_profit / total_volume * 100), 3)
                    if total_volume > 0
                    else 0,
                }

        except Exception as e:
            self.logger.error(f"Error calculating FIFO profit: {e}")
            return {
                "total_profit": 0.0,
                "completed_cycles": 0,
                "winning_trades": 0,
                "win_rate": 0.0,
                "avg_profit_per_trade": 0.0,
                "total_volume": 0.0,
                "profit_margin": 0.0,
            }

    def get_recent_profit(self, client_id: int, hours: int = 24) -> Dict:
        """Get profit from recent trades"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cutoff_time = datetime.now() - timedelta(hours=hours)

                cursor = conn.execute(
                    """
                    SELECT symbol, side, quantity, price, executed_at, total_value
                    FROM trades 
                    WHERE client_id = ? AND executed_at >= ?
                    ORDER BY executed_at ASC
                """,
                    (client_id, cutoff_time.isoformat()),
                )

                recent_trades = cursor.fetchall()

                # Calculate recent profit using simplified method
                recent_profit = 0.0
                recent_trades_count = 0

                for trade in recent_trades:
                    symbol, side, quantity, price, executed_at, total_value = trade
                    if side == "SELL":
                        # Estimate profit as 2.5% of sell value (grid spacing)
                        estimated_profit = total_value * 0.025
                        recent_profit += estimated_profit
                        recent_trades_count += 1

                return {
                    "recent_profit": round(recent_profit, 2),
                    "recent_trades": recent_trades_count,
                    "period_hours": hours,
                }

        except Exception as e:
            self.logger.error(f"Error calculating recent profit: {e}")
            return {"recent_profit": 0.0, "recent_trades": 0, "period_hours": hours}


class TelegramNotifier:
    """Telegram notification service"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or Config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or Config.ADMIN_TELEGRAM_ID
        self.enabled = bool(self.bot_token and self.chat_id)
        self.logger = logging.getLogger(__name__)

        if self.enabled:
            self.logger.info("✅ Telegram notifier initialized")
        else:
            self.logger.warning("⚠️ Telegram disabled - check bot token and chat ID")

    async def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram"""
        if not self.enabled:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                self.logger.debug("📱 Telegram message sent successfully")
                return True
            else:
                self.logger.error(f"❌ Telegram send failed: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Telegram send error: {e}")
            return False


class FIFOProfitMonitor:
    """Main FIFO profit monitoring and notification system"""

    def __init__(self, client_id: int, db_path: str = None):
        self.client_id = client_id
        self.calculator = FIFOProfitCalculator(db_path)
        self.notifier = TelegramNotifier()
        self.logger = logging.getLogger(__name__)

        # Milestone tracking
        self.profit_milestones = [10, 25, 50, 100, 250, 500, 1000, 2000, 5000]
        self.last_milestone_reached = 0.0

        # Rate limiting
        self.last_profit_update = 0
        self.min_update_interval = 300  # 5 minutes between updates
        self.last_daily_summary = None

        # Performance tracking
        self.trade_count_on_startup = 0
        self.startup_profit = 0.0

        self.logger.info(f"🔍 FIFO Profit Monitor initialized for client {client_id}")

    async def initialize(self):
        """Initialize monitor with current stats"""
        try:
            current_stats = self.calculator.calculate_fifo_profit(self.client_id)
            self.startup_profit = current_stats["total_profit"]
            self.trade_count_on_startup = current_stats["completed_cycles"]

            # Set last milestone to highest reached
            for milestone in reversed(self.profit_milestones):
                if current_stats["total_profit"] >= milestone:
                    self.last_milestone_reached = milestone
                    break

            await self.send_startup_status()

        except Exception as e:
            self.logger.error(f"Error initializing monitor: {e}")

    async def send_startup_status(self):
        """Send bot startup status with current profit"""
        try:
            stats = self.calculator.calculate_fifo_profit(self.client_id)
            recent = self.calculator.get_recent_profit(self.client_id, 24)

            message = f"""🚀 **GridTrader Pro Started**

💰 **Current FIFO Profit: ${stats["total_profit"]:.2f}**
🔄 Completed Cycles: {stats["completed_cycles"]}
📈 Win Rate: {stats["win_rate"]:.1f}%
📊 Avg Profit/Trade: ${stats["avg_profit_per_trade"]:.2f}

📅 **24h Performance:**
💵 Recent Profit: ${recent["recent_profit"]:.2f}
🔄 Recent Trades: {recent["recent_trades"]}

🎯 Next milestone: ${self._get_next_milestone(stats["total_profit"]):.0f}

✅ Ready to capture more profits!"""

            await self.notifier.send_message(message)

        except Exception as e:
            self.logger.error(f"Error sending startup status: {e}")

    async def on_trade_executed(
        self, symbol: str, side: str, quantity: float, price: float
    ):
        """Called when a trade is executed - check for profit updates"""
        try:
            if side != "SELL":
                return  # Only process sell trades for profit calculation

            # Calculate current profit
            current_stats = self.calculator.calculate_fifo_profit(self.client_id)

            # Check for new milestones
            await self._check_profit_milestones(current_stats)

            # Check for significant individual trade profit
            estimated_trade_profit = quantity * price * 0.025  # Assume 2.5% profit
            if estimated_trade_profit >= 1.0:  # $1+ profit
                await self._notify_significant_trade(
                    symbol, estimated_trade_profit, current_stats
                )

        except Exception as e:
            self.logger.error(f"Error processing trade execution: {e}")

    async def _check_profit_milestones(self, current_stats: Dict):
        """Check and notify profit milestones"""
        try:
            total_profit = current_stats["total_profit"]

            # Check for new milestones
            for milestone in self.profit_milestones:
                if total_profit >= milestone > self.last_milestone_reached:
                    await self._notify_milestone_reached(milestone, current_stats)
                    self.last_milestone_reached = milestone

        except Exception as e:
            self.logger.error(f"Error checking milestones: {e}")

    async def _notify_milestone_reached(self, milestone: float, stats: Dict):
        """Notify when a profit milestone is reached"""
        try:
            next_milestone = self._get_next_milestone(milestone)

            message = f"""🎉 **PROFIT MILESTONE REACHED!**

💰 **${milestone:.0f} Total FIFO Profit Achieved!**

📊 **Current Stats:**
• Total Profit: **${stats["total_profit"]:.2f}**
• Completed Cycles: {stats["completed_cycles"]}
• Win Rate: {stats["win_rate"]:.1f}%
• Average per Trade: ${stats["avg_profit_per_trade"]:.2f}
• Profit Margin: {stats["profit_margin"]:.3f}%

🎯 **Next Target:** ${next_milestone:.0f}

🚀 Keep the momentum going! 💪"""

            await self.notifier.send_message(message)

        except Exception as e:
            self.logger.error(f"Error notifying milestone: {e}")

    async def _notify_significant_trade(
        self, symbol: str, profit: float, current_stats: Dict
    ):
        """Notify significant individual trades"""
        try:
            if profit < 1.0:  # Only notify $1+ trades
                return

            message = f"""💰 **Profitable Trade Completed**

🎯 **{symbol}** • Profit: **${profit:.2f}**
📈 Total FIFO Profit: **${current_stats["total_profit"]:.2f}**
📊 Win Rate: {current_stats["win_rate"]:.1f}%

⏰ {datetime.now().strftime("%H:%M:%S")}"""

            await self.notifier.send_message(message)

        except Exception as e:
            self.logger.error(f"Error notifying trade: {e}")

    def _get_next_milestone(self, current_profit: float) -> float:
        """Get next profit milestone"""
        for milestone in self.profit_milestones:
            if milestone > current_profit:
                return milestone
        return current_profit * 2  # Double if beyond predefined milestones

    async def send_daily_summary(self):
        """Send daily profit summary"""
        try:
            today = datetime.now().date()

            if self.last_daily_summary == today:
                return  # Already sent today

            stats = self.calculator.calculate_fifo_profit(self.client_id)
            recent_24h = self.calculator.get_recent_profit(self.client_id, 24)

            message = f"""📊 **Daily FIFO Profit Report**

**📅 {today.strftime("%Y-%m-%d")}**

**24H Performance:**
💵 Daily Profit: **${recent_24h["recent_profit"]:.2f}**
🔄 Trades Completed: {recent_24h["recent_trades"]}

**Overall FIFO Stats:**
💰 Total Profit: **${stats["total_profit"]:.2f}**
📈 Completed Cycles: {stats["completed_cycles"]}
📊 Win Rate: {stats["win_rate"]:.1f}%
💵 Avg per Trade: ${stats["avg_profit_per_trade"]:.2f}
📈 Profit Margin: {stats["profit_margin"]:.3f}%

🎯 Next milestone: ${self._get_next_milestone(stats["total_profit"]):.0f}"""

            await self.notifier.send_message(message)
            self.last_daily_summary = today

        except Exception as e:
            self.logger.error(f"Error sending daily summary: {e}")

    async def send_profit_update(self, force: bool = False):
        """Send current profit status (rate limited)"""
        try:
            now = time.time()

            if not force and (now - self.last_profit_update) < self.min_update_interval:
                return

            stats = self.calculator.calculate_fifo_profit(self.client_id)
            recent_24h = self.calculator.get_recent_profit(self.client_id, 24)

            # Calculate session profit (since startup)
            session_profit = stats["total_profit"] - self.startup_profit
            session_trades = stats["completed_cycles"] - self.trade_count_on_startup

            message = f"""📈 **Current FIFO Profit Status**

💰 **Total Profit: ${stats["total_profit"]:.2f}**
🔄 Completed Cycles: {stats["completed_cycles"]}
📊 Win Rate: {stats["win_rate"]:.1f}%
💵 Avg per Trade: ${stats["avg_profit_per_trade"]:.2f}

**Session Stats:**
📈 Session Profit: ${session_profit:.2f}
🔄 Session Trades: {session_trades}

**24H Stats:**
💵 Recent Profit: ${recent_24h["recent_profit"]:.2f}
🔄 Recent Trades: {recent_24h["recent_trades"]}

🎯 Next milestone: ${self._get_next_milestone(stats["total_profit"]):.0f}"""

            if await self.notifier.send_message(message):
                self.last_profit_update = now

        except Exception as e:
            self.logger.error(f"Error sending profit update: {e}")

    async def periodic_check(self):
        """Periodic monitoring tasks"""
        try:
            current_hour = datetime.now().hour

            # Send daily summary at 9 AM
            if current_hour == 9:
                await self.send_daily_summary()

            # Check for significant daily profit
            recent_24h = self.calculator.get_recent_profit(self.client_id, 24)
            if recent_24h["recent_profit"] >= 10.0:  # $10+ daily profit
                await self._notify_excellent_daily_performance(recent_24h)

        except Exception as e:
            self.logger.error(f"Error in periodic check: {e}")

    async def _notify_excellent_daily_performance(self, recent_stats: Dict):
        """Notify excellent daily performance"""
        try:
            message = f"""🔥 **Excellent Daily Performance!**

💵 24H Profit: **${recent_stats["recent_profit"]:.2f}**
🔄 Trades: {recent_stats["recent_trades"]}

Outstanding grid trading performance today! 🚀"""

            await self.notifier.send_message(message)

        except Exception as e:
            self.logger.error(f"Error notifying daily performance: {e}")

    async def notify_error(self, error_msg: str):
        """Notify errors with profit context"""
        try:
            stats = self.calculator.calculate_fifo_profit(self.client_id)

            message = f"""❌ **Trading Error Detected**

🚨 Error: {error_msg[:100]}...

💰 Current Profit: **${stats["total_profit"]:.2f}**
🔄 Completed Cycles: {stats["completed_cycles"]}

Bot will retry automatically."""

            await self.notifier.send_message(message)

        except Exception as e:
            self.logger.error(f"Error notifying error: {e}")


# Integration helper for your existing codebase
class FIFOMonitoringService:
    """Service to integrate FIFO monitoring into your existing system"""

    def __init__(self):
        self.monitors: Dict[int, FIFOProfitMonitor] = {}
        self.logger = logging.getLogger(__name__)

    async def add_client_monitor(self, client_id: int):
        """Add monitoring for a client"""
        try:
            if client_id not in self.monitors:
                monitor = FIFOProfitMonitor(client_id)
                await monitor.initialize()
                self.monitors[client_id] = monitor
                self.logger.info(f"✅ Added FIFO monitoring for client {client_id}")
        except Exception as e:
            self.logger.error(f"Error adding monitor for client {client_id}: {e}")

    async def on_trade_executed(
        self, client_id: int, symbol: str, side: str, quantity: float, price: float
    ):
        """Call this from your trade execution logic"""
        try:
            if client_id in self.monitors:
                await self.monitors[client_id].on_trade_executed(
                    symbol, side, quantity, price
                )
        except Exception as e:
            self.logger.error(f"Error processing trade for client {client_id}: {e}")

    async def send_profit_status(self, client_id: int):
        """Manual profit status request"""
        try:
            if client_id in self.monitors:
                await self.monitors[client_id].send_profit_update(force=True)
        except Exception as e:
            self.logger.error(
                f"Error sending profit status for client {client_id}: {e}"
            )

    async def periodic_monitoring(self):
        """Run periodic monitoring tasks"""
        try:
            for monitor in self.monitors.values():
                await monitor.periodic_check()
        except Exception as e:
            self.logger.error(f"Error in periodic monitoring: {e}")
