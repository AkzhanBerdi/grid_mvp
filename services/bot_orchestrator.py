import logging
from typing import Dict

from repositories.user_repository import UserRepository

from .user_trading_bot import TradingMode, UserTradingBot


class BotOrchestrator:
    """Fixed Bot Orchestrator - properly detects trading mode"""

    def __init__(self):
        self.active_bots: Dict[int, UserTradingBot] = {}
        self.user_repo = UserRepository()
        self.logger = logging.getLogger(__name__)

    def _determine_trading_mode(self, user) -> str:
        """Determine if user should use real or demo trading"""
        if not user.binance_api_key or not user.binance_secret_key:
            return TradingMode.DEMO

        # Check if keys are demo keys
        if (
            "demo" in user.binance_api_key.lower()
            or "test" in user.binance_api_key.lower()
        ):
            return TradingMode.DEMO

        # If keys look real (no demo/test in them), use real mode
        return TradingMode.REAL

    async def start_user_bot(self, user_id: int, symbol: str, capital: float) -> bool:
        """Start trading bot for a user with correct mode detection"""
        try:
            # Get user from database
            user = self.user_repo.get_user(user_id)
            if not user:
                self.logger.error(f"User {user_id} not found")
                return False

            # Stop existing bot if running
            if user_id in self.active_bots:
                await self.stop_user_bot(user_id)

            # Determine correct trading mode based on user's API keys
            trading_mode = self._determine_trading_mode(user)

            # Log the mode determination
            self.logger.info(f"User {user_id} trading mode: {trading_mode}")
            self.logger.info(
                f"API key preview: {user.binance_api_key[:10] if user.binance_api_key else 'None'}..."
            )

            # Create new user trading bot with correct mode
            user_bot = UserTradingBot(user, trading_mode=trading_mode)

            # Start grid trading
            success = await user_bot.start_grid_trading(symbol, capital)

            if success:
                self.active_bots[user_id] = user_bot
                mode_name = "REAL" if trading_mode == TradingMode.REAL else "DEMO"
                self.logger.info(
                    f"✅ Started {mode_name} bot for user {user_id}: {symbol} with ${capital}"
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
                await user_bot.stop_trading()  # Changed from stop_grid_trading
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
                    # Note: UserTradingBot should have this method
                    if hasattr(user_bot, "check_and_update_orders"):
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
