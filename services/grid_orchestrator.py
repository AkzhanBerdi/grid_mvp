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
from services.enhanced_fifo_service import EnhancedFIFOService
from services.single_advanced_grid_manager import SingleAdvancedGridManager
from services.telegram_notifier import TelegramNotifier
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
    """Singleton GridOrchestrator to ensure only one instance exists"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern - always return the same instance"""
        if cls._instance is None:
            cls._instance = super(GridOrchestrator, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize only once, even if called multiple times"""
        # Prevent re-initialization
        if GridOrchestrator._initialized:
            self.logger.info(
                f"🔄 GridOrchestrator already initialized - returning existing instance ID: {id(self)}"
            )
            return

        import time
        import traceback
        from typing import Dict

        from binance.client import Client

        # Import required services
        from services.single_advanced_grid_manager import SingleAdvancedGridManager

        # Initialize logging first
        self.logger = logging.getLogger(__name__)

        # Track creation details
        self.creation_time = time.time()
        self.creation_id = id(self)

        # Log the instance creation with detailed info
        instance_id = id(self)
        self.logger.info(f"🎯 GridOrchestrator singleton created - ID: {instance_id}")
        self.logger.error(
            f"🎯 SINGLETON GridOrchestrator created! ID: {self.creation_id}"
        )
        print(f"🎯 SINGLETON GridOrchestrator created! ID: {self.creation_id}")

        # Initialize core services
        self.client_repo = ClientRepository()
        self.crypto_utils = CryptoUtils()

        # Create debug-enabled dictionary for managers
        class DebugDict(dict):
            def __init__(self, logger):
                super().__init__()
                self.logger = logger

            def __delitem__(self, key):
                self.logger.error(f"🚨 CRITICAL: Manager {key} being DELETED!")
                print(f"🚨 CRITICAL: Manager {key} being DELETED!")
                self.logger.error("DELETION Stack trace:")
                for line in traceback.format_stack():
                    self.logger.error(line.strip())
                super().__delitem__(key)

            def clear(self):
                self.logger.error("🚨 CRITICAL: ALL MANAGERS BEING CLEARED!")
                print("🚨 CRITICAL: ALL MANAGERS BEING CLEARED!")
                self.logger.error("CLEAR Stack trace:")
                for line in traceback.format_stack():
                    self.logger.error(line.strip())
                super().clear()

        # Initialize managers dictionary with debug capabilities
        self.advanced_managers: Dict[int, SingleAdvancedGridManager] = DebugDict(
            self.logger
        )

        # Initialize Binance clients cache
        self.binance_clients: Dict[int, Client] = {}

        # Initialize services
        try:
            self.notification_manager = EnhancedFIFOService()
            self.logger.info("✅ FIFOMonitoringService initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize FIFOMonitoringService: {e}")
            self.notification_manager = None

        try:
            self.fifo_service = EnhancedFIFOService()
            self.logger.info("✅ EnhancedFIFOService initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize EnhancedFIFOService: {e}")
            self.fifo_service = None

        # Initialize state variables
        self.last_daily_summary = None
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

        # Log architecture info
        self.logger.info(
            "🚀 GridOrchestrator initialized for Single Advanced Grid System"
        )
        self.logger.info("   🎯 Architecture: Single Advanced Grid per Asset")
        self.logger.info("   💎 Capital Efficiency: 100% (no dual-grid splits)")
        self.logger.info("   🔧 Management: Simplified unified system")

        # Final confirmation
        self.logger.error(
            f"✅ GridOrchestrator {self.creation_id} initialization complete"
        )
        print(f"✅ GridOrchestrator {self.creation_id} initialization complete")

        # Mark as initialized
        GridOrchestrator._initialized = True

    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        return cls()

    @classmethod
    def reset_instance(cls):
        """Reset singleton (for testing purposes)"""
        cls._instance = None
        cls._initialized = False

    # Add debug logging to track instance access
    def _log_instance_access(self, method_name):
        instance_id = id(self)
        self.logger.error(f"🔍 GridOrchestrator {instance_id} - {method_name} accessed")

    def ensure_initialized(self):
        """Ensure the orchestrator is properly initialized"""
        if not hasattr(self, "advanced_managers"):
            raise RuntimeError("GridOrchestrator not properly initialized!")

        if not hasattr(self, "client_repo"):
            raise RuntimeError("GridOrchestrator missing ClientRepository!")

    # Add this method to get client's Binance client
    def get_client_binance_client(self, client_id: int) -> Client:
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

            # Decrypt credentials
            decrypted_api_key = self.crypto_utils.decrypt(client.binance_api_key)
            decrypted_secret = self.crypto_utils.decrypt(client.binance_secret_key)

            # Create Binance client
            binance_client = Client(decrypted_api_key, decrypted_secret)
            self.binance_clients[client_id] = binance_client

            self.logger.info(f"✅ Created Binance client for client {client_id}")
            return binance_client

        except Exception as e:
            self.logger.error(
                f"❌ Failed to create Binance client for {client_id}: {e}"
            )
            raise

    def __getattribute__(self, name):
        if name == "advanced_managers":
            creation_id = super().__getattribute__("creation_id")
            logger = super().__getattribute__("logger")
            logger.error(
                f"🔍 GridOrchestrator {creation_id} - advanced_managers accessed"
            )
            print(f"🔍 GridOrchestrator {creation_id} - advanced_managers accessed")
        return super().__getattribute__(name)

    def __str__(self):
        """String representation for debugging"""
        return f"GridOrchestrator(ID={id(self)}, managers={len(self.advanced_managers)}, initialized={self._initialized})"

    def __setitem__(self, key, value):
        """Debug wrapper to track manager additions"""
        self.logger.error(f"🔥 DEBUG: Manager {key} being ADDED")
        print(f"🔥 DEBUG: Manager {key} being ADDED")
        import traceback

        self.logger.error(f"Stack trace: {traceback.format_stack()[-3:-1]}")
        super().__setitem__(key, value)

    def __delitem__(self, key):
        """Debug wrapper to track manager deletions"""
        self.logger.error(f"🚨 CRITICAL: Manager {key} being DELETED!")
        print(f"🚨 CRITICAL: Manager {key} being DELETED!")
        import traceback

        self.logger.error(f"DELETION Stack trace: {traceback.format_stack()}")
        super().__delitem__(key)

    async def create_advanced_manager(self, client_id: int) -> bool:
        """
        Create Single Advanced Grid Manager for client
        FIXED: Use correct constructor parameters
        """
        try:
            if client_id in self.advanced_managers:
                self.logger.info(
                    f"✅ Advanced manager already exists for client {client_id}"
                )
                return True

            # Get or create Binance client
            binance_client = await self._get_or_create_binance_client(client_id)
            if not binance_client:
                self.logger.error(
                    f"❌ DEBUG: Failed to create Binance client for {client_id}"
                )
                return False

            self.logger.error(f"✅ DEBUG: Binance client ready for client {client_id}")
            print(f"✅ DEBUG: Binance client ready for client {client_id}")

            # 🔥 FIX: Create manager with correct parameters (no fifo_service)
            manager = SingleAdvancedGridManager(
                binance_client=binance_client, client_id=client_id
            )

            # 🔥 CRITICAL: Actually add to the managers dictionary
            self.advanced_managers[client_id] = manager

            self.logger.error(
                f"✅ DEBUG: Manager created and added to dictionary for client {client_id}"
            )
            print(
                f"✅ DEBUG: Manager created and added to dictionary for client {client_id}"
            )

            self.logger.error(
                f"✅ DEBUG: Total managers now: {len(self.advanced_managers)}"
            )
            print(f"✅ DEBUG: Total managers now: {len(self.advanced_managers)}")

            self.logger.info(
                f"✅ SingleAdvancedGridManager created for client {client_id}"
            )
            self.logger.info("   🎯 Features: ALL advanced features unified")
            self.logger.info("   💰 Capital: 100% allocation efficiency")
            self.logger.info("   🔧 Management: Simplified single-grid system")

            return True

        except Exception as e:
            self.logger.error(
                f"❌ Advanced manager creation error for client {client_id}: {e}"
            )
            import traceback

            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    async def _get_or_create_binance_client(self, client_id: int) -> Optional[Client]:
        """Get existing or create new Binance client for client - FIXED"""
        try:
            # Check if we already have a client
            if client_id in self.binance_clients:
                self.logger.error(
                    f"✅ DEBUG: Using existing Binance client for {client_id}"
                )
                print(f"✅ DEBUG: Using existing Binance client for {client_id}")
                return self.binance_clients[client_id]

            # Get client from repository
            client = self.client_repo.get_client(client_id)
            if not client:
                self.logger.error(
                    f"❌ DEBUG: Client {client_id} not found in repository"
                )
                print(f"❌ DEBUG: Client {client_id} not found in repository")
                return None

            self.logger.error(f"✅ DEBUG: Client {client_id} found in repository")
            print(f"✅ DEBUG: Client {client_id} found in repository")

            # Check if client has API keys
            if not client.binance_api_key or not client.binance_secret_key:
                self.logger.error(f"❌ DEBUG: Client {client_id} missing API keys")
                print(f"❌ DEBUG: Client {client_id} missing API keys")
                return None

            self.logger.error(f"✅ DEBUG: Client {client_id} has encrypted API keys")
            print(f"✅ DEBUG: Client {client_id} has encrypted API keys")

            # 🔥 FIX: Decrypt the API keys using the repository method
            try:
                api_key, secret_key = self.client_repo.get_decrypted_api_keys(client)

                if not api_key or not secret_key:
                    self.logger.error(
                        f"❌ DEBUG: Failed to decrypt API keys for client {client_id}"
                    )
                    print(
                        f"❌ DEBUG: Failed to decrypt API keys for client {client_id}"
                    )
                    return None

                self.logger.error(
                    f"✅ DEBUG: Successfully decrypted API keys for client {client_id}"
                )
                print(
                    f"✅ DEBUG: Successfully decrypted API keys for client {client_id}"
                )

            except Exception as decrypt_error:
                self.logger.error(
                    f"❌ DEBUG: API key decryption error for client {client_id}: {decrypt_error}"
                )
                print(
                    f"❌ DEBUG: API key decryption error for client {client_id}: {decrypt_error}"
                )
                return None

            # 🔥 FIX: Create Binance client with decrypted keys
            try:
                from binance.client import Client as BinanceClient

                binance_client = BinanceClient(
                    api_key=api_key,
                    api_secret=secret_key,
                    testnet=False,  # Set to True if using testnet
                )

                self.logger.error(
                    f"✅ DEBUG: Binance client object created for client {client_id}"
                )
                print(f"✅ DEBUG: Binance client object created for client {client_id}")

            except Exception as client_error:
                self.logger.error(
                    f"❌ DEBUG: Binance client creation error for client {client_id}: {client_error}"
                )
                print(
                    f"❌ DEBUG: Binance client creation error for client {client_id}: {client_error}"
                )
                return None

            # Test the connection
            try:
                account = binance_client.get_account()
                self.logger.error(
                    f"✅ DEBUG: Binance connection test successful for client {client_id}"
                )
                print(
                    f"✅ DEBUG: Binance connection test successful for client {client_id}"
                )

                # Log account info
                self.logger.info(f"✅ Binance client created for client {client_id}")
                self.logger.info(
                    f"   📊 Account Type: {account.get('accountType', 'Unknown')}"
                )
                self.logger.info(f"   🔑 Can Trade: {account.get('canTrade', False)}")

            except Exception as test_error:
                self.logger.error(
                    f"❌ DEBUG: Binance connection test failed for client {client_id}: {test_error}"
                )
                print(
                    f"❌ DEBUG: Binance connection test failed for client {client_id}: {test_error}"
                )
                return None

            # Cache the client
            self.binance_clients[client_id] = binance_client

            self.logger.error(f"✅ DEBUG: Binance client cached for client {client_id}")
            print(f"✅ DEBUG: Binance client cached for client {client_id}")

            return binance_client

        except Exception as e:
            self.logger.error(
                f"❌ Binance client creation error for client {client_id}: {e}"
            )
            print(f"❌ Binance client creation error for client {client_id}: {e}")

            # Log full traceback for debugging
            import traceback

            self.logger.error(f"Full traceback: {traceback.format_exc()}")

            return None

    # ALSO ADD: Method to decrypt API secret for the existing crypto_utils usage
    def decrypt_api_secret(self, encrypted_secret: str) -> str:
        """Decrypt API secret - for backward compatibility"""
        return self.crypto_utils.decrypt(encrypted_secret)

    # DEBUGGING: Add this method to test API key decryption independently
    def debug_api_key_decryption(self, client_id: int):
        """Debug API key decryption for a specific client"""
        try:
            self.logger.error(
                f"🔍 DEBUG: Testing API key decryption for client {client_id}"
            )
            print(f"🔍 DEBUG: Testing API key decryption for client {client_id}")

            # Get client
            client = self.client_repo.get_client(client_id)
            if not client:
                self.logger.error(f"❌ DEBUG: Client {client_id} not found")
                print(f"❌ DEBUG: Client {client_id} not found")
                return False

            # Check encrypted keys
            if client.binance_api_key:
                self.logger.error(
                    f"✅ DEBUG: Found encrypted API key (length: {len(client.binance_api_key)})"
                )
                print(
                    f"✅ DEBUG: Found encrypted API key (length: {len(client.binance_api_key)})"
                )
            else:
                self.logger.error("❌ DEBUG: No API key found")
                print("❌ DEBUG: No API key found")
                return False

            if client.binance_secret_key:
                self.logger.error(
                    f"✅ DEBUG: Found encrypted secret key (length: {len(client.binance_secret_key)})"
                )
                print(
                    f"✅ DEBUG: Found encrypted secret key (length: {len(client.binance_secret_key)})"
                )
            else:
                self.logger.error("❌ DEBUG: No secret key found")
                print("❌ DEBUG: No secret key found")
                return False

            # Test decryption
            api_key, secret_key = self.client_repo.get_decrypted_api_keys(client)

            if api_key and secret_key:
                self.logger.error("✅ DEBUG: Decryption successful")
                self.logger.error(f"   API Key: {api_key[:10]}...{api_key[-10:]}")
                self.logger.error(
                    f"   Secret Key: {secret_key[:10]}...{secret_key[-10:]}"
                )
                print("✅ DEBUG: Decryption successful")
                return True
            else:
                self.logger.error("❌ DEBUG: Decryption failed")
                print("❌ DEBUG: Decryption failed")
                return False

        except Exception as e:
            self.logger.error(f"❌ DEBUG: API key decryption test error: {e}")
            print(f"❌ DEBUG: API key decryption test error: {e}")
            return False

    def debug_fifo_service_availability(self):
        """Debug method to check FIFO service availability"""
        try:
            self.logger.error("🔍 DEBUG: Checking FIFO service availability")
            print("🔍 DEBUG: Checking FIFO service availability")

            # Check if we have a FIFO service
            if hasattr(self, "fifo_service") and self.fifo_service:
                self.logger.error("✅ DEBUG: GridOrchestrator has FIFO service")
                print("✅ DEBUG: GridOrchestrator has FIFO service")
            else:
                self.logger.error("❌ DEBUG: GridOrchestrator missing FIFO service")
                print("❌ DEBUG: GridOrchestrator missing FIFO service")
                # Create it if missing
                from services.enhanced_fifo_service import EnhancedFIFOService

                self.fifo_service = EnhancedFIFOService()
                self.logger.error("✅ DEBUG: Created new FIFO service")
                print("✅ DEBUG: Created new FIFO service")

            # Check if EnhancedFIFOService can be imported
            try:
                from services.enhanced_fifo_service import EnhancedFIFOService

                test_fifo = EnhancedFIFOService()
                self.logger.error(
                    "✅ DEBUG: EnhancedFIFOService imports and creates successfully"
                )
                print("✅ DEBUG: EnhancedFIFOService imports and creates successfully")
            except Exception as fifo_error:
                self.logger.error(
                    f"❌ DEBUG: EnhancedFIFOService import/creation error: {fifo_error}"
                )
                print(
                    f"❌ DEBUG: EnhancedFIFOService import/creation error: {fifo_error}"
                )

        except Exception as e:
            self.logger.error(f"❌ DEBUG: FIFO service check error: {e}")
            print(f"❌ DEBUG: FIFO service check error: {e}")

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
                self.logger.error(
                    f"❌ DEBUG: Failed to create manager for client {client_id}"
                )
                print(f"❌ DEBUG: Failed to create manager for client {client_id}")
                return {"success": False, "error": "Failed to create advanced manager"}

            self.logger.error(
                f"✅ DEBUG: Manager created/exists for client {client_id}"
            )
            print(f"✅ DEBUG: Manager created/exists for client {client_id}")

            self.logger.error(
                f"🚨 DEBUG: Current managers count: {len(self.advanced_managers)}"
            )
            print(f"🚨 DEBUG: Current managers count: {len(self.advanced_managers)}")

            # 🔥 FIX: Get manager reference in proper scope
            manager = self.advanced_managers[client_id]

            # Execute force command through SingleAdvancedGridManager
            self.logger.error(
                f"🔥 DEBUG: About to call handle_force_command for client {client_id}"
            )
            print(
                f"🔥 DEBUG: About to call handle_force_command for client {client_id}"
            )
            self._log_instance_access("handle_force_command")
            self.ensure_initialized()
            result = await manager.handle_force_command(command)

            self.logger.error(
                f"✅ DEBUG: handle_force_command completed for client {client_id}: success={result.get('success', False)}"
            )
            print(
                f"✅ DEBUG: handle_force_command completed for client {client_id}: success={result.get('success', False)}"
            )

            if result["success"]:
                # Update client status
                client = self.client_repo.get_client(client_id)
                if client:
                    client.grid_status = GridStatus.ACTIVE
                    self.client_repo.update_client(client)

                # Update system metrics
                self.system_metrics["total_grids_started"] += 1
                self.system_metrics["total_force_commands"] += 1

                # After manager.handle_force_command(command), add:
                self.logger.error(
                    f"✅ DEBUG: Manager {client_id} now has {len(manager.active_grids)} active grids"
                )
                print(
                    f"✅ DEBUG: Manager {client_id} now has {len(manager.active_grids)} active grids"
                )

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

    async def get_client_status(self, client_id: int) -> Dict:
        """Get comprehensive status for specific client"""
        self.ensure_initialized()
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
        """Clean up managers for clients with no active grids - DISABLED FOR DEBUG"""
        try:
            self.logger.error(
                "🔍 DEBUG: cleanup_inactive_managers called - TEMPORARILY DISABLED"
            )
            print("🔍 DEBUG: cleanup_inactive_managers called - TEMPORARILY DISABLED")

            # TEMPORARY DISABLE: Don't actually clean up managers during debugging
            return

            # Original code commented out for debugging:
            # inactive_clients = []
            # for client_id, manager in self.advanced_managers.items():
            #     try:
            #         all_grids = manager.get_all_active_grids()
            #         if not all_grids.get("grids"):
            #             inactive_clients.append(client_id)
            #     except Exception as e:
            #         self.logger.warning(f"⚠️ Cleanup check failed for client {client_id}: {e}")
            #         inactive_clients.append(client_id)

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

    def get_all_active_grids(self) -> Dict:
        self._log_instance_access("get_all_active_grids")
        self.ensure_initialized()
        """Get status of all active single advanced grids across all clients"""
        try:
            self.logger.error(
                "🔍 DEBUG: GridOrchestrator.get_all_active_grids() called"
            )
            print("🔍 DEBUG: GridOrchestrator.get_all_active_grids() called")

            all_grids = {}
            system_summary = {
                "total_clients": len(self.advanced_managers),
                "total_active_grids": 0,
                "total_capital_deployed": 0.0,
                "architecture": "Single Advanced Grid System",
                "efficiency": "100% - No dual-grid overhead",
            }

            self.logger.error(
                f"🔍 DEBUG: Processing {len(self.advanced_managers)} managers"
            )
            print(f"🔍 DEBUG: Processing {len(self.advanced_managers)} managers")

            for client_id, manager in self.advanced_managers.items():
                try:
                    self.logger.error(f"🔍 DEBUG: Getting grids for client {client_id}")
                    print(f"🔍 DEBUG: Getting grids for client {client_id}")

                    client_grids = manager.get_all_active_grids()

                    self.logger.error(
                        f"🔍 DEBUG: Client {client_id} returned {len(client_grids.get('grids', {}))} grids"
                    )
                    print(
                        f"🔍 DEBUG: Client {client_id} returned {len(client_grids.get('grids', {}))} grids"
                    )

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
                        system_summary["total_active_grids"] += len(
                            client_grids["grids"]
                        )

                        # Calculate total capital deployed
                        for grid_data in client_grids["grids"].values():
                            grid_details = grid_data.get("grid_details", {})
                            if "total_capital" in grid_details:
                                system_summary["total_capital_deployed"] += (
                                    grid_details["total_capital"]
                                )

                except Exception as e:
                    self.logger.error(
                        f"❌ Failed to get grids for client {client_id}: {e}"
                    )
                    print(f"❌ DEBUG: Failed to get grids for client {client_id}: {e}")

            self.logger.error(
                f"✅ DEBUG: GridOrchestrator returning {system_summary['total_active_grids']} total active grids"
            )
            print(
                f"✅ DEBUG: GridOrchestrator returning {system_summary['total_active_grids']} total active grids"
            )

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

        except Exception as e:
            self.logger.error(f"❌ GridOrchestrator.get_all_active_grids error: {e}")
            print(f"❌ DEBUG: GridOrchestrator.get_all_active_grids error: {e}")
            import traceback

            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "system_summary": {
                    "total_clients": 0,
                    "total_active_grids": 0,
                    "total_capital_deployed": 0.0,
                    "architecture": "Single Advanced Grid System",
                    "efficiency": "Error occurred",
                },
                "client_grids": {},
                "error": str(e),
            }

    async def update_all_grids(self) -> Dict:
        """DEBUG VERSION with manager count monitoring"""
        self._log_instance_access("update_all_grids")

        try:
            # Check manager count at start
            start_count = len(self.advanced_managers)
            self.logger.error(
                f"🔍 DEBUG: update_all_grids START - {start_count} managers"
            )
            print(f"🔍 DEBUG: update_all_grids START - {start_count} managers")

            self.logger.error("🚨 DEBUG: update_all_grids() CALLED")
            print("🚨 DEBUG: update_all_grids() CALLED")

            self.logger.info("🔄 Compatibility call: update_all_grids()")

            # Check if we have any managers
            self.logger.error(f"🚨 DEBUG: Found {len(self.advanced_managers)} managers")
            print(f"🚨 DEBUG: Found {len(self.advanced_managers)} managers")

            if not self.advanced_managers:
                self.logger.error("🚨 DEBUG: NO ADVANCED MANAGERS FOUND!")
                print("🚨 DEBUG: NO ADVANCED MANAGERS FOUND!")
                return {
                    "success": False,
                    "error": "No advanced managers",
                    "updated_grids": 0,
                    "total_clients": 0,
                    "monitoring_active": self.monitoring_active,
                }

            # Check each manager before monitoring
            for client_id, manager in self.advanced_managers.items():
                try:
                    active_grids_count = len(manager.active_grids)
                    self.logger.error(
                        f"🔍 DEBUG: Client {client_id} has {active_grids_count} active grids"
                    )
                    print(
                        f"🔍 DEBUG: Client {client_id} has {active_grids_count} active grids"
                    )

                    if active_grids_count > 0:
                        grid_symbols = list(manager.active_grids.keys())
                        self.logger.error(f"   Grid symbols: {grid_symbols}")
                        print(f"   Grid symbols: {grid_symbols}")

                except Exception as check_error:
                    self.logger.error(
                        f"❌ DEBUG: Error checking manager {client_id}: {check_error}"
                    )
                    print(
                        f"❌ DEBUG: Error checking manager {client_id}: {check_error}"
                    )

            # Start monitoring if not already active
            if not self.monitoring_active:
                self.logger.error("🚨 DEBUG: Starting monitoring task")
                print("🚨 DEBUG: Starting monitoring task")
                asyncio.create_task(self.start_monitoring())

            # Check manager count before get_all_active_grids
            mid_count = len(self.advanced_managers)
            self.logger.error(
                f"🔍 DEBUG: Before get_all_active_grids - {mid_count} managers"
            )
            print(f"🔍 DEBUG: Before get_all_active_grids - {mid_count} managers")

            # Get current status of all grids
            all_grids = self.get_all_active_grids()

            # Check manager count after get_all_active_grids
            after_get_count = len(self.advanced_managers)
            self.logger.error(
                f"🔍 DEBUG: After get_all_active_grids - {after_get_count} managers"
            )
            print(f"🔍 DEBUG: After get_all_active_grids - {after_get_count} managers")

            # Update each active grid
            updated_grids = 0
            for client_id, manager in list(
                self.advanced_managers.items()
            ):  # Use list() to avoid dict change during iteration
                try:
                    self.logger.error(
                        f"🚨 DEBUG: Calling monitor_and_update_grids() for client {client_id}"
                    )
                    print(
                        f"🚨 DEBUG: Calling monitor_and_update_grids() for client {client_id}"
                    )

                    await manager.monitor_and_update_grids()
                    updated_grids += 1

                    self.logger.error(
                        f"✅ DEBUG: Successfully updated grids for client {client_id}"
                    )
                    print(
                        f"✅ DEBUG: Successfully updated grids for client {client_id}"
                    )

                except Exception as e:
                    self.logger.error(
                        f"❌ DEBUG: Update error for client {client_id}: {e}"
                    )
                    print(f"❌ DEBUG: Update error for client {client_id}: {e}")

            # Check final manager count
            end_count = len(self.advanced_managers)
            self.logger.error(f"🔍 DEBUG: update_all_grids END - {end_count} managers")
            print(f"🔍 DEBUG: update_all_grids END - {end_count} managers")

            if start_count != end_count:
                self.logger.error(
                    f"🚨 CRITICAL: Manager count changed from {start_count} to {end_count}!"
                )
                print(
                    f"🚨 CRITICAL: Manager count changed from {start_count} to {end_count}!"
                )

            return {
                "success": True,
                "updated_grids": updated_grids,
                "total_clients": len(self.advanced_managers),
                "monitoring_active": self.monitoring_active,
                "message": f"Updated {updated_grids} grids across {len(self.advanced_managers)} clients",
            }

        except Exception as e:
            self.logger.error(f"❌ DEBUG: Compatibility update_all_grids error: {e}")
            print(f"❌ DEBUG: Compatibility update_all_grids error: {e}")
            return {"success": False, "error": str(e), "updated_grids": 0}

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

    def debug_advanced_managers(self):
        """Debug method to check advanced managers state"""
        self.logger.error("🚨 DEBUG MANAGERS CHECK:")
        print("🚨 DEBUG MANAGERS CHECK:")

        self.logger.error(f"   Total managers: {len(self.advanced_managers)}")
        print(f"   Total managers: {len(self.advanced_managers)}")

        for client_id, manager in self.advanced_managers.items():
            active_grids = manager.get_all_active_grids()
            grid_count = len(active_grids.get("grids", {}))

            self.logger.error(f"   Client {client_id}: {grid_count} active grids")
            print(f"   Client {client_id}: {grid_count} active grids")

            if grid_count > 0:
                symbols = list(active_grids.get("grids", {}).keys())
                self.logger.error(f"     Symbols: {symbols}")
                print(f"     Symbols: {symbols}")

    def debug_manager_persistence(self, client_id: int):
        """Debug method to check if manager persists"""
        try:
            self.logger.error(
                f"🔍 DEBUG: Checking manager persistence for client {client_id}"
            )
            print(f"🔍 DEBUG: Checking manager persistence for client {client_id}")

            if client_id in self.advanced_managers:
                manager = self.advanced_managers[client_id]
                active_count = len(manager.active_grids)

                self.logger.error(
                    f"✅ DEBUG: Manager exists with {active_count} active grids"
                )
                print(f"✅ DEBUG: Manager exists with {active_count} active grids")

                if active_count > 0:
                    symbols = list(manager.active_grids.keys())
                    self.logger.error(f"   Symbols: {symbols}")
                    print(f"   Symbols: {symbols}")

                    # Test get_all_active_grids
                    all_grids = manager.get_all_active_grids()
                    grids_returned = len(all_grids.get("grids", {}))
                    self.logger.error(
                        f"   get_all_active_grids returns: {grids_returned} grids"
                    )
                    print(f"   get_all_active_grids returns: {grids_returned} grids")

                    return True
                else:
                    self.logger.error("⚠️ DEBUG: Manager exists but no active grids")
                    print("⚠️ DEBUG: Manager exists but no active grids")
                    return False
            else:
                self.logger.error(f"❌ DEBUG: Manager not found for client {client_id}")
                print(f"❌ DEBUG: Manager not found for client {client_id}")
                return False

        except Exception as e:
            self.logger.error(f"❌ DEBUG: Manager persistence check error: {e}")
            print(f"❌ DEBUG: Manager persistence check error: {e}")
            return False
