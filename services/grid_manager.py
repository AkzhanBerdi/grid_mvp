# services/grid_manager.py
"""
Grid Manager - Production Version
=================================

Clean production version with all debug code removed.
Manages single advanced grids with full feature integration.
"""

import logging
import time
from typing import Dict, Optional, Tuple

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


class SmartDecisionEngine:
    """Smart hierarchical decision engine - integrated into GridManager"""

    def __init__(self, client_id: int, fifo_service):
        self.client_id = client_id
        self.fifo_service = fifo_service
        self.logger = logging.getLogger(__name__)

        # Base configuration per symbol
        self.symbol_targets = {
            "ADAUSDT": {"base_size": 25.0, "base_spacing": 0.04, "daily_target": 2.0},
            "ETHUSDT": {"base_size": 50.0, "base_spacing": 0.035, "daily_target": 5.0},
            "SOLUSDT": {"base_size": 40.0, "base_spacing": 0.045, "daily_target": 4.0},
        }

        self.logger.info("🧠 Smart Decision Engine activated for passive income")

    async def get_smart_order_size(
        self, symbol: str, total_capital: float, binance_client
    ) -> float:
        """Master order sizing with hierarchical intelligence"""
        try:
            config = self.symbol_targets.get(symbol, {"base_size": 30.0})
            base_size = config["base_size"]

            # LEVEL 1: Risk Protection (40% weight)
            risk_factor = self._calculate_risk_factor()

            # LEVEL 2: Performance Growth (30% weight)
            performance_factor = self._calculate_performance_factor()

            # LEVEL 3: Market Adaptation (20% weight)
            market_factor = await self._calculate_market_factor(symbol, binance_client)

            # LEVEL 4: Consistency Bonus (10% weight)
            consistency_factor = 1.0  # Start neutral, grows with success

            # Hierarchical combination
            smart_factor = (
                risk_factor * 0.4
                + performance_factor * 0.3
                + market_factor * 0.2
                + consistency_factor * 0.1
            )

            smart_size = base_size * smart_factor

            # Safety bounds
            min_size = 12.0
            max_size = total_capital * 0.15
            final_size = max(min_size, min(smart_size, max_size))

            # Smart logging
            self.logger.info(f"🧠 Smart sizing for {symbol}:")
            self.logger.info(f"   💰 ${base_size} → ${final_size:.2f}")
            self.logger.info(
                f"   🛡️ Risk: {risk_factor:.2f}x, 📈 Performance: {performance_factor:.2f}x"
            )
            self.logger.info(
                f"   🌊 Market: {market_factor:.2f}x, Combined: {smart_factor:.2f}x"
            )

            return final_size

        except Exception as e:
            self.logger.error(f"❌ Smart sizing error: {e}")
            return config["base_size"]

    def _calculate_risk_factor(self) -> float:
        """Level 1: Risk protection factor"""
        try:
            performance = self._get_performance_metrics()
            recent_24h = performance.get("recent_24h_profit", 0.0)
            total_profit = performance.get("total_profit", 0.0)
            win_rate = performance.get("win_rate", 50.0)

            risk_factor = 1.0

            # Recent losses reduce risk appetite
            if recent_24h < -20.0:
                risk_factor *= 0.7
                self.logger.info(f"   🛡️ Risk protection: Recent loss ${recent_24h:.2f}")

            # Poor win rate increases caution
            if win_rate < 40.0:
                risk_factor *= 0.8

            # Good performance allows more risk
            if total_profit > 100.0 and win_rate > 60.0:
                risk_factor *= 1.1

            return max(0.5, min(1.5, risk_factor))

        except Exception:
            return 1.0

    def _calculate_performance_factor(self) -> float:
        """Level 2: Performance growth factor"""
        try:
            performance = self._get_performance_metrics()
            total_profit = performance.get("total_profit", 0.0)
            total_trades = performance.get("total_trades", 0)
            win_rate = performance.get("win_rate", 50.0)

            performance_factor = 1.0

            if total_trades >= 20:
                if total_profit > 50.0 and win_rate > 60.0:
                    performance_factor *= 1.15
                    self.logger.info(
                        f"   📈 Performance bonus: ${total_profit:.2f}, {win_rate:.1f}%"
                    )
                elif total_profit < -25.0:
                    performance_factor *= 0.85
            elif total_trades < 10:
                performance_factor *= 0.9  # Conservative start

            return max(0.8, min(1.2, performance_factor))

        except Exception:
            return 1.0

    async def _calculate_market_factor(self, symbol: str, binance_client) -> float:
        """Level 3: Market adaptation factor"""
        try:
            ticker = binance_client.get_ticker(symbol=symbol)
            high_24h = float(ticker["highPrice"])
            low_24h = float(ticker["lowPrice"])
            current_price = float(ticker["lastPrice"])

            volatility = (high_24h - low_24h) / current_price
            market_factor = 1.0

            if volatility > 0.6:  # High volatility
                market_factor *= 0.8
                self.logger.info(f"   🌊 Market: High volatility {volatility:.2f}")
            elif volatility < 0.25:  # Low volatility
                market_factor *= 1.05

            return max(0.7, min(1.1, market_factor))

        except Exception:
            return 1.0

    def should_smart_reset(
        self, symbol: str, current_price: float, center_price: float, grid_config
    ) -> Tuple[bool, str]:
        """Smart reset decision with multiple triggers"""
        try:
            # TRIGGER 1: Adaptive price threshold
            price_deviation = abs(current_price - center_price) / center_price
            adaptive_threshold = self._get_adaptive_threshold(symbol)

            if price_deviation >= adaptive_threshold:
                return (
                    True,
                    f"Price deviation {price_deviation:.1%} exceeds adaptive threshold {adaptive_threshold:.1%}",
                )

            # TRIGGER 2: Fill ratio (fixes your business logic issue)
            if hasattr(grid_config, "buy_levels") and hasattr(
                grid_config, "sell_levels"
            ):
                filled_buys = len(
                    [l for l in grid_config.buy_levels if l.get("filled", False)]
                )
                total_buys = len(grid_config.buy_levels)
                buy_fill_ratio = filled_buys / total_buys if total_buys > 0 else 0

                filled_sells = len(
                    [l for l in grid_config.sell_levels if l.get("filled", False)]
                )
                total_sells = len(grid_config.sell_levels)
                sell_fill_ratio = filled_sells / total_sells if total_sells > 0 else 0

                # Reset when grid becomes one-sided (BUSINESS LOGIC FIX)
                if buy_fill_ratio >= 0.8:
                    return (
                        True,
                        f"Grid one-sided: {buy_fill_ratio:.1%} buy orders filled",
                    )

                if buy_fill_ratio >= 0.6 and sell_fill_ratio <= 0.2:
                    return (
                        True,
                        f"Grid becoming buy-heavy: {buy_fill_ratio:.1%} vs {sell_fill_ratio:.1%}",
                    )

            return False, f"Reset conditions normal (deviation: {price_deviation:.1%})"

        except Exception as e:
            return False, f"Reset check error: {e}"

    def _get_adaptive_threshold(self, symbol: str) -> float:
        """Adaptive threshold based on conditions"""
        try:
            base_threshold = 0.08  # 8% base
            performance = self._get_performance_metrics()

            # Good performance = allow wider range before reset
            if performance.get("win_rate", 50) > 65:
                return base_threshold * 1.2  # 9.6%
            elif performance.get("total_profit", 0) < -50:
                return base_threshold * 0.8  # 6.4%

            return base_threshold

        except Exception:
            return 0.08

    def _get_performance_metrics(self) -> Dict:
        """Get performance from FIFO service"""
        try:
            if hasattr(self.fifo_service, "calculate_fifo_profit_with_cost_basis"):
                return self.fifo_service.calculate_fifo_profit_with_cost_basis(
                    self.client_id
                )
            return {
                "total_profit": 0.0,
                "total_trades": 0,
                "win_rate": 50.0,
                "recent_24h_profit": 0.0,
            }
        except:
            return {
                "total_profit": 0.0,
                "total_trades": 0,
                "win_rate": 50.0,
                "recent_24h_profit": 0.0,
            }


class GridManager:
    """Production single advanced grid manager with proper inventory integration"""

    def __init__(self, binance_client: Client, client_id: int, fifo_service=None):
        self.binance_client = binance_client
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        # Core services
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()

        if fifo_service:
            self.fifo_service = fifo_service
            self.logger.info("✅ Using shared FIFO service")
        else:
            self.fifo_service = FIFOService()
            self.logger.info("⚠️ Created new FIFO service instance")

        # Trading engine (handles all order operations)
        self.trading_engine = GridTradingEngine(binance_client, client_id)
        self.utility = GridUtilityService(binance_client)
        self.monitoring = GridMonitoringService(client_id, binance_client)
        self.smart_engine = SmartDecisionEngine(client_id, self.fifo_service)

        # Advanced features
        self.market_timer = IntelligentMarketTimer()
        self.volatility_managers: Dict[str, VolatilityBasedRiskManager] = {}
        self.auto_reset_managers: Dict[str, SmartGridAutoReset] = {}

        # Initialize compound manager
        self.compound_manager = CompoundInterestManager(self.fifo_service)
        self.logger.info(
            "✅ Advanced CompoundInterestManager with Kelly Criterion activated"
        )

        # Create inventory manager
        self.inventory_manager = SingleGridInventoryManager(
            binance_client=binance_client, total_capital=2400.0
        )
        self.logger.info("✅ Created inventory manager")

        # Inject inventory manager into trading engine
        if hasattr(self.trading_engine, "set_managers"):
            self.trading_engine.set_managers(
                self.inventory_manager, self.compound_manager
            )
            self.logger.info("✅ Used set_managers method to inject inventory manager")
        else:
            # Fallback: direct assignment
            self.trading_engine.inventory_manager = self.inventory_manager
            self.logger.info("✅ Direct assignment of inventory manager")

        # Verify injection
        if self.trading_engine.inventory_manager is not None:
            self.logger.info("✅ Inventory manager injection verified")
        else:
            self.logger.error("❌ Inventory manager injection failed")

        # State
        self.active_grids: Dict[str, GridConfig] = {}

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
        """Start single advanced grid"""
        try:
            self.logger.info(f"🚀 Starting SINGLE ADVANCED GRID for {symbol}")
            self.logger.info(
                f"   💰 Total Capital: ${total_capital:,.2f} (100% allocation)"
            )

            # Validate inputs
            if not symbol or total_capital <= 0:
                return {"success": False, "error": "Invalid symbol or capital"}

            # Ensure inventory manager
            await self._ensure_inventory_manager(total_capital)

            # Add symbol tracking
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

            self.logger.info(f"📊 Current price for {symbol}: ${current_price:.6f}")

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

            self.logger.info(
                f"🚀 FORCE COMMAND SUCCESS: {symbol.replace('USDT', '')} ${total_capital:.2f}"
            )

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
        """Ensure inventory manager is properly set up"""
        try:
            if not self.inventory_manager:
                self.logger.info("Creating new inventory manager...")
                self.inventory_manager = SingleGridInventoryManager(
                    self.binance_client, total_capital
                )

                # Inject into trading engine
                success = self.trading_engine.set_managers(
                    self.inventory_manager, self.compound_manager
                )

                if not success:
                    self.logger.error("❌ Failed to inject managers - aborting")
                    raise RuntimeError("Manager injection failed")

                self.logger.info("✅ Inventory manager created and injected")

            else:
                # Update existing manager capital if needed
                original_capital = self.inventory_manager.total_capital

                if total_capital > original_capital:
                    self.inventory_manager.total_capital = total_capital
                    self.logger.info(
                        f"📊 Updated inventory manager capital: ${original_capital:.2f} → ${total_capital:.2f}"
                    )

                self.logger.info("✅ Inventory manager validated and updated")

        except Exception as e:
            self.logger.error(f"❌ Inventory manager setup error: {e}")
            raise

    async def _add_symbol_to_inventory(self, symbol: str, total_capital: float) -> bool:
        """Add symbol tracking to inventory manager"""
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

                    # Ensure inventory tracking exists
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
            self.logger.info(f"🧮 Calculating optimal grid for {symbol}")

            asset_config = self.asset_configs.get(
                symbol,
                {
                    "allocation": 1.0,
                    "risk_profile": "moderate",
                    "grid_spacing_base": 0.025,
                    "volatility_threshold": 1.0,
                },
            )

            # Create grid configuration
            grid_config = GridConfig(
                symbol,  # symbol
                self.client_id,  # client_id
                asset_config.get("grid_spacing_base", 0.025),  # grid_spacing
                total_capital,  # total_capital
                asset_config.get("grid_levels", 8),  # grid_levels
                total_capital / 16,  # order_size
            )

            grid_config.center_price = current_price

            # Calculate optimal parameters
            optimal_config = await self._calculate_optimal_parameters(
                symbol, current_price, total_capital, asset_config
            )

            # Apply optimal parameters
            grid_config.base_order_size = optimal_config["base_order_size"]
            grid_config.grid_spacing = optimal_config["grid_spacing"]

            # Add compound/volatility attributes
            grid_config.compound_multiplier = optimal_config.get(
                "compound_multiplier", 1.0
            )
            grid_config.volatility_regime = optimal_config.get(
                "volatility_regime", "moderate"
            )

            # Create grid levels
            await self.trading_engine.create_advanced_grid_levels(
                grid_config, current_price, optimal_config
            )

            self.logger.info(f"✅ Grid configuration created for {symbol}")
            self.logger.info(f"   💰 Total capital: ${grid_config.total_capital:,.2f}")
            self.logger.info(f"   👤 Client ID: {grid_config.client_id}")
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
        """
        SMART: Use hierarchical decision engine instead of conflicting managers
        """
        try:
            # Use smart engine for order sizing (eliminates conflicts)
            smart_order_size = await self.smart_engine.get_smart_order_size(
                symbol, total_capital, self.binance_client
            )

            # Use smart spacing from base config with minor volatility adjustment
            base_spacing = asset_config.get("grid_spacing_base", 0.04)

            # Simple volatility check (not conflicting with other systems)
            try:
                if symbol in self.volatility_managers:
                    volatility_result = await self.volatility_managers[
                        symbol
                    ].get_risk_adjusted_parameters(smart_order_size, base_spacing)
                    # Use volatility spacing if available, otherwise base
                    smart_spacing = volatility_result.get(
                        "adjusted_grid_spacing", base_spacing
                    )
                else:
                    smart_spacing = base_spacing
            except:
                smart_spacing = base_spacing

            # Ensure minimum notional compliance
            if smart_order_size < 12.0:
                smart_order_size = 12.0
                self.logger.info(
                    f"📈 Order size adjusted to ${smart_order_size:.2f} for compliance"
                )

            optimal_config = {
                "base_order_size": smart_order_size,
                "grid_spacing": smart_spacing,
                "compound_multiplier": 1.0,  # Simplified
                "volatility_regime": "smart",
                "market_timing_score": 1.0,
                "total_optimization_factor": smart_order_size
                / 30.0,  # Show optimization
            }

            self.logger.info(f"✅ SMART grid calculated for {symbol}:")
            self.logger.info(
                f"   💰 Order size: ${smart_order_size:.2f} (smart hierarchical)"
            )
            self.logger.info(f"   📊 Grid spacing: {smart_spacing * 100:.1f}%")
            self.logger.info("   🧠 Intelligence: Risk+Performance+Market adaptive")

            return optimal_config

        except Exception as e:
            self.logger.error(f"❌ Smart parameter calculation error: {e}")
            # Safe fallback
            return {
                "base_order_size": 30.0,
                "grid_spacing": asset_config.get("grid_spacing_base", 0.04),
                "compound_multiplier": 1.0,
                "volatility_regime": "fallback",
                "market_timing_score": 1.0,
                "total_optimization_factor": 1.0,
            }

    async def _update_advanced_features(self, symbol: str):
        """SMART: Enhanced reset logic using smart engine"""
        try:
            if not hasattr(self, "_last_feature_update"):
                self._last_feature_update = {}

            if symbol not in self._last_feature_update:
                self._last_feature_update[symbol] = 0

            if time.time() - self._last_feature_update[symbol] < 300:  # 5 minutes
                return

            self._last_feature_update[symbol] = time.time()

            # Use smart engine for reset decisions
            current_price = await self._get_current_price(symbol)
            if current_price and symbol in self.active_grids:
                grid_config = self.active_grids[symbol]

                # SMART RESET: Use hierarchical decision
                should_reset, reason = self.smart_engine.should_smart_reset(
                    symbol, current_price, grid_config.center_price, grid_config
                )

                if should_reset:
                    self.logger.info(f"🧠 Smart reset triggered for {symbol}: {reason}")
                    await self._execute_smart_reset(symbol, current_price)

        except Exception as e:
            self.logger.error(f"❌ Smart features update error: {e}")

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
