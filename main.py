#!/usr/bin/env python3
"""
GridTrader Pro - Simplified Client Service
Production-ready grid trading for paying clients
WITH INTEGRATED NETWORK RECOVERY
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
from handlers.smart_client_handler import SmartClientHandler
from services.enhanced_grid_orchestrator import EnhancedGridOrchestrator
from utils.network_recovery import create_network_recovery_service

# FIFO Profit Monitoring Integration
try:
    from utils.fifo_telegram_monitor import FIFOMonitoringService

    FIFO_AVAILABLE = True
except ImportError:
    print("⚠️ FIFO monitoring not available - install analytics dependencies")
    FIFO_AVAILABLE = False


class GridTradingService:
    """Simplified Grid Trading Service for Paying Clients with Network Recovery"""

    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()

        # Initialize components
        self.db_setup = DatabaseSetup()
        self.grid_orchestrator = EnhancedGridOrchestrator()
        self.handler = SmartClientHandler()

        # Network Recovery Integration (NEW)
        self.network_service = create_network_recovery_service()

        # FIFO Profit Monitoring (NEW)
        if FIFO_AVAILABLE:
            self.fifo_service = FIFOMonitoringService()
        else:
            self.fifo_service = None
        self.last_health_check = datetime.now()
        self.health_check_interval = timedelta(minutes=5)  # Check every 5 minutes

        # Service state
        self.running = False
        self.telegram_app = None

        self.logger.info(
            "🤖 GridTrader Pro Client Service initialized with Network Recovery"
        )

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

    async def _startup_checks(self):
        """Perform startup connectivity and health checks (NEW)"""
        self.logger.info("🔍 Performing startup connectivity checks...")

        # Check network connectivity before starting
        connectivity_ok = await self.network_service.startup_connectivity_check()

        if not connectivity_ok:
            self.logger.warning("⚠️ Some network services are offline")
            self.logger.warning("Bot will start but may have limited functionality")
        else:
            self.logger.info("✅ All network services operational")

        return connectivity_ok

    async def _periodic_health_check(self):
        """Perform periodic health check if interval has passed (NEW)"""
        now = datetime.now()

        if now - self.last_health_check >= self.health_check_interval:
            self.last_health_check = now

            try:
                # Run comprehensive health check
                health_ok = await self.network_service.periodic_health_check()

                if not health_ok:
                    self.logger.critical(
                        "🚨 Network health check failed - emergency conditions detected"
                    )

                    # Check if we should trigger emergency stop
                    emergency = await self.network_service.check_emergency_conditions()
                    if emergency:
                        self.logger.critical("🚨 Network emergency stop triggered")
                        return False  # Signal to stop the service

                # Log network status
                health_status = self.network_service.get_network_health_display()
                self.logger.info(f"📊 {health_status}")

            except Exception as e:
                # Don't let health check failures crash the bot
                self.logger.error(f"Health check error: {e}")
                await self.network_service.health_monitor.handle_network_error(
                    e, "periodic_health_check"
                )

        return True  # Continue operation

    async def grid_management_loop(self):
        """Enhanced grid management loop with network recovery"""
        self.logger.info("🔄 Starting grid management loop with network recovery")

        while self.running:
            try:
                # Periodic health check (NEW)
                health_ok = await self._periodic_health_check()
                if not health_ok:
                    self.logger.critical(
                        "🚨 Health check failed - stopping grid management"
                    )
                    self.running = False
                    break

                # Update all active grids (wrapped with network recovery)
                try:
                    await self._safe_grid_update()
                except Exception as e:
                    # Enhanced error handling with network context
                    await self.network_service.health_monitor.handle_network_error(
                        e, "grid_update"
                    )

                    # Check if this is a network-related emergency
                    emergency = await self.network_service.check_emergency_conditions()
                    if emergency:
                        self.logger.critical(
                            "🚨 Grid update emergency - stopping service"
                        )
                        self.running = False
                        break

                    # Log error and continue
                    self.logger.error(f"Grid update error: {e}")

                # Log status every 5 minutes (your existing pattern)
                active_grids = self.grid_orchestrator.get_all_active_grids()
                if active_grids:
                    self.logger.info(f"📊 Managing {len(active_grids)} active grids")

                # Wait 30 seconds before next update (your existing pattern)
                await asyncio.sleep(30)

            except Exception as e:
                # Top-level error handling with network recovery
                await self.network_service.health_monitor.handle_network_error(
                    e, "grid_management_loop"
                )

                self.logger.error(f"Error in grid management loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _safe_grid_update(self):
        """Grid update wrapped with network recovery (NEW)"""
        try:
            # Your existing grid update logic
            await self.grid_orchestrator.update_all_grids()

            # Signal successful network operation
            await self.network_service.health_monitor.handle_network_success(
                "grid_update"
            )

        except Exception as e:
            # Let the calling function handle the error
            raise e

    async def telegram_start(self, update, context):
        """Handle /start command with network recovery"""
        try:
            await self.handler.handle_start(update, context)

            # Signal successful Telegram operation
            await self.network_service.health_monitor.handle_network_success(
                "telegram_start"
            )

        except Exception as e:
            # Enhanced error handling for Telegram operations
            await self.network_service.health_monitor.handle_network_error(
                e, "telegram_start"
            )
            self.logger.error(f"Error in start handler: {e}")

    async def telegram_callback(self, update, context):
        """Handle callback queries with network recovery"""
        try:
            await self.handler.handle_callback(update, context)

            # Signal successful Telegram operation
            await self.network_service.health_monitor.handle_network_success(
                "telegram_callback"
            )

        except Exception as e:
            # Enhanced error handling for Telegram operations
            await self.network_service.health_monitor.handle_network_error(
                e, "telegram_callback"
            )
            self.logger.error(f"Error in callback handler: {e}")

    async def telegram_message(self, update, context):
        """Handle text messages with network recovery"""
        try:
            await self.handler.handle_message(update, context)

            # Signal successful Telegram operation
            await self.network_service.health_monitor.handle_network_success(
                "telegram_message"
            )

        except Exception as e:
            # Enhanced error handling for Telegram operations
            await self.network_service.health_monitor.handle_network_error(
                e, "telegram_message"
            )
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
                # Enhanced Telegram startup error handling
                await self.network_service.health_monitor.handle_network_error(
                    e, "telegram_startup"
                )
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
            # Enhanced top-level error handling
            await self.network_service.health_monitor.handle_network_error(
                e, "service_runtime"
            )
            self.logger.error(f"❌ Service error: {e}")
        finally:
            # Cleanup
            await self.stop_service()

    async def stop_service(self):
        """Stop the service gracefully"""
        self.logger.info("🛑 Stopping GridTrader Pro Service...")
        self.running = False

        # Stop all grids first
        try:
            await self.grid_orchestrator.shutdown_all_grids()
        except Exception as e:
            self.logger.error(f"Error stopping grids: {e}")

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
        """Enhanced async start method with network recovery"""
        self.logger.info(
            "🚀 Starting GridTrader Pro Client Service with Network Recovery"
        )

        try:
            self._init_database()
            await self._startup_checks()

            if self.fifo_service:
                await self._init_fifo_monitoring()

            self.setup_telegram_bot()

            self.running = True
            await self.run_service()

        except Exception as e:
            await self.network_service.health_monitor.handle_network_error(
                e, "service_startup"
            )
            self.logger.error(f"❌ Startup error: {e}")
            raise

    async def _init_fifo_monitoring(self):
        """Initialize FIFO monitoring for existing clients"""
        try:
            # Get all active clients
            with sqlite3.connect(self.config.DATABASE_PATH) as conn:
                cursor = conn.execute(
                    "SELECT telegram_id FROM clients WHERE status = 'active'"
                )
                active_clients = [row[0] for row in cursor.fetchall()]

            # Add FIFO monitoring for each client
            for client_id in active_clients:
                await self.fifo_service.add_client_monitor(client_id)

            self.logger.info(
                f"✅ FIFO monitoring initialized for {len(active_clients)} clients"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize FIFO monitoring: {e}")

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

    def get_service_status(self):
        """Get comprehensive service status including network health (NEW)"""
        try:
            network_health = self.network_service.get_network_health_display()
            active_grids = (
                len(self.grid_orchestrator.get_all_active_grids())
                if hasattr(self.grid_orchestrator, "get_all_active_grids")
                else 0
            )

            return {
                "running": self.running,
                "network_health": network_health,
                "active_grids": active_grids,
                "telegram_bot": self.telegram_app is not None,
                "last_health_check": self.last_health_check.isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}


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
    print("✅ Network recovery enabled")  # NEW
    print("✅ Production ready")
    print("=" * 50)

    # Create and start service
    service = GridTradingService()
    service.start()


if __name__ == "__main__":
    main()
