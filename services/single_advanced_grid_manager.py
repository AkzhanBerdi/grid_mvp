# services/single_advanced_grid_manager.py
"""
Single Advanced Grid Manager - Refactored with Separated Trading Engine
=======================================================================

Unified Advanced Grid Manager that eliminates dual-grid complexity
while maximizing ALL advanced features in one optimized system.

Now uses GridTradingEngine for all trading operations to improve
code organization and separation of concerns.

Replaces: EnhancedDualScaleGridManager
Benefits: 100% capital efficiency, simplified management, maximum feature utilization
"""

import logging
import time
from typing import Dict, Optional

from binance.client import Client

from models.single_advanced_grid_config import SingleAdvancedGridConfig
from repositories.client_repository import ClientRepository
from repositories.trade_repository import TradeRepository
from services.advanced_trading_features import (
    IntelligentMarketTimer,
    PrecisionOrderHandler,
    SmartGridAutoReset,
    VolatilityBasedRiskManager,
)
from services.enhanced_fifo_service import EnhancedFIFOService
from services.grid_monitoring_service import GridMonitoringService
from services.grid_trading_engine import (
    GridTradingEngine,
)  # NEW: Separated trading engine
from services.grid_utility_service import GridUtilityService
from services.inventory_manager import SingleGridInventoryManager
from services.market_analysis import MarketAnalysisService
from services.order_replacement_diagnosis_fix import OrderReplacementDiagnostics
from utils.fifo_telegram_monitor import FIFOMonitoringService

# Replace the entire compound manager section with this:
try:
    from services.compound_interest_manager import CompoundInterestManager

    COMPOUND_AVAILABLE = True

    def create_advanced_compound_manager(client_id):
        """Create advanced compound manager with FIFO integration"""
        fifo_service = EnhancedFIFOService()
        return CompoundInterestManager(fifo_service)

except ImportError:
    COMPOUND_AVAILABLE = False

    # Simple fallback
    class CompoundInterestManager:
        def __init__(self, fifo_service):
            self.fifo_service = fifo_service

        async def get_current_order_size(self, client_id, symbol, base_capital):
            return base_capital / 10


# Import other services you have available
try:
    from services.market_analysis import MarketAnalysisService

    MARKET_ANALYSIS_AVAILABLE = True
except ImportError:
    MARKET_ANALYSIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Market analysis service not available")


class SingleAdvancedGridManager:
    """
    Single Advanced Grid Manager - Refactored with Trading Engine Separation
    """

    def __init__(self, binance_client: Client, client_id: int):
        self.binance_client = binance_client
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        self.inventory_manager = None  # Will be initialized with capital
        self.volatility_managers: Dict[str, VolatilityBasedRiskManager] = {}
        self.auto_reset_managers: Dict[str, SmartGridAutoReset] = {}

        # Core repositories
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()

        # 🔥 NEW: Separated trading engine
        self.trading_engine = GridTradingEngine(binance_client, client_id)
        self.utility = GridUtilityService(self.binance_client)
        self.monitoring = GridMonitoringService(self.client_id, self.binance_client)
        self.order_diagnostics = OrderReplacementDiagnostics(self, self.trading_engine)

        # Services
        self.logger.info("✅ Working notification integration initialized")
        self.fifo_service = EnhancedFIFOService()
        if MARKET_ANALYSIS_AVAILABLE:
            self.market_analysis = MarketAnalysisService(binance_client)

        # Active grids tracking
        self.active_grids: Dict[str, SingleAdvancedGridConfig] = {}

        # Performance metrics
        self.metrics = {
            "grids_started": 0,
            "grids_stopped": 0,
            "total_trades": 0,
            "grid_optimizations": 0,
            "compound_events": 0,
            "volatility_adjustments": 0,
            "auto_resets": 0,
            "precision_orders": 0,
            "kelly_adjustments": 0,
        }

        # Initialize compound manager
        if COMPOUND_AVAILABLE:
            self.compound_manager = create_advanced_compound_manager(client_id)
            self.logger.info(
                "✅ Advanced CompoundInterestManager with Kelly Criterion activated"
            )
        else:
            self.compound_manager = CompoundInterestManager(EnhancedFIFOService())
            self.logger.warning("⚠️ Using basic compound manager fallback")

        # Initialize advanced feature managers
        self.market_timer = IntelligentMarketTimer()
        self.precision_handler = PrecisionOrderHandler(binance_client)

        # Asset configurations for $2400 allocation
        self.asset_configs = {
            "ETHUSDT": {
                "allocation": 960,  # 40% of $2400
                "risk_profile": "conservative",
                "grid_spacing_base": 0.025,  # 2.5%
                "volatility_threshold": 0.8,
                "compound_aggressiveness": 0.6,
                "max_order_size_multiplier": 2.5,
            },
            "SOLUSDT": {
                "allocation": 840,  # 35% of $2400
                "risk_profile": "moderate-aggressive",
                "grid_spacing_base": 0.03,  # 3.0%
                "volatility_threshold": 1.2,
                "compound_aggressiveness": 0.8,
                "max_order_size_multiplier": 3.0,
            },
            "ADAUSDT": {
                "allocation": 600,  # 25% of $2400
                "risk_profile": "moderate",
                "grid_spacing_base": 0.025,  # 2.5%
                "volatility_threshold": 1.0,
                "compound_aggressiveness": 0.7,
                "max_order_size_multiplier": 2.8,
            },
        }

        # Add FIFO notification manager
        self.notification_manager = FIFOMonitoringService()
        self.logger.info("✅ FIFO Notification Manager initialized")

        self.logger.info(
            "🚀 SingleAdvancedGridManager initialized with separated trading engine"
        )
        self.logger.info("   💰 Compound Management: UNIFIED")
        self.logger.info("   ⏰ Intelligent Market Timing: UNIFIED")
        self.logger.info("   🛡️ Volatility Risk Management: UNIFIED")
        self.logger.info("   🔄 Smart Auto-Reset: UNIFIED")
        self.logger.info("   🎯 Precision Order Handling: UNIFIED")
        self.logger.info("   📊 Advanced Performance Monitoring: UNIFIED")
        self.logger.info("   🎯 Grid Strategy: Single 10-Level Advanced Grid")
        self.logger.info("   💎 Capital Efficiency: 100% (vs 35/65 split)")

    async def diagnose_order_issues(self, symbol: str):
        """Run comprehensive order replacement diagnostics"""
        try:
            self.logger.info(f"🔍 Running order replacement diagnostics for {symbol}")

            # Run the diagnostic
            diagnosis = await self.order_diagnostics.diagnose_order_replacement_issues(
                symbol
            )

            # Log the results
            self.logger.info("📊 DIAGNOSTIC RESULTS:")
            self.logger.info(f"   Current State: {diagnosis.get('current_state', {})}")

            # Log issues found
            issues = diagnosis.get("issues_found", [])
            if issues:
                self.logger.error("❌ ISSUES FOUND:")
                for issue in issues:
                    self.logger.error(
                        f"   - {issue['issue']}: {issue['details']} (severity: {issue['severity']})"
                    )

            # Log inventory issues
            inventory_issues = diagnosis.get("inventory_issues", [])
            if inventory_issues:
                self.logger.error("🏭 INVENTORY ISSUES:")
                for issue in inventory_issues:
                    self.logger.error(
                        f"   - {issue['type']}: {issue.get('reason', issue.get('error', 'Unknown'))}"
                    )

            # Log method issues
            method_issues = diagnosis.get("method_issues", [])
            if method_issues:
                self.logger.error("🔧 METHOD ISSUES:")
                for issue in method_issues:
                    self.logger.error(
                        f"   - {issue['type']}: {issue.get('method', issue.get('error', 'Unknown'))}"
                    )

            # Log recommendations
            recommendations = diagnosis.get("recommendations", [])
            if recommendations:
                self.logger.info("💡 RECOMMENDATIONS:")
                for rec in recommendations:
                    self.logger.info(f"   {rec}")

            return diagnosis

        except Exception as e:
            self.logger.error(f"❌ Error running diagnostics: {e}")
            return {"error": str(e)}

    async def start_single_advanced_grid(
        self, symbol: str, total_capital: float
    ) -> Dict:
        """
        ENHANCED: Pure USDT allocation with proper 50/50 split before grid initialization
        Now uses separated GridTradingEngine for all trading operations
        """
        try:
            self.logger.info(f"🚀 Starting SINGLE ADVANCED GRID for {symbol}")
            self.logger.info(
                f"   💰 Total Capital: ${total_capital:,.2f} (100% allocation)"
            )

            # STEP 1: Validate inputs
            if not symbol:
                return {"success": False, "error": "Symbol is required"}
            if total_capital <= 0:
                return {"success": False, "error": "Capital must be positive"}

            # STEP 2: Check asset_configs
            self.logger.info(f"🔍 Checking asset_configs for {symbol}")
            if not hasattr(self, "asset_configs") or self.asset_configs is None:
                self.logger.error("❌ asset_configs not found")
                return {"success": False, "error": "Asset configs not initialized"}

            if symbol not in self.asset_configs:
                self.logger.error(f"❌ {symbol} not in asset_configs")
                # CREATE DEFAULT CONFIG
                default_config = {
                    "allocation": total_capital,
                    "risk_profile": "moderate",
                    "grid_spacing_base": 0.025,  # 2.5%
                    "volatility_threshold": 1.0,
                    "compound_aggressiveness": 0.7,
                    "max_order_size_multiplier": 2.5,
                }
                self.asset_configs[symbol] = default_config
                self.logger.info(f"✅ Created default config for {symbol}")

            # STEP 3: Initialize managers safely
            try:
                if (
                    not hasattr(self, "inventory_manager")
                    or self.inventory_manager is None
                ):
                    self.logger.info("Creating new inventory manager...")
                    self.inventory_manager = SingleGridInventoryManager(
                        self.binance_client, total_capital
                    )
                    await self.inventory_manager.initialize_asset_positions()

                    # 🔥 NEW: Inject managers into trading engine
                    self.trading_engine.set_managers(
                        self.inventory_manager, self.compound_manager
                    )
                    self.logger.info(
                        "✅ Inventory manager created and injected into trading engine"
                    )
            except Exception as inv_error:
                self.logger.error(f"❌ Inventory manager error: {inv_error}")
                self.inventory_manager = None

            try:
                await self._safe_initialize_advanced_managers(symbol)
            except Exception as mgr_error:
                self.logger.error(f"❌ Advanced managers error: {mgr_error}")

            # STEP 4: Get current price safely
            self.logger.info(f"🔍 Getting current price for {symbol}")
            try:
                current_price = await self._get_current_price_with_precision(symbol)
                if current_price is None or current_price <= 0:
                    return {
                        "success": False,
                        "error": f"Could not get valid price for {symbol}",
                    }
                self.logger.info(f"📊 Current price for {symbol}: ${current_price:.6f}")
            except Exception as price_error:
                self.logger.error(f"❌ Price error: {price_error}")
                return {
                    "success": False,
                    "error": f"Price retrieval failed: {price_error}",
                }

            # STEP 5: 🔥 NEW - Execute 50/50 split using trading engine
            self.logger.info("💰 Executing 50/50 split for pure USDT allocation")
            try:
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
            except Exception as split_error:
                self.logger.error(f"❌ 50/50 split error: {split_error}")
                return {
                    "success": False,
                    "error": f"Initial asset purchase failed: {split_error}",
                }

            # STEP 6: Create grid config
            self.logger.info("🔧 Creating grid configuration")
            try:
                grid_config = await self._safe_create_grid_config(
                    symbol, total_capital, current_price
                )
                if grid_config is None:
                    return {
                        "success": False,
                        "error": "Failed to create grid configuration",
                    }
            except Exception as config_error:
                self.logger.error(f"❌ Grid config error: {config_error}")
                return {
                    "success": False,
                    "error": f"Grid configuration failed: {config_error}",
                }

            # STEP 7: 🔥 NEW - Execute grid setup using trading engine
            self.logger.info("🎯 Executing grid setup")
            try:
                execution_result = (
                    await self.trading_engine.execute_enhanced_grid_setup(
                        symbol, grid_config
                    )
                )
                if execution_result is None:
                    return {"success": False, "error": "Grid setup returned None"}
                if not execution_result.get("success", False):
                    return {
                        "success": False,
                        "error": execution_result.get("error", "Grid setup failed"),
                        "details": execution_result,
                    }
            except Exception as exec_error:
                self.logger.error(f"❌ Grid setup error: {exec_error}")
                return {"success": False, "error": f"Grid setup failed: {exec_error}"}

            # STEP 8: Store grid and return success
            try:
                self.active_grids[symbol] = grid_config
                self.metrics["grids_started"] += 1

                return {
                    "success": True,
                    "symbol": symbol,
                    "capital": total_capital,
                    "orders_placed": execution_result.get("orders_placed", 0),
                    "grid_details": execution_result,
                    "initial_split": split_result,
                    "message": f"Grid successfully started for {symbol} with 50/50 allocation",
                }
            except Exception as store_error:
                self.logger.error(f"❌ Grid storage error: {store_error}")
                return {
                    "success": False,
                    "error": f"Failed to store grid: {store_error}",
                }

        except Exception as e:
            self.logger.error(
                f"❌ Single advanced grid startup error for {symbol}: {e}"
            )
            import traceback

            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    async def _safe_create_grid_config(
        self, symbol: str, total_capital: float, current_price: float
    ):
        """Safely create grid configuration"""
        try:
            asset_config = self.asset_configs.get(symbol, {})

            # Create basic grid config
            grid_config = SingleAdvancedGridConfig(symbol, total_capital, asset_config)
            grid_config.center_price = current_price

            # Calculate optimal grid
            optimal_config = await self._calculate_optimal_grid(
                symbol, current_price, total_capital, asset_config
            )

            # Apply optimal parameters
            await self._apply_optimal_parameters(
                grid_config, optimal_config, current_price
            )
            self.logger.info("🔍 Parameters being passed:")
            self.logger.info(f"   grid_config type: {type(grid_config)}")
            self.logger.info(f"   current_price type: {type(current_price)}")
            self.logger.info(f"   optimal_config type: {type(optimal_config)}")
            # 🔥 NEW - Create grid levels using trading engine
            grid_levels = await self.trading_engine.create_advanced_grid_levels(
                grid_config, current_price, optimal_config
            )

            self.logger.info(f"✅ Grid configuration created for {symbol}")
            self.logger.info(f"   📉 Buy levels: {len(grid_levels['buy_levels'])}")
            self.logger.info(f"   📈 Sell levels: {len(grid_levels['sell_levels'])}")

            return grid_config

        except Exception as e:
            self.logger.error(f"❌ Grid config creation error: {e}")
            return None

    async def _safe_initialize_advanced_managers(self, symbol: str):
        """Safely initialize advanced managers with error handling"""
        try:
            # Initialize volatility manager
            if not hasattr(self, "volatility_managers"):
                self.volatility_managers = {}

            if symbol not in self.volatility_managers:
                self.volatility_managers[symbol] = VolatilityBasedRiskManager(
                    self.binance_client, symbol
                )
                self.logger.info(f"✅ VolatilityRiskManager initialized for {symbol}")

            # Initialize auto-reset manager
            if not hasattr(self, "auto_reset_managers"):
                self.auto_reset_managers = {}

            if symbol not in self.auto_reset_managers:
                self.auto_reset_managers[symbol] = SmartGridAutoReset(
                    symbol, self.client_id
                )
                self.logger.info(f"✅ SmartGridAutoReset initialized for {symbol}")

            self.logger.info(f"🔧 Advanced managers initialized for {symbol}")

        except Exception as e:
            self.logger.error(f"❌ Advanced managers initialization error: {e}")
            # Don't fail the entire grid for this

    async def handle_force_command(self, command: str) -> Dict:
        """
        Handle simplified force commands for single advanced grids

        Commands:
        - FORCE ETH 880  -> Single 10-level advanced ETH grid
        - FORCE SOL 660  -> Single 10-level advanced SOL grid
        - FORCE ADA 660  -> Single 10-level advanced ADA grid
        """
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

            # Map short symbols to full trading pairs
            symbol_map = {"ETH": "ETHUSDT", "SOL": "SOLUSDT", "ADA": "ADAUSDT"}

            full_symbol = symbol_map.get(symbol_short)
            if not full_symbol:
                return {
                    "success": False,
                    "error": f"Unsupported symbol: {symbol_short}. Supported: {list(symbol_map.keys())}",
                }

            # Validate amount against recommended allocation
            recommended = self.asset_configs[full_symbol]["allocation"]
            if abs(amount - recommended) > recommended * 0.5:  # 50% tolerance
                self.logger.warning(
                    f"⚠️ Amount ${amount} differs from recommended ${recommended} for {symbol_short}"
                )

            # Start single advanced grid
            result = await self.start_single_advanced_grid(full_symbol, amount)

            if result["success"]:
                self.logger.info(f"🚀 FORCE COMMAND SUCCESS: {symbol_short} ${amount}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Force command error: {e}")
            return {"success": False, "error": str(e)}

    async def stop_single_advanced_grid(self, symbol: str) -> Dict:
        """Stop single advanced grid and generate final report"""
        if symbol not in self.active_grids:
            return {"success": False, "error": "Grid not found"}

        try:
            self.logger.info(f"🛑 Stopping single advanced grid for {symbol}")

            grid_config = self.active_grids[symbol]

            # 🔥 NEW - Use trading engine to cancel orders
            cancelled_orders = await self.trading_engine.cancel_all_orders(
                symbol, grid_config
            )

            # Generate final performance report
            try:
                final_report = await self.get_unified_performance_report()
                performance_grade = final_report.get("performance_grade", "N/A")
            except:
                performance_grade = "N/A"

            # Cleanup managers
            if symbol in self.volatility_managers:
                del self.volatility_managers[symbol]
            if symbol in self.auto_reset_managers:
                del self.auto_reset_managers[symbol]

            # Remove from active grids
            del self.active_grids[symbol]
            self.metrics["grids_stopped"] += 1

            result = {
                "success": True,
                "symbol": symbol,
                "strategy": "Single Advanced Grid",
                "cancelled_orders": cancelled_orders,
                "final_performance_grade": performance_grade,
                "final_metrics": self.metrics.copy(),
                "system_summary": "Single Advanced Grid System with 100% feature utilization",
            }

            self.logger.info(f"✅ Single advanced grid stopped for {symbol}")
            self.logger.info(f"   📊 Orders cancelled: {cancelled_orders}")
            self.logger.info(f"   🏆 Performance grade: {performance_grade}")

            return result

        except Exception as e:
            self.logger.error(f"❌ Grid stop error for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    async def monitor_and_update_grids(self):
        """Enhanced monitoring with automatic diagnostics"""
        try:
            for symbol in list(self.active_grids.keys()):
                try:
                    grid_config = self.active_grids[symbol]

                    # 🔥 CRITICAL FIX: Add the missing order monitoring call
                    self.logger.debug(f"🔍 Checking filled orders for {symbol}")
                    await self.trading_engine.check_and_replace_filled_orders(
                        symbol, grid_config
                    )

                    # Count orders after monitoring (existing code)
                    active_orders = sum(
                        1
                        for level in grid_config.buy_levels + grid_config.sell_levels
                        if level.get("order_id") and not level.get("filled")
                    )

                    # Log order status
                    self.logger.info(
                        f"📊 {symbol}: {active_orders} active orders after monitoring"
                    )

                    # If order count is low, run diagnostic (existing code)
                    if active_orders < 8:  # Should have ~10 orders
                        self.logger.warning(
                            f"⚠️ Low order count for {symbol}: {active_orders}"
                        )

                        # Run diagnostic (keep your existing diagnostic code if you have it)
                        if hasattr(self, "diagnostic_service"):
                            diagnosis = await self.diagnostic_service.diagnose_order_replacement_issues(
                                symbol
                            )

                            if diagnosis.get("issues_found"):
                                self.logger.error(
                                    f"🚨 Diagnostic found issues for {symbol}:"
                                )
                                for issue in diagnosis["issues_found"]:
                                    self.logger.error(
                                        f"   • {issue['issue']}: {issue['details']}"
                                    )

                    # Update other systems (keep your existing update calls if you have them)
                    try:
                        await self._update_compound_management(symbol)
                    except:
                        pass  # Don't break if this method doesn't exist

                    try:
                        await self._check_volatility_adjustments(symbol)
                    except:
                        pass  # Don't break if this method doesn't exist

                    try:
                        await self._check_smart_auto_reset(symbol)
                    except:
                        pass  # Don't break if this method doesn't exist

                    try:
                        await self._update_performance_tracking(symbol, grid_config)
                    except:
                        pass  # Don't break if this method doesn't exist

                except Exception as e:
                    self.logger.error(f"❌ Monitoring error for {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"❌ Grid monitoring system error: {e}")

    async def _get_current_price_with_precision(self, symbol: str) -> Optional[float]:
        """Get current price with precision handling"""
        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker["price"])
            self.logger.info(f"📊 Current price for {symbol}: ${current_price:.6f}")
            return current_price
        except Exception as e:
            self.logger.error(f"❌ Price fetch error for {symbol}: {e}")
            return None

    async def _calculate_optimal_grid(
        self,
        symbol: str,
        current_price: float,
        total_capital: float,
        asset_config: Dict,
    ) -> Dict:
        """
        Calculate single optimized grid with ALL advanced features integrated
        This is the core optimization engine that replaces dual-grid complexity
        """
        try:
            self.logger.info(f"🧮 Calculating optimal grid for {symbol}")

            # 1. Compound Interest Optimization (gets 100% of capital)
            try:
                compound_order_size = (
                    await self.compound_manager.get_current_order_size(
                        self.client_id, symbol, total_capital
                    )
                )
            except TypeError:
                try:
                    compound_order_size = self.compound_manager.get_current_order_size()
                except:
                    compound_order_size = (
                        total_capital / 10
                    )  # Simple division for 10 levels

            try:
                compound_multiplier = self.compound_manager.get_current_multiplier()
            except:
                compound_multiplier = 1.0

            compound_active = compound_multiplier > 1.0

            # 2. Volatility-Based Risk Adjustment
            try:
                volatility_params = await self.volatility_managers[
                    symbol
                ].get_risk_adjusted_parameters(
                    compound_order_size, asset_config["grid_spacing_base"]
                )
            except:
                # Fallback volatility parameters
                volatility_params = {
                    "adjusted_order_size": compound_order_size,
                    "adjusted_grid_spacing": asset_config["grid_spacing_base"],
                    "regime": "moderate",
                    "order_size_multiplier": 1.0,
                }

            # 3. Market Timing Optimization
            try:
                market_timing = self.market_timer.get_session_info()
                timing_multiplier = market_timing["trading_intensity"]
            except:
                timing_multiplier = 1.0

            # 4. Kelly Criterion Position Sizing
            try:
                kelly_fraction = await self.compound_manager.calculate_kelly_fraction(
                    self.client_id, symbol
                )
            except:
                kelly_fraction = 0.1  # Conservative 10%

            kelly_active = kelly_fraction > 0.05

            # 5. Unified Optimization Calculation
            base_order_size = total_capital / 10
            optimized_order_size = compound_order_size
            optimized_order_size *= volatility_params["order_size_multiplier"]
            optimized_order_size *= timing_multiplier

            # Apply Kelly Criterion constraint
            kelly_max_order = total_capital * kelly_fraction / 5
            if optimized_order_size > kelly_max_order and kelly_active:
                optimized_order_size = kelly_max_order
                self.logger.info(
                    f"🎯 Kelly Criterion constraint applied: ${optimized_order_size:.2f}"
                )

            # Safety caps
            max_order = total_capital * 0.25
            optimized_order_size = min(optimized_order_size, max_order)

            optimal_config = {
                "base_order_size": optimized_order_size,
                "grid_spacing": volatility_params["adjusted_grid_spacing"],
                "compound_multiplier": compound_multiplier,
                "compound_active": compound_active,
                "volatility_regime": volatility_params["regime"],
                "volatility_adjustment_factor": volatility_params[
                    "order_size_multiplier"
                ],
                "market_timing_score": timing_multiplier,
                "kelly_fraction": kelly_fraction,
                "kelly_active": kelly_active,
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
            self.logger.error(f"❌ Grid optimization error for {symbol}: {e}")
            # Return safe fallback configuration
            return {
                "base_order_size": total_capital / 10,
                "grid_spacing": asset_config.get("grid_spacing_base", 0.025),
                "compound_multiplier": 1.0,
                "compound_active": False,
                "volatility_regime": "moderate",
                "volatility_adjustment_factor": 1.0,
                "market_timing_score": 1.0,
                "kelly_fraction": 0.1,
                "kelly_active": False,
                "total_optimization_factor": 1.0,
            }

    async def _apply_optimal_parameters(
        self,
        grid_config: SingleAdvancedGridConfig,
        optimal_config: Dict,
        current_price: float,
    ):
        """Apply optimal parameters to grid configuration"""
        try:
            grid_config.base_order_size = optimal_config["base_order_size"]
            grid_config.grid_spacing = optimal_config["grid_spacing"]
            grid_config.center_price = current_price
            grid_config.compound_multiplier = optimal_config["compound_multiplier"]
            grid_config.volatility_regime = optimal_config["volatility_regime"]
            grid_config.kelly_fraction = optimal_config["kelly_fraction"]
            self.logger.info(f"🔧 Parameters applied to {grid_config.symbol}")
        except Exception as e:
            self.logger.error(f"❌ Parameter application error: {e}")
            raise

    async def _update_compound_management(self, symbol: str):
        """Update compound management with latest performance"""
        try:
            # Get latest FIFO performance
            fifo_performance = self.fifo_service.calculate_fifo_performance(
                self.client_id
            )

            # Update compound manager
            compound_changed = await self.compound_manager.update_from_fifo_profit(
                fifo_performance["total_profit"]
            )

            if compound_changed:
                self.metrics["compound_events"] += 1
                compound_status = self.compound_manager.get_compound_status()
                self.logger.info(
                    f"💰 Compound update for {symbol}: {compound_status['current_multiplier']:.2f}x"
                )

        except Exception as e:
            self.logger.error(f"❌ Compound management update error: {e}")

    async def _check_volatility_adjustments(self, symbol: str):
        """Check and apply volatility-based adjustments"""
        try:
            if symbol not in self.volatility_managers:
                return

            volatility_manager = self.volatility_managers[symbol]
            grid_config = self.active_grids[symbol]

            # Get current volatility adjustment
            base_order_size = await self.compound_manager.get_current_order_size(
                self.client_id, symbol, grid_config.total_capital
            )
            current_spacing = grid_config.grid_spacing

            volatility_adjustment = (
                await volatility_manager.get_risk_adjusted_parameters(
                    base_order_size, current_spacing
                )
            )

            # Check if significant adjustment is needed
            spacing_change = abs(
                volatility_adjustment["adjusted_grid_spacing"] - current_spacing
            )

            if spacing_change > 0.005:  # 0.5% threshold
                self.logger.info(
                    f"🛡️ Volatility adjustment for {symbol}: {volatility_adjustment['regime']} regime"
                )

                # Apply adjustment
                grid_config.grid_spacing = volatility_adjustment[
                    "adjusted_grid_spacing"
                ]
                grid_config.volatility_regime = volatility_adjustment["regime"]

                self.metrics["volatility_adjustments"] += 1

        except Exception as e:
            self.logger.error(f"❌ Volatility adjustment check error: {e}")

    async def _check_smart_auto_reset(self, symbol: str):
        """Check for smart auto-reset conditions"""
        try:
            if symbol not in self.auto_reset_managers:
                return

            grid_config = self.active_grids[symbol]
            auto_reset_manager = self.auto_reset_managers[symbol]

            # Get current price
            current_price = await self._get_current_price_with_precision(symbol)
            if not current_price:
                return

            # Check if reset is needed
            should_reset, reason = auto_reset_manager.should_reset_grid(
                current_price, grid_config.center_price
            )

            if should_reset:
                self.logger.info(
                    f"🔄 Smart auto-reset triggered for {symbol}: {reason}"
                )

                # Execute smart reset
                await self._execute_smart_reset(symbol, current_price)

                self.metrics["auto_resets"] += 1

        except Exception as e:
            self.logger.error(f"❌ Smart auto-reset check error: {e}")

    async def _execute_smart_reset(self, symbol: str, new_center_price: float):
        """Execute smart grid reset using trading engine"""
        try:
            grid_config = self.active_grids[symbol]

            # 🔥 NEW - Use trading engine to cancel orders
            await self.trading_engine.cancel_all_orders(symbol, grid_config)

            # Update center price
            grid_config.center_price = new_center_price

            # Recalculate optimal grid
            asset_config = self.asset_configs[symbol]
            optimal_config = await self._calculate_optimal_grid(
                symbol, new_center_price, grid_config.total_capital, asset_config
            )

            # Apply new parameters
            await self._apply_optimal_parameters(
                grid_config, optimal_config, new_center_price
            )

            # 🔥 NEW - Create new grid levels using trading engine
            await self.trading_engine.create_advanced_grid_levels(
                symbol, new_center_price, grid_config, optimal_config
            )

            # 🔥 NEW - Execute new grid setup using trading engine
            await self.trading_engine.execute_enhanced_grid_setup(symbol, grid_config)

            self.logger.info(
                f"✅ Smart reset completed for {symbol} at ${new_center_price:.6f}"
            )

        except Exception as e:
            self.logger.error(f"❌ Smart reset execution error for {symbol}: {e}")

    async def _update_performance_tracking(
        self, symbol: str, grid_config: SingleAdvancedGridConfig
    ):
        """Update advanced performance tracking"""
        try:
            # Update performance metrics periodically
            if not hasattr(self, "_last_performance_update"):
                self._last_performance_update = {}

            if symbol not in self._last_performance_update:
                self._last_performance_update[symbol] = 0

            if time.time() - self._last_performance_update[symbol] < 3600:  # 1 hour
                return

            self._last_performance_update[symbol] = time.time()

            # Generate performance update
            grid_performance = self.monitoring.calculate_grid_performance(
                symbol, grid_config
            )

            self.logger.info(f"📊 Performance update for {symbol}:")
            self.logger.info(
                f"   🎯 Grid efficiency: {grid_performance['grid_efficiency']:.1f}%"
            )
            self.logger.info(
                f"   💰 Realized PnL: ${grid_performance['realized_pnl']:.2f}"
            )
            self.logger.info(
                f"   📈 Features score: {grid_performance['advanced_features_score']:.1f}%"
            )

        except Exception as e:
            self.logger.error(f"❌ Performance tracking update error: {e}")

    def get_single_grid_status(self, symbol: str) -> Dict:
        """Get comprehensive status for single advanced grid"""
        if symbol not in self.active_grids:
            return {"active": False, "error": "Grid not found"}

        try:
            grid_config = self.active_grids[symbol]

            # Get basic monitoring status
            status = self.monitoring.get_single_grid_status(symbol, grid_config)

            # 🔥 NEW - Add trading engine statistics
            trading_stats = self.trading_engine.get_trading_stats(symbol, grid_config)
            status.update(trading_stats)

            return status

        except Exception as e:
            self.logger.error(f"❌ Status error for {symbol}: {e}")
            return {"active": False, "error": str(e)}

    def get_all_active_grids(self) -> Dict:
        """Get status of all active single advanced grids"""
        try:
            base_status = self.monitoring.get_all_active_grids_status(self.active_grids)

            # 🔥 NEW - Add trading engine statistics for each grid
            for symbol in self.active_grids:
                if symbol in base_status.get("grids", {}):
                    trading_stats = self.trading_engine.get_trading_stats(
                        symbol, self.active_grids[symbol]
                    )
                    base_status["grids"][symbol].update(trading_stats)

            return base_status

        except Exception as e:
            self.logger.error(f"❌ All grids status error: {e}")
            return {
                "total_active_grids": 0,
                "trading_mode": "Single Advanced Grid",
                "grids": {},
                "error": str(e),
            }

    async def get_unified_performance_report(self) -> Dict:
        """Generate comprehensive performance report for all active grids"""
        try:
            base_report = self.monitoring.get_unified_performance_report(
                self.active_grids
            )

            # 🔥 NEW - Add trading engine metrics
            trading_summary = {
                "total_orders_placed": 0,
                "total_orders_filled": 0,
                "avg_grid_utilization": 0,
                "trading_engine_metrics": {},
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
                trading_summary["trading_engine_metrics"][symbol] = trading_stats

            if self.active_grids:
                trading_summary["avg_grid_utilization"] = (
                    trading_summary["total_orders_filled"]
                    / max(trading_summary["total_orders_placed"], 1)
                    * 100
                )

            base_report["trading_summary"] = trading_summary
            base_report["separation_of_concerns"] = {
                "grid_manager": "Strategy, optimization, advanced features",
                "trading_engine": "Order execution, precision handling, trade management",
                "monitoring_service": "Performance tracking, status reporting",
                "benefits": "Improved maintainability, cleaner code, separated responsibilities",
            }

            return base_report

        except Exception as e:
            self.logger.error(f"❌ Performance report error: {e}")
            return {
                "report_type": "Single Advanced Grid Performance Report",
                "error": str(e),
                "timestamp": time.time(),
            }

    def _get_advanced_features_status(self, symbol: str) -> Dict:
        """Get status of advanced features for monitoring service"""
        try:
            return {
                "compound_active": hasattr(
                    self.compound_manager, "get_current_multiplier"
                )
                and self.compound_manager.get_current_multiplier() > 1.0,
                "volatility_active": symbol in getattr(self, "volatility_managers", {}),
                "auto_reset_active": symbol in getattr(self, "auto_reset_managers", {}),
                "market_timing_active": hasattr(self, "market_timer")
                and getattr(
                    self.market_timer,
                    "get_session_info",
                    lambda: {"trading_intensity": 1.0},
                )()["trading_intensity"]
                != 1.0,
                "precision_handling": True,  # Always active in trading engine
                "kelly_criterion": getattr(self, "metrics", {}).get(
                    "kelly_adjustments", 0
                )
                > 0,
                "trading_engine_active": True,  # NEW: Trading engine separation
            }
        except Exception as e:
            self.logger.error(f"❌ Features status error: {e}")
            return {
                "compound_active": False,
                "volatility_active": False,
                "auto_reset_active": False,
                "market_timing_active": False,
                "precision_handling": True,
                "kelly_criterion": False,
                "trading_engine_active": True,
            }

    async def _optimize_grid_levels_for_capital(
        self, total_capital: float, order_size: float
    ) -> Dict:
        """
        Optimize grid levels based on available capital and minimum order sizes
        """
        min_order_size = 10.0

        # Calculate maximum viable levels
        max_levels = int(total_capital / min_order_size)

        if max_levels < 5:
            # Insufficient capital for full grid
            self.logger.warning(f"⚠️ Limited capital: only {max_levels} levels possible")
            return {
                "buy_levels": min(max_levels // 2, 3),
                "sell_levels": min(max_levels // 2, 3),
                "adjusted_order_size": max(order_size, min_order_size),
                "capital_efficiency": "Limited",
            }

        # Full grid possible
        return {
            "buy_levels": 5,
            "sell_levels": 5,
            "adjusted_order_size": max(order_size, min_order_size),
            "capital_efficiency": "Optimal",
        }


# Helper function for FORCE commands with proper allocation
def get_force_command_allocation(symbol: str, amount: float) -> Dict:
    """
    Helper function for FORCE commands with proper allocation
    """
    if symbol == "ETHUSDT":
        return {
            "symbol": symbol,
            "total_capital": amount,
            "allocation_pct": 1.0,  # 100% for single asset
            "grid_spacing": 0.025,  # 2.5%
            "risk_profile": "conservative",
            "reasoning": "ETH - Conservative anchor with institutional adoption",
        }
    elif symbol == "SOLUSDT":
        return {
            "symbol": symbol,
            "total_capital": amount,
            "allocation_pct": 1.0,  # 100% for single asset
            "grid_spacing": 0.030,  # 3.0%
            "risk_profile": "moderate-aggressive",
            "reasoning": "SOL - High growth potential with DeFi ecosystem",
        }
    elif symbol == "ADAUSDT":
        return {
            "symbol": symbol,
            "total_capital": amount,
            "allocation_pct": 1.0,  # 100% for single asset
            "grid_spacing": 0.028,  # 2.8%
            "risk_profile": "moderate",
            "reasoning": "ADA - Academic blockchain with steady development",
        }
    else:
        return {"error": f"Unsupported symbol: {symbol}"}
