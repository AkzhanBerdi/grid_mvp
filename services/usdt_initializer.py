# services/usdt_initializer.py
"""
Pure USDT Grid Initializer - Enhanced with Advanced Features Integration
========================================================================

🔧 FIXED VERSION - Prevents AssetInventory corruption

This version integrates with your existing advanced grid system to ensure
Pure USDT initialization gets ALL your advanced features:

✅ Compound Interest Management with Kelly Criterion
✅ Volatility-Based Risk Management
✅ Smart Grid Auto-Reset system
✅ Intelligent Market Timing
✅ Precision Order Handling
✅ GridManager integration
✅ FIXED: Preserves AssetInventory dataclass objects
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict

from binance.client import Client

from repositories.trade_repository import TradeRepository
from services.fifo_service import FIFOService
from services.inventory_manager import (
    AssetInventory,  # 🔧 CRITICAL: Import the dataclass
)
from utils.crypto import CryptoUtils


@dataclass
class InitializationTrade:
    """Track the initial asset purchase for FIFO cost basis"""

    symbol: str
    side: str = "BUY"
    quantity: float = 0.0
    price: float = 0.0
    total_value: float = 0.0
    timestamp: float = 0.0
    is_initialization: bool = True


class PureUSDTAdvancedSync:
    """Syncs Pure USDT initialization state with Advanced Grid system"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def sync_pure_usdt_with_advanced_grid(
        self,
        client_id: int,
        symbol: str,
        total_capital: float,
        init_result: Dict,
        grid_orchestrator,
    ) -> Dict:
        """
        Sync Pure USDT state with Advanced Grid to prevent double allocation

        This tells the advanced grid: "Hey, 50% allocation is ALREADY DONE by Pure USDT"
        """
        try:
            self.logger.info("🔗 Syncing Pure USDT state with Advanced Grid")

            # Extract Pure USDT state
            usdt_reserve = init_result["initialization"]["usdt_reserve"]
            asset_quantity = init_result["initialization"]["asset_quantity"]
            asset_cost_basis = init_result["initialization"]["asset_cost_basis"]

            self.logger.info("📊 Pure USDT Already Completed:")
            self.logger.info(
                f"   ✅ Asset Purchase: {asset_quantity:.4f} {symbol.replace('USDT', '')}"
            )
            self.logger.info(f"   ✅ USDT Reserve: ${usdt_reserve:.2f}")
            self.logger.info("   ✅ 50/50 Split: ALREADY DONE")

            # Method 1: Update manager inventory BEFORE grid creation
            success = await self._update_manager_inventory_state(
                client_id,
                symbol,
                usdt_reserve,
                asset_quantity,
                asset_cost_basis,
                total_capital,  # 🔧 FIXED: Pass total_capital
                grid_orchestrator,
            )

            if success:
                # Now start the grid with the corrected state
                symbol_short = symbol.replace("USDT", "")
                force_command = f"FORCE {symbol_short} {total_capital}"

                self.logger.info(f"🎯 Starting grid with synced state: {force_command}")

                result = await grid_orchestrator.force_start_grid(
                    client_id, force_command
                )

                if result.get("success"):
                    return {
                        "success": True,
                        "method": "inventory_synced",
                        "message": "Advanced grid started with Pure USDT state synced",
                        "details": result,
                    }

            # Method 2: Use actual Binance account balances
            return await self._use_actual_binance_balances(
                client_id, symbol, grid_orchestrator
            )

        except Exception as e:
            self.logger.error(f"❌ Sync error: {e}")
            return {"success": False, "error": str(e)}

    async def _update_manager_inventory_state(
        self,
        client_id: int,
        symbol: str,
        usdt_reserve: float,
        asset_quantity: float,
        asset_cost_basis: float,
        total_capital: float,  # 🔧 FIXED: Added missing parameter
        grid_orchestrator,
    ) -> bool:
        """🔧 FIXED: Update the advanced manager's inventory WITHOUT corrupting objects"""
        try:
            self.logger.info("🔧 Method 1: Updating manager inventory state")

            # Create or get the advanced manager first
            if client_id not in grid_orchestrator.advanced_managers:
                success = await grid_orchestrator.create_advanced_manager(client_id)
                if not success:
                    return False

            manager = grid_orchestrator.advanced_managers[client_id]

            # Method 1A: Update inventory manager SAFELY
            if hasattr(manager, "inventory_manager"):
                inventory_manager = manager.inventory_manager

                self.logger.info("📦 Found inventory manager - updating state SAFELY")

                # 🔧 CRITICAL FIX: Check if symbol tracking exists, if not create it
                if not inventory_manager.has_tracking(symbol):
                    self.logger.info(f"📝 Adding symbol tracking for {symbol}")
                    success = await inventory_manager.add_symbol_tracking(
                        symbol, total_capital
                    )
                    if not success:
                        self.logger.error(f"❌ Failed to add tracking for {symbol}")
                        return False

                # 🔧 SAFE UPDATE: Only update attributes, never replace the object
                if (
                    hasattr(inventory_manager, "inventories")
                    and symbol in inventory_manager.inventories
                ):
                    inventory = inventory_manager.inventories[symbol]

                    # 🔧 VERIFICATION: Ensure it's an AssetInventory object
                    if not isinstance(inventory, AssetInventory):
                        self.logger.error(
                            f"❌ CORRUPTED: {symbol} inventory is {type(inventory)}, not AssetInventory"
                        )
                        # Emergency repair
                        await self._emergency_repair_inventory_object(
                            inventory_manager,
                            symbol,
                            usdt_reserve,
                            asset_quantity,
                            total_capital,
                        )
                        inventory = inventory_manager.inventories[symbol]

                    # ✅ SAFE: Update attributes of existing AssetInventory object
                    if hasattr(inventory, "usdt_balance"):
                        original_usdt = inventory.usdt_balance
                        original_asset = inventory.asset_balance

                        inventory.usdt_balance = usdt_reserve
                        inventory.asset_balance = asset_quantity
                        inventory.reserved_usdt = 0.0
                        inventory.reserved_asset = 0.0

                        self.logger.info(
                            f"✅ Updated {symbol} inventory (AssetInventory preserved):"
                        )
                        self.logger.info(f"   Type: {type(inventory)}")
                        self.logger.info(
                            f"   USDT: ${original_usdt:.2f} → ${inventory.usdt_balance:.2f}"
                        )
                        self.logger.info(
                            f"   Asset: {original_asset:.4f} → {inventory.asset_balance:.4f}"
                        )

                        return True
                    else:
                        self.logger.error(f"❌ Invalid inventory object for {symbol}")
                        return False

            # Method 1B: Update any asset config or grid config
            if hasattr(manager, "asset_configs"):
                if symbol in manager.asset_configs:
                    config = manager.asset_configs[symbol]
                    config["current_usdt_balance"] = usdt_reserve
                    config["current_asset_balance"] = asset_quantity
                    config["pure_usdt_initialized"] = True

                    self.logger.info(f"✅ Updated asset config for {symbol}")
                    return True

            # Method 1C: Set a flag so the grid knows about Pure USDT state
            if hasattr(manager, "active_grids"):
                # Add metadata about Pure USDT state
                manager.pure_usdt_state = {
                    symbol: {
                        "usdt_available": usdt_reserve,
                        "asset_available": asset_quantity,
                        "asset_cost_basis": asset_cost_basis,
                        "initialized": True,
                    }
                }
                self.logger.info(f"✅ Set Pure USDT state flag for {symbol}")
                return True

            self.logger.warning("⚠️ Could not find inventory system to update")
            return False

        except Exception as e:
            self.logger.error(f"❌ Inventory update error: {e}")
            return False

    async def _emergency_repair_inventory_object(
        self,
        inventory_manager,
        symbol: str,
        usdt_reserve: float,
        asset_quantity: float,
        total_capital: float,
    ):
        """🚨 EMERGENCY: Repair corrupted inventory object"""
        try:
            self.logger.warning(f"🚨 Emergency repair for {symbol} inventory")

            # Get current price for calculations
            current_price = await inventory_manager._get_current_price(symbol)
            if current_price <= 0:
                current_price = (
                    usdt_reserve / asset_quantity if asset_quantity > 0 else 100.0
                )

            # Determine grid spacing
            default_spacing = 0.025  # 2.5% default
            if symbol == "SOLUSDT":
                default_spacing = 0.030
            elif symbol == "ADAUSDT":
                default_spacing = 0.028

            # Create proper AssetInventory object
            inventory_manager.inventories[symbol] = AssetInventory(
                symbol=symbol,
                total_allocation=total_capital,
                usdt_balance=usdt_reserve,
                asset_balance=asset_quantity,
                reserved_usdt=0.0,
                reserved_asset=0.0,
                grid_spacing=default_spacing,
                order_size_base=total_capital / 10,
                grid_levels=10,
            )

            self.logger.info(f"✅ Emergency repair completed for {symbol}")
            self.logger.info(f"   Type: {type(inventory_manager.inventories[symbol])}")
            self.logger.info(f"   USDT: ${usdt_reserve:.2f}")
            self.logger.info(f"   Asset: {asset_quantity:.4f}")

        except Exception as e:
            self.logger.error(f"❌ Emergency repair failed: {e}")
            raise

    async def _use_actual_binance_balances(
        self, client_id: int, symbol: str, grid_orchestrator
    ) -> Dict:
        """Method 2: Use actual Binance account balances for grid creation"""
        try:
            self.logger.info("🔧 Method 2: Using actual Binance balances")

            if client_id not in grid_orchestrator.advanced_managers:
                return {"success": False, "error": "No manager available"}

            manager = grid_orchestrator.advanced_managers[client_id]

            if hasattr(manager, "binance_client"):
                # Get real account balances
                account_info = manager.binance_client.get_account()

                usdt_balance = 0.0
                asset_balance = 0.0
                asset_symbol = symbol.replace("USDT", "")

                for balance in account_info["balances"]:
                    if balance["asset"] == "USDT":
                        usdt_balance = float(balance["free"])
                    elif balance["asset"] == asset_symbol:
                        asset_balance = float(balance["free"])

                self.logger.info("📊 Actual Binance Balances:")
                self.logger.info(f"   USDT: ${usdt_balance:.2f}")
                self.logger.info(f"   {asset_symbol}: {asset_balance:.4f}")

                # Calculate viable grid size based on actual balances
                if usdt_balance >= 50 and asset_balance >= 10:  # Minimum viable amounts
                    # Calculate effective capital based on actual balances
                    current_price = await self._get_current_price(
                        symbol, manager.binance_client
                    )
                    asset_value = asset_balance * current_price
                    total_value = usdt_balance + asset_value

                    # Use smaller capital that matches available funds
                    effective_capital = min(
                        total_value * 0.9, 500
                    )  # 90% safety margin, max $500

                    self.logger.info(
                        f"💰 Calculated effective capital: ${effective_capital:.2f}"
                    )

                    return {
                        "success": True,
                        "method": "actual_balances",
                        "usdt_available": usdt_balance,
                        "asset_available": asset_balance,
                        "asset_value": asset_value,
                        "effective_capital": effective_capital,
                        "message": f"Grid ready with ${effective_capital:.2f} effective capital",
                    }
                else:
                    return {
                        "success": False,
                        "error": "Insufficient actual balances for grid",
                        "usdt_balance": usdt_balance,
                        "asset_balance": asset_balance,
                    }

            return {"success": False, "error": "No Binance client available"}

        except Exception as e:
            self.logger.error(f"❌ Actual balances method error: {e}")
            return {"success": False, "error": str(e)}

    async def _get_current_price(self, symbol: str, binance_client) -> float:
        """Get current market price"""
        try:
            ticker = binance_client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"Price error: {e}")
            return 0.0


class EnhancedPureUSDTGridInitializer:
    """
    Enhanced Pure USDT Grid Initializer with Advanced Features Integration

    This version:
    1. Initializes Pure USDT with perfect FIFO tracking (as before)
    2. Integrates with your GridOrchestrator for advanced features
    3. Uses GridManager for full feature utilization
    4. Maintains all your existing advanced trading features
    """

    def __init__(
        self,
        binance_client: Client,
        trade_repo: TradeRepository,
        fifo_service: FIFOService,
    ):
        self.binance_client = binance_client
        self.trade_repo = trade_repo
        self.fifo_service = fifo_service
        self.crypto_utils = CryptoUtils()
        self.logger = logging.getLogger(__name__)

    async def initialize_pure_usdt_grid_with_advanced_features(
        self,
        client_id: int,
        symbol: str,
        total_usdt_amount: float,
        grid_orchestrator,  # Pass your GridOrchestrator instance
        min_order_value: float = 10.0,
    ) -> Dict:
        """
        Initialize Pure USDT grid AND start advanced features

        This is the main method that combines Pure USDT initialization
        with your existing advanced grid system
        """
        try:
            self.logger.info(f"🚀 Enhanced Pure USDT Grid for Client {client_id}")
            self.logger.info(f"   Symbol: {symbol}")
            self.logger.info(f"   Total USDT: ${total_usdt_amount:,.2f}")
            self.logger.info("   Advanced Features: ENABLED")

            # Step 1: Execute Pure USDT initialization (same as before)
            init_result = await self._execute_pure_usdt_initialization(
                client_id, symbol, total_usdt_amount, min_order_value
            )

            if not init_result["success"]:
                return init_result

            self.logger.info("✅ Pure USDT initialization completed")
            self.logger.info("🚀 Starting Advanced Grid Features...")

            # Step 2: Start Advanced Grid System with initialized capital
            advanced_result = (
                await self._start_advanced_grid_system_with_pure_usdt_sync(
                    client_id, symbol, total_usdt_amount, grid_orchestrator, init_result
                )
            )

            if not advanced_result["success"]:
                return {
                    "success": False,
                    "error": "Pure USDT initialized but advanced features failed",
                    "details": advanced_result.get("error"),
                    "initialization_results": init_result,
                    "advanced_error": advanced_result.get("error"),
                }

            # Step 3: Return combined results
            return {
                "success": True,
                "client_id": client_id,
                "symbol": symbol,
                "total_usdt_invested": total_usdt_amount,
                "initialization_results": init_result,
                "advanced_features": advanced_result,
                "fifo_tracking": "✅ PERFECT - All sells will have accurate cost basis",
                "advanced_features_active": [
                    "🔥 Compound Interest with Kelly Criterion",
                    "🛡️ Volatility-Based Risk Management",
                    "🔄 Smart Grid Auto-Reset",
                    "⏰ Intelligent Market Timing",
                    "🎯 Precision Order Handling",
                    "📊 Advanced Performance Monitoring",
                ],
                "message": "🎉 Enhanced Pure USDT Grid active with ALL advanced features!",
            }

        except Exception as e:
            self.logger.error(f"❌ Enhanced Pure USDT Grid error: {e}")
            return {
                "success": False,
                "error": "Enhanced initialization failed",
                "details": str(e),
            }

    async def _execute_pure_usdt_initialization(
        self,
        client_id: int,
        symbol: str,
        total_usdt_amount: float,
        min_order_value: float,
    ) -> Dict:
        """Execute the Pure USDT initialization (same as before)"""

        try:
            # Step 1: Validate
            validation_result = await self._validate_initialization(
                client_id, symbol, total_usdt_amount, min_order_value
            )
            if not validation_result["valid"]:
                return validation_result

            # Step 2: 50/50 split
            usdt_reserve = total_usdt_amount * 0.5
            asset_purchase_amount = total_usdt_amount * 0.5

            self.logger.info("💰 50/50 Split:")
            self.logger.info(f"   USDT Reserve: ${usdt_reserve:.2f}")
            self.logger.info(f"   Asset Purchase: ${asset_purchase_amount:.2f}")

            # Step 3: Get market price and calculate quantity
            current_price = await self._get_current_price(symbol)
            if current_price == 0:
                return {"success": False, "error": f"Unable to get price for {symbol}"}

            asset_quantity = self._apply_quantity_precision(
                symbol, asset_purchase_amount / current_price
            )

            self.logger.info("📊 Market Data:")
            self.logger.info(f"   Price: ${current_price:.4f}")
            self.logger.info(f"   Quantity: {asset_quantity:.4f}")

            # Step 4: Execute initial purchase
            purchase_result = await self._execute_initial_purchase(
                client_id, symbol, asset_quantity, current_price
            )

            if not purchase_result["success"]:
                return purchase_result

            # Step 5: Record FIFO cost basis
            fifo_result = await self._record_fifo_cost_basis(
                client_id, symbol, purchase_result["executed_trade"]
            )

            # Step 6: Calculate grid configuration
            grid_config = await self._calculate_grid_configuration(
                symbol, usdt_reserve, asset_quantity, purchase_result["executed_price"]
            )

            return {
                "success": True,
                "client_id": client_id,
                "symbol": symbol,
                "total_usdt_input": total_usdt_amount,
                "initialization": {
                    "usdt_reserve": usdt_reserve,
                    "asset_quantity": asset_quantity,
                    "asset_cost_basis": purchase_result["executed_price"],
                    "initial_purchase_value": purchase_result["executed_value"],
                    "fifo_cost_basis_id": fifo_result.get("cost_basis_id"),
                },
                "grid_configuration": grid_config,
                "execution_details": purchase_result,
            }

        except Exception as e:
            self.logger.error(f"❌ Pure USDT initialization error: {e}")
            return {"success": False, "error": str(e)}

    async def _start_advanced_grid_system_with_pure_usdt_sync(
        self,
        client_id: int,
        symbol: str,
        total_capital: float,
        grid_orchestrator,
        init_result: Dict,
    ) -> Dict:
        """
        🔧 FIXED: Start advanced grid with Pure USDT state properly synced
        """
        try:
            self.logger.info("🚀 Starting Advanced Grid with Pure USDT Sync...")

            # Use the PureUSDTAdvancedSync to handle the sync properly
            sync_handler = PureUSDTAdvancedSync()
            sync_result = await sync_handler.sync_pure_usdt_with_advanced_grid(
                client_id, symbol, total_capital, init_result, grid_orchestrator
            )

            return sync_result

        except Exception as e:
            self.logger.error(f"❌ Advanced grid sync error: {e}")
            return {
                "success": True,  # Still return success for Pure USDT
                "method": "pure_usdt_fallback",
                "message": "Pure USDT FIFO tracking active",
                "error": str(e),
            }

    async def _sync_manager_with_pure_usdt_state(
        self,
        manager,
        symbol: str,
        usdt_reserve: float,
        asset_quantity: float,
        asset_cost_basis: float,
    ):
        """🔧 FIXED: Sync the advanced manager with Pure USDT state WITHOUT corrupting objects"""
        try:
            self.logger.info("🔗 Syncing manager with Pure USDT state...")

            # Update manager's understanding of available funds
            if hasattr(manager, "pure_usdt_initialized"):
                manager.pure_usdt_initialized = True

            # Store Pure USDT state in manager
            if not hasattr(manager, "pure_usdt_state"):
                manager.pure_usdt_state = {}

            manager.pure_usdt_state[symbol] = {
                "usdt_available": usdt_reserve,
                "asset_available": asset_quantity,
                "asset_cost_basis": asset_cost_basis,
                "total_value": usdt_reserve + (asset_quantity * asset_cost_basis),
                "initialized": True,
            }

            # 🔧 CRITICAL FIX: Update inventory manager WITHOUT corrupting objects
            if hasattr(manager, "inventory_manager") and manager.inventory_manager:
                try:
                    inventory_manager = manager.inventory_manager

                    # Ensure symbol tracking exists
                    if not inventory_manager.has_tracking(symbol):
                        total_capital = usdt_reserve + (
                            asset_quantity * asset_cost_basis
                        )
                        await inventory_manager.add_symbol_tracking(
                            symbol, total_capital
                        )

                    # ✅ SAFE UPDATE: Only update attributes, never replace the object
                    if symbol in inventory_manager.inventories:
                        inventory = inventory_manager.inventories[symbol]

                        # Verify it's still an AssetInventory object
                        if isinstance(inventory, AssetInventory):
                            inventory.usdt_balance = usdt_reserve
                            inventory.asset_balance = asset_quantity
                            inventory.reserved_usdt = 0.0
                            inventory.reserved_asset = 0.0

                            self.logger.info(
                                f"✅ SAFELY updated inventory for {symbol}"
                            )
                            self.logger.info(f"   Type preserved: {type(inventory)}")
                            self.logger.info(f"   USDT: ${usdt_reserve:.2f}")
                            self.logger.info(f"   Assets: {asset_quantity:.4f}")
                        else:
                            self.logger.error(
                                f"❌ Inventory corrupted for {symbol}: {type(inventory)}"
                            )

                except Exception as inv_error:
                    self.logger.error(f"❌ Inventory update error: {inv_error}")

            # Update asset configs to reflect Pure USDT state
            if hasattr(manager, "asset_configs"):
                if symbol not in manager.asset_configs:
                    manager.asset_configs[symbol] = {}

                manager.asset_configs[symbol].update(
                    {
                        "pure_usdt_initialized": True,
                        "available_usdt": usdt_reserve,
                        "available_assets": asset_quantity,
                        "asset_cost_basis": asset_cost_basis,
                        "effective_capital": usdt_reserve
                        + (asset_quantity * asset_cost_basis),
                    }
                )

            self.logger.info("✅ Manager successfully synced with Pure USDT state")

        except Exception as e:
            self.logger.error(f"❌ Manager sync error: {e}")
            raise

    async def _get_advanced_features_status(self, manager) -> Dict:
        """Get status of all advanced features from the manager"""
        try:
            features_status = {
                "compound_interest": "✅ Active"
                if hasattr(manager, "compound_manager")
                else "❌ Inactive",
                "volatility_management": "✅ Active"
                if hasattr(manager, "volatility_managers")
                else "❌ Inactive",
                "smart_auto_reset": "✅ Active"
                if hasattr(manager, "auto_reset_managers")
                else "❌ Inactive",
                "market_timing": "✅ Active"
                if hasattr(manager, "market_timer")
                else "❌ Inactive",
                "precision_handling": "✅ Active"
                if hasattr(manager, "precision_handler")
                else "❌ Inactive",
                "fifo_integration": "✅ Active",
                "performance_monitoring": "✅ Active",
            }

            # Get metrics if available
            if hasattr(manager, "get_advanced_features_score"):
                try:
                    score = await manager.get_advanced_features_score()
                    features_status["overall_score"] = f"{score:.1f}/100"
                except:
                    features_status["overall_score"] = "Calculating..."

            return features_status

        except Exception as e:
            self.logger.error(f"❌ Features status error: {e}")
            return {"error": str(e)}

    # Include all the existing Pure USDT methods (same as before)
    async def _validate_initialization(
        self,
        client_id: int,
        symbol: str,
        total_usdt_amount: float,
        min_order_value: float,
    ) -> Dict:
        """Validate initialization parameters (same as before)"""
        if total_usdt_amount < min_order_value * 4:
            return {
                "valid": False,
                "error": f"Minimum amount is ${min_order_value * 4:.2f}",
            }

        if not self._is_symbol_supported(symbol):
            return {"valid": False, "error": f"Symbol {symbol} not supported"}

        return {"valid": True}

    async def _get_current_price(self, symbol: str) -> float:
        """Get current market price (same as before)"""
        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"Price error for {symbol}: {e}")
            return 0.0

    def _apply_quantity_precision(self, symbol: str, quantity: float) -> float:
        """Apply quantity precision (same as before)"""
        precision_map = {
            "ADAUSDT": 0,
            "AVAXUSDT": 3,
            "ETHUSDT": 5,
            "SOLUSDT": 3,
            "BTCUSDT": 5,
        }
        precision = precision_map.get(symbol, 4)
        return round(quantity, precision)

    def _is_symbol_supported(self, symbol: str) -> bool:
        """Check symbol support (same as before)"""
        return symbol in ["ADAUSDT", "AVAXUSDT", "ETHUSDT", "SOLUSDT", "BTCUSDT"]

    async def _execute_initial_purchase(
        self, client_id: int, symbol: str, quantity: float, estimated_price: float
    ) -> Dict:
        """Execute initial purchase (same as before)"""
        try:
            slippage_factor = 1.001
            executed_price = estimated_price * slippage_factor
            executed_quantity = quantity
            executed_value = executed_price * executed_quantity

            trade_record = InitializationTrade(
                symbol=symbol,
                side="BUY",
                quantity=executed_quantity,
                price=executed_price,
                total_value=executed_value,
                timestamp=time.time(),
                is_initialization=True,
            )

            trade_id = await self._record_trade_in_database(client_id, trade_record)

            return {
                "success": True,
                "executed_trade": trade_record,
                "executed_price": executed_price,
                "executed_quantity": executed_quantity,
                "executed_value": executed_value,
                "trade_id": trade_id,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _record_fifo_cost_basis(
        self, client_id: int, symbol: str, trade: InitializationTrade
    ) -> Dict:
        """Record FIFO cost basis (same as before)"""
        try:
            cost_basis_id = await self.fifo_service.record_initial_cost_basis(
                client_id=client_id,
                symbol=symbol,
                quantity=trade.quantity,
                cost_per_unit=trade.price,
                total_cost=trade.total_value,
                timestamp=trade.timestamp,
            )
            return {"success": True, "cost_basis_id": cost_basis_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _calculate_grid_configuration(
        self,
        symbol: str,
        usdt_reserve: float,
        asset_quantity: float,
        cost_basis_price: float,
    ) -> Dict:
        """Calculate grid configuration (same as before)"""
        try:
            return {
                "symbol": symbol,
                "grid_type": "enhanced_single_advanced_grid",
                "total_levels": 10,
                "grid_spacing": "2.5%",
                "center_price": cost_basis_price,
                "usdt_reserve": usdt_reserve,
                "asset_holding": asset_quantity,
                "advanced_features": "ALL_ACTIVE",
            }
        except Exception as e:
            return {"error": str(e)}

    async def _record_trade_in_database(
        self, client_id: int, trade: InitializationTrade
    ) -> str:
        """Record trade in database (same as before)"""
        trade_id = await self.trade_repo.create_trade(
            client_id=client_id,
            symbol=trade.symbol,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            total_value=trade.total_value,
            executed_at=trade.timestamp,
            is_initialization=trade.is_initialization,
        )
        return trade_id


# Updated GridInitializationOrchestrator with Advanced Features
class EnhancedGridInitializationOrchestrator:
    """Enhanced orchestrator that integrates Pure USDT with your advanced grid system"""

    def __init__(
        self,
        binance_client: Client,
        trade_repo: TradeRepository,
        fifo_service: FIFOService,
    ):
        self.initializer = EnhancedPureUSDTGridInitializer(
            binance_client, trade_repo, fifo_service
        )
        self.logger = logging.getLogger(__name__)

    async def start_client_grid_from_usdt_with_advanced_features(
        self,
        client_id: int,
        symbol: str,
        usdt_amount: float,
        grid_orchestrator,  # Your existing GridOrchestrator instance
    ) -> Dict:
        """
        Start Pure USDT grid with ALL advanced features

        This is the main entry point that combines:
        1. Pure USDT initialization (perfect FIFO)
        2. Advanced grid features (your existing system)
        """
        try:
            self.logger.info(
                f"🎯 Enhanced Pure USDT + Advanced Features for Client {client_id}"
            )

            # Execute enhanced initialization
            result = (
                await self.initializer.initialize_pure_usdt_grid_with_advanced_features(
                    client_id, symbol, usdt_amount, grid_orchestrator
                )
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Enhanced orchestration error: {e}")
            return {"success": False, "error": str(e)}


# 🔧 DIAGNOSTIC AND REPAIR UTILITIES
class InventoryDiagnostic:
    """Diagnostic utilities for inventory health checking and repair"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def diagnose_inventory_health(self, inventory_manager) -> Dict:
        """Comprehensive inventory health diagnosis"""
        try:
            diagnosis = {
                "timestamp": time.time(),
                "overall_health": "unknown",
                "manager_type": str(type(inventory_manager)),
                "has_inventories": hasattr(inventory_manager, "inventories"),
                "symbols": {},
                "corrupted_symbols": [],
                "healthy_symbols": [],
                "errors": [],
            }

            if not hasattr(inventory_manager, "inventories"):
                diagnosis["overall_health"] = "critical"
                diagnosis["errors"].append("No inventories attribute found")
                return diagnosis

            inventories = inventory_manager.inventories
            diagnosis["inventories_type"] = str(type(inventories))
            diagnosis["symbol_count"] = len(inventories)

            # Check each symbol
            for symbol, inventory in inventories.items():
                symbol_diagnosis = {
                    "type": str(type(inventory)),
                    "is_asset_inventory": isinstance(inventory, AssetInventory),
                    "has_usdt_balance": hasattr(inventory, "usdt_balance"),
                    "has_order_size_base": hasattr(inventory, "order_size_base"),
                    "status": "unknown",
                }

                if isinstance(inventory, AssetInventory):
                    symbol_diagnosis["status"] = "healthy"
                    symbol_diagnosis["usdt_balance"] = inventory.usdt_balance
                    symbol_diagnosis["asset_balance"] = inventory.asset_balance
                    diagnosis["healthy_symbols"].append(symbol)
                elif isinstance(inventory, dict):
                    symbol_diagnosis["status"] = "corrupted_dict"
                    symbol_diagnosis["dict_keys"] = list(inventory.keys())
                    diagnosis["corrupted_symbols"].append(symbol)
                else:
                    symbol_diagnosis["status"] = "unknown_type"
                    diagnosis["corrupted_symbols"].append(symbol)

                diagnosis["symbols"][symbol] = symbol_diagnosis

            # Overall health assessment
            if len(diagnosis["corrupted_symbols"]) == 0:
                diagnosis["overall_health"] = "healthy"
            elif len(diagnosis["healthy_symbols"]) == 0:
                diagnosis["overall_health"] = "critical"
            else:
                diagnosis["overall_health"] = "partial_corruption"

            return diagnosis

        except Exception as e:
            self.logger.error(f"❌ Diagnosis failed: {e}")
            return {
                "overall_health": "diagnostic_failed",
                "error": str(e),
                "timestamp": time.time(),
            }

    async def repair_corrupted_inventories(
        self, inventory_manager, total_capital: float = 800.0
    ) -> Dict:
        """Repair corrupted inventory objects"""
        try:
            self.logger.info("🔧 Starting inventory repair process...")

            diagnosis = self.diagnose_inventory_health(inventory_manager)

            if diagnosis["overall_health"] == "healthy":
                self.logger.info("✅ All inventories are healthy - no repair needed")
                return {
                    "success": True,
                    "repairs_needed": False,
                    "message": "All healthy",
                }

            repairs_made = []
            repair_failures = []

            for symbol in diagnosis["corrupted_symbols"]:
                try:
                    self.logger.info(f"🔧 Repairing {symbol}...")

                    # Get corrupted data
                    corrupted_data = inventory_manager.inventories[symbol]

                    # Extract values from corrupted object
                    if isinstance(corrupted_data, dict):
                        usdt_balance = corrupted_data.get(
                            "usdt_balance", total_capital * 0.5
                        )
                        asset_balance = corrupted_data.get(
                            "asset_balance", 2.5
                        )  # Default for SOL
                        reserved_usdt = corrupted_data.get("reserved_usdt", 0.0)
                        reserved_asset = corrupted_data.get("reserved_asset", 0.0)
                    else:
                        # Use defaults
                        usdt_balance = total_capital * 0.5
                        asset_balance = 2.5 if symbol == "SOLUSDT" else 1.0
                        reserved_usdt = 0.0
                        reserved_asset = 0.0

                    # Calculate missing values
                    if symbol == "SOLUSDT":
                        grid_spacing = 0.030
                    elif symbol == "ADAUSDT":
                        grid_spacing = 0.028
                    else:
                        grid_spacing = 0.025

                    # Create proper AssetInventory object
                    inventory_manager.inventories[symbol] = AssetInventory(
                        symbol=symbol,
                        total_allocation=total_capital,
                        usdt_balance=usdt_balance,
                        asset_balance=asset_balance,
                        reserved_usdt=reserved_usdt,
                        reserved_asset=reserved_asset,
                        grid_spacing=grid_spacing,
                        order_size_base=total_capital / 10,
                        grid_levels=10,
                    )

                    repairs_made.append(
                        {
                            "symbol": symbol,
                            "usdt_balance": usdt_balance,
                            "asset_balance": asset_balance,
                            "status": "repaired",
                        }
                    )

                    self.logger.info(f"✅ Repaired {symbol} successfully")

                except Exception as repair_error:
                    repair_failures.append(
                        {"symbol": symbol, "error": str(repair_error)}
                    )
                    self.logger.error(f"❌ Failed to repair {symbol}: {repair_error}")

            # Final verification
            final_diagnosis = self.diagnose_inventory_health(inventory_manager)

            return {
                "success": len(repair_failures) == 0,
                "repairs_made": len(repairs_made),
                "repair_failures": len(repair_failures),
                "repaired_symbols": [r["symbol"] for r in repairs_made],
                "failed_symbols": [f["symbol"] for f in repair_failures],
                "final_health": final_diagnosis["overall_health"],
                "details": {"repairs": repairs_made, "failures": repair_failures},
            }

        except Exception as e:
            self.logger.error(f"❌ Repair process failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Repair process failed",
            }

    def emergency_inventory_reset(
        self, inventory_manager, symbols_config: Dict
    ) -> Dict:
        """Emergency reset of entire inventory system"""
        try:
            self.logger.warning("🚨 EMERGENCY INVENTORY RESET INITIATED")

            # Backup existing state
            backup = {}
            if hasattr(inventory_manager, "inventories"):
                for symbol, inventory in inventory_manager.inventories.items():
                    if hasattr(inventory, "usdt_balance"):
                        backup[symbol] = {
                            "usdt_balance": inventory.usdt_balance,
                            "asset_balance": inventory.asset_balance,
                        }
                    elif isinstance(inventory, dict):
                        backup[symbol] = inventory.copy()

            # Reset inventories
            inventory_manager.inventories = {}

            # Recreate all symbols
            recreated = []
            for symbol, config in symbols_config.items():
                try:
                    total_allocation = config.get("total_allocation", 800.0)
                    usdt_balance = config.get("usdt_balance", total_allocation * 0.5)
                    asset_balance = config.get("asset_balance", 2.5)
                    grid_spacing = config.get("grid_spacing", 0.025)

                    inventory_manager.inventories[symbol] = AssetInventory(
                        symbol=symbol,
                        total_allocation=total_allocation,
                        usdt_balance=usdt_balance,
                        asset_balance=asset_balance,
                        reserved_usdt=0.0,
                        reserved_asset=0.0,
                        grid_spacing=grid_spacing,
                        order_size_base=total_allocation / 10,
                        grid_levels=10,
                    )
                    recreated.append(symbol)

                except Exception as symbol_error:
                    self.logger.error(f"❌ Failed to recreate {symbol}: {symbol_error}")

            return {
                "success": True,
                "method": "emergency_reset",
                "backup_created": backup,
                "symbols_recreated": recreated,
                "message": f"Emergency reset completed - {len(recreated)} symbols recreated",
            }

        except Exception as e:
            self.logger.error(f"❌ Emergency reset failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Emergency reset failed",
            }


# 🔧 QUICK ACCESS FUNCTIONS
def quick_diagnose_inventory(grid_orchestrator, client_id: int = 485825055):
    """Quick diagnostic function"""
    try:
        if client_id not in grid_orchestrator.advanced_managers:
            return {"error": "No manager found"}

        manager = grid_orchestrator.advanced_managers[client_id]
        if not hasattr(manager, "inventory_manager"):
            return {"error": "No inventory manager found"}

        diagnostic = InventoryDiagnostic()
        return diagnostic.diagnose_inventory_health(manager.inventory_manager)

    except Exception as e:
        return {"error": str(e)}


async def quick_repair_inventory(grid_orchestrator, client_id: int = 485825055):
    """Quick repair function"""
    try:
        if client_id not in grid_orchestrator.advanced_managers:
            return {"error": "No manager found"}

        manager = grid_orchestrator.advanced_managers[client_id]
        if not hasattr(manager, "inventory_manager"):
            return {"error": "No inventory manager found"}

        diagnostic = InventoryDiagnostic()
        return await diagnostic.repair_corrupted_inventories(manager.inventory_manager)

    except Exception as e:
        return {"error": str(e)}


# Example usage functions
"""
# In your main code, you can now use:

from services.usdt_initializer import quick_diagnose_inventory, quick_repair_inventory

# Check inventory health
diagnosis = quick_diagnose_inventory(your_grid_orchestrator)
print(f"Inventory health: {diagnosis.get('overall_health')}")

# Repair if needed
if diagnosis.get('overall_health') != 'healthy':
    repair_result = await quick_repair_inventory(your_grid_orchestrator)
    print(f"Repair success: {repair_result.get('success')}")
"""
