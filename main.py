#!/usr/bin/env python3
"""
GridTrader Pro - Simplified Client Service
Production-ready grid trading for paying clients
WITH PHASE 4 ENHANCED NETWORK RECOVERY
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
from services.fifo_service import FIFOService
from services.grid_orchestrator import GridOrchestrator
from utils.network_recovery import EnhancedNetworkRecovery
from utils.network_utils import NetworkUtils


class GridTradingService:
    """Simplified Grid Trading Service with Phase 4 Enhanced Network Recovery Only"""

    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()

        # Initialize components
        self.db_setup = DatabaseSetup()
        self.grid_orchestrator = GridOrchestrator()
        self.handler = ClientHandler()

        # Enhanced Network Recovery (Phase 4 - ONLY NETWORK RECOVERY SYSTEM)
        self.network_recovery = EnhancedNetworkRecovery()

        # FIFO Profit Monitoring (Phase 3)
        self.fifo_service = FIFOService()

        self.last_health_check = datetime.now()
        self.health_check_interval = timedelta(minutes=5)

        # Service state
        self.running = False
        self.telegram_app = None

        self.logger.info(
            "🤖 GridTrader Pro Client Service initialized with Enhanced Network Recovery"
        )

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration - FIXED"""
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
        """Initialize database tables"""
        try:
            self.db_setup.initialize()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def _startup_checks(self):
        """Perform startup connectivity and health checks"""
        self.logger.info("🔍 Performing startup connectivity checks...")

        # Enhanced health check (Phase 4)
        health_ok = await self.network_recovery.health_check()

        if not health_ok:
            self.logger.warning("⚠️ Some network services are offline")
            self.logger.warning("Bot will start but may have limited functionality")
        else:
            self.logger.info("✅ All network services operational")

        # Log initial health status
        health_status = self.network_recovery.get_health_status()
        self.logger.info(
            f"📊 Network Health: {health_status['status']} ({health_status['uptime_percentage']:.1f}% uptime)"
        )

        return health_ok

    async def _periodic_health_check(self):
        """Perform periodic health check if interval has passed"""
        now = datetime.now()

        if now - self.last_health_check >= self.health_check_interval:
            self.last_health_check = now

            try:
                # Enhanced health check (Phase 4)
                health_ok = await self.network_recovery.health_check()

                if not health_ok:
                    self.logger.critical(
                        "🚨 Network health check failed - emergency conditions detected"
                    )

                    # Check if we should trigger emergency stop
                    if self.network_recovery.is_emergency_stop_needed():
                        self.logger.critical("🚨 Network emergency stop triggered")
                        return False

                # Enhanced status logging
                health_status = self.network_recovery.get_health_status()
                self.logger.info(
                    f"📊 Network Health: {health_status['status']} ({health_status['uptime_percentage']:.1f}% uptime)"
                )

            except Exception as e:
                # Enhanced error handling
                await self.network_recovery._handle_failure("health_check", None, e)
                self.logger.error(f"Health check error: {e}")

        return True

    async def grid_management_loop(self):
        """Enhanced grid management loop with network recovery"""
        self.logger.info("🔄 Starting enhanced grid management loop")

        while self.running:
            try:
                # Health check
                health_ok = await self._periodic_health_check()
                if not health_ok:
                    self.logger.critical(
                        "🚨 Health check failed - stopping grid management"
                    )
                    self.running = False
                    break

                # Emergency stop check
                if self.network_recovery.is_emergency_stop_needed():
                    self.logger.critical(
                        "🚨 Emergency stop triggered by network conditions"
                    )
                    await self._emergency_shutdown()
                    self.running = False
                    break

                # Update all active grids with enhanced error handling
                try:
                    # Use NetworkUtils for enhanced reliability
                    await NetworkUtils.safe_request(
                        self._safe_grid_update, max_retries=3, base_delay=2.0
                    )

                except Exception as e:
                    # Enhanced error handling
                    await self.network_recovery._handle_failure("grid_update", None, e)

                    # Check for emergency conditions
                    if self.network_recovery.is_emergency_stop_needed():
                        self.logger.critical(
                            "🚨 Grid update emergency - stopping service"
                        )
                        self.running = False
                        break

                    self.logger.error(f"Grid update error: {e}")

                # Enhanced status logging
                active_grids = self.grid_orchestrator.get_all_active_grids()
                if active_grids:
                    health_status = self.network_recovery.get_health_status()
                    self.logger.info(
                        f"📊 Managing {len(active_grids)} active grids - "
                        f"Network Health: {health_status['status']} ({health_status['uptime_percentage']:.1f}% uptime)"
                    )

                await asyncio.sleep(30)

            except Exception as e:
                # Top-level enhanced error handling
                await self.network_recovery._handle_failure(
                    "grid_management_loop", None, e
                )
                self.logger.error(f"Error in grid management loop: {e}")
                await asyncio.sleep(60)

    async def _safe_grid_update(self):
        """Grid update wrapped with network recovery"""
        try:
            # Your existing grid update logic
            await self.grid_orchestrator.update_all_grids()

            # Signal successful operation
            await self.network_recovery._handle_success("grid_update", None, 0.5)

        except Exception as e:
            # Let the calling function handle the error
            raise e

    async def _emergency_shutdown(self):
        """Emergency shutdown procedure"""
        self.logger.critical("🚨 Initiating emergency shutdown...")

        try:
            # Stop all grids with enhanced retry logic
            await NetworkUtils.safe_request(
                self.grid_orchestrator.shutdown_all_grids,
                max_retries=10,
                base_delay=5.0,
            )

            self.logger.critical("🛑 Emergency shutdown complete")

        except Exception as e:
            self.logger.critical(f"❌ Emergency shutdown failed: {e}")

    async def telegram_start(self, update, context):
        """Handle /start command with enhanced network recovery"""
        try:
            await self.handler.handle_start(update, context)

            # Signal successful operation
            await self.network_recovery._handle_success(
                "telegram_start", update.effective_user.id, 0.1
            )

        except Exception as e:
            # Enhanced error handling for Telegram operations
            await self.network_recovery._handle_failure(
                "telegram_start", update.effective_user.id, e
            )
            self.logger.error(f"Error in start handler: {e}")

    async def telegram_callback(self, update, context):
        """Handle callback queries with enhanced network recovery"""
        try:
            await self.handler.handle_callback(update, context)

            # Signal successful operation
            await self.network_recovery._handle_success(
                "telegram_callback", update.effective_user.id, 0.1
            )

        except Exception as e:
            # Enhanced error handling for Telegram operations
            await self.network_recovery._handle_failure(
                "telegram_callback", update.effective_user.id, e
            )
            self.logger.error(f"Error in callback handler: {e}")

    async def telegram_message(self, update, context):
        """Handle text messages with enhanced network recovery"""
        try:
            await self.handler.handle_message(update, context)

            # Signal successful operation
            await self.network_recovery._handle_success(
                "telegram_message", update.effective_user.id, 0.1
            )

        except Exception as e:
            # Enhanced error handling for Telegram operations
            await self.network_recovery._handle_failure(
                "telegram_message", update.effective_user.id, e
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
                # Initialize and start Telegram bot with enhanced error handling
                await NetworkUtils.safe_request(
                    self._start_telegram_bot, max_retries=5, base_delay=3.0
                )

                # Create polling task
                telegram_task = asyncio.create_task(
                    self.telegram_app.updater.start_polling()
                )
                tasks.append(telegram_task)

                self.logger.info("✅ Both grid management and Telegram bot started")

            except Exception as e:
                # Enhanced Telegram startup error handling
                await self.network_recovery._handle_failure("telegram_startup", None, e)
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
            await self.network_recovery._handle_failure("service_runtime", None, e)
            self.logger.error(f"❌ Service error: {e}")
        finally:
            # Cleanup
            await self.stop_service()

    async def _start_telegram_bot(self):
        """Start Telegram bot with enhanced error handling"""
        await self.telegram_app.initialize()
        await self.telegram_app.start()

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
            "🚀 Starting GridTrader Pro Client Service with Enhanced Network Recovery"
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
            # Enhanced startup error handling
            await self.network_recovery._handle_failure("service_startup", None, e)
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

            # Initialize FIFO monitoring using the new FIFOService
            for client_id in active_clients:
                self.fifo_service.calculate_fifo_performance(client_id)

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
        """Get comprehensive service status including enhanced network health"""
        try:
            # Enhanced network health
            health_status = self.network_recovery.get_health_status()

            active_grids = (
                len(self.grid_orchestrator.get_all_active_grids())
                if hasattr(self.grid_orchestrator, "get_all_active_grids")
                else 0
            )

            return {
                "running": self.running,
                "network_health": health_status,
                "active_grids": active_grids,
                "telegram_bot": self.telegram_app is not None,
                "last_health_check": self.last_health_check.isoformat(),
                "emergency_stop_needed": self.network_recovery.is_emergency_stop_needed(),
                "total_network_requests": health_status.get("total_requests", 0),
                "network_uptime_percentage": health_status.get(
                    "uptime_percentage", 100.0
                ),
                "network_status": health_status.get("status", "unknown"),
                "consecutive_failures": health_status.get("consecutive_failures", 0),
            }
        except Exception as e:
            return {"error": str(e)}


def main():
    """Entry point - Clean Phase 4 Implementation"""
    # Validate configuration
    if not Config.validate():
        print("❌ Invalid configuration. Please check your environment variables.")
        sys.exit(1)

    print("🚀 Starting GridTrader Pro Client Service")
    print("=" * 50)
    print("✅ Real trading only - no trials or demos")
    print("✅ Client API key management")
    print("✅ Professional grid trading")
    print("✅ Smart client handler (Phase 2)")
    print("✅ Clean time sync (Phase 1)")
    print("✅ Unified FIFO service (Phase 3)")
    print("✅ Enhanced network recovery (Phase 4)")
    print("✅ Emergency stop protection")
    print("✅ Comprehensive health monitoring")
    print("✅ Telegram interface")
    print("✅ Production ready")
    print("=" * 50)

    # Create and start service
    service = GridTradingService()
    service.start()


if __name__ == "__main__":
    main()
