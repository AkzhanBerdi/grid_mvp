import logging
from typing import Dict

from repositories.user_repository import UserRepository

from .user_trading_bot import UserTradingBot


class BotOrchestrator:
    """Updated Bot Orchestrator - manages multiple UserTradingBot instances"""

    def __init__(self):
        self.active_bots: Dict[int, UserTradingBot] = {}
        self.user_repo = UserRepository()
        self.logger = logging.getLogger(__name__)

    async def start_user_bot(self, user_id: int, symbol: str, capital: float) -> bool:
        """Start trading bot for a user"""
        try:
            # Get user from database
            user = self.user_repo.get_user(user_id)
            if not user:
                self.logger.error(f"User {user_id} not found")
                return False

            # Stop existing bot if running
            if user_id in self.active_bots:
                await self.stop_user_bot(user_id)

            # Create new user trading bot
            user_bot = UserTradingBot(user)

            # Start grid trading
            success = await user_bot.start_grid_trading(symbol, capital)

            if success:
                self.active_bots[user_id] = user_bot
                self.logger.info(
                    f"✅ Started bot for user {user_id}: {symbol} with ${capital}"
                )
                return True
            else:
                self.logger.error(f"Failed to start grid trading for user {user_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error starting bot for user {user_id}: {e}")
            return False

    async def stop_user_bot(self, user_id: int) -> bool:
        """Stop trading bot for a user"""
        try:
            if user_id in self.active_bots:
                user_bot = self.active_bots[user_id]
                await user_bot.stop_grid_trading()
                del self.active_bots[user_id]

            self.logger.info(f"🛑 Stopped bot for user {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping bot for user {user_id}: {e}")
            return False

    async def update_all_bots(self):
        """Update all active user bots - check orders, etc."""
        for user_id, user_bot in list(self.active_bots.items()):
            try:
                # Check if user still has active subscription
                user = self.user_repo.get_user(user_id)
                if not user or not user.is_subscription_active():
                    await self.stop_user_bot(user_id)
                    continue

                # Update bot orders for their trading pairs
                for pair in user.trading_pairs:
                    symbol = f"{pair}USDT"
                    await user_bot.check_and_update_orders(symbol)

            except Exception as e:
                self.logger.error(f"Error updating bot for user {user_id}: {e}")

    def get_user_bot_status(self, user_id: int) -> Dict:
        """Get bot status for a specific user"""
        if user_id not in self.active_bots:
            return {
                "status": "inactive",
                "active_orders": 0,
                "pairs": [],
                "running": False,
                "mode": "demo",
                "total_trades": 0,
                "total_profit": 0.0,
            }

        user_bot = self.active_bots[user_id]
        status = user_bot.get_status()

        # Add user-specific info
        user = self.user_repo.get_user(user_id)
        status.update(
            {
                "status": "active" if status["active"] else "inactive",
                "pairs": user.trading_pairs if user else [],
                "running": status["active"],
            }
        )

        return status

    def get_all_active_bots(self) -> Dict[int, Dict]:
        """Get status of all active bots"""
        return {
            user_id: self.get_user_bot_status(user_id)
            for user_id in self.active_bots.keys()
        }

    async def process_user_trade_command(
        self, user_id: int, symbol: str, capital: float
    ) -> Dict:
        """Process a trade command from user via Telegram"""
        try:
            # Validate user
            user = self.user_repo.get_user(user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            if not user.is_subscription_active():
                return {"success": False, "error": "No active subscription"}

            # Update user configuration
            user.total_capital = capital
            user.trading_pairs = [symbol.replace("USDT", "")]
            self.user_repo.update_user(user)

            # Start the bot
            success = await self.start_user_bot(user_id, f"{symbol}USDT", capital)

            if success:
                bot_status = self.get_user_bot_status(user_id)
                return {
                    "success": True,
                    "message": f"Grid trading started for {symbol}",
                    "status": bot_status,
                }
            else:
                return {"success": False, "error": "Failed to start trading bot"}

        except Exception as e:
            self.logger.error(f"Error processing trade command for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_performance(self, user_id: int) -> Dict:
        """Get detailed performance metrics for a user"""
        try:
            status = self.get_user_bot_status(user_id)

            # Get trade history from database
            import sqlite3

            from config import Config

            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) as total_trades, 
                           SUM(value) as total_volume,
                           AVG(value) as avg_trade_size
                    FROM trades 
                    WHERE telegram_id = ?
                """,
                    (user_id,),
                )

                trade_stats = cursor.fetchone()

                # Get recent trades
                cursor = conn.execute(
                    """
                    SELECT symbol, side, quantity, price, value, timestamp
                    FROM trades 
                    WHERE telegram_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                """,
                    (user_id,),
                )

                recent_trades = cursor.fetchall()

            return {
                "user_id": user_id,
                "bot_status": status,
                "total_trades": trade_stats[0] if trade_stats[0] else 0,
                "total_volume": trade_stats[1] if trade_stats[1] else 0.0,
                "avg_trade_size": trade_stats[2] if trade_stats[2] else 0.0,
                "recent_trades": [
                    {
                        "symbol": trade[0],
                        "side": trade[1],
                        "quantity": trade[2],
                        "price": trade[3],
                        "value": trade[4],
                        "timestamp": trade[5],
                    }
                    for trade in recent_trades
                ],
            }

        except Exception as e:
            self.logger.error(f"Error getting performance for user {user_id}: {e}")
            return {"error": str(e)}

    async def shutdown_all_bots(self):
        """Gracefully shutdown all user bots"""
        self.logger.info("🛑 Shutting down all user bots...")

        for user_id in list(self.active_bots.keys()):
            try:
                await self.stop_user_bot(user_id)
            except Exception as e:
                self.logger.error(f"Error stopping bot for user {user_id}: {e}")

        self.logger.info("✅ All user bots stopped")
