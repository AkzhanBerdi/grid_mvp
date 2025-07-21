# services/single_advanced_grid_manager.py
"""
Single Advanced Grid Manager - Phase 1 Core Implementation
==========================================================

Unified Advanced Grid Manager that eliminates dual-grid complexity
while maximizing ALL advanced features in one optimized system.

Replaces: EnhancedDualScaleGridManager
Benefits: 100% capital efficiency, simplified management, maximum feature utilization
"""

import asyncio
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
from services.api_error_notifier import APIErrorNotifier
from services.fifo_service import FIFOService
from services.inventory_manager import SingleGridInventoryManager
from services.market_analysis import MarketAnalysisService
from services.working_fifo_integration import WorkingFIFOIntegration
from utils.fifo_telegram_monitor import FIFOMonitoringService

# Replace the entire compound manager section with this:
try:
    from services.compound_interest_manager import CompoundInterestManager
    from services.fifo_service import FIFOService

    COMPOUND_AVAILABLE = True

    def create_advanced_compound_manager(client_id):
        """Create advanced compound manager with FIFO integration"""
        fifo_service = FIFOService()
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
    Single Advanced Grid Manager - Phase 1 Core Implementation
    """

    def __init__(self, binance_client: Client, client_id: int):
        self.binance_client = binance_client
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        self.error_notifier = APIErrorNotifier()

        self.inventory_manager = None  # Will be initialized with capital
        self.volatility_managers: Dict[str, VolatilityBasedRiskManager] = {}
        self.auto_reset_managers: Dict[str, SmartGridAutoReset] = {}

        # Core repositories
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()

        # Services
        # 🔥 REPLACE: Use working integration instead of the broken one
        self.working_integration = WorkingFIFOIntegration(client_id)
        self.logger.info("✅ Working notification integration initialized")
        self.logger.info("✅ FIXED Grid notification integration initialized")
        self.fifo_service = FIFOService()
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

        # Then in your __init__ method:
        if COMPOUND_AVAILABLE:
            self.compound_manager = create_advanced_compound_manager(client_id)
            self.logger.info(
                "✅ Advanced CompoundInterestManager with Kelly Criterion activated"
            )
        else:
            self.compound_manager = CompoundInterestManager(FIFOService())
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
        self.logger.info("🚀 SingleAdvancedGridManager initialized")
        self.logger.info("   💰 Compound Management: UNIFIED")
        self.logger.info("   ⏰ Intelligent Market Timing: UNIFIED")
        self.logger.info("   🛡️ Volatility Risk Management: UNIFIED")
        self.logger.info("   🔄 Smart Auto-Reset: UNIFIED")
        self.logger.info("   🎯 Precision Order Handling: UNIFIED")
        self.logger.info("   📊 Advanced Performance Monitoring: UNIFIED")
        self.logger.info("   🎯 Grid Strategy: Single 10-Level Advanced Grid")
        self.logger.info("   💎 Capital Efficiency: 100% (vs 35/65 split)")

    async def start_single_advanced_grid(
        self, symbol: str, total_capital: float
    ) -> Dict:
        """
        CORRECTED: Start single advanced grid with proper feature activation order
        """
        try:
            self.logger.info(f"🚀 Starting SINGLE ADVANCED GRID for {symbol}")
            self.logger.info(
                f"   💰 Total Capital: ${total_capital:,.2f} (100% allocation)"
            )
            self.logger.info(
                "   🎯 Strategy: 10-Level Unified Advanced Grid with Inventory Management"
            )

            # Initialize inventory manager if not exists
            if not self.inventory_manager:
                self.inventory_manager = SingleGridInventoryManager(
                    self.binance_client, total_capital
                )
                await self.inventory_manager.initialize_asset_positions()

            # Validate symbol configuration
            if symbol not in self.asset_configs:
                return {
                    "success": False,
                    "error": f"Unsupported symbol: {symbol}. Supported: {list(self.asset_configs.keys())}",
                }

            # Get inventory status for this symbol
            inventory_status = self.inventory_manager.get_inventory_status(symbol)
            if "error" in inventory_status:
                return {"success": False, "error": inventory_status["error"]}

            # Get asset config and initialize symbol managers
            asset_config = self.asset_configs[symbol]
            await self._initialize_symbol_managers(symbol, asset_config)

            # 🔥 ACTIVATE ADVANCED FEATURES (MOVED TO CORRECT LOCATION)
            self.volatility_managers[symbol] = VolatilityBasedRiskManager(
                self.binance_client, symbol
            )

            # Check constructor - may need different parameters
            self.auto_reset_managers[symbol] = SmartGridAutoReset(
                symbol, self.client_id
            )

            self.logger.info(f"🔥 Advanced features activated for {symbol}")

            # Get current price
            current_price = await self._get_current_price_with_precision(symbol)
            if not current_price:
                return {"success": False, "error": "Failed to get current price"}

            # Create grid configuration with inventory awareness
            grid_config = SingleAdvancedGridConfig(symbol, total_capital, asset_config)

            # Initialize grid levels with inventory-based sizing
            await self._create_inventory_aware_grid_levels(grid_config, current_price)

            # Execute grid setup with inventory validation
            execution_result = await self._execute_inventory_aware_grid_setup(
                grid_config
            )

            if execution_result["success"]:
                # Store active grid and start monitoring
                self.active_grids[symbol] = grid_config
                asyncio.create_task(self._inventory_aware_monitoring_loop(symbol))

                return {
                    "success": True,
                    "symbol": symbol,
                    "orders_placed": execution_result["orders_placed"],
                    "inventory_status": inventory_status,
                    "grid_config": grid_config.to_dict()
                    if hasattr(grid_config, "to_dict")
                    else {},
                    "capital_allocation": f"${total_capital:,.2f} (100%)",
                    "advanced_features_active": {
                        "compound_interest": True,
                        "volatility_management": True,
                        "auto_reset": True,
                        "market_timing": True,
                        "precision_handling": True,
                    },
                }
            else:
                return execution_result

        except Exception as e:
            self.logger.error(
                f"❌ Single advanced grid startup error for {symbol}: {e}"
            )
            return {"success": False, "error": str(e)}

    async def _inventory_aware_monitoring_loop(self, symbol: str):
        """
        ADD this new method: Monitoring loop with inventory management
        """
        try:
            while symbol in self.active_grids:
                # Check for filled orders with inventory updates
                await self._check_and_replace_filled_orders_with_inventory(symbol)

                # Log inventory status periodically
                if self._should_log_inventory():
                    inventory_status = self.inventory_manager.get_inventory_status(
                        symbol
                    )
                    self.logger.info(
                        f"📊 {symbol} Inventory: USDT Available=${inventory_status['usdt_available']}, Asset Available={inventory_status['asset_available']}"
                    )

                await asyncio.sleep(30)  # Check every 30 seconds

        except Exception as e:
            self.logger.error(f"❌ Inventory-aware monitoring error for {symbol}: {e}")

    async def _create_inventory_aware_grid_levels(
        self, grid_config: SingleAdvancedGridConfig, current_price: float
    ):
        """
        BULLETPROOF: Create grid levels that work for any asset and any amount
        """
        try:
            symbol = grid_config.symbol
            spacing = grid_config.grid_spacing

            self.logger.info(f"🔧 Creating bulletproof grid levels for {symbol}")

            # Get exchange rules
            rules = await self._get_exchange_rules_simple(symbol)

            # Make current price valid
            valid_center_price = self._make_valid_price(
                current_price, rules["tick_size"], rules["price_precision"]
            )

            self.logger.info(
                f"💲 Center price: ${current_price:.8f} → ${valid_center_price:.8f}"
            )

            # Clear existing levels
            grid_config.buy_levels = []
            grid_config.sell_levels = []

            # Calculate order size from total capital
            total_capital = grid_config.total_capital
            order_size_usd = total_capital / 10  # 10 orders total

            # Ensure minimum order size
            min_order_size = max(order_size_usd, rules["min_notional"] * 1.5)

            self.logger.info(f"💰 Order size: ${min_order_size:.2f} per order")

            # Create 5 buy levels
            for i in range(1, 6):
                # Calculate price
                price_multiplier = 1 - (spacing * i)
                raw_price = valid_center_price * price_multiplier
                valid_price = self._make_valid_price(
                    raw_price, rules["tick_size"], rules["price_precision"]
                )

                # Calculate quantity
                raw_quantity = min_order_size / valid_price
                valid_quantity = self._make_valid_quantity(
                    raw_quantity,
                    rules["step_size"],
                    rules["quantity_precision"],
                    rules["min_qty"],
                )

                # Recalculate actual USD
                actual_usd = valid_quantity * valid_price

                buy_level = {
                    "level": -i,
                    "side": "BUY",
                    "price": valid_price,
                    "quantity": valid_quantity,
                    "order_size_usd": actual_usd,
                    "order_id": None,
                    "filled": False,
                    "spacing_factor": i,
                }
                grid_config.buy_levels.append(buy_level)

            # Create 5 sell levels
            for i in range(1, 6):
                # Calculate price
                price_multiplier = 1 + (spacing * i)
                raw_price = valid_center_price * price_multiplier
                valid_price = self._make_valid_price(
                    raw_price, rules["tick_size"], rules["price_precision"]
                )

                # Calculate quantity
                raw_quantity = min_order_size / valid_price
                valid_quantity = self._make_valid_quantity(
                    raw_quantity,
                    rules["step_size"],
                    rules["quantity_precision"],
                    rules["min_qty"],
                )

                # Recalculate actual USD
                actual_usd = valid_quantity * valid_price

                sell_level = {
                    "level": i,
                    "side": "SELL",
                    "price": valid_price,
                    "quantity": valid_quantity,
                    "order_size_usd": actual_usd,
                    "order_id": None,
                    "filled": False,
                    "spacing_factor": i,
                }
                grid_config.sell_levels.append(sell_level)

            grid_config.center_price = valid_center_price

            # Log results
            buy_min = min(level["price"] for level in grid_config.buy_levels)
            buy_max = max(level["price"] for level in grid_config.buy_levels)
            sell_min = min(level["price"] for level in grid_config.sell_levels)
            sell_max = max(level["price"] for level in grid_config.sell_levels)

            self.logger.info(f"✅ Grid levels created for {symbol}:")
            self.logger.info(
                f"   📉 Buy levels: 5 levels from ${buy_min:.{rules['price_precision']}f} to ${buy_max:.{rules['price_precision']}f}"
            )
            self.logger.info(
                f"   📈 Sell levels: 5 levels from ${sell_min:.{rules['price_precision']}f} to ${sell_max:.{rules['price_precision']}f}"
            )

        except Exception as e:
            self.logger.error(f"❌ Grid level creation error: {e}")
            raise

    async def _execute_inventory_aware_grid_setup(
        self, grid_config: SingleAdvancedGridConfig
    ) -> Dict:
        """
        ENHANCED: Execute orders with FIFO trade notifications
        """
        try:
            symbol = grid_config.symbol
            orders_placed = 0
            failed_orders = 0

            self.logger.info(f"🎯 Executing bulletproof grid setup for {symbol}")

            # Get exchange rules for formatting
            rules = await self._get_exchange_rules_simple(symbol)

            # Place BUY orders
            for level in grid_config.buy_levels:
                try:
                    # Format with exact precision
                    quantity_str = (
                        f"{level['quantity']:.{rules['quantity_precision']}f}".rstrip(
                            "0"
                        ).rstrip(".")
                    )
                    price_str = f"{level['price']:.{rules['price_precision']}f}".rstrip(
                        "0"
                    ).rstrip(".")

                    # Ensure minimum decimal places
                    if "." not in quantity_str and rules["quantity_precision"] > 0:
                        quantity_str += ".0"
                    if "." not in price_str and rules["price_precision"] > 0:
                        price_str += ".0"

                    self.logger.info(f"📤 Placing BUY: {quantity_str} @ {price_str}")

                    order = self.binance_client.order_limit_buy(
                        symbol=symbol,
                        quantity=quantity_str,
                        price=price_str,
                        recvWindow=60000,
                    )

                    level["order_id"] = order["orderId"]
                    orders_placed += 1

                    self.logger.info(
                        f"✅ BUY Level {level['level']}: {order['origQty']} @ ${order['price']}"
                    )

                    # 🔔 NOTIFY FIFO SYSTEM OF TRADE
                    await self._notify_trade_execution(symbol, "BUY", order)

                except Exception as e:
                    failed_orders += 1
                    self.logger.error(f"❌ BUY Level {level['level']} failed: {e}")

            # Place SELL orders
            for level in grid_config.sell_levels:
                try:
                    # Format with exact precision
                    quantity_str = (
                        f"{level['quantity']:.{rules['quantity_precision']}f}".rstrip(
                            "0"
                        ).rstrip(".")
                    )
                    price_str = f"{level['price']:.{rules['price_precision']}f}".rstrip(
                        "0"
                    ).rstrip(".")

                    # Ensure minimum decimal places
                    if "." not in quantity_str and rules["quantity_precision"] > 0:
                        quantity_str += ".0"
                    if "." not in price_str and rules["price_precision"] > 0:
                        price_str += ".0"

                    self.logger.info(f"📤 Placing SELL: {quantity_str} @ {price_str}")

                    order = self.binance_client.order_limit_sell(
                        symbol=symbol,
                        quantity=quantity_str,
                        price=price_str,
                        recvWindow=60000,
                    )

                    level["order_id"] = order["orderId"]
                    orders_placed += 1

                    self.logger.info(
                        f"✅ SELL Level {level['level']}: {order['origQty']} @ ${order['price']}"
                    )

                    # 🔔 NOTIFY FIFO SYSTEM OF TRADE
                    await self._notify_trade_execution(symbol, "SELL", order)

                except Exception as e:
                    failed_orders += 1
                    self.logger.error(f"❌ SELL Level {level['level']} failed: {e}")

            success_rate = (
                (orders_placed / (orders_placed + failed_orders) * 100)
                if (orders_placed + failed_orders) > 0
                else 0
            )

            self.logger.info("✅ Grid setup completed:")
            self.logger.info(f"   🎯 Orders placed: {orders_placed}")
            self.logger.info(f"   ❌ Failed orders: {failed_orders}")
            self.logger.info(f"   📊 Success rate: {success_rate:.1f}%")
            self.logger.info(f"   🔔 FIFO notifications sent: {orders_placed}")

            return {
                "success": orders_placed > 0,
                "orders_placed": orders_placed,
                "failed_orders": failed_orders,
                "success_rate": f"{success_rate:.1f}%",
                "fifo_notifications_sent": orders_placed,
            }

        except Exception as e:
            self.logger.error(f"❌ Grid setup execution error: {e}")
            return {"success": False, "error": str(e)}

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

    async def _initialize_symbol_managers(self, symbol: str, asset_config: Dict):
        """Initialize all symbol-specific advanced managers"""
        try:
            # Simple, robust initialization
            self.volatility_managers[symbol] = VolatilityBasedRiskManager(
                self.binance_client, symbol
            )
            self.auto_reset_managers[symbol] = SmartGridAutoReset(
                symbol, self.client_id
            )

            self.logger.info(f"🔧 Advanced managers initialized for {symbol}")

        except Exception as e:
            self.logger.error(f"❌ Manager initialization error for {symbol}: {e}")
            raise

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
                # Try the new interface first
                compound_order_size = (
                    await self.compound_manager.get_current_order_size(
                        self.client_id, symbol, total_capital
                    )
                )
            except TypeError:
                # Fallback to existing interface - just use current_order_size method
                try:
                    compound_order_size = self.compound_manager.get_current_order_size()
                except:
                    # Ultimate fallback - calculate base order size
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
                market_timing = {
                    "session_recommendation": "Normal",
                    "trading_intensity": 1.0,
                }
                timing_multiplier = 1.0

            # 4. Kelly Criterion Position Sizing
            try:
                kelly_fraction = await self.compound_manager.calculate_kelly_fraction(
                    self.client_id, symbol
                )
            except:
                # Fallback Kelly fraction
                kelly_fraction = 0.1  # Conservative 10%

            kelly_active = kelly_fraction > 0.05  # Active if suggests >5% allocation

            # 5. Unified Optimization Calculation
            base_order_size = total_capital / 10  # Base size for 10 levels

            # Apply all optimizations
            optimized_order_size = compound_order_size  # Start with compound size
            optimized_order_size *= volatility_params[
                "order_size_multiplier"
            ]  # Volatility adjustment
            optimized_order_size *= timing_multiplier  # Market timing

            # Apply Kelly Criterion constraint
            kelly_max_order = total_capital * kelly_fraction / 5  # Max per buy level
            if optimized_order_size > kelly_max_order and kelly_active:
                optimized_order_size = kelly_max_order
                self.logger.info(
                    f"🎯 Kelly Criterion constraint applied: ${optimized_order_size:.2f}"
                )

            # Safety caps
            max_order = total_capital * 0.25  # Never more than 25% per order
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

    async def _create_advanced_grid_levels(
        self,
        grid_config: SingleAdvancedGridConfig,
        current_price: float,
        optimal_config: Dict,
    ) -> Dict:
        """
        Create 10 optimized levels with advanced distribution and proper Binance precision

        Layout: 5 SELL levels above current price + 5 BUY levels below current price
        """
        try:
            spacing = grid_config.grid_spacing
            base_order_size = grid_config.base_order_size

            self.logger.info(
                f"🎯 Creating advanced grid levels for {grid_config.symbol}"
            )
            self.logger.info(f"   📊 Spacing: {spacing * 100:.2f}%")
            self.logger.info(f"   💰 Base order size: ${base_order_size:.2f}")
            self.logger.info(f"   💲 Current price: ${current_price:.6f}")

            # Get symbol precision requirements
            symbol_info = await self._get_symbol_precision_info(grid_config.symbol)
            price_precision = symbol_info.get("price_precision", 6)
            tick_size = symbol_info.get("tick_size", 0.01)

            self.logger.info(
                f"   🔧 Price precision: {price_precision} decimals, tick size: {tick_size}"
            )

            # SELL LEVELS (5 levels above current price)
            sell_levels = []
            for i in range(1, 6):
                # Progressive spacing for better profit capture
                level_spacing = spacing * (
                    1 + i * 0.1
                )  # 1.1x, 1.2x, 1.3x, 1.4x, 1.5x spacing
                raw_price = current_price * (1 + level_spacing)

                # Apply proper price precision
                price = self._round_to_tick_size(raw_price, tick_size)

                # Compound-progressive order sizing (larger orders higher up for more profit)
                level_order_size = base_order_size * (
                    1 + i * 0.05
                )  # 5% increase per level
                quantity = level_order_size / price

                sell_levels.append(
                    {
                        "level": i,
                        "side": "SELL",
                        "price": price,
                        "quantity": quantity,
                        "order_size_usd": level_order_size,
                        "order_id": None,
                        "filled": False,
                        "spacing_factor": 1 + i * 0.1,
                        "raw_price": raw_price,  # For debugging
                    }
                )

            # BUY LEVELS (5 levels below current price)
            buy_levels = []
            for i in range(1, 6):
                level_spacing = spacing * (1 + i * 0.1)
                raw_price = current_price * (1 - level_spacing)

                # Apply proper price precision
                price = self._round_to_tick_size(raw_price, tick_size)

                level_order_size = base_order_size * (1 + i * 0.05)
                quantity = level_order_size / price

                buy_levels.append(
                    {
                        "level": -i,
                        "side": "BUY",
                        "price": price,
                        "quantity": quantity,
                        "order_size_usd": level_order_size,
                        "order_id": None,
                        "filled": False,
                        "spacing_factor": 1 + i * 0.1,
                        "raw_price": raw_price,  # For debugging
                    }
                )

            # Update grid config
            grid_config.buy_levels = buy_levels
            grid_config.sell_levels = sell_levels

            # Debug logging
            self.logger.info("✅ Grid levels created with proper precision:")
            self.logger.info(f"   📈 SELL levels: {len(sell_levels)}")
            for level in sell_levels[:2]:  # Show first 2
                self.logger.info(
                    f"      Level {level['level']}: ${level['raw_price']:.6f} → ${level['price']:.6f}"
                )

            self.logger.info(f"   📉 BUY levels: {len(buy_levels)}")
            for level in buy_levels[:2]:  # Show first 2
                self.logger.info(
                    f"      Level {level['level']}: ${level['raw_price']:.6f} → ${level['price']:.6f}"
                )

            grid_levels = {
                "buy_levels": buy_levels,
                "sell_levels": sell_levels,
                "total_levels": 10,
                "center_price": current_price,
                "total_capital_allocated": sum(
                    level["order_size_usd"] for level in buy_levels
                ),
                "symbol_info": symbol_info,
            }

            return grid_levels

        except Exception as e:
            self.logger.error(f"❌ Grid level creation error: {e}")
            raise

    def _round_to_tick_size(self, price: float, tick_size: float) -> float:
        """Round price to the nearest valid tick size"""
        try:
            if tick_size <= 0:
                return round(price, 6)  # Fallback

            # Round to nearest tick
            rounded = round(price / tick_size) * tick_size

            # Ensure we don't round to zero
            if rounded <= 0:
                rounded = tick_size

            return rounded

        except Exception as e:
            self.logger.error(f"Tick size rounding error: {e}")
            return round(price, 6)  # Safe fallback

    async def _get_symbol_precision_info(self, symbol: str) -> Dict:
        """Get symbol precision information with ADA-specific overrides"""
        try:
            # FORCE ADA overrides to fix precision issues
            if symbol == "ADAUSDT":
                info = {
                    "price_precision": 4,
                    "quantity_precision": 1,  # Allow 1 decimal place
                    "tick_size": 0.0001,
                    "step_size": 0.1,  # Correct ADA step size
                    "min_notional": 5.0,
                    "status": "TRADING",
                }
                self.logger.info(
                    f"🔒 FORCED ADA precision: step_size={info['step_size']}, quantity_precision={info['quantity_precision']}"
                )
                return info

            # FORCE ETH overrides to fix precision issues
            if symbol == "ETHUSDT":
                info = {
                    "price_precision": 2,
                    "quantity_precision": 5,  # Allow 5 decimal places
                    "tick_size": 0.01,
                    "step_size": 0.00001,  # ETH step size is 0.00001
                    "min_notional": 5.0,
                    "status": "TRADING",
                }
                self.logger.info(
                    f"🔒 FORCED ETH precision: step_size={info['step_size']}, quantity_precision={info['quantity_precision']}"
                )
                return info

            # For other symbols, get from Binance API# FORCE SOL overrides to fix precision issues
            if symbol == "SOLUSDT":
                info = {
                    "price_precision": 3,
                    "quantity_precision": 4,  # Allow 4 decimal places
                    "tick_size": 0.001,
                    "step_size": 0.0001,  # SOL step size is 0.0001
                    "min_notional": 5.0,
                    "status": "TRADING",
                }
                self.logger.info(
                    f"🔒 FORCED SOL precision: step_size={info['step_size']}, quantity_precision={info['quantity_precision']}"
                )
                return info

            # For other symbols, get from Binance API# For other symbols, get from Binance API
            exchange_info = self.binance_client.get_exchange_info()
            exchange_info = self.binance_client.get_exchange_info()

            for s in exchange_info["symbols"]:
                if s["symbol"] == symbol:
                    # Extract precision info
                    price_precision = s.get("quotePrecision", 6)

                    # Get tick size from PRICE_FILTER
                    tick_size = 0.01  # Default
                    for f in s.get("filters", []):
                        if f["filterType"] == "PRICE_FILTER":
                            tick_size = float(f["tickSize"])
                            break

                    # Get quantity precision from LOT_SIZE
                    quantity_precision = s.get("baseAssetPrecision", 6)
                    step_size = 1.0  # Default
                    for f in s.get("filters", []):
                        if f["filterType"] == "LOT_SIZE":
                            step_size = float(f["stepSize"])
                            break

                    # Get minimum notional
                    min_notional = 10.0  # Default
                    for f in s.get("filters", []):
                        if f["filterType"] in ["NOTIONAL", "MIN_NOTIONAL"]:
                            min_notional = float(f.get("minNotional", "10.0"))
                            break

                    info = {
                        "price_precision": price_precision,
                        "quantity_precision": quantity_precision,
                        "tick_size": tick_size,
                        "step_size": step_size,
                        "min_notional": min_notional,
                        "status": s.get("status", "TRADING"),
                    }

                    self.logger.info(
                        f"📊 {symbol} precision info: tick_size={tick_size}, step_size={step_size}, min_notional=${min_notional}"
                    )
                    return info

            # Symbol not found, return defaults
            self.logger.warning(
                f"⚠️ Symbol {symbol} not found in exchange info, using defaults"
            )
            return {
                "price_precision": 6,
                "quantity_precision": 6,
                "tick_size": 0.01,
                "step_size": 1.0,
                "min_notional": 10.0,
                "status": "UNKNOWN",
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to get symbol precision for {symbol}: {e}")
            # Return safe defaults
            return {
                "price_precision": 6,
                "quantity_precision": 6,
                "tick_size": 0.01,
                "step_size": 1.0,
                "min_notional": 10.0,
                "status": "ERROR",
            }

    async def _execute_precision_grid_setup(
        self, grid_config: SingleAdvancedGridConfig, grid_levels: Dict
    ) -> Dict:
        """Execute precision order placement for all grid levels"""
        try:
            self.logger.info(
                f"🎯 Executing precision grid setup for {grid_config.symbol}"
            )

            orders_placed = 0
            failed_orders = 0

            # Place BUY orders first (below current price)
            for level in grid_levels["buy_levels"]:
                try:
                    order_result = await self.precision_handler.execute_precision_order(
                        grid_config.symbol, "BUY", level["quantity"], level["price"]
                    )

                    if order_result["success"]:
                        level["order_id"] = order_result["order_id"]
                        level["actual_price"] = order_result["price"]
                        level["actual_quantity"] = order_result["quantity"]
                        orders_placed += 1

                        # Log trade
                        self.trade_repo.log_grid_order(
                            client_id=self.client_id,
                            symbol=grid_config.symbol,
                            side="BUY",
                            quantity=order_result["quantity"],
                            price=order_result["price"],
                            order_id=order_result["order_id"],
                            grid_level=level["level"],
                        )
                    else:
                        failed_orders += 1
                        self.logger.warning(
                            f"⚠️ BUY order failed at level {level['level']}: {order_result.get('error')}"
                        )

                except Exception as e:
                    failed_orders += 1
                    self.logger.error(
                        f"❌ BUY order error at level {level['level']}: {e}"
                    )

            # Place SELL orders (above current price) - only if we have existing position
            # For initial grid, we'll place conditional sells or skip them
            self.logger.info("📈 SELL orders will be placed as BUY orders are filled")

            self.metrics["precision_orders"] += orders_placed

            result = {
                "success": orders_placed > 0,
                "orders_placed": orders_placed,
                "failed_orders": failed_orders,
                "buy_orders": orders_placed,
                "sell_orders": 0,  # Will be placed dynamically
                "total_levels_active": orders_placed,
            }

            if orders_placed > 0:
                self.logger.info("✅ Grid setup completed:")
                self.logger.info(f"   🎯 Orders placed: {orders_placed}")
                self.logger.info(f"   ❌ Failed orders: {failed_orders}")
                self.logger.info(
                    f"   📊 Success rate: {orders_placed / (orders_placed + failed_orders) * 100:.1f}%"
                )
            else:
                self.logger.error("❌ No orders were successfully placed")

            return result

        except Exception as e:
            self.logger.error(f"❌ Grid setup execution error: {e}")
            return {"success": False, "error": str(e)}

    def get_single_grid_status(self, symbol: str) -> Dict:
        """Get comprehensive status for single advanced grid"""
        if symbol not in self.active_grids:
            return {"active": False, "error": "Grid not found"}

        try:
            grid_config = self.active_grids[symbol]

            # Get advanced features status
            compound_status = self.compound_manager.get_compound_status()
            market_session = self.market_timer.get_session_info()

            # Get volatility status
            volatility_status = {}
            if symbol in self.volatility_managers:
                volatility_status = {
                    "regime": grid_config.volatility_regime,
                    "active": True,
                    "current_threshold": self.asset_configs[symbol][
                        "volatility_threshold"
                    ],
                }

            # Get auto-reset status
            auto_reset_status = {}
            if symbol in self.auto_reset_managers:
                auto_reset_status = self.auto_reset_managers[symbol].get_reset_status()

            return {
                "active": True,
                "symbol": symbol,
                "strategy": "Single Advanced Grid (10 levels)",
                "capital_efficiency": "100%",
                "grid_details": {
                    "total_levels": 10,
                    "buy_levels": len(grid_config.buy_levels),
                    "sell_levels": len(grid_config.sell_levels),
                    "center_price": grid_config.center_price,
                    "current_spacing": f"{grid_config.grid_spacing * 100:.2f}%",
                },
                "advanced_features_status": {
                    "compound_management": {
                        "active": compound_status["compound_active"],
                        "current_multiplier": compound_status["current_multiplier"],
                        "order_size": compound_status["current_order_size"],
                    },
                    "market_timing": {
                        "session": market_session["session_recommendation"],
                        "intensity": market_session["trading_intensity"],
                        "should_trade": market_session["should_place_orders"],
                    },
                    "volatility_management": volatility_status,
                    "auto_reset": {
                        "active": symbol in self.auto_reset_managers,
                        "can_reset": auto_reset_status.get("can_reset_now", False),
                        "resets_today": auto_reset_status.get("resets_today", 0),
                    },
                    "precision_handling": {
                        "active": True,
                        "orders_processed": self.metrics["precision_orders"],
                    },
                },
                "performance_metrics": {
                    "optimization_events": self.metrics["grid_optimizations"],
                    "compound_events": self.metrics["compound_events"],
                    "volatility_adjustments": self.metrics["volatility_adjustments"],
                    "auto_resets": self.metrics["auto_resets"],
                },
                "asset_config": self.asset_configs[symbol],
            }

        except Exception as e:
            self.logger.error(f"❌ Status error for {symbol}: {e}")
            return {"active": False, "error": str(e)}

    async def stop_single_advanced_grid(self, symbol: str) -> Dict:
        """Stop single advanced grid and generate final report"""
        if symbol not in self.active_grids:
            return {"success": False, "error": "Grid not found"}

        try:
            self.logger.info(f"🛑 Stopping single advanced grid for {symbol}")

            grid_config = self.active_grids[symbol]
            cancelled_orders = 0

            # Cancel all active orders
            for level in grid_config.buy_levels + grid_config.sell_levels:
                if level["order_id"] and not level["filled"]:
                    try:
                        self.binance_client.cancel_order(
                            symbol=symbol, orderId=level["order_id"]
                        )
                        cancelled_orders += 1
                    except Exception as e:
                        self.logger.warning(
                            f"⚠️ Failed to cancel order {level['order_id']}: {e}"
                        )

            # Generate final performance report
            try:
                final_report = (
                    await self.performance_monitor.generate_comprehensive_report(30)
                )
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

    def get_all_active_grids(self) -> Dict:
        """Get status of all active single advanced grids"""
        all_grids = {}

        for symbol in self.active_grids:
            try:
                grid_status = self.get_single_grid_status(symbol)
                if grid_status.get("active"):
                    all_grids[symbol] = grid_status
            except Exception as e:
                self.logger.error(f"❌ Failed to get status for {symbol}: {e}")

        return {
            "total_active_grids": len(all_grids),
            "trading_mode": "Single Advanced Grid with 100% Feature Utilization",
            "grids": all_grids,
            "global_metrics": self.metrics,
            "system_efficiency": "Maximized - No dual-grid overhead",
        }

    async def get_unified_performance_report(self) -> Dict:
        """Generate comprehensive performance report for all active grids"""
        try:
            performance_data = {
                "report_type": "Single Advanced Grid Performance Report",
                "timestamp": time.time(),
                "total_active_grids": len(self.active_grids),
                "system_efficiency": "100% - Unified Architecture",
                "global_metrics": {
                    "total_optimizations": self.metrics["grid_optimizations"],
                    "compound_events": self.metrics["compound_events"],
                    "volatility_adjustments": self.metrics["volatility_adjustments"],
                    "auto_resets": self.metrics["auto_resets"],
                    "precision_orders": self.metrics["precision_orders"],
                    "kelly_adjustments": self.metrics["kelly_adjustments"],
                },
                "grid_summaries": {},
                "feature_utilization": {
                    "compound_management": "100% - Full capital allocation",
                    "volatility_management": "100% - Unified grid adjustment",
                    "market_timing": "100% - Single optimization path",
                    "auto_reset": "100% - Simplified reset logic",
                    "precision_handling": "100% - Single execution path",
                    "kelly_criterion": "100% - Unified position sizing",
                },
            }

            # Add individual grid performance
            for symbol, grid_config in self.active_grids.items():
                try:
                    grid_performance = await self._calculate_grid_performance(
                        symbol, grid_config
                    )
                    performance_data["grid_summaries"][symbol] = grid_performance
                except Exception as e:
                    self.logger.error(
                        f"❌ Performance calculation error for {symbol}: {e}"
                    )

            # Calculate overall system performance
            if performance_data["grid_summaries"]:
                total_capital = sum(
                    grid["total_capital"]
                    for grid in performance_data["grid_summaries"].values()
                )
                total_realized_pnl = sum(
                    grid["realized_pnl"]
                    for grid in performance_data["grid_summaries"].values()
                )

                performance_data["system_performance"] = {
                    "total_capital_deployed": total_capital,
                    "total_realized_pnl": total_realized_pnl,
                    "overall_roi": (total_realized_pnl / total_capital * 100)
                    if total_capital > 0
                    else 0,
                    "architecture_efficiency": "Maximized - Single grid architecture",
                }

            return performance_data

        except Exception as e:
            self.logger.error(f"❌ Performance report generation error: {e}")
            return {"error": str(e)}

    async def _calculate_grid_performance(
        self, symbol: str, grid_config: SingleAdvancedGridConfig
    ) -> Dict:
        """Calculate performance metrics for individual grid"""
        try:
            # Get FIFO performance data
            fifo_performance = self.fifo_service.calculate_fifo_performance(
                self.client_id
            )

            # Count filled orders
            filled_buys = sum(1 for level in grid_config.buy_levels if level["filled"])
            filled_sells = sum(
                1 for level in grid_config.sell_levels if level["filled"]
            )

            # Calculate unrealized PnL (simplified)
            current_price = await self._get_current_price_with_precision(symbol)
            unrealized_pnl = 0.0
            if current_price:
                # Calculate based on open positions
                for level in grid_config.buy_levels:
                    if level["filled"]:
                        unrealized_pnl += (current_price - level["price"]) * level[
                            "quantity"
                        ]

            return {
                "symbol": symbol,
                "total_capital": grid_config.total_capital,
                "strategy": "Single Advanced Grid",
                "levels_active": len(grid_config.buy_levels)
                + len(grid_config.sell_levels),
                "filled_orders": filled_buys + filled_sells,
                "filled_buys": filled_buys,
                "filled_sells": filled_sells,
                "realized_pnl": fifo_performance.get("total_profit", 0.0),
                "unrealized_pnl": unrealized_pnl,
                "current_price": current_price,
                "center_price": grid_config.center_price,
                "price_deviation": (
                    (current_price - grid_config.center_price)
                    / grid_config.center_price
                    * 100
                )
                if current_price and grid_config.center_price
                else 0,
                "compound_multiplier": grid_config.compound_multiplier,
                "volatility_regime": grid_config.volatility_regime,
                "grid_efficiency": self._calculate_grid_efficiency(grid_config),
                "advanced_features_score": self._calculate_features_score(symbol),
            }

        except Exception as e:
            self.logger.error(
                f"❌ Grid performance calculation error for {symbol}: {e}"
            )
            return {"error": str(e)}

    def _calculate_grid_efficiency(
        self, grid_config: SingleAdvancedGridConfig
    ) -> float:
        """Calculate grid efficiency score (0-100)"""
        try:
            total_levels = len(grid_config.buy_levels) + len(grid_config.sell_levels)
            filled_levels = sum(
                1
                for level in grid_config.buy_levels + grid_config.sell_levels
                if level["filled"]
            )

            if total_levels == 0:
                return 0.0

            # Base efficiency from filled orders
            fill_efficiency = (filled_levels / total_levels) * 40  # Max 40 points

            # Compound efficiency bonus
            compound_bonus = (
                min(grid_config.compound_multiplier - 1, 0.5) * 30
            )  # Max 30 points for 1.5x+ compound

            # Volatility adaptation bonus
            volatility_bonus = (
                15 if grid_config.volatility_regime in ["moderate", "high"] else 10
            )  # Max 15 points

            # Configuration optimization bonus
            config_bonus = 15  # Base bonus for advanced configuration

            efficiency = (
                fill_efficiency + compound_bonus + volatility_bonus + config_bonus
            )
            return min(efficiency, 100.0)

        except Exception as e:
            self.logger.error(f"❌ Efficiency calculation error: {e}")
            return 0.0

    def _calculate_features_score(self, symbol: str) -> float:
        """Calculate advanced features utilization score (0-100)"""
        try:
            score = 0

            # Compound management (20 points)
            if self.compound_manager.get_current_multiplier() > 1.0:
                score += 20

            # Volatility management (20 points)
            if symbol in self.volatility_managers:
                score += 20

            # Auto-reset capability (15 points)
            if symbol in self.auto_reset_managers:
                score += 15

            # Market timing (15 points)
            market_session = self.market_timer.get_session_info()
            if market_session["trading_intensity"] != 1.0:  # Active timing adjustments
                score += 15

            # Precision handling (15 points)
            if self.metrics["precision_orders"] > 0:
                score += 15

            # Kelly Criterion (15 points)
            if self.metrics["kelly_adjustments"] > 0:
                score += 15

            return min(score, 100.0)

        except Exception as e:
            self.logger.error(f"❌ Features score calculation error: {e}")
            return 0.0

    async def monitor_and_update_grids(self):
        """
        Continuous monitoring and updating of all active grids
        This replaces the dual-grid monitoring complexity
        """
        try:
            for symbol in list(self.active_grids.keys()):
                try:
                    await self._monitor_single_grid(symbol)
                except Exception as e:
                    self.logger.error(f"❌ Monitoring error for {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"❌ Grid monitoring error: {e}")

    async def _monitor_single_grid(self, symbol: str):
        """Monitor and update individual grid with all advanced features"""
        try:
            grid_config = self.active_grids[symbol]

            # Check for filled orders and replace them
            await self._check_and_replace_filled_orders(symbol, grid_config)

            # Update compound management
            await self._update_compound_management(symbol)

            # Check volatility adjustments
            await self._check_volatility_adjustments(symbol)

            # Check auto-reset conditions
            await self._check_smart_auto_reset(symbol)

            # Update performance tracking
            await self._update_performance_tracking(symbol)

        except Exception as e:
            self.logger.error(f"❌ Single grid monitoring error for {symbol}: {e}")

    async def _check_and_replace_filled_orders_with_inventory(self, symbol: str):
        """
        CONSOLIDATED: Check for filled orders and replace them with inventory management
        This is the ONLY method you need for order replacement
        """
        try:
            grid_config = self.active_grids[symbol]

            # Get open orders to determine which are filled
            open_orders = self.binance_client.get_open_orders(symbol=symbol)
            open_order_ids = {order["orderId"] for order in open_orders}

            self.logger.debug(
                f"🔍 Checking filled orders for {symbol}: {len(open_order_ids)} still open"
            )

            # Check buy levels for fills
            for level in grid_config.buy_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level.get("filled", False)
                ):
                    # Mark as filled
                    level["filled"] = True

                    # Update inventory after fill
                    self.inventory_manager.update_after_fill(
                        symbol, "BUY", level["quantity"], level["price"]
                    )
                    # 🔥 ADD THIS: Log trade execution to database
                    self.trade_repo.log_trade_execution(
                        client_id=self.client_id,
                        symbol=symbol,
                        side="BUY",
                        quantity=level["quantity"],
                        price=level["price"],
                        order_id=level["order_id"],
                    )
                    self.logger.info(
                        f"💰 BUY order filled: Level {level['level']} - {level['quantity']:.4f} @ ${level['price']:.2f}"
                    )
                    # 🔥 NEW: Send notification for order fill
                    await self.working_integration.on_order_filled(
                        symbol,
                        "BUY",
                        level["quantity"],
                        level["price"],
                        level.get("level"),
                    )

                    # Create replacement sell order with inventory check
                    await self._create_replacement_sell_order(
                        symbol, level, grid_config
                    )

            # Check sell levels for fills
            for level in grid_config.sell_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level.get("filled", False)
                ):
                    # Mark as filled
                    level["filled"] = True

                    # Update inventory after fill
                    self.inventory_manager.update_after_fill(
                        symbol, "SELL", level["quantity"], level["price"]
                    )
                    # 🔥 ADD THIS: Log trade execution to database
                    self.trade_repo.log_trade_execution(
                        client_id=self.client_id,
                        symbol=symbol,
                        side="SELL",
                        quantity=level["quantity"],
                        price=level["price"],
                        order_id=level["order_id"],
                    )
                    self.logger.info(
                        f"💰 SELL order filled: Level {level['level']} - {level['quantity']:.4f} @ ${level['price']:.2f}"
                    )
                    # 🔥 NEW: Send notification for order fill
                    await self.working_integration.on_order_filled(
                        symbol,
                        "SELL",
                        level["quantity"],
                        level["price"],
                        level.get("level"),
                    )

                    # Create replacement buy order with inventory check
                    await self._create_replacement_buy_order(symbol, level, grid_config)

            # Update performance metrics if any orders were filled
            filled_orders = sum(
                1
                for level in grid_config.buy_levels + grid_config.sell_levels
                if level.get("filled", False)
            )
            if filled_orders > 0:
                self.metrics["total_trades"] += filled_orders

            # Optional: Run additional management tasks
            await self._run_grid_maintenance(symbol)

        except Exception as e:
            self.logger.error(f"❌ Order replacement error for {symbol}: {e}")

            await self.grid_integration.on_api_error(
                error_code=str(getattr(e, "code", "UNKNOWN")),
                error_message=str(e),
                symbol=symbol,
                operation="order_placement",
            )

    async def _create_replacement_sell_order(
        self, symbol: str, filled_buy_level: Dict, grid_config: SingleAdvancedGridConfig
    ):
        """
        Create replacement sell order when a buy order fills
        """
        try:
            # Get exchange rules for this symbol
            rules = await self._get_exchange_rules_simple(symbol)

            # Calculate new sell price (above the filled buy price)
            spacing = grid_config.grid_spacing
            raw_sell_price = filled_buy_level["price"] * (1 + spacing)

            # Make price valid
            valid_sell_price = self._make_valid_price(
                raw_sell_price, rules["tick_size"], rules["price_precision"]
            )

            # Calculate order size (same USD value as original)
            # Get compound-enhanced order size
            compound_order_size = await self.compound_manager.get_current_order_size(
                self.client_id, symbol, grid_config.total_capital
            )
            order_usd = compound_order_size  # Growing with profits!
            raw_quantity = order_usd / valid_sell_price

            # Make quantity valid
            valid_quantity = self._make_valid_quantity(
                raw_quantity,
                rules["step_size"],
                rules["quantity_precision"],
                rules["min_qty"],
            )

            # Check if we can place the sell order
            can_place, reason = self.inventory_manager.can_place_sell_order(
                symbol, valid_quantity
            )

            if can_place:
                # Reserve inventory
                if self.inventory_manager.reserve_for_order(
                    symbol, "SELL", valid_quantity, valid_sell_price
                ):
                    try:
                        # Format strings for order
                        quantity_str = (
                            f"{valid_quantity:.{rules['quantity_precision']}f}".rstrip(
                                "0"
                            ).rstrip(".")
                        )
                        price_str = (
                            f"{valid_sell_price:.{rules['price_precision']}f}".rstrip(
                                "0"
                            ).rstrip(".")
                        )

                        # Ensure minimum formatting
                        if "." not in quantity_str and rules["quantity_precision"] > 0:
                            quantity_str += ".0"
                        if "." not in price_str and rules["price_precision"] > 0:
                            price_str += ".0"

                        # Place sell order
                        order = self.binance_client.order_limit_sell(
                            symbol=symbol,
                            quantity=quantity_str,
                            price=price_str,
                            recvWindow=60000,
                        )

                        # Create new sell level
                        new_sell_level = {
                            "level": filled_buy_level["level"]
                            + 100,  # Offset to avoid conflicts
                            "side": "SELL",
                            "price": valid_sell_price,
                            "quantity": valid_quantity,
                            "order_size_usd": valid_quantity * valid_sell_price,
                            "order_id": order["orderId"],
                            "filled": False,
                            "created_from_buy": filled_buy_level["level"],
                        }

                        # Add to grid config
                        grid_config.sell_levels.append(new_sell_level)

                        self.logger.info(
                            f"✅ Replacement SELL order: {valid_quantity:.4f} @ ${valid_sell_price:.4f} (from buy level {filled_buy_level['level']})"
                        )

                    except Exception as e:
                        # Release reservation if order failed
                        self.inventory_manager.release_reservation(
                            symbol, "SELL", valid_quantity, valid_sell_price
                        )
                        self.logger.error(
                            f"❌ Failed to place replacement SELL order: {e}"
                        )
                else:
                    self.logger.warning(
                        "⚠️ Could not reserve inventory for replacement SELL order"
                    )
            else:
                self.logger.warning(f"⚠️ Cannot place replacement SELL order: {reason}")

        except Exception as e:
            self.logger.error(f"❌ Create replacement sell order error: {e}")

            await self.grid_integration.on_api_error(
                error_code=str(getattr(e, "code", "UNKNOWN")),
                error_message=str(e),
                symbol=symbol,
                operation="order_placement",
            )

    async def _create_replacement_buy_order(
        self,
        symbol: str,
        filled_sell_level: Dict,
        grid_config: SingleAdvancedGridConfig,
    ):
        """
        Create replacement buy order when a sell order fills
        """
        try:
            # Get exchange rules for this symbol
            rules = await self._get_exchange_rules_simple(symbol)

            # Calculate new buy price (below the filled sell price)
            spacing = grid_config.grid_spacing
            raw_buy_price = filled_sell_level["price"] * (1 - spacing)

            # Make price valid
            valid_buy_price = self._make_valid_price(
                raw_buy_price, rules["tick_size"], rules["price_precision"]
            )

            # Calculate order size (same USD value as original)
            # Get compound-enhanced order size
            compound_order_size = await self.compound_manager.get_current_order_size(
                self.client_id, symbol, grid_config.total_capital
            )
            order_usd = compound_order_size  # Growing with profits!
            raw_quantity = order_usd / valid_buy_price

            # Make quantity valid
            valid_quantity = self._make_valid_quantity(
                raw_quantity,
                rules["step_size"],
                rules["quantity_precision"],
                rules["min_qty"],
            )

            # Calculate actual order value
            actual_order_value = valid_quantity * valid_buy_price

            # Check if we can place the buy order
            can_place, reason = self.inventory_manager.can_place_buy_order(
                symbol, actual_order_value
            )

            if can_place:
                # Reserve inventory
                if self.inventory_manager.reserve_for_order(
                    symbol, "BUY", valid_quantity, valid_buy_price
                ):
                    try:
                        # Format strings for order
                        quantity_str = (
                            f"{valid_quantity:.{rules['quantity_precision']}f}".rstrip(
                                "0"
                            ).rstrip(".")
                        )
                        price_str = (
                            f"{valid_buy_price:.{rules['price_precision']}f}".rstrip(
                                "0"
                            ).rstrip(".")
                        )

                        # Ensure minimum formatting
                        if "." not in quantity_str and rules["quantity_precision"] > 0:
                            quantity_str += ".0"
                        if "." not in price_str and rules["price_precision"] > 0:
                            price_str += ".0"

                        # Place buy order
                        order = self.binance_client.order_limit_buy(
                            symbol=symbol,
                            quantity=quantity_str,
                            price=price_str,
                            recvWindow=60000,
                        )

                        # Create new buy level
                        new_buy_level = {
                            "level": filled_sell_level["level"]
                            - 100,  # Offset to avoid conflicts
                            "side": "BUY",
                            "price": valid_buy_price,
                            "quantity": valid_quantity,
                            "order_size_usd": actual_order_value,
                            "order_id": order["orderId"],
                            "filled": False,
                            "created_from_sell": filled_sell_level["level"],
                        }

                        # Add to grid config
                        grid_config.buy_levels.append(new_buy_level)

                        self.logger.info(
                            f"✅ Replacement BUY order: {valid_quantity:.4f} @ ${valid_buy_price:.4f} (from sell level {filled_sell_level['level']})"
                        )

                    except Exception as e:
                        # Release reservation if order failed
                        self.inventory_manager.release_reservation(
                            symbol, "BUY", valid_quantity, valid_buy_price
                        )
                        self.logger.error(
                            f"❌ Failed to place replacement BUY order: {e}"
                        )
                        await self.grid_integration.on_api_error(
                            error_code=str(getattr(e, "code", "UNKNOWN")),
                            error_message=str(e),
                            symbol=symbol,
                            operation="order_placement",
                        )
                else:
                    self.logger.warning(
                        "⚠️ Could not reserve inventory for replacement BUY order"
                    )
            else:
                self.logger.warning(f"⚠️ Cannot place replacement BUY order: {reason}")

        except Exception as e:
            self.logger.error(f"❌ Create replacement buy order error: {e}")

            await self.grid_integration.on_api_error(
                error_code=str(getattr(e, "code", "UNKNOWN")),
                error_message=str(e),
                symbol=symbol,
                operation="order_placement",
            )

    def _should_log_inventory(self) -> bool:
        """Helper to determine when to log inventory status (every 5 minutes)"""
        import time

        return int(time.time()) % 300 == 0

    def get_inventory_status_for_all_grids(self) -> Dict:
        """
        ADD this new method: Get inventory status for all active grids
        """
        if not self.inventory_manager:
            return {"error": "Inventory manager not initialized"}

        status = {
            "total_capital": f"${self.inventory_manager.total_capital:,.2f}",
            "assets": {},
            "allocation_reasoning": self.inventory_manager.get_allocation_reasoning(),
        }

        for symbol in self.active_grids.keys():
            status["assets"][symbol] = self.inventory_manager.get_inventory_status(
                symbol
            )

        return status

    # SIMPLE BULLETPROOF FIX: Add this method to your single_advanced_grid_manager.py

    async def _get_exchange_rules_simple(self, symbol: str) -> dict:
        """Get exchange rules with bulletproof fallbacks for any asset"""
        try:
            self.logger.info(f"🔍 Getting exchange rules for {symbol}")

            # Fetch from Binance API
            exchange_info = self.binance_client.get_exchange_info()

            for sym_info in exchange_info["symbols"]:
                if sym_info["symbol"] == symbol:
                    # Extract filters
                    filters = {}
                    for filter_info in sym_info.get("filters", []):
                        filters[filter_info["filterType"]] = filter_info

                    # Get price filter (tick_size)
                    price_filter = filters.get("PRICE_FILTER", {})
                    tick_size = float(price_filter.get("tickSize", "0.00000001"))

                    # Get lot size filter (step_size)
                    lot_size = filters.get("LOT_SIZE", {})
                    step_size = float(lot_size.get("stepSize", "0.00000001"))
                    min_qty = float(lot_size.get("minQty", "0.00000001"))

                    # Get minimum notional
                    min_notional = filters.get("MIN_NOTIONAL", {})
                    min_notional_value = float(min_notional.get("minNotional", "5.0"))

                    rules = {
                        "symbol": symbol,
                        "tick_size": tick_size,
                        "step_size": step_size,
                        "min_qty": min_qty,
                        "min_notional": min_notional_value,
                        "price_precision": self._get_precision_from_step(tick_size),
                        "quantity_precision": self._get_precision_from_step(step_size),
                    }

                    self.logger.info(f"✅ Exchange rules for {symbol}:")
                    self.logger.info(
                        f"   💲 Price: tick_size={tick_size}, precision={rules['price_precision']}"
                    )
                    self.logger.info(
                        f"   📦 Quantity: step_size={step_size}, precision={rules['quantity_precision']}"
                    )
                    self.logger.info(f"   💰 Min notional: ${min_notional_value}")

                    return rules

            raise ValueError(f"Symbol {symbol} not found")

        except Exception as e:
            self.logger.error(f"❌ Failed to get exchange rules for {symbol}: {e}")
            # Return safe defaults
            return {
                "symbol": symbol,
                "tick_size": 0.00000001,
                "step_size": 0.00000001,
                "min_qty": 0.00000001,
                "min_notional": 10.0,
                "price_precision": 8,
                "quantity_precision": 8,
            }

    def _get_precision_from_step(self, step_size: float) -> int:
        """Calculate precision from step size"""
        try:
            if step_size >= 1:
                return 0

            # Convert to string and count decimal places
            step_str = f"{step_size:.10f}".rstrip("0")
            if "." in step_str:
                return len(step_str.split(".")[1])
            return 0
        except:
            return 8

    def _make_valid_price(
        self, price: float, tick_size: float, precision: int
    ) -> float:
        """Make any price valid for Binance"""
        try:
            # Round to tick size
            rounded = round(price / tick_size) * tick_size

            # Format with correct precision
            formatted = round(rounded, precision)

            return formatted
        except:
            return round(price, precision)

    def _make_valid_quantity(
        self, quantity: float, step_size: float, precision: int, min_qty: float
    ) -> float:
        """Make any quantity valid for Binance"""
        try:
            # Round to step size
            rounded = round(quantity / step_size) * step_size

            # Ensure minimum quantity
            if rounded < min_qty:
                rounded = min_qty

            # Format with correct precision
            formatted = round(rounded, precision)

            return formatted
        except:
            return max(round(quantity, precision), min_qty)

    async def _create_enhanced_sell_order(
        self, symbol: str, buy_level: Dict, grid_config: SingleAdvancedGridConfig
    ):
        """Create enhanced sell order when buy order is filled"""
        try:
            # Get current compound multiplier
            compound_multiplier = self.compound_manager.get_current_multiplier()

            # Calculate sell price with enhanced spacing
            spacing_multiplier = 1.5  # Enhanced spacing for sells
            sell_price = buy_level["price"] * (
                1 + grid_config.grid_spacing * spacing_multiplier
            )

            # Use same quantity as buy (maintaining coin balance)
            sell_quantity = buy_level["quantity"]

            # Execute precision sell order
            order_result = await self.precision_handler.execute_precision_order(
                symbol, "SELL", sell_quantity, sell_price
            )

            if order_result["success"]:
                # Add to sell levels or update existing
                sell_level = {
                    "level": abs(buy_level["level"]),
                    "side": "SELL",
                    "price": order_result["price"],
                    "quantity": order_result["quantity"],
                    "order_id": order_result["order_id"],
                    "filled": False,
                    "created_from_buy": buy_level["level"],
                }

                grid_config.sell_levels.append(sell_level)

                # Log the trade
                self.trade_repo.log_grid_order(
                    client_id=self.client_id,
                    symbol=symbol,
                    side="SELL",
                    quantity=order_result["quantity"],
                    price=order_result["price"],
                    order_id=order_result["order_id"],
                    grid_level=sell_level["level"],
                )

                self.logger.info(
                    f"✅ Enhanced sell order created: {sell_quantity:.6f} @ ${sell_price:.6f}"
                )

        except Exception as e:
            self.logger.error(f"❌ Enhanced sell order creation error: {e}")

    async def _create_enhanced_buy_order(
        self, symbol: str, sell_level: Dict, grid_config: SingleAdvancedGridConfig
    ):
        """Create enhanced buy order when sell order is filled"""
        try:
            # Get current compound order size (enhanced by profits)
            compound_order_size = await self.compound_manager.get_current_order_size(
                self.client_id, symbol, grid_config.total_capital
            )

            # Calculate buy price with enhanced spacing
            spacing_multiplier = 1.5
            buy_price = sell_level["price"] * (
                1 - grid_config.grid_spacing * spacing_multiplier
            )

            # Use compound-enhanced order size
            buy_quantity = compound_order_size / buy_price

            # Execute precision buy order
            order_result = await self.precision_handler.execute_precision_order(
                symbol, "BUY", buy_quantity, buy_price
            )

            if order_result["success"]:
                # Add to buy levels or update existing
                buy_level = {
                    "level": -abs(sell_level["level"]),
                    "side": "BUY",
                    "price": order_result["price"],
                    "quantity": order_result["quantity"],
                    "order_id": order_result["order_id"],
                    "filled": False,
                    "created_from_sell": sell_level["level"],
                }

                grid_config.buy_levels.append(buy_level)

                # Log the trade
                self.trade_repo.log_grid_order(
                    client_id=self.client_id,
                    symbol=symbol,
                    side="BUY",
                    quantity=order_result["quantity"],
                    price=order_result["price"],
                    order_id=order_result["order_id"],
                    grid_level=buy_level["level"],
                )

                self.logger.info(
                    f"✅ Enhanced buy order created: {buy_quantity:.6f} @ ${buy_price:.6f}"
                )

        except Exception as e:
            self.logger.error(f"❌ Enhanced buy order creation error: {e}")

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
            base_order_size = self.compound_manager.get_current_order_size(
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
        """Execute smart grid reset"""
        try:
            grid_config = self.active_grids[symbol]

            # Cancel all existing orders
            for level in grid_config.buy_levels + grid_config.sell_levels:
                if level["order_id"] and not level["filled"]:
                    try:
                        self.binance_client.cancel_order(
                            symbol=symbol, orderId=level["order_id"]
                        )
                    except:
                        pass  # Order may already be filled or cancelled

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

            # Create new grid levels
            new_grid_levels = await self._create_advanced_grid_levels(
                grid_config, new_center_price, optimal_config
            )

            # Execute new grid setup
            await self._execute_precision_grid_setup(grid_config, new_grid_levels)

            self.logger.info(
                f"✅ Smart reset completed for {symbol} at ${new_center_price:.6f}"
            )

        except Exception as e:
            self.logger.error(f"❌ Smart reset execution error for {symbol}: {e}")

    async def _update_performance_tracking(self, symbol: str):
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
            grid_performance = await self._calculate_grid_performance(
                symbol, self.active_grids[symbol]
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

    async def _run_grid_maintenance(self, symbol: str):
        """
        Optional: Run additional maintenance tasks after order fills
        """
        try:
            # Update compound management if available
            if hasattr(self, "compound_manager"):
                try:
                    current_multiplier = self.compound_manager.get_current_multiplier()
                    self.logger.debug(
                        f"🔄 Compound multiplier for {symbol}: {current_multiplier:.2f}x"
                    )
                except:
                    pass

            # Check if grid needs rebalancing
            if hasattr(self, "inventory_manager"):
                try:
                    should_rebalance, reason = self.inventory_manager.should_rebalance(
                        symbol
                    )
                    if should_rebalance:
                        self.logger.info(f"🔄 {symbol} may need rebalancing: {reason}")
                except:
                    pass

            # Update performance metrics
            self.metrics["compound_events"] += 1

        except Exception as e:
            self.logger.debug(f"⚠️ Grid maintenance warning for {symbol}: {e}")
            # Don't let maintenance errors break the main flow

    async def _notify_trade_execution(self, symbol: str, side: str, order: dict):
        """Notify FIFO monitoring system of trade execution"""
        try:
            if hasattr(self, "notification_manager"):
                # Ensure client monitoring is set up
                await self.notification_manager.add_client_monitor(self.client_id)

                # Notify the trade execution
                await self.notification_manager.on_trade_executed(
                    client_id=self.client_id,
                    symbol=symbol,
                    side=side,
                    quantity=float(order["origQty"]),
                    price=float(order["price"]),
                )

                self.logger.debug(
                    f"📊 FIFO notification: {symbol} {side} {order['origQty']}@{order['price']}"
                )

        except Exception as e:
            self.logger.error(f"❌ Error notifying trade execution: {e}")


# ADD this helper function outside the class
def get_force_command_allocation(symbol: str, amount: float) -> Dict:
    """
    Helper function for FORCE commands with proper allocation
    CALL this from your handle_force_command method
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
