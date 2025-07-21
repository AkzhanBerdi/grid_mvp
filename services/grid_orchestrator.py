# services/grid_orchestrator.py - UPDATED FOR SINGLE ADVANCED GRID
"""
Updated Grid Orchestrator for Single Advanced Grid Architecture
==============================================================

Replaces dual-grid management with simplified single advanced grid system.
Integrates with SingleAdvancedGridManager for maximum efficiency.

Changes from previous version:
- Replaced EnhancedDualScaleGridManager with SingleAdvancedGridManager
- Simplified command interface (FORCE ETH 880, FORCE SOL 660, etc.)
- 100% capital allocation efficiency
- Unified performance monitoring
- Streamlined grid management
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, Optional

from binance.client import Client

from config import Config
from models.client import GridStatus
from repositories.client_repository import ClientRepository
from services.fifo_service import FIFOService
from services.single_advanced_grid_manager import SingleAdvancedGridManager
from utils.crypto import CryptoUtils

try:
    from utils.fifo_telegram_monitor import FIFOMonitoringService
except ImportError:
    # Fallback if TelegramNotifier doesn't exist
    class TelegramNotifier:
        def __init__(self):
            self.enabled = False

        async def send_message(self, message):
            pass


class GridOrchestrator:
    """
    Unified Grid Orchestrator for Single Advanced Grid System

    Key improvements:
    - Single manager per client (no dual-grid complexity)
    - Simplified command processing
    - 100% capital utilization
    - Enhanced monitoring and reporting
    - Streamlined client management
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Core services
        self.client_repo = ClientRepository()
        self.crypto_utils = CryptoUtils()

        # Single Advanced Grid Managers (one per client)
        self.advanced_managers: Dict[int, SingleAdvancedGridManager] = {}

        # Binance clients cache (matches your existing pattern)
        self.binance_clients: Dict[int, Client] = {}
        self.notification_manager = FIFOMonitoringService()
        self.last_daily_summary = None

        # Monitoring state
        self.monitoring_active = False
        self.last_health_check = 0

        # Performance tracking
        self.system_metrics = {
            "total_grids_started": 0,
            "total_grids_stopped": 0,
            "total_force_commands": 0,
            "system_uptime_start": time.time(),
            "last_optimization": 0,
        }
        self.fifo_service = FIFOService()
        self.last_daily_summary = None

        self.logger.info(
            "🚀 GridOrchestrator initialized for Single Advanced Grid System"
        )
        self.logger.info("   🎯 Architecture: Single Advanced Grid per Asset")
        self.logger.info("   💎 Capital Efficiency: 100% (no dual-grid splits)")
        self.logger.info("   🔧 Management: Simplified unified system")

    async def create_advanced_manager(self, client_id: int) -> bool:
        """
        Create Single Advanced Grid Manager for client

        Replaces the dual-grid manager creation with simplified single manager
        """
        try:
            if client_id in self.advanced_managers:
                self.logger.info(
                    f"✅ Advanced manager already exists for client {client_id}"
                )
                return True

            # Get or create Binance client using existing pattern
            binance_client = await self._get_binance_client(client_id)
            if not binance_client:
                self.logger.error(
                    f"❌ Failed to create Binance client for client {client_id}"
                )
                return False

            # Create Single Advanced Grid Manager
            self.advanced_managers[client_id] = SingleAdvancedGridManager(
                binance_client, client_id
            )

            self.logger.info(
                f"✅ SingleAdvancedGridManager created for client {client_id}"
            )
            self.logger.info("   🎯 Features: ALL advanced features unified")
            self.logger.info("   💰 Capital: 100% allocation efficiency")
            self.logger.info("   🔧 Management: Simplified single-grid system")

            return True

        except Exception as e:
            self.logger.error(
                f"❌ Failed to create advanced manager for client {client_id}: {e}"
            )
            return False

    async def _get_binance_client(self, client_id: int) -> Optional[Client]:
        """Get or create Binance client using existing pattern from your system"""
        try:
            if client_id in self.binance_clients:
                return self.binance_clients[client_id]

            # Get client credentials using your existing pattern
            client = self.client_repo.get_client(client_id)
            if not client:
                self.logger.error(f"❌ Client {client_id} not found in database")
                return None

            if not client.binance_api_key or not client.binance_secret_key:
                self.logger.error(f"❌ Missing API credentials for client {client_id}")
                return None

            # Decrypt API keys using your existing method
            api_key, secret_key = self.client_repo.get_decrypted_api_keys(client)
            if not api_key or not secret_key:
                self.logger.error(
                    f"❌ Failed to decrypt API keys for client {client_id}"
                )
                return None

            # Create Binance client using your existing pattern
            binance_client = Client(api_key, secret_key, testnet=False)

            # Test connection with recv_window handling (matches your existing code)
            try:
                account = binance_client.get_account(recvWindow=60000)
            except TypeError:
                # Fallback for older binance versions
                account = binance_client.get_account()

            if binance_client:
                self.binance_clients[client_id] = binance_client
                self.logger.info(f"✅ Binance client created for client {client_id}")
                self.logger.info(
                    f"   📊 Account Type: {account.get('accountType', 'Unknown')}"
                )
                self.logger.info(f"   🔑 Can Trade: {account.get('canTrade', False)}")

            return binance_client

        except Exception as e:
            self.logger.error(
                f"❌ Binance client creation error for client {client_id}: {e}"
            )
            return None

    async def force_start_grid(self, client_id: int, command: str) -> Dict:
        """
        Handle simplified FORCE commands for single advanced grids

        Examples:
        - FORCE ETH 880  -> Start single advanced ETH grid with $880
        - FORCE SOL 660  -> Start single advanced SOL grid with $660
        - FORCE ADA 660  -> Start single advanced ADA grid with $660
        """
        try:
            self.logger.info(
                f"🚀 Processing FORCE command for client {client_id}: {command}"
            )

            # Ensure advanced manager exists
            if not await self.create_advanced_manager(client_id):
                return {"success": False, "error": "Failed to create advanced manager"}

            # Execute force command through SingleAdvancedGridManager
            manager = self.advanced_managers[client_id]
            result = await manager.handle_force_command(command)

            if result["success"]:
                # Update client status
                client = self.client_repo.get_client(client_id)
                if client:
                    client.grid_status = GridStatus.ACTIVE
                    self.client_repo.update_client(client)

                # Update system metrics
                self.system_metrics["total_grids_started"] += 1
                self.system_metrics["total_force_commands"] += 1

                # Enhanced success logging
                self.logger.info(f"🎉 FORCE COMMAND SUCCESS for client {client_id}:")
                self.logger.info(f"   📊 Symbol: {result.get('symbol', 'Unknown')}")
                self.logger.info(
                    f"   💰 Capital: ${result.get('total_capital', 0):,.2f}"
                )
                self.logger.info(
                    f"   🎯 Strategy: {result.get('strategy', 'Single Advanced Grid')}"
                )
                self.logger.info(
                    f"   📈 Orders Placed: {result.get('grid_details', {}).get('orders_placed', 0)}"
                )
                self.logger.info(
                    f"   ⚡ Efficiency: {result.get('capital_efficiency', '100%')}"
                )

                # Send notification
                try:
                    await self._send_grid_start_notification(client_id, result)
                except Exception as e:
                    self.logger.warning(f"⚠️ Notification failed: {e}")

            else:
                self.logger.error(
                    f"❌ FORCE command failed for client {client_id}: {result.get('error', 'Unknown error')}"
                )

            return result

        except Exception as e:
            self.logger.error(f"❌ Force start error for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    def __del__(self):
        """Cleanup on object destruction"""
        try:
            if self.monitoring_active:
                self.monitoring_active = False
        except:
            pass

    async def stop_grid(self, client_id: int, symbol: str) -> Dict:
        """Stop single advanced grid for specific symbol"""
        try:
            if client_id not in self.advanced_managers:
                return {"success": False, "error": "No active manager for client"}

            manager = self.advanced_managers[client_id]
            result = await manager.stop_single_advanced_grid(symbol)

            if result["success"]:
                # Update system metrics
                self.system_metrics["total_grids_stopped"] += 1

                # Check if client has any remaining active grids
                all_grids = manager.get_all_active_grids()
                if not all_grids.get("grids"):
                    # No more active grids, update client status
                    client = self.client_repo.get_client(client_id)
                    if client:
                        client.grid_status = GridStatus.INACTIVE
                        self.client_repo.update_client(client)

                self.logger.info(
                    f"✅ Grid stopped for client {client_id}, symbol {symbol}"
                )

                # Send notification
                try:
                    await self._send_grid_stop_notification(client_id, result)
                except Exception as e:
                    self.logger.warning(f"⚠️ Stop notification failed: {e}")

            return result

        except Exception as e:
            self.logger.error(
                f"❌ Grid stop error for client {client_id}, symbol {symbol}: {e}"
            )
            return {"success": False, "error": str(e)}

    async def stop_all_grids(self, client_id: int) -> Dict:
        """Stop all active grids for a client"""
        try:
            if client_id not in self.advanced_managers:
                return {"success": False, "error": "No active manager for client"}

            manager = self.advanced_managers[client_id]
            all_grids = manager.get_all_active_grids()

            if not all_grids.get("grids"):
                return {"success": True, "message": "No active grids to stop"}

            results = {}
            total_stopped = 0

            # Stop each active grid
            for symbol in all_grids["grids"].keys():
                try:
                    result = await manager.stop_single_advanced_grid(symbol)
                    results[symbol] = result
                    if result["success"]:
                        total_stopped += 1
                except Exception as e:
                    results[symbol] = {"success": False, "error": str(e)}

            # Update client status
            client = self.client_repo.get_client(client_id)
            if client:
                client.grid_status = GridStatus.INACTIVE
                self.client_repo.update_client(client)

            # Update system metrics
            self.system_metrics["total_grids_stopped"] += total_stopped

            summary = {
                "success": total_stopped > 0,
                "total_stopped": total_stopped,
                "total_attempted": len(all_grids["grids"]),
                "details": results,
            }

            self.logger.info(
                f"✅ All grids stopped for client {client_id}: {total_stopped} grids"
            )

            return summary

        except Exception as e:
            self.logger.error(f"❌ Stop all grids error for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_all_active_grids(self) -> Dict:
        """Get status of all active single advanced grids across all clients"""
        all_grids = {}
        system_summary = {
            "total_clients": len(self.advanced_managers),
            "total_active_grids": 0,
            "total_capital_deployed": 0.0,
            "architecture": "Single Advanced Grid System",
            "efficiency": "100% - No dual-grid overhead",
        }

        for client_id, manager in self.advanced_managers.items():
            try:
                client_grids = manager.get_all_active_grids()
                if client_grids.get("grids"):
                    all_grids[client_id] = {
                        "client_id": client_id,
                        "trading_mode": client_grids.get(
                            "trading_mode", "Single Advanced Grid"
                        ),
                        "grids": client_grids["grids"],
                        "client_metrics": client_grids.get("global_metrics", {}),
                        "system_efficiency": client_grids.get(
                            "system_efficiency", "Maximized"
                        ),
                    }

                    # Aggregate system metrics
                    system_summary["total_active_grids"] += len(client_grids["grids"])

                    # Calculate total capital deployed
                    for grid_data in client_grids["grids"].values():
                        grid_details = grid_data.get("grid_details", {})
                        if "total_capital" in grid_details:
                            system_summary["total_capital_deployed"] += grid_details[
                                "total_capital"
                            ]

            except Exception as e:
                self.logger.error(f"❌ Failed to get grids for client {client_id}: {e}")

        return {
            "system_summary": system_summary,
            "client_grids": all_grids,
            "system_metrics": self.system_metrics,
            "architecture_benefits": [
                "100% capital allocation efficiency",
                "Simplified management (no dual-grid coordination)",
                "Maximum advanced features utilization",
                "Unified performance monitoring",
                "Streamlined command interface",
            ],
        }

    async def get_client_status(self, client_id: int) -> Dict:
        """Get comprehensive status for specific client"""
        try:
            if client_id not in self.advanced_managers:
                return {
                    "client_id": client_id,
                    "status": "inactive",
                    "error": "No active manager found",
                }

            manager = self.advanced_managers[client_id]

            # Get all grids for this client
            client_grids = manager.get_all_active_grids()

            # Get unified performance report
            performance_report = await manager.get_unified_performance_report()

            # Get client info from database
            client = self.client_repo.get_client(client_id)

            return {
                "client_id": client_id,
                "status": "active",
                "client_info": {
                    "username": client.username if client else "Unknown",
                    "grid_status": client.grid_status.value if client else "Unknown",
                    "created_at": client.created_at if client else None,
                },
                "trading_system": {
                    "architecture": "Single Advanced Grid",
                    "capital_efficiency": "100%",
                    "total_active_grids": len(client_grids.get("grids", {})),
                    "system_efficiency": client_grids.get(
                        "system_efficiency", "Maximized"
                    ),
                },
                "active_grids": client_grids.get("grids", {}),
                "performance_report": performance_report,
                "advanced_features": {
                    "compound_management": "Active - 100% allocation",
                    "volatility_management": "Active - Unified adjustment",
                    "market_timing": "Active - Single optimization",
                    "auto_reset": "Active - Simplified logic",
                    "precision_handling": "Active - Single execution path",
                    "kelly_criterion": "Active - Unified position sizing",
                },
            }

        except Exception as e:
            self.logger.error(f"❌ Client status error for {client_id}: {e}")
            return {"client_id": client_id, "status": "error", "error": str(e)}

    async def get_system_performance_report(self) -> Dict:
        """Generate comprehensive system performance report"""
        try:
            system_start_time = self.system_metrics["system_uptime_start"]
            current_time = time.time()
            uptime_hours = (current_time - system_start_time) / 3600

            # Aggregate performance across all clients
            total_clients = len(self.advanced_managers)
            total_grids = 0
            total_capital = 0.0
            total_realized_pnl = 0.0
            total_optimization_events = 0

            client_performances = {}

            for client_id, manager in self.advanced_managers.items():
                try:
                    # Get unified performance report for this client
                    client_performance = await manager.get_unified_performance_report()
                    client_performances[client_id] = client_performance

                    # Aggregate metrics
                    if "grid_summaries" in client_performance:
                        total_grids += len(client_performance["grid_summaries"])

                        for grid_data in client_performance["grid_summaries"].values():
                            total_capital += grid_data.get("total_capital", 0)
                            total_realized_pnl += grid_data.get("realized_pnl", 0)

                    if "global_metrics" in client_performance:
                        global_metrics = client_performance["global_metrics"]
                        total_optimization_events += global_metrics.get(
                            "total_optimizations", 0
                        )

                except Exception as e:
                    self.logger.error(
                        f"❌ Performance aggregation error for client {client_id}: {e}"
                    )

            # Calculate system-wide metrics
            avg_capital_per_grid = total_capital / total_grids if total_grids > 0 else 0
            overall_roi = (
                (total_realized_pnl / total_capital * 100) if total_capital > 0 else 0
            )

            return {
                "system_performance_report": {
                    "timestamp": current_time,
                    "report_period_hours": uptime_hours,
                    "architecture": "Single Advanced Grid System",
                    "system_overview": {
                        "total_clients": total_clients,
                        "total_active_grids": total_grids,
                        "total_capital_deployed": total_capital,
                        "average_capital_per_grid": avg_capital_per_grid,
                        "architecture_efficiency": "100% - No dual-grid overhead",
                    },
                    "financial_performance": {
                        "total_realized_pnl": total_realized_pnl,
                        "overall_roi_percent": overall_roi,
                        "average_pnl_per_grid": total_realized_pnl / total_grids
                        if total_grids > 0
                        else 0,
                        "capital_efficiency": "Maximized through unified allocation",
                    },
                    "system_metrics": {
                        "grids_started_total": self.system_metrics[
                            "total_grids_started"
                        ],
                        "grids_stopped_total": self.system_metrics[
                            "total_grids_stopped"
                        ],
                        "force_commands_processed": self.system_metrics[
                            "total_force_commands"
                        ],
                        "total_optimization_events": total_optimization_events,
                        "system_uptime_hours": uptime_hours,
                    },
                    "advanced_features_utilization": {
                        "compound_management": "100% - Full capital allocation per grid",
                        "volatility_management": "100% - Unified grid-wide adjustments",
                        "market_timing": "100% - Single optimization path",
                        "auto_reset": "100% - Simplified reset logic",
                        "precision_handling": "100% - Unified order execution",
                        "kelly_criterion": "100% - Optimal position sizing",
                    },
                    "architecture_benefits": {
                        "eliminated_complexity": "No dual-grid coordination overhead",
                        "capital_efficiency": "100% allocation vs previous 35/65 split",
                        "computational_efficiency": "Single optimization path per asset",
                        "management_simplification": "One grid type instead of two",
                        "monitoring_clarity": "Single performance stream per asset",
                    },
                },
                "client_breakdown": client_performances,
            }

        except Exception as e:
            self.logger.error(f"❌ System performance report error: {e}")
            return {"error": str(e)}

    async def start_monitoring(self):
        """Start continuous monitoring of all single advanced grids"""
        if self.monitoring_active:
            self.logger.warning("⚠️ Monitoring already active")
            return

        self.monitoring_active = True
        self.logger.info("🔍 Starting Single Advanced Grid monitoring system")

        try:
            while self.monitoring_active:
                await self._monitor_all_grids()
                await self._perform_health_check()
                await asyncio.sleep(30)  # Check every 30 seconds

        except Exception as e:
            self.logger.error(f"❌ Monitoring system error: {e}")
        finally:
            self.monitoring_active = False
            self.logger.info("🔍 Monitoring system stopped")

    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
        self.logger.info("🛑 Stopping monitoring system")

    async def _monitor_all_grids(self):
        """Monitor all active grids across all clients"""
        try:
            for client_id, manager in self.advanced_managers.items():
                try:
                    # Use the unified monitoring from SingleAdvancedGridManager
                    await manager.monitor_and_update_grids()

                except Exception as e:
                    self.logger.error(
                        f"❌ Grid monitoring error for client {client_id}: {e}"
                    )

        except Exception as e:
            self.logger.error(f"❌ System monitoring error: {e}")

    async def _perform_health_check(self):
        """Perform system health check"""
        try:
            current_time = time.time()

            # Only perform health check every 5 minutes
            if current_time - self.last_health_check < 300:
                return

            self.last_health_check = current_time

            # Check system health
            total_managers = len(self.advanced_managers)
            healthy_managers = 0

            for client_id, manager in self.advanced_managers.items():
                try:
                    # Check if manager is responsive
                    all_grids = manager.get_all_active_grids()
                    if isinstance(all_grids, dict):
                        healthy_managers += 1
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Health check failed for client {client_id}: {e}"
                    )

            health_percentage = (
                (healthy_managers / total_managers * 100) if total_managers > 0 else 100
            )

            self.logger.info(
                f"💚 System Health Check: {healthy_managers}/{total_managers} managers healthy ({health_percentage:.1f}%)"
            )

            # Log system metrics
            uptime_hours = (
                current_time - self.system_metrics["system_uptime_start"]
            ) / 3600
            self.logger.info(
                f"📊 System Metrics: {self.system_metrics['total_grids_started']} grids started, "
                f"{uptime_hours:.1f}h uptime, {self.system_metrics['total_force_commands']} commands processed"
            )

        except Exception as e:
            self.logger.error(f"❌ Health check error: {e}")

    async def _send_grid_start_notification(self, client_id: int, result: Dict):
        """Send notification when grid is started"""
        try:
            notifier = TelegramNotifier()
            if not notifier.enabled:
                return

            symbol = result.get("symbol", "Unknown")
            capital = result.get("total_capital", 0)
            strategy = result.get("strategy", "Single Advanced Grid")
            orders_placed = result.get("grid_details", {}).get("orders_placed", 0)

            # Simple message format to avoid parsing issues
            message = f"""🚀 Single Advanced Grid Started

👤 Client: {client_id}
📊 Symbol: {symbol}
💰 Capital: ${capital:,.2f}

🎯 Strategy: {strategy}
📈 Orders Placed: {orders_placed}
⚡ Efficiency: 100% capital allocation
🔧 Features: ALL advanced features unified

🎉 Architecture: Single optimized grid
💎 Benefits: Maximum feature utilization

⏰ {time.strftime("%H:%M:%S")}"""

            await notifier.send_message(message)

        except Exception as e:
            self.logger.error(f"❌ Grid start notification error: {e}")

    async def _send_grid_stop_notification(self, client_id: int, result: Dict):
        """Send notification when grid is stopped"""
        try:
            notifier = TelegramNotifier()
            if not notifier.enabled:
                return

            symbol = result.get("symbol", "Unknown")
            cancelled_orders = result.get("cancelled_orders", 0)
            performance_grade = result.get("final_performance_grade", "N/A")

            # Simple message format to avoid parsing issues
            message = f"""🛑 Single Advanced Grid Stopped

👤 Client: {client_id}
📊 Symbol: {symbol}
🔄 Orders Cancelled: {cancelled_orders}
🏆 Performance Grade: {performance_grade}

📊 System: Single Advanced Grid
✅ Status: Successfully stopped

⏰ {time.strftime("%H:%M:%S")}"""

            await notifier.send_message(message)

        except Exception as e:
            self.logger.error(f"❌ Grid stop notification error: {e}")

    def get_system_metrics(self) -> Dict:
        """Get current system metrics"""
        current_time = time.time()
        uptime_hours = (
            current_time - self.system_metrics["system_uptime_start"]
        ) / 3600

        return {
            "system_metrics": {
                **self.system_metrics,
                "current_uptime_hours": uptime_hours,
                "active_managers": len(self.advanced_managers),
                "monitoring_active": self.monitoring_active,
                "last_health_check": self.last_health_check,
            },
            "architecture_info": {
                "system_type": "Single Advanced Grid",
                "capital_efficiency": "100%",
                "management_complexity": "Simplified",
                "feature_utilization": "Maximized",
            },
        }

    async def cleanup_inactive_managers(self):
        """Clean up managers for clients with no active grids"""
        try:
            inactive_clients = []

            for client_id, manager in self.advanced_managers.items():
                try:
                    all_grids = manager.get_all_active_grids()
                    if not all_grids.get("grids"):
                        inactive_clients.append(client_id)
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Cleanup check failed for client {client_id}: {e}"
                    )
                    inactive_clients.append(client_id)

            # Remove inactive managers
            for client_id in inactive_clients:
                try:
                    del self.advanced_managers[client_id]
                    if client_id in self.binance_clients:
                        del self.binance_clients[client_id]

                    self.logger.info(
                        f"🧹 Cleaned up inactive manager for client {client_id}"
                    )

                except Exception as e:
                    self.logger.error(f"❌ Cleanup error for client {client_id}: {e}")

            if inactive_clients:
                self.logger.info(
                    f"🧹 Cleanup completed: {len(inactive_clients)} inactive managers removed"
                )

        except Exception as e:
            self.logger.error(f"❌ Manager cleanup error: {e}")

    # COMPATIBILITY METHODS - Bridge between old and new system
    async def start_client_grid(
        self, client_id: int, symbol: str, capital: float
    ) -> Dict:
        """
        Compatibility method for existing system calls
        Maps to the new force_start_grid method
        """
        try:
            self.logger.info(
                f"🔄 Compatibility call: start_client_grid({client_id}, {symbol}, ${capital})"
            )

            # Map symbol to force command format
            symbol_map = {"ETHUSDT": "ETH", "SOLUSDT": "SOL", "ADAUSDT": "ADA"}

            symbol_short = symbol_map.get(symbol, symbol.replace("USDT", ""))
            force_command = f"FORCE {symbol_short} {capital}"

            # Use the new force_start_grid method
            result = await self.force_start_grid(client_id, force_command)

            # Convert result to expected format for compatibility
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Grid started for {symbol} with ${capital}",
                    "symbol": symbol,
                    "capital": capital,
                    "strategy": "Single Advanced Grid",
                    "grid_details": result.get("grid_details", {}),
                    "orders_placed": result.get("grid_details", {}).get(
                        "orders_placed", 0
                    ),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "symbol": symbol,
                    "capital": capital,
                }

        except Exception as e:
            self.logger.error(f"❌ Compatibility start_client_grid error: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "capital": capital,
            }

    async def update_all_grids(self) -> Dict:
        """
        Compatibility method for grid monitoring
        Maps to the new monitoring system
        """
        try:
            self.logger.info("🔄 Compatibility call: update_all_grids()")

            # Start monitoring if not already active
            if not self.monitoring_active:
                asyncio.create_task(self.start_monitoring())

            # Get current status of all grids
            all_grids = self.get_all_active_grids()

            # Update each active grid
            updated_grids = 0
            for client_id, manager in self.advanced_managers.items():
                try:
                    await manager.monitor_and_update_grids()
                    updated_grids += 1
                except Exception as e:
                    self.logger.error(f"❌ Update error for client {client_id}: {e}")

            await self.check_and_send_daily_summaries()

            return {
                "success": True,
                "updated_grids": updated_grids,
                "total_clients": len(self.advanced_managers),
                "monitoring_active": self.monitoring_active,
                "system_summary": all_grids.get("system_summary", {}),
                "message": f"Updated {updated_grids} grids across {len(self.advanced_managers)} clients",
            }

        except Exception as e:
            self.logger.error(f"❌ Compatibility update_all_grids error: {e}")
            return {"success": False, "error": str(e), "updated_grids": 0}

    async def get_client_grid_status(self, client_id: int, symbol: str = None) -> Dict:
        """
        Compatibility method for getting grid status
        Maps to new single grid status methods
        """
        try:
            if client_id not in self.advanced_managers:
                return {
                    "success": False,
                    "error": "No active manager for client",
                    "client_id": client_id,
                }

            manager = self.advanced_managers[client_id]

            if symbol:
                # Get specific symbol status
                status = manager.get_single_grid_status(symbol)
                return {
                    "success": status.get("active", False),
                    "client_id": client_id,
                    "symbol": symbol,
                    "grid_status": status,
                    "strategy": "Single Advanced Grid",
                }
            else:
                # Get all grids for client
                all_grids = manager.get_all_active_grids()
                return {
                    "success": True,
                    "client_id": client_id,
                    "total_grids": all_grids.get("total_active_grids", 0),
                    "grids": all_grids.get("grids", {}),
                    "strategy": "Single Advanced Grid",
                    "system_efficiency": all_grids.get(
                        "system_efficiency", "Maximized"
                    ),
                }

        except Exception as e:
            self.logger.error(f"❌ Compatibility get_client_grid_status error: {e}")
            return {"success": False, "error": str(e), "client_id": client_id}

    async def stop_client_grid(self, client_id: int, symbol: str) -> Dict:
        """
        Compatibility method for stopping grids
        Maps to new stop_grid method
        """
        try:
            return await self.stop_grid(client_id, symbol)
        except Exception as e:
            self.logger.error(f"❌ Compatibility stop_client_grid error: {e}")
            return {"success": False, "error": str(e)}

    def get_grid_performance(self, client_id: int, symbol: str = None) -> Dict:
        """
        Compatibility method for performance data
        """
        try:
            if client_id not in self.advanced_managers:
                return {
                    "success": False,
                    "error": "No active manager for client",
                    "client_id": client_id,
                }

            manager = self.advanced_managers[client_id]

            if symbol:
                # Get specific symbol performance
                status = manager.get_single_grid_status(symbol)
                return {
                    "success": status.get("active", False),
                    "client_id": client_id,
                    "symbol": symbol,
                    "performance": status.get("performance_metrics", {}),
                    "advanced_features": status.get("advanced_features_status", {}),
                    "strategy": "Single Advanced Grid",
                }
            else:
                # Get overall client performance
                all_grids = manager.get_all_active_grids()
                return {
                    "success": True,
                    "client_id": client_id,
                    "overall_performance": all_grids.get("global_metrics", {}),
                    "total_grids": all_grids.get("total_active_grids", 0),
                    "strategy": "Single Advanced Grid",
                }

        except Exception as e:
            self.logger.error(f"❌ Compatibility get_grid_performance error: {e}")
            return {"success": False, "error": str(e)}

    async def test_client_api(self, client_id: int) -> Dict:
        """
        Compatibility method for API testing
        Uses existing pattern from your system
        """
        try:
            client = self.client_repo.get_client(client_id)
            if (
                not client
                or not client.binance_api_key
                or not client.binance_secret_key
            ):
                return {"success": False, "error": "API keys not configured"}

            # Decrypt API keys using your existing method
            api_key, secret_key = self.client_repo.get_decrypted_api_keys(client)
            if not api_key or not secret_key:
                return {"success": False, "error": "Failed to decrypt API keys"}

            # Create Binance client using your existing pattern
            binance_client = Client(api_key, secret_key, testnet=False)

            # Test connection with recv_window handling
            try:
                account = binance_client.get_account(recvWindow=60000)
            except TypeError:
                account = binance_client.get_account()

            # Store client for later use
            self.binance_clients[client_id] = binance_client

            return {
                "success": True,
                "account_type": account.get("accountType"),
                "can_trade": account.get("canTrade", False),
                "permissions": account.get("permissions", []),
                "balances_count": len(account.get("balances", [])),
            }

        except Exception as e:
            self.logger.error(f"❌ API test failed for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def check_and_send_daily_summaries(self):
        """Check if we should send daily summaries to clients with FIFO profit data"""
        try:
            now = datetime.now()

            # Send daily summary once per day at 9 AM
            should_send = False
            if self.last_daily_summary is None:
                should_send = True
            elif now.hour == 9 and now.minute < 5:  # 9:00-9:05 AM
                if self.last_daily_summary.date() < now.date():
                    should_send = True

            if should_send:
                # Get all active clients
                with sqlite3.connect(Config.DATABASE_PATH) as conn:
                    cursor = conn.execute(
                        "SELECT telegram_id FROM clients WHERE status = 'active'"
                    )
                    active_clients = [row[0] for row in cursor.fetchall()]

                # Send summary to each client
                summary_count = 0
                for client_id in active_clients:
                    try:
                        # Ensure client has monitoring set up
                        await self.notification_manager.add_client_monitor(client_id)

                        # Send the daily summary
                        await self.notification_manager.send_profit_status(client_id)
                        summary_count += 1

                    except Exception as e:
                        self.logger.error(
                            f"Error sending summary to client {client_id}: {e}"
                        )

                self.last_daily_summary = now
                self.logger.info(
                    f"✅ FIFO daily summaries sent to {summary_count}/{len(active_clients)} clients"
                )

        except Exception as e:
            self.logger.error(f"Error in FIFO daily summary check: {e}")

    # Add this method to your class:
    async def on_trade_completed(
        self, client_id: int, symbol: str, side: str, quantity: float, price: float
    ):
        """Called when a trade is executed - notify FIFO monitor"""
        try:
            # Ensure client monitoring is set up
            await self.notification_manager.add_client_monitor(client_id)

            # Notify the trade execution
            await self.notification_manager.on_trade_executed(
                client_id, symbol, side, quantity, price
            )

            self.logger.debug(
                f"📊 Trade notification sent: {client_id} {symbol} {side} {quantity}@{price}"
            )

        except Exception as e:
            self.logger.error(f"Error notifying trade completion: {e}")
