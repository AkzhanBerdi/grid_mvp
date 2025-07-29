# services/grid_manager.py

import logging
import time
from typing import Dict, Optional

from binance.client import Client

from models.grid_config import GridConfig
from repositories.client_repository import ClientRepository
from repositories.trade_repository import TradeRepository
from services.compound_manager import CompoundInterestManager
from services.fifo_service import FIFOService
from services.grid_monitor import GridMonitoringService
from services.grid_trading_engine import GridTradingEngine
from services.grid_utils import GridUtilityService
from services.inventory_manager import SingleGridInventoryManager
from services.trading_features import (
    IntelligentMarketTimer,
    SmartGridAutoReset,
    VolatilityBasedRiskManager,
)


class GridManager:
    """Clean single advanced grid manager with proper inventory integration"""

    def __init__(self, binance_client: Client, client_id: int):
        self.binance_client = binance_client
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        # Core services
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()
        self.fifo_service = FIFOService()

        # Trading engine (handles all order operations)
        self.trading_engine = GridTradingEngine(binance_client, client_id)
        self.utility = GridUtilityService(binance_client)
        self.monitoring = GridMonitoringService(client_id, binance_client)

        # Advanced features
        self.market_timer = IntelligentMarketTimer()
        self.volatility_managers: Dict[str, VolatilityBasedRiskManager] = {}
        self.auto_reset_managers: Dict[str, SmartGridAutoReset] = {}

        # Initialize compound manager
        self.compound_manager = CompoundInterestManager(self.fifo_service)
        self.logger.info(
            "✅ Advanced CompoundInterestManager with Kelly Criterion activated"
        )

        # State
        self.active_grids: Dict[str, GridConfig] = {}
        self.inventory_manager: Optional[SingleGridInventoryManager] = None

        # Metrics
        self.metrics = {
            "grids_started": 0,
            "grids_stopped": 0,
            "total_trades": 0,
            "optimizations": 0,
        }

        # Asset configurations
        self.asset_configs = {
            "ETHUSDT": {
                "allocation": 0.40,
                "risk_profile": "conservative",
                "grid_spacing_base": 0.025,
                "volatility_threshold": 0.8,
            },
            "SOLUSDT": {
                "allocation": 0.35,
                "risk_profile": "moderate-aggressive",
                "grid_spacing_base": 0.03,
                "volatility_threshold": 1.2,
            },
            "ADAUSDT": {
                "allocation": 0.25,
                "risk_profile": "moderate",
                "grid_spacing_base": 0.025,
                "volatility_threshold": 1.0,
            },
        }

        self.logger.info("🚀 GridManager initialized with separated trading engine")
        self.logger.info("   🎯 Grid Strategy: Single 10-Level Advanced Grid")
        self.logger.info("   💎 Capital Efficiency: 100% (vs 35/65 split)")

    async def handle_force_command(self, command: str) -> Dict:
        """Handle FORCE commands: FORCE ETH 880, FORCE SOL 660, FORCE ADA 660"""
        try:
            parts = command.strip().split()
            if len(parts) != 3 or parts[0].upper() != "FORCE":
                return {
                    "success": False,
                    "error": "Format: FORCE <SYMBOL> <AMOUNT> (e.g., FORCE ETH 880)",
                }

            symbol_short = parts[1].upper()
            try:
                amount = float(parts[2])
            except ValueError:
                return {"success": False, "error": "Invalid amount format"}

            # Map to full trading pairs
            symbol_map = {"ETH": "ETHUSDT", "SOL": "SOLUSDT", "ADA": "ADAUSDT"}
            full_symbol = symbol_map.get(symbol_short)

            if not full_symbol:
                return {
                    "success": False,
                    "error": f"Unsupported symbol: {symbol_short}. Supported: ETH, SOL, ADA",
                }

            # Start grid
            result = await self.start_single_advanced_grid(full_symbol, amount)

            if result["success"]:
                self.logger.info(f"🚀 FORCE COMMAND SUCCESS: {symbol_short} ${amount}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Force command error: {e}")
            return {"success": False, "error": str(e)}

    async def start_single_advanced_grid(
        self, symbol: str, total_capital: float
    ) -> Dict:
        """Start single advanced grid with proper inventory integration"""
        try:
            self.logger.info(f"🚀 Starting SINGLE ADVANCED GRID for {symbol}")
            self.logger.info(
                f"   💰 Total Capital: ${total_capital:,.2f} (100% allocation)"
            )

            # Validate inputs
            if not symbol or total_capital <= 0:
                return {"success": False, "error": "Invalid symbol or capital"}

            # 🔧 FIX 1: Initialize inventory manager if needed
            await self._ensure_inventory_manager(total_capital)

            # 🔧 FIX 2: Add tracking for this specific symbol
            if not await self._add_symbol_to_inventory(symbol, total_capital):
                return {
                    "success": False,
                    "error": f"Failed to set up inventory tracking for {symbol}",
                }

            # Initialize advanced managers for this symbol
            await self._initialize_advanced_managers(symbol)

            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return {"success": False, "error": f"Could not get price for {symbol}"}

            # Execute 50/50 split
            split_result = await self.trading_engine.execute_initial_50_50_split(
                symbol, total_capital, current_price
            )
            if not split_result["success"]:
                return {
                    "success": False,
                    "error": f"50/50 split failed: {split_result['error']}",
                }

            self.logger.info(
                f"✅ 50/50 split completed: {split_result['asset_quantity']:.4f} {symbol.replace('USDT', '')} acquired"
            )

            # Create and configure grid
            grid_config = await self._create_grid_config(
                symbol, total_capital, current_price
            )
            if not grid_config:
                return {
                    "success": False,
                    "error": "Failed to create grid configuration",
                }

            # Execute grid setup
            execution_result = await self.trading_engine.execute_enhanced_grid_setup(
                symbol, grid_config
            )
            if not execution_result.get("success"):
                return {
                    "success": False,
                    "error": execution_result.get("error", "Grid setup failed"),
                }

            # Store grid and update metrics
            self.active_grids[symbol] = grid_config
            self.metrics["grids_started"] += 1

            return {
                "success": True,
                "symbol": symbol,
                "capital": total_capital,
                "orders_placed": execution_result.get("orders_placed", 0),
                "grid_details": execution_result,
                "initial_split": split_result,
                "message": f"Grid successfully started for {symbol}",
            }

        except Exception as e:
            self.logger.error(f"❌ Grid startup error for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    async def _ensure_inventory_manager(self, total_capital: float):
        """🔧 FIX: Ensure inventory manager exists and is properly initialized"""
        try:
            if not self.inventory_manager:
                self.logger.info("Creating new inventory manager...")
                self.inventory_manager = SingleGridInventoryManager(
                    self.binance_client, total_capital
                )

                # Don't auto-initialize positions - let symbols add themselves
                # await self.inventory_manager.initialize_asset_positions()

                # Inject into trading engine
                self.trading_engine.set_managers(
                    self.inventory_manager, self.compound_manager
                )
                self.logger.info(
                    "✅ Inventory manager created and injected into trading engine"
                )
            else:
                # Update total capital if larger
                if total_capital > self.inventory_manager.total_capital:
                    self.inventory_manager.total_capital = total_capital
                    self.logger.info(
                        f"📊 Updated inventory manager capital to ${total_capital:,.2f}"
                    )

        except Exception as e:
            self.logger.error(f"❌ Inventory manager setup error: {e}")
            raise

    async def _add_symbol_to_inventory(self, symbol: str, total_capital: float) -> bool:
        """🔧 FIX: Add symbol tracking to inventory manager"""
        try:
            if not self.inventory_manager:
                self.logger.error(f"❌ Cannot add {symbol} - no inventory manager")
                return False

            # Add tracking for this symbol
            success = await self.inventory_manager.add_symbol_tracking(
                symbol, total_capital
            )

            if success:
                self.logger.info(f"✅ Added inventory tracking for {symbol}")
            else:
                self.logger.error(f"❌ Failed to add inventory tracking for {symbol}")

            return success

        except Exception as e:
            self.logger.error(f"❌ Error adding {symbol} to inventory: {e}")
            return False

    async def stop_single_advanced_grid(self, symbol: str) -> Dict:
        """Stop single advanced grid"""
        if symbol not in self.active_grids:
            return {"success": False, "error": "Grid not found"}

        try:
            self.logger.info(f"🛑 Stopping grid for {symbol}")

            grid_config = self.active_grids[symbol]

            # Cancel all orders
            cancelled_orders = await self.trading_engine.cancel_all_orders(
                symbol, grid_config
            )

            # Cleanup managers
            self.volatility_managers.pop(symbol, None)
            self.auto_reset_managers.pop(symbol, None)

            # Remove from active grids
            del self.active_grids[symbol]
            self.metrics["grids_stopped"] += 1

            self.logger.info(
                f"✅ Grid stopped for {symbol}, cancelled {cancelled_orders} orders"
            )

            return {
                "success": True,
                "symbol": symbol,
                "cancelled_orders": cancelled_orders,
                "final_performance_grade": "Complete",
            }

        except Exception as e:
            self.logger.error(f"❌ Grid stop error for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    async def monitor_and_update_grids(self):
        """Monitor and update all active grids"""
        try:
            if not self.active_grids:
                return

            for symbol in list(self.active_grids.keys()):
                try:
                    grid_config = self.active_grids[symbol]

                    # 🔧 FIX: Ensure inventory tracking exists before monitoring
                    if (
                        self.inventory_manager
                        and not self.inventory_manager.has_tracking(symbol)
                    ):
                        self.logger.warning(
                            f"⚠️ {symbol} missing inventory tracking - attempting to add"
                        )
                        await self.inventory_manager.add_symbol_tracking(
                            symbol, grid_config.total_capital
                        )

                    # Check and replace filled orders
                    await self.trading_engine.check_and_replace_filled_orders(
                        symbol, grid_config
                    )

                    # Update advanced features periodically
                    await self._update_advanced_features(symbol)

                except Exception as e:
                    self.logger.error(f"❌ Error monitoring {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"❌ Grid monitoring error: {e}")

    async def _initialize_advanced_managers(self, symbol: str):
        """Initialize advanced managers for symbol"""
        try:
            # Volatility manager
            if symbol not in self.volatility_managers:
                self.volatility_managers[symbol] = VolatilityBasedRiskManager(
                    self.binance_client, symbol
                )
                self.logger.info(f"✅ VolatilityRiskManager initialized for {symbol}")

            # Auto-reset manager
            if symbol not in self.auto_reset_managers:
                self.auto_reset_managers[symbol] = SmartGridAutoReset(
                    symbol, self.client_id
                )
                self.logger.info(f"✅ SmartGridAutoReset initialized for {symbol}")

        except Exception as e:
            self.logger.error(f"❌ Advanced managers error for {symbol}: {e}")

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
            self.logger.info(f"📊 Current price for {symbol}: ${price:.6f}")
            return price
        except Exception as e:
            self.logger.error(f"❌ Price fetch error for {symbol}: {e}")
            return None

    async def _create_grid_config(
        self, symbol: str, total_capital: float, current_price: float
    ) -> Optional[GridConfig]:
        """Create optimized grid configuration"""
        try:
            self.logger.info("🧮 Calculating optimal grid for {symbol}")

            asset_config = self.asset_configs.get(
                symbol,
                {
                    "allocation": 1.0,
                    "risk_profile": "moderate",
                    "grid_spacing_base": 0.025,
                    "volatility_threshold": 1.0,
                },
            )

            # Create grid config
            grid_config = GridConfig(symbol, total_capital, asset_config)
            grid_config.center_price = current_price

            # Calculate optimal parameters
            optimal_config = await self._calculate_optimal_parameters(
                symbol, current_price, total_capital, asset_config
            )

            # Apply optimal parameters
            grid_config.base_order_size = optimal_config["base_order_size"]
            grid_config.grid_spacing = optimal_config["grid_spacing"]
            grid_config.compound_multiplier = optimal_config.get(
                "compound_multiplier", 1.0
            )
            grid_config.volatility_regime = optimal_config.get(
                "volatility_regime", "moderate"
            )

            self.logger.info("🔍 Parameters being passed:")
            self.logger.info(f"   grid_config type: {type(grid_config)}")
            self.logger.info(f"   current_price type: {type(current_price)}")
            self.logger.info(f"   optimal_config type: {type(optimal_config)}")

            # Create grid levels
            await self.trading_engine.create_advanced_grid_levels(
                grid_config, current_price, optimal_config
            )

            self.logger.info(f"✅ Grid configuration created for {symbol}")
            self.logger.info(f"   📉 Buy levels: {len(grid_config.buy_levels)}")
            self.logger.info(f"   📈 Sell levels: {len(grid_config.sell_levels)}")

            return grid_config

        except Exception as e:
            self.logger.error(f"❌ Grid config creation error: {e}")
            return None

    async def _calculate_optimal_parameters(
        self,
        symbol: str,
        current_price: float,
        total_capital: float,
        asset_config: Dict,
    ) -> Dict:
        """Calculate optimal grid parameters using all advanced features"""
        try:
            # Base order size
            base_order_size = total_capital / 10

            # Compound optimization
            try:
                compound_order_size = (
                    await self.compound_manager.get_current_order_size(
                        self.client_id, symbol, total_capital
                    )
                )
                compound_multiplier = self.compound_manager.get_current_multiplier()
            except:
                compound_order_size = base_order_size
                compound_multiplier = 1.0

            # Volatility adjustment
            try:
                volatility_params = await self.volatility_managers[
                    symbol
                ].get_risk_adjusted_parameters(
                    compound_order_size, asset_config["grid_spacing_base"]
                )
            except:
                volatility_params = {
                    "adjusted_order_size": compound_order_size,
                    "adjusted_grid_spacing": asset_config["grid_spacing_base"],
                    "regime": "moderate",
                    "order_size_multiplier": 1.0,
                }

            # Market timing
            try:
                market_timing = self.market_timer.get_session_info()
                timing_multiplier = market_timing["trading_intensity"]
            except:
                timing_multiplier = 1.0

            # Calculate final optimized parameters
            optimized_order_size = compound_order_size
            optimized_order_size *= volatility_params["order_size_multiplier"]
            optimized_order_size *= timing_multiplier

            # Apply Kelly Criterion constraint
            try:
                kelly_fraction = await self.compound_manager.calculate_kelly_fraction(
                    self.client_id, symbol
                )
                kelly_max_order = total_capital * kelly_fraction / 5
                if optimized_order_size > kelly_max_order:
                    optimized_order_size = kelly_max_order
                    self.logger.info(
                        f"🎯 Kelly Criterion constraint applied: ${optimized_order_size:.2f}"
                    )
            except:
                pass

            # Safety cap
            max_order = total_capital * 0.25
            optimized_order_size = min(optimized_order_size, max_order)

            optimal_config = {
                "base_order_size": optimized_order_size,
                "grid_spacing": volatility_params["adjusted_grid_spacing"],
                "compound_multiplier": compound_multiplier,
                "volatility_regime": volatility_params["regime"],
                "market_timing_score": timing_multiplier,
                "total_optimization_factor": optimized_order_size / base_order_size,
            }

            self.logger.info(f"✅ Optimal grid calculated for {symbol}:")
            self.logger.info(
                f"   💰 Base order size: ${base_order_size:.2f} → ${optimized_order_size:.2f}"
            )
            self.logger.info(
                f"   🔄 Total optimization: {optimal_config['total_optimization_factor']:.2f}x"
            )
            self.logger.info(f"   🛡️ Volatility regime: {volatility_params['regime']}")
            self.logger.info(f"   ⏰ Market timing: {timing_multiplier:.2f}x")

            return optimal_config

        except Exception as e:
            self.logger.error(f"❌ Parameter calculation error: {e}")
            return {
                "base_order_size": total_capital / 10,
                "grid_spacing": asset_config.get("grid_spacing_base", 0.025),
                "compound_multiplier": 1.0,
                "volatility_regime": "moderate",
                "market_timing_score": 1.0,
                "total_optimization_factor": 1.0,
            }

    async def _update_advanced_features(self, symbol: str):
        """Update advanced features periodically"""
        try:
            # Simple periodic check - every 5 minutes
            if not hasattr(self, "_last_feature_update"):
                self._last_feature_update = {}

            if symbol not in self._last_feature_update:
                self._last_feature_update[symbol] = 0

            if time.time() - self._last_feature_update[symbol] < 300:  # 5 minutes
                return

            self._last_feature_update[symbol] = time.time()

            # Check for auto-reset conditions
            current_price = await self._get_current_price(symbol)
            if current_price and symbol in self.auto_reset_managers:
                grid_config = self.active_grids[symbol]
                should_reset, reason = self.auto_reset_managers[
                    symbol
                ].should_reset_grid(current_price, grid_config.center_price)

                if should_reset:
                    self.logger.info(f"🔄 Auto-reset triggered for {symbol}: {reason}")
                    await self._execute_smart_reset(symbol, current_price)

        except Exception as e:
            self.logger.error(f"❌ Advanced features update error: {e}")

    async def _execute_smart_reset(self, symbol: str, new_center_price: float):
        """Execute smart grid reset"""
        try:
            grid_config = self.active_grids[symbol]

            # Cancel existing orders
            await self.trading_engine.cancel_all_orders(symbol, grid_config)

            # Update center price and recalculate
            grid_config.center_price = new_center_price
            asset_config = self.asset_configs.get(
                symbol,
                {
                    "grid_spacing_base": 0.025,
                    "risk_profile": "moderate",
                },
            )

            optimal_config = await self._calculate_optimal_parameters(
                symbol, new_center_price, grid_config.total_capital, asset_config
            )

            # Apply new parameters
            grid_config.base_order_size = optimal_config["base_order_size"]
            grid_config.grid_spacing = optimal_config["grid_spacing"]

            # Create and execute new grid
            await self.trading_engine.create_advanced_grid_levels(
                grid_config, new_center_price, optimal_config
            )
            await self.trading_engine.execute_enhanced_grid_setup(symbol, grid_config)

            self.logger.info(
                f"✅ Smart reset completed for {symbol} at ${new_center_price:.6f}"
            )
            self.metrics["optimizations"] += 1

        except Exception as e:
            self.logger.error(f"❌ Smart reset error for {symbol}: {e}")

    def get_all_active_grids(self) -> Dict:
        """Get status of all active grids"""
        try:
            if not self.active_grids:
                return {
                    "total_active_grids": 0,
                    "trading_mode": "Single Advanced Grid",
                    "grids": {},
                }

            base_status = self.monitoring.get_all_active_grids_status(self.active_grids)

            # Add trading engine statistics
            for symbol in self.active_grids:
                if symbol in base_status.get("grids", {}):
                    trading_stats = self.trading_engine.get_trading_stats(
                        symbol, self.active_grids[symbol]
                    )
                    base_status["grids"][symbol].update(trading_stats)

            return base_status

        except Exception as e:
            self.logger.error(f"❌ Get all grids error: {e}")
            return {
                "total_active_grids": 0,
                "trading_mode": "Single Advanced Grid",
                "grids": {},
                "error": str(e),
            }

    def get_single_grid_status(self, symbol: str) -> Dict:
        """Get status for specific grid"""
        if symbol not in self.active_grids:
            return {"active": False, "error": "Grid not found"}

        try:
            grid_config = self.active_grids[symbol]
            status = self.monitoring.get_single_grid_status(symbol, grid_config)

            # Add trading engine stats
            trading_stats = self.trading_engine.get_trading_stats(symbol, grid_config)
            status.update(trading_stats)

            # Add inventory status if available
            if self.inventory_manager and self.inventory_manager.has_tracking(symbol):
                inventory_status = self.inventory_manager.get_inventory_status(symbol)
                status["inventory"] = inventory_status

            return status

        except Exception as e:
            self.logger.error(f"❌ Status error for {symbol}: {e}")
            return {"active": False, "error": str(e)}

    async def get_unified_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        try:
            base_report = self.monitoring.get_unified_performance_report(
                self.active_grids
            )

            # Add trading engine metrics
            trading_summary = {
                "total_orders_placed": 0,
                "total_orders_filled": 0,
                "avg_grid_utilization": 0,
            }

            for symbol in self.active_grids:
                trading_stats = self.trading_engine.get_trading_stats(
                    symbol, self.active_grids[symbol]
                )
                trading_summary["total_orders_placed"] += trading_stats.get(
                    "total_orders_active", 0
                )
                trading_summary["total_orders_filled"] += trading_stats.get(
                    "total_orders_filled", 0
                )

            if self.active_grids:
                trading_summary["avg_grid_utilization"] = (
                    trading_summary["total_orders_filled"]
                    / max(trading_summary["total_orders_placed"], 1)
                    * 100
                )

            base_report["trading_summary"] = trading_summary
            base_report["metrics"] = self.metrics

            # Add inventory health report
            if self.inventory_manager:
                base_report["inventory_health"] = (
                    self.inventory_manager.validate_inventory_health()
                )

            return base_report

        except Exception as e:
            self.logger.error(f"❌ Performance report error: {e}")
            return {
                "report_type": "Single Advanced Grid Performance Report",
                "error": str(e),
                "timestamp": time.time(),
            }
