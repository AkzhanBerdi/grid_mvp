# utils/enhanced_network_recovery.py
"""
FIXED Network Recovery System - Phase 4 Implementation
Corrected syntax errors and optimized for your existing setup
"""

import logging
import sqlite3
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import requests

from config import Config
from utils.network_utils import NetworkUtils


class EnhancedNetworkRecovery:
    """
    Complete network recovery service using clean NetworkUtils
    FIXED VERSION - No syntax errors
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

        # Health tracking
        self.consecutive_failures = 0
        self.total_requests = 0
        self.failed_requests = 0
        self.last_success_time = datetime.now()
        self.in_outage = False
        self.outage_start_time = None

        # Initialize monitoring
        self._init_monitoring_table()

    def _init_monitoring_table(self):
        """Initialize network monitoring table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS network_monitoring (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        event_type TEXT NOT NULL,
                        operation TEXT,
                        client_id INTEGER,
                        details TEXT,
                        consecutive_failures INTEGER,
                        status TEXT
                    )
                """)
        except Exception as e:
            self.logger.error(f"Failed to init monitoring table: {e}")

    async def safe_api_call(
        self,
        operation_name: str,
        api_func: Callable,
        client_id: Optional[int] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        *args,
        **kwargs,
    ) -> Any:
        """
        Main entry point for all network operations - FIXED VERSION
        Replaces complex error handling throughout the codebase
        """
        start_time = time.time()

        try:
            # Use NetworkUtils for clean retry logic - FIXED: All args in correct order
            result = await NetworkUtils.safe_request(
                api_func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                **kwargs,
            )

            # Track success
            await self._handle_success(
                operation_name, client_id, time.time() - start_time
            )
            return result

        except Exception as e:
            # Track failure
            await self._handle_failure(operation_name, client_id, e)
            raise

    async def _handle_success(
        self, operation: str, client_id: Optional[int], duration: float
    ):
        """Handle successful operations"""
        self.total_requests += 1

        # Detect recovery from outage
        if self.in_outage:
            outage_duration = datetime.now() - self.outage_start_time
            self.in_outage = False
            self.consecutive_failures = 0

            self.logger.info(
                f"🎉 Network recovery! {operation} succeeded after {outage_duration.total_seconds():.1f}s outage"
            )

            # Log recovery event - FIXED: Correct argument order
            self._log_event(
                "recovery", operation, f"Duration: {outage_duration}", client_id
            )

        self.last_success_time = datetime.now()

        # Log network event for monitoring
        NetworkUtils.log_network_event(
            "success", f"{operation} completed in {duration:.2f}s"
        )

    async def _handle_failure(
        self, operation: str, client_id: Optional[int], error: Exception
    ):
        """Handle failed operations"""
        self.failed_requests += 1
        self.consecutive_failures += 1

        # Detect outage start
        if not self.in_outage and self.consecutive_failures >= 3:
            self.in_outage = True
            self.outage_start_time = datetime.now()

            self.logger.warning(
                f"🚨 Network outage detected! {self.consecutive_failures} consecutive failures"
            )

            # Log outage event - FIXED: Correct argument order
            self._log_event("outage_start", operation, str(error), client_id)

        # Log failure event - FIXED: Correct argument order
        self._log_event("failure", operation, str(error), client_id)

        # Log network event for monitoring
        NetworkUtils.log_network_event("failure", f"{operation} failed: {error}")

    def _log_event(
        self, event_type: str, operation: str, details: str, client_id: Optional[int]
    ):
        """Log events to database - FIXED VERSION"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO network_monitoring 
                    (event_type, operation, client_id, details, consecutive_failures, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        event_type,
                        operation,
                        client_id,
                        details,
                        self.consecutive_failures,
                        "outage" if self.in_outage else "normal",
                    ),
                )
        except Exception as e:
            self.logger.error(f"Failed to log network event: {e}")

    async def health_check(self) -> bool:
        """Perform comprehensive health check"""
        try:
            # Test basic connectivity
            health_tests = [
                ("binance_ping", self._test_binance_connectivity),
                ("telegram_ping", self._test_telegram_connectivity),
                ("database_test", self._test_database_connectivity),
            ]

            all_healthy = True
            for test_name, test_func in health_tests:
                try:
                    await self.safe_api_call(test_name, test_func)
                except Exception as e:
                    self.logger.warning(f"Health check failed: {test_name} - {e}")
                    all_healthy = False

            return all_healthy

        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return False

    async def _test_binance_connectivity(self):
        """Test Binance API connectivity"""
        response = requests.get("https://api.binance.com/api/v3/ping", timeout=10)
        response.raise_for_status()
        return True

    async def _test_telegram_connectivity(self):
        """Test Telegram API connectivity"""
        # Simple test - just check if Telegram API is reachable
        response = requests.get("https://api.telegram.org", timeout=10)
        # 401 is expected without token, but means API is reachable
        return response.status_code in [200, 401, 404]

    async def _test_database_connectivity(self):
        """Test database connectivity"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("SELECT 1").fetchone()
        return True

    def get_health_status(self) -> Dict:
        """Get current health status"""
        uptime_percentage = 100.0
        if self.total_requests > 0:
            uptime_percentage = (
                (self.total_requests - self.failed_requests) / self.total_requests
            ) * 100

        return {
            "status": "healthy" if not self.in_outage else "outage",
            "uptime_percentage": round(uptime_percentage, 2),
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "last_success": self.last_success_time.isoformat(),
            "in_outage": self.in_outage,
            "outage_duration": (
                (datetime.now() - self.outage_start_time).total_seconds()
                if self.outage_start_time
                else 0
            ),
        }

    def is_emergency_stop_needed(self) -> bool:
        """Check if emergency stop is needed"""
        # Emergency stop if 5+ consecutive failures or outage > 10 minutes
        return self.consecutive_failures >= 5 or (
            self.in_outage
            and self.outage_start_time
            and (datetime.now() - self.outage_start_time).total_seconds() > 600
        )


# Simple wrapper for your existing grid orchestrator
class NetworkWrappedGridOrchestrator:
    """
    Simple wrapper for your existing grid orchestrator
    Adds network recovery without changing existing code
    """

    def __init__(self, base_orchestrator):
        self.base_orchestrator = base_orchestrator
        self.network_recovery = EnhancedNetworkRecovery()

    async def start_client_grid_with_recovery(
        self, client_id: int, symbol: str, capital: float
    ):
        """Start grid with network recovery"""
        return await self.network_recovery.safe_api_call(
            f"start_grid_{client_id}_{symbol}",
            self.base_orchestrator.start_client_grid,
            client_id=client_id,
            max_retries=3,
            base_delay=2.0,
            symbol=symbol,
            capital=capital,
        )

    async def stop_all_client_grids_with_recovery(self, client_id: int):
        """Stop grids with network recovery"""
        return await self.network_recovery.safe_api_call(
            f"stop_grids_{client_id}",
            self.base_orchestrator.stop_all_client_grids,
            client_id=client_id,
            max_retries=5,  # More retries for stop operations
            base_delay=1.0,
        )

    async def update_all_grids_with_recovery(self):
        """Update all grids with network recovery"""
        return await self.network_recovery.safe_api_call(
            "update_all_grids",
            self.base_orchestrator.update_all_grids,
            max_retries=3,
            base_delay=1.5,
        )

    # Delegate all other methods to base orchestrator
    def __getattr__(self, name):
        """Delegate unknown attributes to base orchestrator"""
        return getattr(self.base_orchestrator, name)
