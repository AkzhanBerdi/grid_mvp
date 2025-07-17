# services/dual_scale_grid_manager.py
"""Smart 35/65 Dual-Scale Grid System - FIXED TIMESTAMP AND API ISSUES"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Tuple

from binance.client import Client

from models.adaptive_grid_config import AdaptiveGridConfig
from repositories.client_repository import ClientRepository
from repositories.trade_repository import TradeRepository
from services.advanced_trading_features import (
    CompoundInterestManager,
    IntelligentMarketTimer,
    PrecisionOrderHandler,
)
from services.compound_interest_manager import CompoundIntegrationService
from services.fifo_service import FIFOService
from services.market_analysis import MarketAnalysisService, MarketCondition
from services.volatility_order_sizer import (
    VolatilityCompoundIntegration,
    VolatilityOrderSizer,
)

"""
INTEGRATION EXAMPLE:
===================

# In your DualScaleGridManager:
from services.volatility_order_sizer import VolatilityOrderSizer, VolatilityCompoundIntegration

class DualScaleGridManager:
    def __init__(self, binance_client, client_id):
        # ... existing compound manager setup ...
        
        # Add volatility sizer
        self.volatility_sizer = VolatilityOrderSizer()
        
        # Create integrated optimizer
        self.optimizer = VolatilityCompoundIntegration(
            self.compound_service.compound_manager,
            self.volatility_sizer
        )
    
    async def start_dual_scale_grid(self, symbol: str, total_capital: float):
        # Get fully optimized configuration
        config = await self.optimizer.get_optimized_grid_config(
            self.client_id, symbol, total_capital
        )
        
        # Use optimized parameters
        order_size = config['order_size']
        grid_spacing = config['grid_spacing']
        grid_levels = config['grid_levels']
        allocation = config['allocation']
        
        self.logger.info(f"🎯 Using optimized config: {config['optimization_summary']}")
        
        # Continue with grid setup using optimized values...

EXPECTED RESULTS:
================
- Order sizes automatically adjust to market volatility
- Calm markets: 30% larger orders, tighter grids
- Volatile markets: 40% smaller orders, wider grids  
- Combined with compound interest for optimal growth
- Real-time volatility monitoring and adjustment
- Risk-appropriate grid level adjustments
"""


class DualScaleGridManager:
    """Smart 35/65 dual-scale grid system - FIXED ALL BINANCE API ISSUES"""

    def __init__(self, binance_client: Client, client_id: int):
        self.binance_client = binance_client
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        self.fifo_service = FIFOService()
        self.compound_service = CompoundIntegrationService(self.fifo_service)
        self.order_sizer = self.compound_service.compound_manager
        # Initialize compound tracking
        asyncio.create_task(self.compound_service.initialize_client(client_id))

        self.volatility_sizer = VolatilityOrderSizer()
        # Create integrated optimizer
        self.optimizer = VolatilityCompoundIntegration(
            self.compound_service.compound_manager, self.volatility_sizer
        )
        self.compound_manager = CompoundInterestManager(client_id)
        self.market_timer = IntelligentMarketTimer()
        self.precision_handler = PrecisionOrderHandler(binance_client)

        # Initialize services
        self.market_analysis = MarketAnalysisService(binance_client)
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()

        # Grid state
        self.active_grids: Dict[str, AdaptiveGridConfig] = {}
        self.last_market_check = {}
        self.last_balance_check = {}

        # Minimum conservative allocation
        self.min_base_allocation = 0.2
        self.max_enhanced_allocation = 0.8  # Maximum aggressive allocation
        self.default_base_allocation = 0.4  # Starting point
        # Symbol configurations
        self.symbol_configs = {
            "ADAUSDT": {
                "min_notional": 10.0,
                "price_precision": 4,
                "quantity_precision": 0,
                "min_quantity": 10,
                "min_base_for_sells": 20.0,
                "base_levels": 5,
                "enhanced_levels": 8,
            },
            "AVAXUSDT": {
                "min_notional": 10.0,
                "price_precision": 2,
                "quantity_precision": 3,
                "min_quantity": 0.1,
                "min_base_for_sells": 0.5,
                "base_levels": 5,
                "enhanced_levels": 8,
            },
        }

        # Performance tracking
        self.performance_metrics = {
            "total_trades": 0,
            "total_profit": 0.0,
            "base_grid_trades": 0,
            "enhanced_grid_trades": 0,
            "dual_scale_adaptations": 0,
        }
        # Fixed intervals removed - will be calculated dynamically
        self.min_market_check_interval = 120  # 2 minutes minimum
        self.max_market_check_interval = 600  # 10 minutes maximum
        self.min_balance_check_interval = 30  # 30 seconds minimum
        self.max_balance_check_interval = 300  # 5 minutes maximum

    async def get_account_balance(self):
        """Get account balance for notifications"""
        try:
            account = self._safe_binance_call("get_account")
            balances = {
                balance["asset"]: float(balance["free"])
                for balance in account["balances"]
            }
            return balances
        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return {}

    async def get_current_price(self, symbol: str):
        """Get current price for notifications"""
        try:
            ticker = self._safe_binance_call("get_symbol_ticker", symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            return 0.0

    async def send_grid_startup_notification(
        self,
        client_id: int,
        symbol: str,
        total_capital: float,
        base_orders: int,
        enhanced_orders: int,
        total_orders: int,
    ):
        """Send comprehensive grid startup notification"""
        try:
            from services.telegram_notifier import TelegramNotifier
            from utils.fifo_telegram_monitor import FIFOProfitMonitor

            # Initialize notifiers
            telegram_notifier = TelegramNotifier()

            if not telegram_notifier.enabled:
                self.logger.warning("Telegram notifications disabled")
                return

            # Get current account balances for the notification
            account_balances = await self.get_account_balance()
            ada_balance = float(account_balances.get("ADA", 0))
            usdt_balance = float(account_balances.get("USDT", 0))

            # Calculate orders breakdown
            base_buy_orders = base_orders // 2
            base_sell_orders = base_orders - base_buy_orders
            enhanced_buy_orders = enhanced_orders // 2
            enhanced_sell_orders = enhanced_orders - enhanced_buy_orders

            # Get current price
            current_price = await self.get_current_price(symbol)

            # Create comprehensive startup message
            startup_message = f"""🚀 **Grid Trading System ACTIVATED**

    **📊 Trading Pair:** {symbol}
    **💰 Total Capital:** ${total_capital:,.2f}
    **📈 Current Price:** ${current_price:.4f}

    **🔧 Grid Configuration:**
    💙 **Base Grid (35%):** {base_orders} orders
    • Buy Orders: {base_buy_orders}
    • Sell Orders: {base_sell_orders}
    • Spacing: 2.5%

    🚀 **Enhanced Grid (65%):** {enhanced_orders} orders  
    • Buy Orders: {enhanced_buy_orders}
    • Sell Orders: {enhanced_sell_orders}
    • Spacing: 2.0%

    **📊 Total Active Orders:** {total_orders}

    **💼 Account Status:**
    • ADA Balance: {ada_balance:,.2f}
    • USDT Balance: ${usdt_balance:,.2f}

    **⚠️ Order Placement Summary:**
    • Planned Orders: 26
    • Successfully Placed: {total_orders}
    {"• ⚠️ Some sell orders skipped due to insufficient ADA balance" if total_orders < 26 else "• ✅ All orders placed successfully"}

    **🎯 System Status:** ACTIVE & MONITORING
    **⏰ Started:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

    💡 **The grid is now hunting for profits!**"""

            # Send the startup notification
            await telegram_notifier.send_message(startup_message)

            # Initialize FIFO monitoring with startup notification
            try:
                fifo_monitor = FIFOProfitMonitor(client_id)
                await fifo_monitor.initialize()  # This sends its own startup status
            except Exception as e:
                self.logger.warning(f"FIFO monitor initialization failed: {e}")

            self.logger.info(
                f"✅ Grid startup notification sent for client {client_id}"
            )

        except Exception as e:
            self.logger.error(f"Failed to send grid startup notification: {e}")

    def _safe_binance_call(self, method_name: str, *args, **kwargs):
        """Simplified API calls with automatic timestamp handling"""
        try:
            method = getattr(self.binance_client, method_name)

            # Add recvWindow for authenticated calls only
            if method_name in [
                "get_account",
                "get_open_orders",
                "order_limit_buy",
                "order_limit_sell",
                "cancel_order",
            ]:
                kwargs["recvWindow"] = 60000

            return method(*args, **kwargs)

        except Exception as e:
            self.logger.error(f"❌ Binance API call failed: {method_name} - {e}")
            raise

    def _sync_server_time(self):
        """Simple, reliable time sync"""
        try:
            import requests

            base_url = (
                "https://testnet.binance.vision"
                if getattr(self.binance_client, "testnet", False)
                else "https://api.binance.com"
            )
            response = requests.get(f"{base_url}/api/v3/time", timeout=10)
            server_time = response.json()["serverTime"]
            local_time = int(time.time() * 1000)

            # Set offset once - handles all future requests automatically
            self.binance_client.timestamp_offset = server_time - local_time
            self.logger.info(
                f"🔄 Time sync: offset {self.binance_client.timestamp_offset}ms"
            )
            return True

        except Exception as e:
            self.logger.warning(f"Time sync failed: {e}")
            self.binance_client.timestamp_offset = -5000  # Safe fallback
            return True  # Continue anyway

    async def start_dual_scale_grid(self, symbol: str, total_capital: float) -> Dict:
        """Start intelligent 35/65 dual-scale grid system - FIXED VERSION"""

        # Get fully optimized configuration
        config = await self.optimizer.get_optimized_grid_config(
            self.client_id, symbol, total_capital
        )

        # Use optimized parameters
        order_size = config["order_size"]
        grid_spacing = config["grid_spacing"]
        grid_levels = config["grid_levels"]
        allocation = config["allocation"]

        self.logger.info(f"🎯 Using optimized config: {config['optimization_summary']}")

        # Continue with grid setup using optimized values...
        # Get dynamic allocation (replaces fixed BASE_ALLOCATION/ENHANCED_ALLOCATION)
        allocation = await self.order_sizer.get_grid_allocation(
            self.client_id, total_capital
        )
        base_capital = allocation["base_capital"]
        enhanced_capital = allocation["enhanced_capital"]

        # Get dynamic order size (replaces fixed order_size)
        base_order_size = await self.order_sizer.get_current_order_size(
            self.client_id, symbol, base_capital
        )
        enhanced_order_size = await self.order_sizer.get_current_order_size(
            self.client_id, symbol, enhanced_capital
        )

        # Continue with existing logic but using dynamic values...
        try:
            self.logger.info(
                f"🚀 Starting 35/65 dual-scale grid for {symbol} with ${total_capital:,.2f}"
            )

            # Simple time sync once
            self._sync_server_time()

            # Calculate capital allocation
            base_capital = total_capital * self.BASE_ALLOCATION  # 35%
            enhanced_capital = total_capital * self.ENHANCED_ALLOCATION  # 65%

            self.logger.info("💰 Capital Allocation Strategy:")
            self.logger.info(
                f"   💙 Base Grid (35%): ${base_capital:.2f} - Conservative foundation"
            )
            self.logger.info(
                f"   🚀 Enhanced Grid (65%): ${enhanced_capital:.2f} - Aggressive profit capture"
            )

            # Get account balances with FIXED timestamp handling
            self.logger.info("📊 Getting account balances...")
            account = self._safe_binance_call("get_account")
            balances = {
                balance["asset"]: float(balance["free"])
                for balance in account["balances"]
            }

            base_asset = symbol.replace("USDT", "")
            quote_asset = "USDT"

            base_balance = balances.get(base_asset, 0.0)
            quote_balance = balances.get(quote_asset, 0.0)

            self.logger.info("💰 Account balances:")
            self.logger.info(f"   {base_asset}: {base_balance}")
            self.logger.info(f"   {quote_asset}: {quote_balance}")

            # Validate minimum capital for dual-scale system
            min_required = 100.0
            if total_capital < min_required:
                return {
                    "success": False,
                    "error": f"Minimum capital for dual-scale system: ${min_required} (current: ${total_capital:.2f})",
                }

            # Get current market condition
            try:
                self.logger.info("📈 Analyzing market conditions...")
                market_condition = await self.market_analysis.get_market_condition(
                    symbol
                )
            except Exception as e:
                self.logger.warning(f"Market analysis failed, using neutral: {e}")
                market_condition = {
                    "condition": MarketCondition.NEUTRAL,
                    "score": 0.5,
                    "confidence": 0.0,
                    "indicators": {
                        "rsi": 50.0,
                        "volatility": 0.25,
                        "volume_ratio": 1.0,
                        "price_trend": 0.0,
                    },
                }

            # Determine dual-scale strategy
            grid_strategy = self._determine_dual_scale_strategy(
                symbol, base_balance, quote_balance, total_capital, market_condition
            )

            # FIXED: Get current price with proper error handling
            self.logger.info(f"💹 Getting current price for {symbol}...")
            try:
                ticker = self._safe_binance_call("get_symbol_ticker", symbol=symbol)
                current_price = float(ticker["price"])
                self.logger.info(f"📊 Current {symbol} price: ${current_price:.4f}")
            except Exception as e:
                self.logger.error(f"❌ Failed to get current price for {symbol}: {e}")
                return {
                    "success": False,
                    "error": f"Failed to get market price: {str(e)}",
                }

            # Create adaptive grid configuration
            adaptive_config = AdaptiveGridConfig(
                symbol=symbol,
                client_id=self.client_id,
                total_capital=total_capital,
                market_condition=market_condition,
                grid_config=grid_strategy,
            )

            # Initialize dual-scale grids
            await self._initialize_dual_scale_grids(
                adaptive_config, current_price, grid_strategy
            )

            # Store active grid
            self.active_grids[symbol] = adaptive_config

            # Start monitoring
            asyncio.create_task(self._monitor_dual_scale_grid(symbol))

            result = {
                "success": True,
                "symbol": symbol,
                "strategy": "dual_scale_35_65",
                "market_condition": market_condition["condition"],
                "market_score": market_condition["score"],
                "current_price": current_price,
                "capital_allocation": {
                    "base_grid": {
                        "percentage": 35,
                        "capital": base_capital,
                        "purpose": "Conservative foundation",
                    },
                    "enhanced_grid": {
                        "percentage": 65,
                        "capital": enhanced_capital,
                        "purpose": "Aggressive profit capture",
                    },
                },
                "grid_info": grid_strategy,
                "balances": {
                    "base_asset": base_asset,
                    "base_balance": base_balance,
                    "quote_asset": quote_asset,
                    "quote_balance": quote_balance,
                },
            }

            await self.complete_grid_initialization(
                self.client_id, symbol, total_capital
            )
            self.active_grids[symbol] = adaptive_config
            asyncio.create_task(self._monitor_dual_scale_grid(symbol))
            return result

        except Exception as e:
            self.logger.error(f"❌ Failed to start dual-scale grid: {e}")
            return {"success": False, "error": str(e)}

    def _determine_dual_scale_strategy(
        self,
        symbol: str,
        base_balance: float,
        quote_balance: float,
        total_capital: float,
        market_condition: Dict,
    ) -> Dict:
        """Determine optimal dual-scale strategy based on balances and market"""

        symbol_config = self.symbol_configs.get(symbol, {})
        min_base_for_sells = symbol_config.get("min_base_for_sells", 10.0)
        min_notional = symbol_config.get("min_notional", 10.0)

        base_levels = symbol_config.get("base_levels", 5)
        enhanced_levels = symbol_config.get("enhanced_levels", 8)

        # Calculate capital allocation
        base_capital = total_capital * self.BASE_ALLOCATION
        enhanced_capital = total_capital * self.ENHANCED_ALLOCATION

        # Calculate order sizes for each grid
        base_order_size = base_capital / (base_levels * 2)
        enhanced_order_size = enhanced_capital / (enhanced_levels * 2)

        # Ensure minimum notional compliance
        if base_order_size < min_notional:
            base_levels = max(3, int(base_capital / (min_notional * 2)))
            base_order_size = base_capital / (base_levels * 2)

        if enhanced_order_size < min_notional:
            enhanced_levels = max(4, int(enhanced_capital / (min_notional * 2)))
            enhanced_order_size = enhanced_capital / (enhanced_levels * 2)

        # Determine grid spacing based on market condition
        market_score = market_condition.get("score", 0.5)
        volatility = market_condition.get("indicators", {}).get("volatility", 0.25)

        # Base grid: Always conservative
        base_spacing = 0.025  # 2.5% conservative spacing

        # Enhanced grid: Adaptive spacing
        if market_score > 0.7:  # Strong bullish
            enhanced_spacing = max(0.01, 0.02 - volatility * 0.01)
        elif market_score < 0.3:  # Strong bearish
            enhanced_spacing = min(0.04, 0.03 + volatility * 0.01)
        else:  # Neutral
            enhanced_spacing = 0.02 + volatility * 0.005

        # Strategy determination
        if base_balance >= min_base_for_sells:
            strategy_type = "dual_scale_full"
            can_place_sells = True
        else:
            strategy_type = "dual_scale_accumulation"
            can_place_sells = False

        return {
            "strategy_type": strategy_type,
            "base_grid": {
                "levels": base_levels,
                "order_size": base_order_size,
                "spacing": base_spacing,
                "capital": base_capital,
                "purpose": "Conservative foundation",
            },
            "enhanced_grid": {
                "levels": enhanced_levels,
                "order_size": enhanced_order_size,
                "spacing": enhanced_spacing,
                "capital": enhanced_capital,
                "purpose": "Aggressive profit capture",
            },
            "can_place_sells": can_place_sells,
            "market_adaptations": {
                "enhanced_spacing_adaptive": True,
                "market_condition": market_condition.get("condition"),
                "market_score": market_score,
                "volatility_factor": volatility,
            },
        }

    async def _initialize_dual_scale_grids(
        self,
        adaptive_config: AdaptiveGridConfig,
        current_price: float,
        grid_strategy: Dict,
    ) -> None:
        """Initialize both base and enhanced grids with 35/65 allocation"""
        try:
            strategy_type = grid_strategy["strategy_type"]
            base_config = grid_strategy["base_grid"]
            enhanced_config = grid_strategy["enhanced_grid"]

            self.logger.info(f"🎯 Initializing {strategy_type} dual-scale system")
            self.logger.info(
                f"💙 BASE GRID (35%): {base_config['levels']} levels, ${base_config['order_size']:.2f}/order, {base_config['spacing'] * 100:.1f}% spacing"
            )
            self.logger.info(
                f"🚀 ENHANCED GRID (65%): {enhanced_config['levels']} levels, ${enhanced_config['order_size']:.2f}/order, {enhanced_config['spacing'] * 100:.1f}% spacing"
            )

            # Configure BASE GRID (35% - Conservative Foundation)
            adaptive_config.base_grid.grid_levels = base_config["levels"]
            adaptive_config.base_grid.order_size = base_config["order_size"]
            adaptive_config.base_grid.grid_spacing = base_config["spacing"]
            adaptive_config.base_grid.calculate_grid_levels(current_price)

            # Configure ENHANCED GRID (65% - Aggressive Profit Capture)
            adaptive_config.enhanced_grid.grid_levels = enhanced_config["levels"]
            adaptive_config.enhanced_grid.order_size = enhanced_config["order_size"]
            adaptive_config.enhanced_grid.grid_spacing = enhanced_config["spacing"]
            adaptive_config.enhanced_grid.calculate_grid_levels(current_price)

            # Execute BASE GRID setup (always active)
            self.logger.info("💙 Setting up BASE GRID (35% allocation)...")
            base_buy_result = await self._execute_smart_buy_setup(
                adaptive_config.base_grid, "BASE_BUY"
            )

            base_sell_result = False
            if grid_strategy["can_place_sells"]:
                base_sell_result = await self._execute_smart_sell_setup(
                    adaptive_config.base_grid, "BASE_SELL"
                )

            # Execute ENHANCED GRID setup
            self.logger.info("🚀 Setting up ENHANCED GRID (65% allocation)...")
            enhanced_buy_result = await self._execute_smart_buy_setup(
                adaptive_config.enhanced_grid, "ENHANCED_BUY"
            )

            enhanced_sell_result = False
            if grid_strategy["can_place_sells"]:
                enhanced_sell_result = await self._execute_smart_sell_setup(
                    adaptive_config.enhanced_grid, "ENHANCED_SELL"
                )
                adaptive_config.enhanced_grid_active = True
            else:
                adaptive_config.enhanced_grid_active = False
                min_base_needed = self.symbol_configs.get(
                    adaptive_config.symbol, {}
                ).get("min_base_for_sells", 20.0)
                self.logger.info(
                    f"📈 Enhanced sells will activate when {adaptive_config.symbol.replace('USDT', '')} balance reaches {min_base_needed}"
                )

            # Verify at least some orders were placed
            if not (base_buy_result or enhanced_buy_result):
                raise Exception("Failed to place any buy orders")

            # Log final setup
            total_base_orders = (
                len(adaptive_config.base_grid.buy_levels)
                + len(adaptive_config.base_grid.sell_levels)
                if base_sell_result
                else len(adaptive_config.base_grid.buy_levels)
            )

            total_enhanced_orders = (
                len(adaptive_config.enhanced_grid.buy_levels)
                + len(adaptive_config.enhanced_grid.sell_levels)
                if enhanced_sell_result
                else len(adaptive_config.enhanced_grid.buy_levels)
            )

            self.logger.info("✅ 35/65 Dual-scale grids initialized:")
            self.logger.info(f"   💙 Base Grid: {total_base_orders} orders active")
            self.logger.info(
                f"   🚀 Enhanced Grid: {total_enhanced_orders} orders active"
            )
            self.logger.info(
                f"   📊 Total system orders: {total_base_orders + total_enhanced_orders}"
            )

        except Exception as e:
            self.logger.error(f"❌ Dual-scale grid initialization error: {e}")
            raise

    async def _execute_smart_buy_setup(self, grid_config, grid_type: str) -> bool:
        """Execute buy orders with FIXED balance checking - NO PREMATURE NOTIFICATIONS"""
        try:
            symbol = grid_config.symbol
            orders_placed = 0

            # FIXED: Get account balance with proper error handling
            self.logger.info(f"💰 Getting account balance for {grid_type}...")
            account = self._safe_binance_call("get_account")
            balances = {
                balance["asset"]: float(balance["free"])
                for balance in account["balances"]
            }
            available_usdt = balances.get("USDT", 0.0)

            # FIXED: Get symbol info with proper error handling
            self.logger.info(f"📋 Getting exchange info for {symbol}...")
            exchange_info = self._safe_binance_call("get_exchange_info")
            symbol_info = next(
                (s for s in exchange_info["symbols"] if s["symbol"] == symbol), None
            )

            if not symbol_info:
                self.logger.error(f"❌ Symbol {symbol} not found in exchange info")
                return False

            filters = {f["filterType"]: f for f in symbol_info["filters"]}
            min_notional = float(
                filters.get("MIN_NOTIONAL", {}).get("minNotional", 10.0)
            )

            self.logger.info(f"💰 {grid_type} setup:")
            self.logger.info(f"   Available USDT: ${available_usdt:.2f}")
            self.logger.info(f"   Target order size: ${grid_config.order_size:.2f}")
            self.logger.info(f"   Grid levels: {grid_config.grid_levels}")

            # Place buy orders
            for level in grid_config.buy_levels:
                try:
                    formatted_price, formatted_quantity = self._format_order_params(
                        level["price"], level["quantity"], filters
                    )

                    notional_value = float(formatted_price) * float(formatted_quantity)

                    # Ensure minimum notional
                    if notional_value < min_notional:
                        required_quantity = (min_notional * 1.05) / float(
                            formatted_price
                        )
                        formatted_price, formatted_quantity = self._format_order_params(
                            level["price"], required_quantity, filters
                        )
                        notional_value = float(formatted_price) * float(
                            formatted_quantity
                        )

                    # Check available balance
                    if notional_value > available_usdt:
                        if available_usdt < min_notional:
                            self.logger.info(
                                f"   ⏭️  Insufficient balance for more {grid_type} orders"
                            )
                            break

                        # Adjust to available balance
                        adjusted_quantity = (available_usdt * 0.99) / float(
                            formatted_price
                        )
                        formatted_price, formatted_quantity = self._format_order_params(
                            level["price"], adjusted_quantity, filters
                        )
                        notional_value = float(formatted_price) * float(
                            formatted_quantity
                        )

                    # FIXED: Place order with proper timestamp handling
                    order = self._safe_binance_call(
                        "order_limit_buy",
                        symbol=symbol,
                        quantity=formatted_quantity,
                        price=formatted_price,
                    )

                    if order and order.get("status") in ["NEW", "PARTIALLY_FILLED"]:
                        level["order_id"] = order["orderId"]
                        orders_placed += 1
                        available_usdt -= notional_value

                        # Log order PLACEMENT (not execution!)
                        self.trade_repo.log_grid_order(
                            client_id=self.client_id,
                            symbol=symbol,
                            side="BUY",
                            quantity=float(formatted_quantity),
                            price=float(formatted_price),
                            order_id=order["orderId"],
                            grid_level=level["level"],
                        )

                        # ✅ CORRECT: Only log placement, not execution
                        self.logger.info(
                            f"✅ {grid_type} ORDER PLACED: {formatted_quantity} at {formatted_price} = ${notional_value:.2f}"
                        )

                        if available_usdt < min_notional:
                            break

                except Exception as e:
                    self.logger.warning(f"❌ Failed {grid_type} order: {e}")

            success = orders_placed > 0
            self.logger.info(
                f"{'✅' if success else '❌'} {grid_type}: {orders_placed} orders placed"
            )

            return success

        except Exception as e:
            self.logger.error(f"❌ {grid_type} setup error: {e}")
            return False

    async def _execute_smart_sell_setup(self, grid_config, grid_type: str) -> bool:
        """Execute sell orders with FIXED balance checking - NO PREMATURE NOTIFICATIONS"""
        try:
            symbol = grid_config.symbol
            base_asset = symbol.replace("USDT", "")
            orders_placed = 0

            # FIXED: Get account balance with proper error handling
            account = self._safe_binance_call("get_account")
            balances = {
                balance["asset"]: float(balance["free"])
                for balance in account["balances"]
            }
            available_base = balances.get(base_asset, 0.0)

            # FIXED: Get symbol info with proper error handling
            exchange_info = self._safe_binance_call("get_exchange_info")
            symbol_info = next(
                (s for s in exchange_info["symbols"] if s["symbol"] == symbol), None
            )

            if not symbol_info:
                self.logger.error(f"❌ Symbol {symbol} not found in exchange info")
                return False

            filters = {f["filterType"]: f for f in symbol_info["filters"]}
            min_notional = float(
                filters.get("MIN_NOTIONAL", {}).get("minNotional", 10.0)
            )

            self.logger.info(f"📈 {grid_type} setup:")
            self.logger.info(f"   Available {base_asset}: {available_base}")
            self.logger.info(f"   Target order size: ${grid_config.order_size:.2f}")

            # Place sell orders
            for level in grid_config.sell_levels:
                try:
                    formatted_price, formatted_quantity = self._format_order_params(
                        level["price"], level["quantity"], filters
                    )

                    required_quantity = float(formatted_quantity)
                    notional_value = float(formatted_price) * required_quantity

                    # Ensure minimum notional
                    if notional_value < min_notional:
                        required_quantity = (min_notional * 1.05) / float(
                            formatted_price
                        )
                        formatted_price, formatted_quantity = self._format_order_params(
                            level["price"], required_quantity, filters
                        )
                        notional_value = float(formatted_price) * float(
                            formatted_quantity
                        )
                        required_quantity = float(formatted_quantity)

                    # Check available balance
                    if required_quantity > available_base:
                        if available_base * float(formatted_price) < min_notional:
                            self.logger.info(
                                f"   ⏭️  Insufficient {base_asset} for more {grid_type} orders"
                            )
                            break

                        # Use available balance
                        adjusted_quantity = available_base * 0.99
                        formatted_price, formatted_quantity = self._format_order_params(
                            level["price"], adjusted_quantity, filters
                        )
                        notional_value = float(formatted_price) * float(
                            formatted_quantity
                        )
                        required_quantity = float(formatted_quantity)

                    # FIXED: Place order with proper timestamp handling
                    order = self._safe_binance_call(
                        "order_limit_sell",
                        symbol=symbol,
                        quantity=formatted_quantity,
                        price=formatted_price,
                    )

                    if order and order.get("status") in ["NEW", "PARTIALLY_FILLED"]:
                        level["order_id"] = order["orderId"]
                        orders_placed += 1
                        available_base -= required_quantity

                        # Log order PLACEMENT (not execution!)
                        self.trade_repo.log_grid_order(
                            client_id=self.client_id,
                            symbol=symbol,
                            side="SELL",
                            quantity=required_quantity,
                            price=float(formatted_price),
                            order_id=order["orderId"],
                            grid_level=level["level"],
                        )

                        # ✅ CORRECT: Only log placement, not execution
                        self.logger.info(
                            f"✅ {grid_type} ORDER PLACED: {formatted_quantity} at {formatted_price} = ${notional_value:.2f}"
                        )

                        if available_base < required_quantity:
                            break

                except Exception as e:
                    self.logger.warning(f"❌ Failed {grid_type} order: {e}")

            success = orders_placed > 0
            self.logger.info(
                f"{'✅' if success else '❌'} {grid_type}: {orders_placed} orders placed"
            )

            return success

        except Exception as e:
            self.logger.error(f"❌ {grid_type} setup error: {e}")
            return False

    def _format_order_params(
        self, price: float, quantity: float, filters: Dict
    ) -> Tuple[str, str]:
        """Format order parameters according to Binance requirements"""
        try:
            # Format price
            if "PRICE_FILTER" in filters:
                tick_size = float(filters["PRICE_FILTER"]["tickSize"])
                formatted_price = round(price / tick_size) * tick_size
                min_price = float(filters["PRICE_FILTER"]["minPrice"])
                max_price = float(filters["PRICE_FILTER"]["maxPrice"])
                formatted_price = max(min_price, min(max_price, formatted_price))
            else:
                formatted_price = round(price, 8)

            # Format quantity
            if "LOT_SIZE" in filters:
                step_size = float(filters["LOT_SIZE"]["stepSize"])
                formatted_quantity = round(quantity / step_size) * step_size
                min_qty = float(filters["LOT_SIZE"]["minQty"])
                max_qty = float(filters["LOT_SIZE"]["maxQty"])
                formatted_quantity = max(min_qty, min(max_qty, formatted_quantity))
            else:
                formatted_quantity = round(quantity, 8)

            return (
                f"{formatted_price:.8f}".rstrip("0").rstrip("."),
                f"{formatted_quantity:.8f}".rstrip("0").rstrip("."),
            )

        except Exception as e:
            self.logger.error(f"❌ Order formatting error: {e}")
            return f"{price:.8f}", f"{quantity:.8f}"

    # Additional monitoring methods with FIXED timestamp handling
    async def _monitor_dual_scale_grid(self, symbol: str) -> None:
        """Monitor dual-scale grid system with FIXED timestamp handling"""
        try:
            while symbol in self.active_grids:
                adaptive_config = self.active_grids[symbol]

                # Check for filled orders on both grids

                # FIFO Integration - Notify Enhanced Grid Orchestrator
                try:
                    if hasattr(self, "client_id") and hasattr(self, "logger"):
                        # This would ideally call the orchestrator's FIFO method
                        # For now, just log that we should notify FIFO
                        self.logger.info(
                            f"📊 FIFO: Should log trade for client {self.client_id}"
                        )
                except Exception as e:
                    self.logger.warning(f"FIFO logging failed: {e}")
                await self._check_filled_orders_dual_scale(adaptive_config)
                # Dynamic interval based on market activity
                interval = await self._calculate_monitoring_interval(symbol)
                await asyncio.sleep(interval)

                # FIFO Integration - Notify Enhanced Grid Orchestrator
                try:
                    if hasattr(self, "client_id") and hasattr(self, "logger"):
                        # This would ideally call the orchestrator's FIFO method
                        # For now, just log that we should notify FIFO
                        self.logger.info(
                            f"📊 FIFO: Should log trade for client {self.client_id}"
                        )
                except Exception as e:
                    self.logger.warning(f"FIFO logging failed: {e}")

                # Check for balance expansion opportunities
                await self._check_balance_expansion_dual_scale(adaptive_config)

                # Check market condition changes for enhanced grid adaptation
                await self._check_market_adaptation_dual_scale(adaptive_config)

                # Update performance metrics
                await self._update_dual_scale_performance(adaptive_config)

        except Exception as e:
            self.logger.error(f"❌ Dual-scale grid monitoring error: {e}")

    async def _check_filled_orders_dual_scale(
        self, adaptive_config: AdaptiveGridConfig
    ) -> None:
        """Check filled orders on both base and enhanced grids with FIXED API calls"""
        self.notify_fifo()

        try:
            symbol = adaptive_config.symbol
            open_orders = self._safe_binance_call("get_open_orders", symbol=symbol)
            open_order_ids = {order["orderId"] for order in open_orders}

            await self._process_filled_orders_with_replacement(
                adaptive_config.base_grid, open_order_ids, "BASE_GRID", adaptive_config
            )

            if adaptive_config.enhanced_grid_active:
                await self._process_filled_orders_with_replacement(
                    adaptive_config.enhanced_grid,
                    open_order_ids,
                    "ENHANCED_GRID",
                    adaptive_config,
                )

        except Exception as e:
            self.logger.error(f"❌ Dual-scale filled orders check error: {e}")
            self.notify_fifo()

    async def _process_filled_orders_with_replacement(
        self,
        grid_config,
        open_order_ids: set,
        grid_type: str,
        adaptive_config: AdaptiveGridConfig,
    ) -> None:
        """Process filled orders and replace them intelligently"""
        try:
            filled_orders = []

            for level in grid_config.buy_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level["filled"]
                ):
                    level["filled"] = True
                    filled_orders.append(("BUY", level))

            for level in grid_config.sell_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level["filled"]
                ):
                    level["filled"] = True
                    filled_orders.append(("SELL", level))

            for side, level in filled_orders:
                # Calculate total value
                total_value = level["quantity"] * level["price"]

                # ✅ CORRECT TIMING: Notify when order is actually FILLED
                await self.notify_trade_execution(
                    self.client_id,
                    grid_config.symbol,
                    side,
                    level["quantity"],
                    level["price"],
                    total_value,
                )

                self.trade_repo.log_trade_execution(
                    client_id=self.client_id,
                    symbol=grid_config.symbol,
                    side=side,
                    quantity=level["quantity"],
                    price=level["price"],
                    order_id=level["order_id"],
                )

                self.performance_metrics["total_trades"] += 1
                if grid_type == "BASE_GRID":
                    self.performance_metrics["base_grid_trades"] += 1
                else:
                    self.performance_metrics["enhanced_grid_trades"] += 1

                if side == "SELL":
                    estimated_profit = (
                        level["price"]
                        - adaptive_config.market_condition.get("indicators", {}).get(
                            "price_trend", level["price"]
                        )
                    ) * level["quantity"]
                    self.performance_metrics["total_profit"] += estimated_profit

                self.logger.info(
                    f"💰 {grid_type} {side} FILLED: {level['quantity']} at ${level['price']:.4f} = ${total_value:.2f}"
                )

                await self._replace_filled_order_dual_scale(
                    grid_config, side, level, grid_type, adaptive_config
                )

        except Exception as e:
            self.logger.error(f"❌ Process filled orders error for {grid_type}: {e}")

    async def _replace_filled_order_dual_scale(
        self,
        grid_config,
        side: str,
        level: dict,
        grid_type: str,
        adaptive_config: AdaptiveGridConfig,
    ) -> None:
        """Replace filled order with intelligent dual-scale logic and FIXED API calls"""
        self.notify_fifo()

        try:
            ticker = self._safe_binance_call(
                "get_symbol_ticker", symbol=grid_config.symbol
            )
            current_price = float(ticker["price"])

            if side == "BUY":
                new_side = "SELL"
                if grid_type == "BASE_GRID":
                    new_price = current_price * (1 + grid_config.grid_spacing * 1.5)
                else:
                    market_score = adaptive_config.market_condition.get("score", 0.5)
                    new_price = current_price * (
                        1
                        + grid_config.grid_spacing
                        * (1.2 if market_score > 0.6 else 1.8)
                    )
            else:
                new_side = "BUY"
                if grid_type == "BASE_GRID":
                    new_price = current_price * (1 - grid_config.grid_spacing * 1.5)
                else:
                    market_score = adaptive_config.market_condition.get("score", 0.5)
                    new_price = current_price * (
                        1
                        - grid_config.grid_spacing
                        * (1.2 if market_score < 0.4 else 1.8)
                    )

            exchange_info = self._safe_binance_call("get_exchange_info")
            symbol_info = next(
                (
                    s
                    for s in exchange_info["symbols"]
                    if s["symbol"] == grid_config.symbol
                ),
                None,
            )
            filters = {f["filterType"]: f for f in symbol_info["filters"]}

            new_quantity = level["quantity"]
            formatted_price, formatted_quantity = self._format_order_params(
                new_price, new_quantity, filters
            )

            if new_side == "BUY":
                order = self._safe_binance_call(
                    "order_limit_buy",
                    symbol=grid_config.symbol,
                    quantity=formatted_quantity,
                    price=formatted_price,
                )
            else:
                order = self._safe_binance_call(
                    "order_limit_sell",
                    symbol=grid_config.symbol,
                    quantity=formatted_quantity,
                    price=formatted_price,
                )

            if order and order.get("status") in ["NEW", "PARTIALLY_FILLED"]:
                level["price"] = new_price
                level["quantity"] = float(formatted_quantity)
                level["order_id"] = order["orderId"]
                level["filled"] = False

                self.trade_repo.log_grid_order(
                    client_id=self.client_id,
                    symbol=grid_config.symbol,
                    side=new_side,
                    quantity=float(formatted_quantity),
                    price=new_price,
                    order_id=order["orderId"],
                    grid_level=level["level"],
                )

                self.logger.info(
                    f"🔄 {grid_type} replacement: {new_side} {formatted_quantity} at {formatted_price}"
                )

        except Exception as e:
            self.logger.error(f"❌ Replace filled order error: {e}")
            self.notify_fifo()

    async def _check_balance_expansion_dual_scale(
        self, adaptive_config: AdaptiveGridConfig
    ) -> None:
        """Check for balance expansion opportunities with FIXED API calls"""
        try:
            symbol = adaptive_config.symbol
            current_time = datetime.now()

            # Don't check too frequently
            last_check = self.last_balance_check.get(symbol, datetime.min)
            if (
                current_time - last_check
            ).total_seconds() < self.balance_check_interval:
                return

            # FIXED: Get current balances with proper timestamp handling
            account = self._safe_binance_call("get_account")
            balances = {
                balance["asset"]: float(balance["free"])
                for balance in account["balances"]
            }

            base_asset = symbol.replace("USDT", "")
            base_balance = balances.get(base_asset, 0.0)

            symbol_config = self.symbol_configs.get(symbol, {})
            min_base_for_sells = symbol_config.get("min_base_for_sells", 20.0)

            # Check if we can activate enhanced grid sells
            if (
                not adaptive_config.enhanced_grid_active
                and base_balance >= min_base_for_sells
            ):
                self.logger.info(f"🎉 Enhanced grid expansion detected for {symbol}!")
                self.logger.info(
                    f"   {base_asset} balance: {base_balance} >= {min_base_for_sells}"
                )
                self.logger.info(
                    "   Activating enhanced sell orders (65% allocation)..."
                )

                # FIXED: Get current price with proper timestamp handling
                ticker = self._safe_binance_call("get_symbol_ticker", symbol=symbol)
                current_price = float(ticker["price"])

                # Configure enhanced grid sells with 65% allocation
                enhanced_capital = (
                    adaptive_config.total_capital * self.ENHANCED_ALLOCATION
                )
                enhanced_levels = symbol_config.get("enhanced_levels", 8)
                enhanced_order_size = enhanced_capital / (enhanced_levels * 2)

                # Recalculate enhanced grid
                adaptive_config.enhanced_grid.order_size = enhanced_order_size
                adaptive_config.enhanced_grid.calculate_grid_levels(current_price)

                # Execute enhanced sell setup
                sell_result = await self._execute_smart_sell_setup(
                    adaptive_config.enhanced_grid, "ENHANCED_SELL_EXPANSION"
                )

                if sell_result:
                    adaptive_config.enhanced_grid_active = True
                    self.performance_metrics["dual_scale_adaptations"] += 1
                    self.logger.info(
                        "✅ Enhanced grid (65%) activated! Full dual-scale system now operational"
                    )
                else:
                    self.logger.warning("❌ Failed to activate enhanced sells")

            self.last_balance_check[symbol] = current_time

        except Exception as e:
            self.logger.error(f"❌ Balance expansion check error: {e}")

    async def _check_market_adaptation_dual_scale(
        self, adaptive_config: AdaptiveGridConfig
    ) -> None:
        """Check for market condition changes and adapt enhanced grid"""
        try:
            symbol = adaptive_config.symbol
            current_time = datetime.now()

            # Check market conditions less frequently
            last_check = self.last_market_check.get(symbol, datetime.min)
            if (current_time - last_check).total_seconds() < self.market_check_interval:
                return

            # Get new market condition
            try:
                new_market_condition = await self.market_analysis.get_market_condition(
                    symbol
                )
            except Exception as e:
                self.logger.warning(f"Market analysis failed: {e}")
                return

            old_condition = adaptive_config.market_condition["condition"]
            new_condition = new_market_condition["condition"]

            # Check for significant changes
            condition_changed = old_condition != new_condition
            score_changed = (
                abs(
                    new_market_condition["score"]
                    - adaptive_config.market_condition["score"]
                )
                > 0.3
            )

            if condition_changed or score_changed:
                self.logger.info(
                    f"📊 Market adaptation for {symbol}: {old_condition} → {new_condition}"
                )

                # Update market condition
                adaptive_config.market_condition = new_market_condition
                self.performance_metrics["dual_scale_adaptations"] += 1

                # Adapt enhanced grid spacing to new market condition
                if adaptive_config.enhanced_grid_active:
                    await self._adapt_enhanced_grid_to_market(
                        adaptive_config, new_market_condition
                    )

            self.last_market_check[symbol] = current_time

        except Exception as e:
            self.logger.error(f"❌ Market adaptation check error: {e}")

    async def _adapt_enhanced_grid_to_market(
        self, adaptive_config: AdaptiveGridConfig, market_condition: Dict
    ) -> None:
        """Adapt enhanced grid spacing based on new market conditions with FIXED API calls"""
        try:
            symbol = adaptive_config.symbol
            market_score = market_condition.get("score", 0.5)
            volatility = market_condition.get("indicators", {}).get("volatility", 0.25)

            # Calculate new adaptive spacing for enhanced grid
            if market_score > 0.7:  # Strong bullish
                new_spacing = max(0.01, 0.02 - volatility * 0.01)
            elif market_score < 0.3:  # Strong bearish
                new_spacing = min(0.04, 0.03 + volatility * 0.01)
            else:  # Neutral
                new_spacing = 0.02 + volatility * 0.005

            # Only adapt if spacing change is significant
            current_spacing = adaptive_config.enhanced_grid.grid_spacing
            if abs(new_spacing - current_spacing) > 0.005:  # 0.5% threshold
                self.logger.info(
                    f"🎯 Adapting enhanced grid spacing: {current_spacing * 100:.1f}% → {new_spacing * 100:.1f}%"
                )

                # Cancel existing enhanced grid orders
                await self._cancel_grid_orders(adaptive_config.enhanced_grid)

                # Update spacing and recalculate
                adaptive_config.enhanced_grid.grid_spacing = new_spacing

                # FIXED: Get current price with proper timestamp handling
                ticker = self._safe_binance_call("get_symbol_ticker", symbol=symbol)
                current_price = float(ticker["price"])

                # Recalculate with new spacing
                adaptive_config.enhanced_grid.calculate_grid_levels(current_price)

                # Re-execute enhanced grid
                buy_result = await self._execute_smart_buy_setup(
                    adaptive_config.enhanced_grid, "ENHANCED_BUY_ADAPTED"
                )
                sell_result = await self._execute_smart_sell_setup(
                    adaptive_config.enhanced_grid, "ENHANCED_SELL_ADAPTED"
                )

                if buy_result or sell_result:
                    self.logger.info(
                        f"✅ Enhanced grid adapted to {market_condition['condition']} market"
                    )
                else:
                    self.logger.warning("❌ Enhanced grid adaptation failed")

        except Exception as e:
            self.logger.error(f"❌ Enhanced grid adaptation error: {e}")

    async def _cancel_grid_orders(self, grid_config) -> None:
        """Cancel all orders for a specific grid with FIXED API calls"""
        try:
            symbol = grid_config.symbol
            open_orders = self._safe_binance_call("get_open_orders", symbol=symbol)

            for level in grid_config.buy_levels + grid_config.sell_levels:
                if level["order_id"]:
                    for order in open_orders:
                        if order["orderId"] == level["order_id"]:
                            try:
                                self._safe_binance_call(
                                    "cancel_order",
                                    symbol=symbol,
                                    orderId=level["order_id"],
                                )
                                level["order_id"] = None
                                level["filled"] = False
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to cancel order {level['order_id']}: {e}"
                                )

        except Exception as e:
            self.logger.error(f"❌ Cancel grid orders error: {e}")

    async def _update_dual_scale_performance(
        self, adaptive_config: AdaptiveGridConfig
    ) -> None:
        """Update performance metrics for dual-scale system"""
        try:
            # Get trade statistics
            stats = self.trade_repo.get_client_trade_stats(self.client_id)

            # Update metrics
            self.performance_metrics["total_profit"] = stats.get("total_profit", 0.0)

            # Calculate dual-scale efficiency
            total_trades = self.performance_metrics["total_trades"]
            if total_trades > 0:
                base_efficiency = (
                    self.performance_metrics["base_grid_trades"] / total_trades
                )
                enhanced_efficiency = (
                    self.performance_metrics["enhanced_grid_trades"] / total_trades
                )

                # Weighted efficiency (35% base, 65% enhanced)
                weighted_efficiency = (base_efficiency * 0.35) + (
                    enhanced_efficiency * 0.65
                )

                adaptive_config.performance_metrics.update(
                    {
                        "base_grid_efficiency": base_efficiency,
                        "enhanced_grid_efficiency": enhanced_efficiency,
                        "dual_scale_efficiency": weighted_efficiency,
                        "total_profit": self.performance_metrics["total_profit"],
                        "adaptations": self.performance_metrics[
                            "dual_scale_adaptations"
                        ],
                    }
                )

        except Exception as e:
            self.logger.error(f"❌ Dual-scale performance update error: {e}")

    def get_dual_scale_status(self, symbol: str) -> Dict:
        """Get comprehensive dual-scale grid status"""
        if symbol not in self.active_grids:
            return {"active": False, "error": "Grid not found"}

        adaptive_config = self.active_grids[symbol]

        return {
            "active": True,
            "symbol": symbol,
            "strategy": "35/65 Dual-Scale System",
            "market_condition": adaptive_config.market_condition,
            "total_capital": adaptive_config.total_capital,
            "capital_allocation": {
                "base_grid": {
                    "percentage": 35,
                    "capital": adaptive_config.total_capital * 0.35,
                    "active": True,
                    "order_size": adaptive_config.base_grid.order_size,
                    "levels": adaptive_config.base_grid.grid_levels,
                    "spacing": adaptive_config.base_grid.grid_spacing,
                    "purpose": "Conservative foundation - steady income",
                },
                "enhanced_grid": {
                    "percentage": 65,
                    "capital": adaptive_config.total_capital * 0.65,
                    "active": adaptive_config.enhanced_grid_active,
                    "order_size": adaptive_config.enhanced_grid.order_size,
                    "levels": adaptive_config.enhanced_grid.grid_levels,
                    "spacing": adaptive_config.enhanced_grid.grid_spacing,
                    "purpose": "Aggressive profit capture - market adaptive",
                },
            },
            "performance_metrics": adaptive_config.performance_metrics,
            "smart_features": {
                "dual_scale_system": True,
                "market_adaptive_spacing": True,
                "balance_expansion": True,
                "intelligent_order_replacement": True,
                "risk_management": True,
            },
        }

    def get_all_grids_status(self) -> Dict:
        """Get status of all active dual-scale grids"""
        return {
            symbol: self.get_dual_scale_status(symbol)
            for symbol in self.active_grids.keys()
        }

    async def stop_dual_scale_grid(self, symbol: str) -> Dict:
        """Stop dual-scale grid system with FIXED API calls"""
        try:
            if symbol not in self.active_grids:
                return {"success": False, "error": "Grid not active"}

            adaptive_config = self.active_grids[symbol]

            # Cancel all orders from both grids
            await self._cancel_grid_orders(adaptive_config.base_grid)
            if adaptive_config.enhanced_grid_active:
                await self._cancel_grid_orders(adaptive_config.enhanced_grid)

            # Remove from active grids
            del self.active_grids[symbol]

            result = {
                "success": True,
                "symbol": symbol,
                "performance_metrics": adaptive_config.performance_metrics,
                "total_profit": self.performance_metrics["total_profit"],
                "system_stopped": "35/65 Dual-Scale Grid System",
            }

            self.logger.info(f"🛑 35/65 Dual-scale grid stopped for {symbol}")
            return result

        except Exception as e:
            self.logger.error(f"❌ Stop dual-scale grid error for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    def notify_fifo(self):
        """Helper to notify FIFO orchestrator (currently logs a message)."""
        try:
            if hasattr(self, "client_id") and hasattr(self, "logger"):
                self.logger.info(
                    f"📊 FIFO: Should log trade for client {self.client_id}"
                )
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"FIFO logging failed: {e}")

    async def complete_grid_initialization(
        self, client_id: int, symbol: str, total_capital: float
    ):
        """Complete grid initialization with notifications - FIXED"""
        try:
            # Count active orders from both grids
            base_buy_orders = len(
                [
                    l
                    for l in self.active_grids[symbol].base_grid.buy_levels
                    if l.get("order_id")
                ]
            )
            base_sell_orders = len(
                [
                    l
                    for l in self.active_grids[symbol].base_grid.sell_levels
                    if l.get("order_id")
                ]
            )
            enhanced_buy_orders = len(
                [
                    l
                    for l in self.active_grids[symbol].enhanced_grid.buy_levels
                    if l.get("order_id")
                ]
            )
            enhanced_sell_orders = len(
                [
                    l
                    for l in self.active_grids[symbol].enhanced_grid.sell_levels
                    if l.get("order_id")
                ]
            )

            total_orders = (
                base_buy_orders
                + base_sell_orders
                + enhanced_buy_orders
                + enhanced_sell_orders
            )
            base_total = base_buy_orders + base_sell_orders
            enhanced_total = enhanced_buy_orders + enhanced_sell_orders

            # Your existing success logging
            self.logger.info("✅ 35/65 Dual-scale grids initialized:")
            self.logger.info(f"   💙 Base Grid: {base_total} orders active")
            self.logger.info(f"   🚀 Enhanced Grid: {enhanced_total} orders active")
            self.logger.info(f"   📊 Total system orders: {total_orders}")
            self.logger.info("✅ 35/65 dual-scale grid system activated!")

            # Send comprehensive startup notification
            await self.send_grid_startup_notification(
                client_id=client_id,
                symbol=symbol,
                total_capital=total_capital,
                base_orders=base_total,
                enhanced_orders=enhanced_total,
                total_orders=total_orders,
            )

        except Exception as e:
            self.logger.error(f"Failed to complete grid initialization: {e}")

    async def notify_trade_execution(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        total_value: float,
    ):
        """Send trade execution notification"""
        try:
            from utils.fifo_telegram_monitor import FIFOMonitoringService

            # Get or create monitoring service instance
            if not hasattr(self, "fifo_monitoring_service"):
                self.fifo_monitoring_service = FIFOMonitoringService()
                await self.fifo_monitoring_service.add_client_monitor(client_id)

            # Notify the monitoring service of trade execution
            await self.fifo_monitoring_service.on_trade_executed(
                client_id=client_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
            )

            # Send immediate trade notification for significant trades
            if side == "SELL" and total_value >= 50.0:  # Notify sells over $50
                from services.telegram_notifier import TelegramNotifier

                notifier = TelegramNotifier()

                if notifier.enabled:
                    estimated_profit = (
                        total_value * 0.025
                    )  # Assume 2.5% grid spacing profit

                    message = f"""💰 **Trade Executed**

    🎯 **{symbol}** {side}
    📊 Quantity: {quantity:.2f} 
    💵 Price: ${price:.4f}
    💰 Value: ${total_value:.2f}
    📈 Est. Profit: ${estimated_profit:.2f}

    ⏰ {datetime.now().strftime("%H:%M:%S")}"""

                    await notifier.send_message(message)

        except Exception as e:
            self.logger.error(f"Failed to notify trade execution: {e}")

        if side == "SELL":
            estimated_profit = quantity * price * 0.025  # Estimate 2.5% grid profit
            await self.compound_service.on_trade_executed(
                client_id, symbol, side, quantity, price, estimated_profit
            )
