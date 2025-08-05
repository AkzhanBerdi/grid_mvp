"""
Bad Trader - Clean Production Version
========================================

Professional grid trading service with clean architecture and minimal complexity.
"""

import asyncio
import logging
import sqlite3
import sys
from datetime import datetime, timedelta
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
from handlers.client_handler import ClientHandler
from services.grid_orchestrator import GridOrchestrator
from services.telegram_notifier import TelegramNotifier
from utils.network_recovery import NetworkRecovery


class BadTradingService:
    """Clean grid trading service with essential functionality"""

    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()

        # Core components
        self.db_setup = DatabaseSetup()
        self.grid_orchestrator = GridOrchestrator()
        self.handler = ClientHandler()
        self.network_recovery = NetworkRecovery()

        # Service state
        self.running = False
        self.telegram_app = None
        self._error_count = 0
        self._last_health_check = datetime.now()

        self.logger.info(
            f"🎯 Main.py using GridOrchestrator instance ID: {id(self.grid_orchestrator)}"
        )
        self.logger.info("🤖 Service initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup clean logging configuration"""
        Path("data/logs").mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("data/logs/gridtrader_service.log"),
                logging.StreamHandler(),
            ],
        )
        return logging.getLogger(__name__)

    def _init_database(self):
        """Initialize database"""
        try:
            self.db_setup.initialize()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def _startup_checks(self):
        """Perform essential startup checks"""
        self.logger.info("🔍 Performing startup connectivity checks...")

        health_ok = await self.network_recovery.health_check()

        if health_ok:
            self.logger.info("✅ All network services operational")
        else:
            self.logger.warning("⚠️ Some network services are offline")

        # Log health status
        health_status = self.network_recovery.get_health_status()
        self.logger.info(
            f"📊 Network Health: {health_status['status']} ({health_status['uptime_percentage']:.1f}% uptime)"
        )

        return health_ok

    async def _periodic_health_check(self):
        """Perform periodic health check"""
        now = datetime.now()

        # Check every 5 minutes
        if now - self._last_health_check >= timedelta(minutes=5):
            self._last_health_check = now

            try:
                health_ok = await self.network_recovery.health_check()

                if not health_ok and self.network_recovery.is_emergency_stop_needed():
                    self.logger.critical("🚨 Emergency stop triggered")
                    return False

            except Exception as e:
                self.logger.error(f"Health check error: {e}")

        return True

    async def grid_management_loop(self):
        """Main grid management loop"""
        self.logger.info("🔄 Starting grid management loop")

        while self.running:
            try:
                # Health check
                if not await self._periodic_health_check():
                    self.logger.critical("🚨 Health check failed - stopping")
                    break

                # Update grids
                try:
                    await self.grid_orchestrator.update_all_grids()
                    self._error_count = 0  # Reset on success
                except Exception as e:
                    self._error_count += 1
                    self.logger.error(f"Grid update error: {e}")

                    if self._error_count > 5:
                        self.logger.critical("🚨 Too many grid update errors")
                        break

                # Log status
                self._log_grid_status()

                # Wait for next cycle
                await asyncio.sleep(30)

            except Exception as e:
                self.logger.error(f"Error in grid management loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    def _log_grid_status(self):
        """Log current grid status"""
        try:
            grids_data = self.grid_orchestrator.get_all_active_grids()
            if grids_data and "system_summary" in grids_data:
                total_grids = grids_data["system_summary"]["total_active_grids"]
                health_status = self.network_recovery.get_health_status()
                self.logger.info(
                    f"📊 Managing {total_grids} active grids - "
                    f"Network Health: {health_status['status']} ({health_status['uptime_percentage']:.1f}% uptime)"
                )
        except Exception as e:
            self.logger.error(f"Error getting grid status: {e}")

    # TELEGRAM HANDLERS

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
        """Updated Telegram bot setup with admin support"""
        if not self.config.TELEGRAM_BOT_TOKEN:
            self.logger.warning("Telegram bot token not configured")
            return None

        try:
            self.telegram_app = (
                Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
            )

            # Initialize your enhanced handler
            from handlers.client_handler import ClientHandler

            self.client_handler = ClientHandler()

            # Add handlers (enhanced versions)
            self.telegram_app.add_handler(
                CommandHandler("start", self.client_handler.handle_start)
            )
            self.telegram_app.add_handler(
                CommandHandler("admin", self.client_handler.handle_admin_command)
            )  # NEW
            self.telegram_app.add_handler(
                CallbackQueryHandler(self.client_handler.handle_callback)
            )
            self.telegram_app.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, self.client_handler.handle_message
                )
            )

            self.logger.info("📱 Enhanced Telegram bot configured successfully")
            return self.telegram_app

        except Exception as e:
            self.logger.error(f"Failed to setup Telegram bot: {e}")
            return None

    async def send_startup_notification(self):
        """Send startup notification"""
        try:
            notifier = TelegramNotifier()
            if not notifier.enabled:
                return

            # Get active clients count
            with sqlite3.connect(self.config.DATABASE_PATH) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM clients WHERE status = 'active'"
                )
                active_clients = cursor.fetchone()[0]

            message = f"""🚀 GridTrader Pro Started
⚡ System: OPERATIONAL
👥 Clients: {active_clients}
📱 Bot: ✅ ENABLED
🕐 {datetime.now().strftime("%H:%M:%S")}
🤖 Ready for trading!"""

            await notifier.send_message(message)
            self.logger.info("✅ Service startup notification sent")

        except Exception as e:
            self.logger.error(f"Failed to send startup notification: {e}")

    async def run_service(self):
        """Run grid management and Telegram bot concurrently"""
        tasks = []

        # Add grid management
        management_task = asyncio.create_task(self.grid_management_loop())
        tasks.append(management_task)

        # Add Telegram bot if configured
        if self.telegram_app:
            try:
                await self.telegram_app.initialize()
                await self.telegram_app.start()

                telegram_task = asyncio.create_task(
                    self.telegram_app.updater.start_polling()
                )
                tasks.append(telegram_task)

                self.logger.info("✅ Both grid management and Telegram bot started")

            except Exception as e:
                self.logger.error(f"Failed to start Telegram bot: {e}")
                self.logger.info("🤖 Continuing with grid management only")
        else:
            self.logger.info("🤖 Starting grid management only")

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("🛑 Service stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Service error: {e}")
        finally:
            await self.stop_service()

    async def stop_service(self):
        """Stop the service gracefully"""
        self.logger.info("🛑 Stopping GridTrader Pro Service...")
        self.running = False

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
        """Main async start method"""
        self.logger.info("🚀 Starting Bad Trader Service")

        try:
            # Initialize components
            self._init_database()
            await self._startup_checks()

            self.setup_telegram_bot()

            # Send startup notification
            await self.send_startup_notification()

            # Start service
            self.running = True
            await self.run_service()

        except Exception as e:
            self.logger.error(f"❌ Startup error: {e}")
            raise

    def start(self):
        """Main start method"""
        try:
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

    print("🚀 Starting Bad Trader Service")
    print("=" * 50)
    print("🎯 CURRENT SYSTEM FEATURES")
    print("✅ Advanced Grid Manager")
    print("✅ Grid Trading Engine")
    print("✅ Inventory Management System")
    print("✅ Compound Interest Manager")
    print("✅ Volatility Risk Management")
    print("✅ Intelligent Market Timing")
    print("✅ Smart Grid Auto-Reset")
    print("✅ Enhanced FIFO Service")
    print("✅ Precision Order Handling")
    print("✅ Grid Utility Service")
    print("✅ Network Recovery & Health Monitoring")
    print("✅ USDT Grid Initializer")
    print("✅ Professional Client Management")
    print("✅ Telegram Bot Integration")
    print("✅ SQLite Analytics System")
    print("✅ Production-Ready Architecture")
    print("=" * 50)

    # Create and start service
    service = BadTradingService()
    service.start()


if __name__ == "__main__":
    main()
