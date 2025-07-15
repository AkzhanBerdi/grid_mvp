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
from services.market_analysis import MarketAnalysisService, MarketCondition


class DualScaleGridManager:
    """Smart 35/65 dual-scale grid system - FIXED ALL BINANCE API ISSUES"""

    def __init__(self, binance_client: Client, client_id: int):
        self.binance_client = binance_client
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        # Initialize services
        self.market_analysis = MarketAnalysisService(binance_client)
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()

        # Grid state
        self.active_grids: Dict[str, AdaptiveGridConfig] = {}
        self.last_market_check = {}
        self.last_balance_check = {}
        self.market_check_interval = 300  # 5 minutes
        self.balance_check_interval = 60  # 1 minute

        # 35/65 ALLOCATION STRATEGY
        self.BASE_ALLOCATION = 0.35  # 35% - Conservative foundation
        self.ENHANCED_ALLOCATION = 0.65  # 65% - Aggressive profit capture

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

    def _safe_binance_call(self, method_name: str, *args, **kwargs):
        """FIXED: Safely call Binance API methods with proper timestamp handling"""
        try:
            method = getattr(self.binance_client, method_name)

            # FIXED: Handle different API methods with appropriate parameters
            if method_name == "get_symbol_ticker":
                # FIXED: get_symbol_ticker doesn't support recvWindow
                # and needs specific parameter handling
                if "symbol" in kwargs:
                    symbol = kwargs.pop("symbol")
                    return method(symbol=symbol)
                elif len(args) > 0:
                    # If symbol passed as positional argument
                    return method(symbol=args[0])
                else:
                    # No symbol specified - get all tickers
                    return method()

            elif method_name in [
                "get_account",
                "get_open_orders",
                "order_limit_buy",
                "order_limit_sell",
                "cancel_order",
            ]:
                # These methods support recvWindow and need timestamp sync
                try:
                    # Add extended recvWindow for timestamp issues
                    kwargs["recvWindow"] = 60000  # 60 seconds
                    return method(*args, **kwargs)
                except Exception as e:
                    if "recvWindow" in str(e) or "timestamp" in str(e).lower():
                        # Retry with larger recvWindow
                        self.logger.warning(
                            f"Timestamp issue, retrying with larger window: {e}"
                        )
                        kwargs["recvWindow"] = 120000  # 2 minutes
                        time.sleep(1)  # Brief pause to let timestamps align
                        return method(*args, **kwargs)
                    else:
                        raise

            elif method_name == "get_exchange_info":
                # get_exchange_info doesn't need recvWindow
                return method(*args, **kwargs)

            elif method_name == "get_server_time":
                # Server time call doesn't need recvWindow
                return method()

            else:
                # Default handling for other methods
                try:
                    return method(*args, **kwargs)
                except TypeError:
                    # If method doesn't support the parameters, try without extras
                    return method(*args)

        except Exception as e:
            self.logger.error(f"❌ Binance API call failed: {method_name} - {e}")

            # Special handling for timestamp errors
            if "timestamp" in str(e).lower() or "recvWindow" in str(e):
                self.logger.error("🕐 Timestamp synchronization issue detected")
                self.logger.error("💡 Consider synchronizing system clock with NTP")

            raise

    def _sync_server_time(self):
        """Sync with Binance server time to avoid timestamp issues"""
        try:
            server_time = self._safe_binance_call("get_server_time")
            server_timestamp = server_time["serverTime"]
            local_timestamp = int(time.time() * 1000)
            time_diff = abs(server_timestamp - local_timestamp)

            self.logger.info(
                f"⏰ Time sync check: local={local_timestamp}, server={server_timestamp}, diff={time_diff}ms"
            )

            if time_diff > 30000:  # More than 30 seconds difference
                self.logger.warning(f"⚠️ Large time difference detected: {time_diff}ms")
                self.logger.warning("💡 System clock may need synchronization")

            return time_diff < 60000  # Return True if within 1 minute

        except Exception as e:
            self.logger.error(f"❌ Failed to sync server time: {e}")
            return False

    async def start_dual_scale_grid(self, symbol: str, total_capital: float) -> Dict:
        """Start intelligent 35/65 dual-scale grid system - FIXED VERSION"""
        try:
            self.logger.info(
                f"🚀 Starting 35/65 dual-scale grid for {symbol} with ${total_capital:,.2f}"
            )

            # FIXED: Sync time before starting
            self.logger.info("🕐 Synchronizing with Binance server time...")
            time_synced = self._sync_server_time()
            if not time_synced:
                self.logger.warning(
                    "⚠️ Time sync warning - continuing with larger recvWindow"
                )

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

            self.logger.info("✅ 35/65 dual-scale grid system activated!")
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
        """Execute buy orders with FIXED balance checking"""
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

                        # Log order
                        self.trade_repo.log_grid_order(
                            client_id=self.client_id,
                            symbol=symbol,
                            side="BUY",
                            quantity=float(formatted_quantity),
                            price=float(formatted_price),
                            order_id=order["orderId"],
                            grid_level=level["level"],
                        )

                        self.logger.info(
                            f"✅ {grid_type}: {formatted_quantity} at {formatted_price} = ${notional_value:.2f}"
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
        """Execute sell orders with FIXED balance checking"""
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

                        # Log order
                        self.trade_repo.log_grid_order(
                            client_id=self.client_id,
                            symbol=symbol,
                            side="SELL",
                            quantity=required_quantity,
                            price=float(formatted_price),
                            order_id=order["orderId"],
                            grid_level=level["level"],
                        )

                        self.logger.info(
                            f"✅ {grid_type}: {formatted_quantity} at {formatted_price} = ${notional_value:.2f}"
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
                await self._check_filled_orders_dual_scale(adaptive_config)

                # Check for balance expansion opportunities
                await self._check_balance_expansion_dual_scale(adaptive_config)

                # Check market condition changes for enhanced grid adaptation
                await self._check_market_adaptation_dual_scale(adaptive_config)

                # Update performance metrics
                await self._update_dual_scale_performance(adaptive_config)

                # Wait before next check
                await asyncio.sleep(60)

        except Exception as e:
            self.logger.error(f"❌ Dual-scale grid monitoring error: {e}")

    async def _check_filled_orders_dual_scale(
        self, adaptive_config: AdaptiveGridConfig
    ) -> None:
        """Check filled orders on both base and enhanced grids with FIXED API calls"""
        try:
            symbol = adaptive_config.symbol

            # FIXED: Get current open orders with proper timestamp handling
            open_orders = self._safe_binance_call("get_open_orders", symbol=symbol)
            open_order_ids = {order["orderId"] for order in open_orders}

            # Check base grid (35% allocation)
            await self._process_filled_orders_with_replacement(
                adaptive_config.base_grid, open_order_ids, "BASE_GRID", adaptive_config
            )

            # Check enhanced grid (65% allocation)
            if adaptive_config.enhanced_grid_active:
                await self._process_filled_orders_with_replacement(
                    adaptive_config.enhanced_grid,
                    open_order_ids,
                    "ENHANCED_GRID",
                    adaptive_config,
                )

        except Exception as e:
            self.logger.error(f"❌ Dual-scale filled orders check error: {e}")

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

            # Check buy levels
            for level in grid_config.buy_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level["filled"]
                ):
                    level["filled"] = True
                    filled_orders.append(("BUY", level))

            # Check sell levels
            for level in grid_config.sell_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level["filled"]
                ):
                    level["filled"] = True
                    filled_orders.append(("SELL", level))

            # Process filled orders
            for side, level in filled_orders:
                # Log trade execution
                self.trade_repo.log_trade_execution(
                    client_id=self.client_id,
                    symbol=grid_config.symbol,
                    side=side,
                    quantity=level["quantity"],
                    price=level["price"],
                    order_id=level["order_id"],
                )

                # Update performance metrics
                self.performance_metrics["total_trades"] += 1
                if grid_type == "BASE_GRID":
                    self.performance_metrics["base_grid_trades"] += 1
                else:
                    self.performance_metrics["enhanced_grid_trades"] += 1

                # Calculate profit for sell orders
                if side == "SELL":
                    estimated_profit = (
                        level["price"]
                        - adaptive_config.market_condition.get("indicators", {}).get(
                            "price_trend", level["price"]
                        )
                    ) * level["quantity"]
                    self.performance_metrics["total_profit"] += estimated_profit

                self.logger.info(
                    f"💰 {grid_type} {side} filled: {level['quantity']} at ${level['price']:.4f}"
                )

                # Replace the filled order
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
        try:
            # FIXED: Get current price with proper timestamp handling
            ticker = self._safe_binance_call(
                "get_symbol_ticker", symbol=grid_config.symbol
            )
            current_price = float(ticker["price"])

            # Determine replacement strategy based on grid type and market conditions
            if side == "BUY":
                # Buy filled, place new sell order
                new_side = "SELL"
                if grid_type == "BASE_GRID":
                    # Conservative replacement
                    new_price = current_price * (1 + grid_config.grid_spacing * 1.5)
                else:
                    # Aggressive replacement with market adaptation
                    market_score = adaptive_config.market_condition.get("score", 0.5)
                    if market_score > 0.6:  # Bullish market
                        new_price = current_price * (1 + grid_config.grid_spacing * 1.2)
                    else:
                        new_price = current_price * (1 + grid_config.grid_spacing * 1.8)
            else:
                # Sell filled, place new buy order
                new_side = "BUY"
                if grid_type == "BASE_GRID":
                    # Conservative replacement
                    new_price = current_price * (1 - grid_config.grid_spacing * 1.5)
                else:
                    # Aggressive replacement with market adaptation
                    market_score = adaptive_config.market_condition.get("score", 0.5)
                    if market_score < 0.4:  # Bearish market
                        new_price = current_price * (1 - grid_config.grid_spacing * 1.2)
                    else:
                        new_price = current_price * (1 - grid_config.grid_spacing * 1.8)

            # FIXED: Get symbol info for formatting with proper timestamp handling
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

            # Calculate new quantity maintaining the same USD value
            new_quantity = level["quantity"]  # Keep same quantity for consistency

            # Format order parameters
            formatted_price, formatted_quantity = self._format_order_params(
                new_price, new_quantity, filters
            )

            # FIXED: Place replacement order with proper timestamp handling
            try:
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
                    # Update level with new order info
                    level["price"] = new_price
                    level["quantity"] = float(formatted_quantity)
                    level["order_id"] = order["orderId"]
                    level["filled"] = False

                    # Log new order
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
                self.logger.warning(
                    f"❌ Failed to place {grid_type} replacement order: {e}"
                )

        except Exception as e:
            self.logger.error(f"❌ Replace filled order error: {e}")

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
