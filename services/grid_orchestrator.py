# services/grid_orchestrator.py

import asyncio
import logging
import time
from typing import Dict, Optional

from binance.client import Client

from models.client import GridStatus
from repositories.client_repository import ClientRepository
from services.fifo_service import FIFOService
from services.grid_manager import GridManager
from utils.crypto import CryptoUtils


class GridOrchestrator:
    """Singleton GridOrchestrator for managing all grid trading operations"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern - always return the same instance"""
        if cls._instance is None:
            cls._instance = super(GridOrchestrator, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize only once, even if called multiple times"""
        if GridOrchestrator._initialized:
            return

        # Core setup
        self.logger = logging.getLogger(__name__)
        self.creation_id = id(self)

        self.logger.info(
            f"🎯 GridOrchestrator singleton created - ID: {self.creation_id}"
        )

        # Initialize services
        self.client_repo = ClientRepository()
        self.crypto_utils = CryptoUtils()

        # Storage for managers and clients
        self.advanced_managers: Dict[int, GridManager] = {}
        self.binance_clients: Dict[int, Client] = {}

        # Services
        try:
            self.fifo_service = FIFOService()
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize FIFOService: {e}")
            self.fifo_service = None

        # State tracking
        self.monitoring_active = False
        self.last_health_check = 0

        # Metrics
        self.system_metrics = {
            "total_grids_started": 0,
            "total_grids_stopped": 0,
            "total_force_commands": 0,
            "system_uptime_start": time.time(),
        }

        self.logger.info(
            "🚀 GridOrchestrator initialized for Single Advanced Grid System"
        )
        GridOrchestrator._initialized = True

    def _log_access(self, method_name: str):
        """Log method access for debugging"""
        self.logger.debug(f"🔍 GridOrchestrator {self.creation_id} - {method_name}")

    def ensure_initialized(self):
        """Ensure proper initialization"""
        if not hasattr(self, "advanced_managers"):
            raise RuntimeError("GridOrchestrator not properly initialized!")

    async def get_client_binance_client(self, client_id: int) -> Optional[Client]:
        """Get or create Binance client for specific client"""
        if client_id in self.binance_clients:
            return self.binance_clients[client_id]

        try:
            client = self.client_repo.get_client(client_id)
            if (
                not client
                or not client.binance_api_key
                or not client.binance_secret_key
            ):
                raise ValueError(f"Client {client_id} missing API credentials")

            # Decrypt API keys
            api_key, secret_key = self.client_repo.get_decrypted_api_keys(client)
            if not api_key or not secret_key:
                raise ValueError(f"Failed to decrypt API keys for client {client_id}")

            # Create and test Binance client
            binance_client = Client(api_key, secret_key, testnet=False)

            # Test connection
            account = binance_client.get_account(recvWindow=60000)

            # Cache client
            self.binance_clients[client_id] = binance_client

            self.logger.info(f"✅ Created Binance client for client {client_id}")
            return binance_client

        except Exception as e:
            self.logger.error(
                f"❌ Failed to create Binance client for {client_id}: {e}"
            )
            raise

    async def create_advanced_manager(self, client_id: int) -> bool:
        """Create Single Advanced Grid Manager for client"""
        try:
            if client_id in self.advanced_managers:
                self.logger.info(f"✅ Manager already exists for client {client_id}")
                return True

            # Get Binance client
            binance_client = await self.get_client_binance_client(client_id)
            if not binance_client:
                return False

            # 🔧 FIXED: Pass shared FIFO service to GridManager
            manager = GridManager(
                binance_client=binance_client,
                client_id=client_id,
                fifo_service=self.fifo_service,  # ✅ Share the single instance
            )

            # Store manager
            self.advanced_managers[client_id] = manager

            self.logger.info(f"✅ Created GridManager for client {client_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Manager creation error for client {client_id}: {e}")
            return False

    async def force_start_grid(self, client_id: int, command: str) -> Dict:
        """
        Handle FORCE commands for single advanced grids
        Examples: FORCE ETH 880, FORCE SOL 660, FORCE ADA 660
        """
        try:
            self.logger.info(
                f"🚀 Processing FORCE command for client {client_id}: {command}"
            )

            # Ensure manager exists
            if not await self.create_advanced_manager(client_id):
                return {"success": False, "error": "Failed to create advanced manager"}

            # Execute command
            manager = self.advanced_managers[client_id]
            result = await manager.handle_force_command(command)

            if result["success"]:
                # Update client status
                client = self.client_repo.get_client(client_id)
                if client:
                    client.grid_status = GridStatus.ACTIVE
                    self.client_repo.update_client(client)

                # Update metrics
                self.system_metrics["total_grids_started"] += 1
                self.system_metrics["total_force_commands"] += 1

                self.logger.info(f"🎉 FORCE command success for client {client_id}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Force start error for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def stop_grid(self, client_id: int, symbol: str) -> Dict:
        """Stop single advanced grid for specific symbol"""
        try:
            if client_id not in self.advanced_managers:
                return {"success": False, "error": "No active manager for client"}

            manager = self.advanced_managers[client_id]
            result = await manager.stop_single_advanced_grid(symbol)

            if result["success"]:
                self.system_metrics["total_grids_stopped"] += 1

                # Check if client has remaining grids
                all_grids = manager.get_all_active_grids()
                if not all_grids.get("grids"):
                    client = self.client_repo.get_client(client_id)
                    if client:
                        client.grid_status = GridStatus.INACTIVE
                        self.client_repo.update_client(client)

                self.logger.info(
                    f"✅ Grid stopped for client {client_id}, symbol {symbol}"
                )

            return result

        except Exception as e:
            self.logger.error(
                f"❌ Grid stop error for client {client_id}, symbol {symbol}: {e}"
            )
            return {"success": False, "error": str(e)}

    async def stop_all_client_grids(self, client_id: int) -> Dict:
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

            self.system_metrics["total_grids_stopped"] += total_stopped

            return {
                "success": total_stopped > 0,
                "total_stopped": total_stopped,
                "total_attempted": len(all_grids["grids"]),
                "details": results,
            }

        except Exception as e:
            self.logger.error(f"❌ Stop all grids error for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_all_active_grids(self) -> Dict:
        """Get status of all active grids across all clients"""
        self._log_access("get_all_active_grids")
        self.ensure_initialized()

        try:
            all_grids = {}
            total_active_grids = 0
            total_capital = 0.0

            for client_id, manager in self.advanced_managers.items():
                try:
                    client_grids = manager.get_all_active_grids()

                    if client_grids.get("grids"):
                        all_grids[client_id] = {
                            "client_id": client_id,
                            "grids": client_grids["grids"],
                            "metrics": client_grids.get("global_metrics", {}),
                        }

                        total_active_grids += len(client_grids["grids"])

                        # Calculate total capital
                        for grid_data in client_grids["grids"].values():
                            grid_details = grid_data.get("grid_details", {})
                            if "total_capital" in grid_details:
                                total_capital += grid_details["total_capital"]

                except Exception as e:
                    self.logger.error(
                        f"❌ Failed to get grids for client {client_id}: {e}"
                    )

            return {
                "system_summary": {
                    "total_clients": len(self.advanced_managers),
                    "total_active_grids": total_active_grids,
                    "total_capital_deployed": total_capital,
                    "architecture": "Single Advanced Grid System",
                },
                "client_grids": all_grids,
                "system_metrics": self.system_metrics,
            }

        except Exception as e:
            self.logger.error(f"❌ get_all_active_grids error: {e}")
            return {
                "system_summary": {
                    "total_clients": 0,
                    "total_active_grids": 0,
                    "total_capital_deployed": 0.0,
                    "architecture": "Single Advanced Grid System",
                },
                "client_grids": {},
                "error": str(e),
            }

    async def update_all_grids(self) -> Dict:
        """Update all active grids across all clients"""
        self._log_access("update_all_grids")

        try:
            if not self.advanced_managers:
                return {
                    "success": False,
                    "error": "No active managers",
                    "updated_grids": 0,
                }

            # Start monitoring if not active
            if not self.monitoring_active:
                asyncio.create_task(self.start_monitoring())

            # Update each client's grids
            updated_grids = 0
            for client_id, manager in self.advanced_managers.items():
                try:
                    await manager.monitor_and_update_grids()
                    updated_grids += 1
                except Exception as e:
                    self.logger.error(f"❌ Update error for client {client_id}: {e}")

            return {
                "success": True,
                "updated_grids": updated_grids,
                "total_clients": len(self.advanced_managers),
                "monitoring_active": self.monitoring_active,
            }

        except Exception as e:
            self.logger.error(f"❌ update_all_grids error: {e}")
            return {"success": False, "error": str(e), "updated_grids": 0}

    async def get_client_grid_status(self, client_id: int) -> Dict:
        """Get grid status for specific client"""
        self._log_access("get_client_grid_status")
        self.ensure_initialized()

        try:
            if client_id not in self.advanced_managers:
                return {
                    "client_id": client_id,
                    "active_grids": {},
                    "status": "No active manager",
                }

            manager = self.advanced_managers[client_id]
            client_grids = manager.get_all_active_grids()

            return {
                "client_id": client_id,
                "active_grids": client_grids.get("grids", {}),
                "status": "active" if client_grids.get("grids") else "inactive",
                "metrics": client_grids.get("global_metrics", {}),
            }

        except Exception as e:
            self.logger.error(f"❌ get_client_grid_status error for {client_id}: {e}")
            return {
                "client_id": client_id,
                "active_grids": {},
                "status": "error",
                "error": str(e),
            }

    async def start_monitoring(self):
        """Start continuous monitoring of all grids"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.logger.info("🔍 Starting grid monitoring system")

        try:
            while self.monitoring_active:
                await self._monitor_all_grids()
                await self._perform_health_check()
                await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            self.logger.error(f"❌ Monitoring system error: {e}")
        finally:
            self.monitoring_active = False

    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
        self.logger.info("🛑 Monitoring system stopped")

    async def _monitor_all_grids(self):
        """Monitor all active grids"""
        try:
            for client_id, manager in self.advanced_managers.items():
                try:
                    await manager.monitor_and_update_grids()
                except Exception as e:
                    self.logger.error(
                        f"❌ Monitoring error for client {client_id}: {e}"
                    )
        except Exception as e:
            self.logger.error(f"❌ System monitoring error: {e}")

    async def _perform_health_check(self):
        """Perform periodic health check"""
        try:
            current_time = time.time()

            # Only check every 5 minutes
            if current_time - self.last_health_check < 300:
                return

            self.last_health_check = current_time

            total_managers = len(self.advanced_managers)
            healthy_managers = 0

            for client_id, manager in self.advanced_managers.items():
                try:
                    all_grids = manager.get_all_active_grids()
                    if isinstance(all_grids, dict):
                        healthy_managers += 1
                except Exception:
                    pass

            health_percentage = (
                (healthy_managers / total_managers * 100) if total_managers > 0 else 100
            )

            self.logger.info(
                f"💚 System Health: {healthy_managers}/{total_managers} managers ({health_percentage:.1f}%)"
            )

        except Exception as e:
            self.logger.error(f"❌ Health check error: {e}")

    # Compatibility methods for existing system
    async def start_client_grid(
        self, client_id: int, symbol: str, capital: float
    ) -> Dict:
        """Compatibility method - maps to force_start_grid"""
        symbol_map = {"ETHUSDT": "ETH", "SOLUSDT": "SOL", "ADAUSDT": "ADA"}
        symbol_short = symbol_map.get(symbol, symbol.replace("USDT", ""))
        force_command = f"FORCE {symbol_short} {capital}"

        result = await self.force_start_grid(client_id, force_command)

        if result["success"]:
            return {
                "success": True,
                "symbol": symbol,
                "capital": capital,
                "orders_placed": result.get("grid_details", {}).get("orders_placed", 0),
            }
        else:
            return {"success": False, "error": result.get("error"), "symbol": symbol}

    async def stop_client_grid(self, client_id: int, symbol: str) -> Dict:
        """Compatibility method"""
        return await self.stop_grid(client_id, symbol)

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
            },
            "architecture": {
                "system_type": "Single Advanced Grid",
                "capital_efficiency": "100%",
                "feature_utilization": "Maximized",
            },
        }

    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        return cls()

    @classmethod
    def reset_instance(cls):
        """Reset singleton for testing"""
        cls._instance = None
        cls._initialized = False

    def __str__(self):
        """String representation for debugging"""
        return f"GridOrchestrator(ID={self.creation_id}, managers={len(self.advanced_managers)})"
