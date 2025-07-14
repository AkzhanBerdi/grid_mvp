#!/usr/bin/env python3
"""Updated main.py - Complete Integration with User Trading System"""

import asyncio
import logging
import sys
from pathlib import Path

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from analytics.conversion_tracker import ConversionTracker
from config import Config
from database.db_setup import DatabaseSetup
from handlers.complete_handler import CompleteHandler
from services.bot_orchestrator import BotOrchestrator


class GridTradingBot:
    """Complete Grid Trading Bot with Per-User API Integration"""

    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()

        # Initialize components
        self.db_setup = DatabaseSetup()
        self.conversion_tracker = ConversionTracker()
        self.bot_orchestrator = BotOrchestrator()
        self.handler = CompleteHandler(self.conversion_tracker)

        # Bot state
        self.running = False
        self.telegram_app = None

        self.logger.info("🤖 GridTrader Pro initialized with per-user API support")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        Path("data/logs").mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.config.LOG_FILE),
                logging.StreamHandler(sys.stdout),
            ],
        )
        return logging.getLogger(__name__)

    def _init_database(self):
        """Initialize database tables"""
        try:
            self.db_setup.initialize()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def user_bot_management_loop(self):
        """Main loop to manage user trading bots"""
        self.logger.info("🔄 Starting user bot management loop")

        while self.running:
            try:
                # Update all active user bots
                await self.bot_orchestrator.update_all_bots()

                # Log status
                active_bots = self.bot_orchestrator.get_all_active_bots()
                if active_bots:
                    self.logger.info(f"🤖 Managing {len(active_bots)} active user bots")

                    # Log some statistics
                    total_trades = sum(
                        bot.get("total_trades", 0) for bot in active_bots.values()
                    )
                    total_profit = sum(
                        bot.get("total_profit", 0) for bot in active_bots.values()
                    )

                    if total_trades > 0:
                        self.logger.info(
                            f"📊 Total trades: {total_trades}, Total profit: ${total_profit:.2f}"
                        )

                # Wait 30 seconds before next update
                await asyncio.sleep(30)

            except Exception as e:
                self.logger.error(f"Error in bot management loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def telegram_start(self, update, context):
        """Handle /start command"""
        try:
            await self.handler.handle_start(update, context)
        except Exception as e:
            self.logger.error(f"Error in start handler: {e}")

    async def telegram_callback(self, update, context):
        """Handle callback queries"""
        try:
            await self.handler.handle_callback(update, context)
        except Exception as e:
            self.logger.error(f"Error in callback handler: {e}")

    async def telegram_message(self, update, context):
        """Handle text messages"""
        try:
            await self.handler.handle_message(update, context)
        except Exception as e:
            self.logger.error(f"Error in message handler: {e}")

    def setup_telegram_bot(self):
        """Setup Telegram bot application"""
        if not self.config.TELEGRAM_BOT_TOKEN:
            self.logger.warning(
                "Telegram bot token not configured - skipping Telegram bot"
            )
            return None

        try:
            # Create Telegram application
            self.telegram_app = (
                Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
            )

            # Add handlers
            self.telegram_app.add_handler(CommandHandler("start", self.telegram_start))
            self.telegram_app.add_handler(CallbackQueryHandler(self.telegram_callback))
            self.telegram_app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.telegram_message)
            )

            self.logger.info("📱 Telegram bot configured successfully")
            return self.telegram_app

        except Exception as e:
            self.logger.error(f"Failed to setup Telegram bot: {e}")
            return None

    async def run_bot(self):
        """Run both bot management and Telegram bot concurrently"""
        tasks = []

        # Add bot management loop
        management_task = asyncio.create_task(self.user_bot_management_loop())
        tasks.append(management_task)

        # Add Telegram bot task if configured
        if self.telegram_app:
            try:
                # Initialize and start Telegram bot
                await self.telegram_app.initialize()
                await self.telegram_app.start()

                # Create polling task
                telegram_task = asyncio.create_task(
                    self.telegram_app.updater.start_polling()
                )
                tasks.append(telegram_task)

                self.logger.info("✅ Both user bot management and Telegram bot started")

            except Exception as e:
                self.logger.error(f"Failed to start Telegram bot: {e}")
                self.logger.info("🤖 Continuing with bot management only")
        else:
            self.logger.info("🤖 Starting bot management only (no Telegram bot)")

        try:
            # Run all tasks concurrently
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("🛑 Bot stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Bot error: {e}")
        finally:
            # Cleanup
            await self.stop_bot()

    async def stop_bot(self):
        """Stop the bot gracefully"""
        self.logger.info("🛑 Stopping GridTrader Pro...")
        self.running = False

        # Stop all user bots first
        await self.bot_orchestrator.shutdown_all_bots()

        # Stop Telegram bot
        if self.telegram_app:
            try:
                await self.telegram_app.updater.stop()
                await self.telegram_app.stop()
                await self.telegram_app.shutdown()
                self.logger.info("📱 Telegram bot stopped")
            except Exception as e:
                self.logger.error(f"Error stopping Telegram bot: {e}")

        self.logger.info("✅ GridTrader Pro stopped")

    async def start_async(self):
        """Async start method"""
        self.logger.info("🚀 Starting GridTrader Pro with Per-User Trading")

        try:
            # Initialize database
            self._init_database()

            # Setup Telegram bot
            self.setup_telegram_bot()

            # Start main loop
            self.running = True
            await self.run_bot()

        except Exception as e:
            self.logger.error(f"❌ Startup error: {e}")
            raise

    def start(self):
        """Main start method - runs async event loop"""
        try:
            # Run the async bot
            asyncio.run(self.start_async())
        except KeyboardInterrupt:
            self.logger.info("🛑 Bot stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Bot error: {e}")
        finally:
            self.running = False


def main():
    """Entry point"""
    # Validate configuration
    if not Config.validate():
        print("❌ Invalid configuration. Please check your environment variables.")
        sys.exit(1)

    print("🚀 Starting GridTrader Pro MVP")
    print("=" * 50)
    print("✅ Per-user API key support")
    print("✅ Individual trading bot instances")
    print("✅ Real & demo trading modes")
    print("✅ Telegram interface")
    print("✅ Ready for 50+ users")
    print("=" * 50)

    # Create and start bot
    bot = GridTradingBot()
    bot.start()


if __name__ == "__main__":
    main()
