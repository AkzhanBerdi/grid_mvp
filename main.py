#!/usr/bin/env python3
"""
GridTrader Pro - Simplified Client Service
Production-ready grid trading for paying clients
"""

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

from config import Config
from database.db_setup import DatabaseSetup

# In main.py, replace ClientHandler with SmartClientHandler
from handlers.smart_client_handler import SmartClientHandler

# from handlers.client_handler import ClientHandler
# from services.grid_orchestrator import GridOrchestrator
from services.enhanced_grid_orchestrator import EnhancedGridOrchestrator


class GridTradingService:
    """Simplified Grid Trading Service for Paying Clients"""

    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()

        # Initialize components
        self.db_setup = DatabaseSetup()
        self.grid_orchestrator = EnhancedGridOrchestrator()
        self.handler = SmartClientHandler()

        # Service state
        self.running = False
        self.telegram_app = None

        self.logger.info("🤖 GridTrader Pro Client Service initialized")

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

    async def grid_management_loop(self):
        """Main loop to manage all client grid trading"""
        self.logger.info("🔄 Starting grid management loop")

        while self.running:
            try:
                # Update all active grids
                await self.grid_orchestrator.update_all_grids()

                # Log status every 5 minutes
                active_grids = self.grid_orchestrator.get_all_active_grids()
                if active_grids:
                    self.logger.info(f"📊 Managing {len(active_grids)} active grids")

                # Wait 30 seconds before next update
                await asyncio.sleep(30)

            except Exception as e:
                self.logger.error(f"Error in grid management loop: {e}")
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

    async def run_service(self):
        """Run both grid management and Telegram bot concurrently"""
        tasks = []

        # Add grid management loop
        management_task = asyncio.create_task(self.grid_management_loop())
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

                self.logger.info("✅ Both grid management and Telegram bot started")

            except Exception as e:
                self.logger.error(f"Failed to start Telegram bot: {e}")
                self.logger.info("🤖 Continuing with grid management only")
        else:
            self.logger.info("🤖 Starting grid management only (no Telegram bot)")

        try:
            # Run all tasks concurrently
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("🛑 Service stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Service error: {e}")
        finally:
            # Cleanup
            await self.stop_service()

    async def stop_service(self):
        """Stop the service gracefully"""
        self.logger.info("🛑 Stopping GridTrader Pro Service...")
        self.running = False

        # Stop all grids first
        await self.grid_orchestrator.shutdown_all_grids()

        # Stop Telegram bot
        if self.telegram_app:
            try:
                await self.telegram_app.updater.stop()
                await self.telegram_app.stop()
                await self.telegram_app.shutdown()
                self.logger.info("📱 Telegram bot stopped")
            except Exception as e:
                self.logger.error(f"Error stopping Telegram bot: {e}")

        self.logger.info("✅ GridTrader Pro Service stopped")

    async def start_async(self):
        """Async start method"""
        self.logger.info("🚀 Starting GridTrader Pro Client Service")

        try:
            # Initialize database
            self._init_database()

            # Setup Telegram bot
            self.setup_telegram_bot()

            # Start main loop
            self.running = True
            await self.run_service()

        except Exception as e:
            self.logger.error(f"❌ Startup error: {e}")
            raise

    def start(self):
        """Main start method - runs async event loop"""
        try:
            # Run the async service
            asyncio.run(self.start_async())
        except KeyboardInterrupt:
            self.logger.info("🛑 Service stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Service error: {e}")
        finally:
            self.running = False


def main():
    """Entry point"""
    # Validate configuration
    if not Config.validate():
        print("❌ Invalid configuration. Please check your environment variables.")
        sys.exit(1)

    print("🚀 Starting GridTrader Pro Client Service")
    print("=" * 50)
    print("✅ Real trading only - no trials or demos")
    print("✅ Client API key management")
    print("✅ Professional grid trading")
    print("✅ Telegram interface")
    print("✅ Production ready")
    print("=" * 50)

    # Create and start service
    service = GridTradingService()
    service.start()


if __name__ == "__main__":
    main()
