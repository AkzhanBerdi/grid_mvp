# services/grid_trading_engine.py
"""
Enhanced Grid Trading Engine - Advanced Error Handling & Recovery
================================================================

Handles all trading operations with intelligent error recovery:
- NOTIONAL filter failure auto-correction
- Order size optimization based on exchange limits
- Dynamic grid level adjustment
- Advanced retry mechanisms
- Fallback strategies for failed orders

This addresses the gaps in the original refactoring by utilizing
advanced features for robust error handling.
"""

import logging
from typing import Dict, Optional, Tuple

from binance.client import Client
from binance.exceptions import BinanceAPIException

from models.single_advanced_grid_config import SingleAdvancedGridConfig
from repositories.trade_repository import TradeRepository
from services.enhanced_fifo_service import EnhancedFIFOService
from services.grid_utility_service import GridUtilityService
from services.inventory_manager import SingleGridInventoryManager


class GridTradingEngine:
    """
    Enhanced trading engine with advanced error handling and recovery
    """

    def __init__(self, binance_client: Client, client_id: int):
        self.binance_client = binance_client
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        # Core services
        self.trade_repo = TradeRepository()
        self.fifo_service = EnhancedFIFOService()
        self.utility = GridUtilityService(binance_client)

        # Will be injected from manager
        self.inventory_manager: Optional[SingleGridInventoryManager] = None
        self.compound_manager = None

        # Advanced error handling configuration
        self.error_handling_config = {
            "max_retries": 3,
            "retry_delay": 1.0,
            "notional_safety_margin": 1.2,  # 20% above minimum
            "dynamic_adjustment_enabled": True,
            "fallback_strategies_enabled": True,
            "auto_recovery_enabled": True,
        }

        # Error statistics
        self.error_stats = {
            "notional_failures": 0,
            "notional_recoveries": 0,
            "total_retries": 0,
            "successful_recoveries": 0,
            "fallback_activations": 0,
        }

        self.logger.info(
            "🔧 EnhancedGridTradingEngine initialized with advanced error handling"
        )

    def set_managers(self, inventory_manager, compound_manager):
        """Inject manager dependencies"""
        self.inventory_manager = inventory_manager
        self.compound_manager = compound_manager

    async def execute_initial_50_50_split(
        self, symbol: str, total_capital: float, current_price: float
    ) -> Dict:
        """
        Execute initial 50/50 split with enhanced error handling
        """
        try:
            self.logger.info(f"💰 Executing enhanced 50/50 split for {symbol}")

            # Calculate 50% for asset purchase
            asset_purchase_value = total_capital * 0.5

            # Get exchange rules and validate minimum notional
            rules = await self.utility.get_exchange_rules_simple(symbol)
            min_notional = rules.get("min_notional", 5.0)

            # 🔥 ENHANCED: Check if purchase value meets minimum requirements
            if (
                asset_purchase_value
                < min_notional * self.error_handling_config["notional_safety_margin"]
            ):
                adjusted_value = (
                    min_notional * self.error_handling_config["notional_safety_margin"]
                )
                self.logger.warning(
                    f"⚠️ Adjusting purchase value from ${asset_purchase_value:.2f} to ${adjusted_value:.2f} "
                    f"to meet minimum notional requirement (${min_notional})"
                )
                asset_purchase_value = min(
                    adjusted_value, total_capital * 0.7
                )  # Max 70% of capital

            # Calculate asset quantity to purchase
            asset_quantity = asset_purchase_value / current_price

            # Format with proper precision
            formatted_quantity = self._format_quantity(asset_quantity, rules)
            formatted_price = self._format_price(current_price, rules)

            self.logger.info(
                f"🛒 Enhanced purchase: {formatted_quantity} {symbol.replace('USDT', '')} @ ${formatted_price}"
            )

            # 🔥 ENHANCED: Execute with retry mechanism
            initial_order = await self._execute_order_with_retry(
                "market_buy",
                symbol=symbol,
                quoteOrderQty=f"{asset_purchase_value:.2f}",
                recvWindow=60000,
            )

            if not initial_order:
                return {
                    "success": False,
                    "error": "Failed to execute initial purchase after retries",
                }

            # Get actual filled quantity from the order
            actual_asset_quantity = float(initial_order["executedQty"])
            actual_spent = float(initial_order["cummulativeQuoteQty"])

            self.logger.info("✅ Enhanced purchase completed:")
            self.logger.info(
                f"   🪙 Asset acquired: {actual_asset_quantity:.4f} {symbol.replace('USDT', '')}"
            )
            self.logger.info(f"   💰 USDT spent: ${actual_spent:.2f}")
            self.logger.info(
                f"   💰 USDT remaining: ${total_capital - actual_spent:.2f}"
            )

            return {
                "success": True,
                "asset_quantity": actual_asset_quantity,
                "asset_balance": actual_asset_quantity,
                "usdt_spent": actual_spent,
                "usdt_remaining": total_capital - actual_spent,
                "purchase_price": actual_spent / actual_asset_quantity
                if actual_asset_quantity > 0
                else current_price,
                "adjustments_made": asset_purchase_value != total_capital * 0.5,
            }

        except Exception as e:
            self.logger.error(f"❌ Enhanced 50/50 split execution error: {e}")
            return {"success": False, "error": str(e)}

    async def execute_enhanced_grid_setup(
        self, symbol: str, grid_config: SingleAdvancedGridConfig
    ) -> Dict:
        """
        Enhanced grid setup with intelligent error handling and recovery
        """
        try:
            orders_placed = 0
            failed_orders = 0
            recovered_orders = 0

            self.logger.info(
                f"🎯 Executing enhanced grid setup with error recovery for {symbol}"
            )

            # Get exchange rules
            rules = await self.utility.get_exchange_rules_simple(symbol)
            if not rules:
                return {"success": False, "error": "Could not get exchange rules"}

            # Check actual balances
            usdt_balance, asset_balance = await self._get_current_balances(symbol)
            self.logger.info(
                f"📊 Actual balances: USDT=${usdt_balance:.2f}, {symbol.replace('USDT', '')}={asset_balance:.4f}"
            )

            # 🔥 ENHANCED: Place BUY orders with intelligent error handling
            if usdt_balance >= rules.get("min_notional", 5.0):
                buy_result = await self._place_enhanced_buy_orders(
                    symbol, grid_config, rules, usdt_balance
                )
                orders_placed += buy_result["orders_placed"]
                failed_orders += buy_result["failed_orders"]
                recovered_orders += buy_result["recovered_orders"]

            # 🔥 ENHANCED: Place SELL orders with intelligent error handling
            if asset_balance > 0:
                sell_result = await self._place_enhanced_sell_orders(
                    symbol, grid_config, rules, asset_balance
                )
                orders_placed += sell_result["orders_placed"]
                failed_orders += sell_result["failed_orders"]
                recovered_orders += sell_result["recovered_orders"]
            else:
                self.logger.error(
                    f"❌ CRITICAL: No {symbol.replace('USDT', '')} balance after 50/50 split!"
                )
                return {
                    "success": False,
                    "error": f"No {symbol.replace('USDT', '')} balance available - 50/50 split may have failed",
                }

            # 🔥 ENHANCED: Apply fallback strategies if needed
            if (
                orders_placed == 0
                and self.error_handling_config["fallback_strategies_enabled"]
            ):
                fallback_result = await self._apply_fallback_strategies(
                    symbol, grid_config, rules, usdt_balance, asset_balance
                )
                orders_placed += fallback_result.get("orders_placed", 0)
                self.error_stats["fallback_activations"] += 1

            self.logger.info("✅ Enhanced grid setup completed:")
            self.logger.info(f"   🎯 Orders placed: {orders_placed}")
            self.logger.info(f"   🔄 Orders recovered: {recovered_orders}")
            self.logger.info(f"   ❌ Failed orders: {failed_orders}")
            self.logger.info(
                f"   📊 Success rate: {orders_placed / max(orders_placed + failed_orders, 1) * 100:.1f}%"
            )

            return {
                "success": orders_placed > 0,
                "orders_placed": orders_placed,
                "failed_orders": failed_orders,
                "recovered_orders": recovered_orders,
                "error_handling_stats": self.error_stats.copy(),
                "message": f"Enhanced grid active with {orders_placed} orders (including error recovery)",
            }

        except Exception as e:
            self.logger.error(f"❌ Enhanced grid setup error: {e}")
            return {"success": False, "error": str(e)}

    async def _place_enhanced_buy_orders(
        self,
        symbol: str,
        grid_config: SingleAdvancedGridConfig,
        rules: Dict,
        usdt_balance: float,
    ) -> Dict:
        """Place BUY orders with enhanced error handling"""
        orders_placed = 0
        failed_orders = 0
        recovered_orders = 0

        for level in grid_config.buy_levels:
            try:
                if usdt_balance < rules.get("min_notional", 5.0):
                    self.logger.warning(
                        f"⚠️ Insufficient USDT balance: ${usdt_balance:.2f}"
                    )
                    break

                # 🔥 ENHANCED: Calculate optimal quantity with error prevention
                optimal_quantity = await self._calculate_optimal_order_quantity(
                    level, rules, usdt_balance, "BUY"
                )

                if optimal_quantity is None:
                    failed_orders += 1
                    continue

                # 🔥 ENHANCED: Try placing order with retry mechanism
                order_result = await self._place_order_with_intelligent_retry(
                    symbol, "BUY", optimal_quantity, level["price"], rules
                )

                if order_result["success"]:
                    level["order_id"] = order_result["order_id"]
                    level["actual_quantity"] = order_result["quantity"]
                    orders_placed += 1
                    usdt_balance -= optimal_quantity * level["price"]

                    self.logger.info(
                        f"✅ BUY Level {level['level']}: {optimal_quantity:.4f} @ ${level['price']:.4f}"
                    )

                    # Log to database
                    self.trade_repo.log_grid_order(
                        client_id=self.client_id,
                        symbol=symbol,
                        side="BUY",
                        quantity=optimal_quantity,
                        price=level["price"],
                        order_id=order_result["order_id"],
                        grid_level=level["level"],
                    )
                elif order_result.get("recovered", False):
                    recovered_orders += 1
                    level["order_id"] = order_result["order_id"]
                    orders_placed += 1
                    self.logger.info(
                        f"🔄 BUY Level {level['level']} RECOVERED: {order_result['quantity']:.4f} @ ${order_result['price']:.4f}"
                    )
                else:
                    failed_orders += 1
                    self.logger.error(
                        f"❌ BUY Level {level['level']} failed after all retries: {order_result.get('error')}"
                    )

            except Exception as e:
                failed_orders += 1
                self.logger.error(f"❌ BUY Level {level['level']} error: {e}")

        return {
            "orders_placed": orders_placed,
            "failed_orders": failed_orders,
            "recovered_orders": recovered_orders,
        }

    async def _place_enhanced_sell_orders(
        self,
        symbol: str,
        grid_config: SingleAdvancedGridConfig,
        rules: Dict,
        asset_balance: float,
    ) -> Dict:
        """Place SELL orders with enhanced error handling"""
        orders_placed = 0
        failed_orders = 0
        recovered_orders = 0
        asset_symbol = symbol.replace("USDT", "")

        self.logger.info(
            f"💡 Attempting enhanced SELL orders with {asset_balance:.4f} {asset_symbol} available"
        )

        for level in grid_config.sell_levels:
            try:
                # 🔥 ENHANCED: Calculate optimal quantity with error prevention
                optimal_quantity = await self._calculate_optimal_order_quantity(
                    level, rules, asset_balance, "SELL"
                )

                if optimal_quantity is None:
                    failed_orders += 1
                    continue

                # Check if we have enough balance for this order
                if asset_balance < optimal_quantity:
                    self.logger.warning(
                        f"⚠️ Insufficient asset balance for SELL Level {level['level']}"
                    )
                    continue

                # 🔥 ENHANCED: Try placing order with retry mechanism
                order_result = await self._place_order_with_intelligent_retry(
                    symbol, "SELL", optimal_quantity, level["price"], rules
                )

                if order_result["success"]:
                    level["order_id"] = order_result["order_id"]
                    level["actual_quantity"] = order_result["quantity"]
                    level["quantity"] = optimal_quantity  # Update with actual quantity
                    orders_placed += 1
                    asset_balance -= optimal_quantity

                    self.logger.info(
                        f"✅ SELL Level {level['level']}: {optimal_quantity:.4f} @ ${level['price']:.4f}"
                    )

                    # Log to database
                    self.trade_repo.log_grid_order(
                        client_id=self.client_id,
                        symbol=symbol,
                        side="SELL",
                        quantity=optimal_quantity,
                        price=level["price"],
                        order_id=order_result["order_id"],
                        grid_level=level["level"],
                    )
                elif order_result.get("recovered", False):
                    recovered_orders += 1
                    level["order_id"] = order_result["order_id"]
                    orders_placed += 1
                    self.logger.info(
                        f"🔄 SELL Level {level['level']} RECOVERED: {order_result['quantity']:.4f} @ ${order_result['price']:.4f}"
                    )
                else:
                    failed_orders += 1
                    self.logger.error(
                        f"❌ SELL Level {level['level']} failed after all retries: {order_result.get('error')}"
                    )

            except Exception as e:
                failed_orders += 1
                self.logger.error(f"❌ SELL Level {level['level']} error: {e}")

        return {
            "orders_placed": orders_placed,
            "failed_orders": failed_orders,
            "recovered_orders": recovered_orders,
        }

    async def _calculate_optimal_order_quantity(
        self, level: Dict, rules: Dict, available_balance: float, side: str
    ) -> Optional[float]:
        """
        🔥 ENHANCED: Calculate optimal order quantity with NOTIONAL error prevention
        """
        try:
            min_notional = rules.get("min_notional", 5.0)
            min_qty = rules.get("min_qty", 0.1)
            step_size = rules.get("step_size", 0.1)

            # Calculate base quantity
            if side == "BUY":
                # For BUY: ensure order value meets minimum notional with safety margin
                min_order_value = (
                    min_notional * self.error_handling_config["notional_safety_margin"]
                )
                max_affordable = available_balance * 0.8  # Use 80% of balance
                order_value = min(
                    level["order_size_usd"], max_affordable, min_order_value
                )
                quantity = order_value / level["price"]
            else:  # SELL
                # For SELL: ensure quantity * price meets minimum notional
                min_quantity_for_notional = (
                    min_notional * self.error_handling_config["notional_safety_margin"]
                ) / level["price"]
                max_available = available_balance * 0.8
                quantity = max(
                    min_quantity_for_notional, min(level["quantity"], max_available)
                )

            # Apply exchange constraints
            quantity = max(quantity, min_qty)

            # Round to step size
            if step_size > 0:
                quantity = round(quantity / step_size) * step_size

            # Final validations
            order_value = quantity * level["price"]

            if order_value < min_notional:
                self.logger.warning(
                    f"⚠️ {side} Level {level['level']}: Order value ${order_value:.2f} below minimum ${min_notional:.2f}"
                )
                return None

            if quantity < min_qty:
                self.logger.warning(
                    f"⚠️ {side} Level {level['level']}: Quantity {quantity:.4f} below minimum {min_qty:.4f}"
                )
                return None

            self.logger.debug(
                f"✅ Optimal {side} quantity: {quantity:.4f} (value: ${order_value:.2f})"
            )
            return quantity

        except Exception as e:
            self.logger.error(f"❌ Error calculating optimal quantity for {side}: {e}")
            return None

    async def _place_order_with_intelligent_retry(
        self, symbol: str, side: str, quantity: float, price: float, rules: Dict
    ) -> Dict:
        """
        🔥 ENHANCED: Place order with intelligent retry and error recovery
        """
        max_retries = self.error_handling_config["max_retries"]
        retry_delay = self.error_handling_config["retry_delay"]

        for attempt in range(max_retries + 1):
            try:
                # Format order parameters
                quantity_str = self._format_quantity(quantity, rules)
                price_str = self._format_price(price, rules)

                # Execute order
                if side == "BUY":
                    order = self.binance_client.order_limit_buy(
                        symbol=symbol,
                        quantity=quantity_str,
                        price=price_str,
                        recvWindow=60000,
                    )
                else:
                    order = self.binance_client.order_limit_sell(
                        symbol=symbol,
                        quantity=quantity_str,
                        price=price_str,
                        recvWindow=60000,
                    )

                return {
                    "success": True,
                    "order_id": order["orderId"],
                    "quantity": float(order["origQty"]),
                    "price": float(order["price"]),
                    "attempts": attempt + 1,
                }

            except BinanceAPIException as e:
                self.error_stats["total_retries"] += 1

                if e.code == -1013 and "NOTIONAL" in str(e):
                    # 🔥 ENHANCED: Handle NOTIONAL filter failure
                    self.error_stats["notional_failures"] += 1

                    recovery_result = await self._handle_notional_error(
                        symbol, side, quantity, price, rules, attempt
                    )

                    if recovery_result["success"]:
                        self.error_stats["notional_recoveries"] += 1
                        self.error_stats["successful_recoveries"] += 1
                        return {
                            "success": True,
                            "recovered": True,
                            "order_id": recovery_result["order_id"],
                            "quantity": recovery_result["quantity"],
                            "price": recovery_result["price"],
                            "original_error": str(e),
                            "recovery_method": recovery_result["method"],
                        }
                    else:
                        quantity = recovery_result.get("adjusted_quantity", quantity)
                        price = recovery_result.get("adjusted_price", price)

                elif attempt < max_retries:
                    self.logger.warning(
                        f"⚠️ {side} order attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s..."
                    )
                    await self._async_sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff

                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1,
                        "final_quantity": quantity,
                        "final_price": price,
                    }

            except Exception as e:
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1,
                    }

                self.logger.warning(
                    f"⚠️ {side} order attempt {attempt + 1} failed with unexpected error: {e}"
                )
                await self._async_sleep(retry_delay)

        return {"success": False, "error": "Max retries exceeded"}

    async def _handle_notional_error(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        rules: Dict,
        attempt: int,
    ) -> Dict:
        """
        🔥 ENHANCED: Intelligent NOTIONAL error recovery
        """
        try:
            self.logger.info(
                f"🔄 Handling NOTIONAL error for {side} {symbol} (attempt {attempt + 1})"
            )

            min_notional = rules.get("min_notional", 5.0)
            current_value = quantity * price

            # Method 1: Increase quantity to meet notional
            if self.error_handling_config["dynamic_adjustment_enabled"]:
                target_value = (
                    min_notional * self.error_handling_config["notional_safety_margin"]
                )
                adjusted_quantity = target_value / price

                # Apply exchange constraints
                step_size = rules.get("step_size", 0.1)
                if step_size > 0:
                    adjusted_quantity = round(adjusted_quantity / step_size) * step_size

                # Validate the adjustment
                new_value = adjusted_quantity * price
                if new_value >= min_notional:
                    self.logger.info(
                        f"💡 NOTIONAL recovery: Adjusting quantity {quantity:.4f} → {adjusted_quantity:.4f} "
                        f"(value: ${current_value:.2f} → ${new_value:.2f})"
                    )

                    # Try the adjusted order
                    try:
                        quantity_str = self._format_quantity(adjusted_quantity, rules)
                        price_str = self._format_price(price, rules)

                        if side == "BUY":
                            order = self.binance_client.order_limit_buy(
                                symbol=symbol,
                                quantity=quantity_str,
                                price=price_str,
                                recvWindow=60000,
                            )
                        else:
                            order = self.binance_client.order_limit_sell(
                                symbol=symbol,
                                quantity=quantity_str,
                                price=price_str,
                                recvWindow=60000,
                            )

                        return {
                            "success": True,
                            "order_id": order["orderId"],
                            "quantity": float(order["origQty"]),
                            "price": float(order["price"]),
                            "method": "quantity_adjustment",
                            "original_quantity": quantity,
                            "adjustment_factor": adjusted_quantity / quantity,
                        }

                    except Exception as retry_error:
                        self.logger.warning(
                            f"⚠️ Quantity adjustment failed: {retry_error}"
                        )

            # Method 2: Slight price adjustment (for limit orders)
            if attempt == 0:  # Only try once
                price_adjustment = 1.001 if side == "BUY" else 0.999  # 0.1% adjustment
                adjusted_price = price * price_adjustment

                # Round to tick size
                tick_size = rules.get("tick_size", 0.0001)
                if tick_size > 0:
                    adjusted_price = round(adjusted_price / tick_size) * tick_size

                new_value = quantity * adjusted_price
                if new_value >= min_notional:
                    return {
                        "success": False,
                        "adjusted_quantity": quantity,
                        "adjusted_price": adjusted_price,
                        "method": "price_adjustment",
                    }

            return {"success": False, "method": "no_recovery_possible"}

        except Exception as e:
            self.logger.error(f"❌ NOTIONAL error recovery failed: {e}")
            return {"success": False, "error": str(e)}

    async def _apply_fallback_strategies(
        self,
        symbol: str,
        grid_config: SingleAdvancedGridConfig,
        rules: Dict,
        usdt_balance: float,
        asset_balance: float,
    ) -> Dict:
        """
        🔥 ENHANCED: Apply fallback strategies when all orders fail
        """
        try:
            self.logger.info(f"🆘 Applying fallback strategies for {symbol}")

            orders_placed = 0
            min_notional = rules.get("min_notional", 5.0)

            # Fallback 1: Single large order at current price
            if (
                usdt_balance >= min_notional * 2
            ):  # Ensure we have enough for a meaningful order
                try:
                    current_price = await self._get_current_price(symbol)
                    if current_price:
                        # Place one larger BUY order
                        order_value = min(
                            usdt_balance * 0.5, min_notional * 3
                        )  # 3x minimum notional
                        quantity = order_value / current_price

                        # Apply constraints
                        quantity = self._apply_quantity_constraints(quantity, rules)

                        order_result = await self._place_order_with_intelligent_retry(
                            symbol, "BUY", quantity, current_price, rules
                        )

                        if order_result["success"]:
                            orders_placed += 1
                            self.logger.info(
                                f"🆘 Fallback BUY order placed: {quantity:.4f} @ ${current_price:.4f}"
                            )

                            # Add to grid config as emergency level
                            emergency_level = {
                                "level": 999,  # Special level for fallback
                                "side": "BUY",
                                "price": current_price,
                                "quantity": quantity,
                                "order_id": order_result["order_id"],
                                "filled": False,
                                "fallback": True,
                            }
                            grid_config.buy_levels.append(emergency_level)

                except Exception as e:
                    self.logger.error(f"❌ Fallback BUY strategy failed: {e}")

            # Fallback 2: Single SELL order if we have assets
            if asset_balance > rules.get("min_qty", 0.1) and orders_placed == 0:
                try:
                    current_price = await self._get_current_price(symbol)
                    if current_price:
                        # Place one SELL order at slightly higher price
                        sell_price = current_price * 1.01  # 1% above current price
                        sell_quantity = min(
                            asset_balance * 0.3, asset_balance
                        )  # Use 30% of balance

                        # Apply constraints
                        sell_quantity = self._apply_quantity_constraints(
                            sell_quantity, rules
                        )

                        # Ensure order value meets minimum notional
                        if sell_quantity * sell_price >= min_notional:
                            order_result = (
                                await self._place_order_with_intelligent_retry(
                                    symbol, "SELL", sell_quantity, sell_price, rules
                                )
                            )

                            if order_result["success"]:
                                orders_placed += 1
                                self.logger.info(
                                    f"🆘 Fallback SELL order placed: {sell_quantity:.4f} @ ${sell_price:.4f}"
                                )

                                # Add to grid config as emergency level
                                emergency_level = {
                                    "level": 998,  # Special level for fallback
                                    "side": "SELL",
                                    "price": sell_price,
                                    "quantity": sell_quantity,
                                    "order_id": order_result["order_id"],
                                    "filled": False,
                                    "fallback": True,
                                }
                                grid_config.sell_levels.append(emergency_level)

                except Exception as e:
                    self.logger.error(f"❌ Fallback SELL strategy failed: {e}")

            self.logger.info(
                f"🆘 Fallback strategies completed: {orders_placed} emergency orders placed"
            )

            return {"orders_placed": orders_placed, "strategy": "emergency_fallback"}

        except Exception as e:
            self.logger.error(f"❌ Fallback strategies error: {e}")
            return {"orders_placed": 0, "error": str(e)}

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol"""
        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"❌ Error getting current price for {symbol}: {e}")
            return None

    def _apply_quantity_constraints(self, quantity: float, rules: Dict) -> float:
        """Apply exchange quantity constraints"""
        min_qty = rules.get("min_qty", 0.1)
        step_size = rules.get("step_size", 0.1)

        # Ensure minimum quantity
        quantity = max(quantity, min_qty)

        # Round to step size
        if step_size > 0:
            quantity = round(quantity / step_size) * step_size

        return quantity

    def _format_quantity(self, quantity: float, rules: Dict) -> str:
        """Format quantity with proper precision"""
        precision = rules.get("quantity_precision", 1)
        formatted = f"{quantity:.{precision}f}".rstrip("0").rstrip(".")
        if "." not in formatted and precision > 0:
            formatted += ".0"
        return formatted

    def _format_price(self, price: float, rules: Dict) -> str:
        """Format price with proper precision"""
        precision = rules.get("price_precision", 4)
        formatted = f"{price:.{precision}f}".rstrip("0").rstrip(".")
        if "." not in formatted and precision > 0:
            formatted += ".0"
        return formatted

    async def _execute_order_with_retry(
        self, order_type: str, **kwargs
    ) -> Optional[Dict]:
        """Execute order with retry mechanism"""
        max_retries = self.error_handling_config["max_retries"]
        retry_delay = self.error_handling_config["retry_delay"]

        for attempt in range(max_retries + 1):
            try:
                if order_type == "market_buy":
                    return self.binance_client.order_market_buy(**kwargs)
                elif order_type == "market_sell":
                    return self.binance_client.order_market_sell(**kwargs)
                # Add more order types as needed

            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(
                        f"⚠️ {order_type} attempt {attempt + 1} failed: {e}. Retrying..."
                    )
                    await self._async_sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    self.logger.error(
                        f"❌ {order_type} failed after {max_retries} retries: {e}"
                    )
                    return None

        return None

    async def _async_sleep(self, seconds: float):
        """Async sleep helper"""
        import asyncio

        await asyncio.sleep(seconds)

    async def _get_current_balances(self, symbol: str) -> Tuple[float, float]:
        """Get current USDT and asset balances with error handling"""
        try:
            account_info = self.binance_client.get_account()
            usdt_balance = 0.0
            asset_balance = 0.0
            asset_symbol = symbol.replace("USDT", "")

            for balance in account_info["balances"]:
                if balance["asset"] == "USDT":
                    usdt_balance = float(balance["free"])
                elif balance["asset"] == asset_symbol:
                    asset_balance = float(balance["free"])

            return usdt_balance, asset_balance

        except Exception as e:
            self.logger.error(f"❌ Enhanced balance check error: {e}")
            return 0.0, 0.0

    async def check_and_replace_filled_orders(
        self, symbol: str, grid_config: SingleAdvancedGridConfig
    ):
        """
        Enhanced order monitoring with error recovery
        """
        try:
            # Get open orders to determine which are filled
            open_orders = self.binance_client.get_open_orders(symbol=symbol)
            open_order_ids = {order["orderId"] for order in open_orders}

            self.logger.debug(
                f"🔍 Enhanced order check for {symbol}: {len(open_order_ids)} still open"
            )

            # Check buy levels for fills with enhanced handling
            for level in grid_config.buy_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level.get("filled", False)
                ):
                    await self._handle_buy_order_fill_enhanced(
                        symbol, level, grid_config
                    )

            # Check sell levels for fills with enhanced handling
            for level in grid_config.sell_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level.get("filled", False)
                ):
                    await self._handle_sell_order_fill_enhanced(
                        symbol, level, grid_config
                    )

        except Exception as e:
            self.logger.error(f"❌ Enhanced order replacement error for {symbol}: {e}")
            await self.fifo_service.on_api_error(
                error_code=str(getattr(e, "code", "UNKNOWN")),
                error_message=str(e),
                symbol=symbol,
                operation="enhanced_order_replacement",
            )

    async def _handle_buy_order_fill_enhanced(
        self, symbol: str, level: Dict, grid_config: SingleAdvancedGridConfig
    ):
        """Enhanced BUY order fill handling"""
        try:
            # Mark as filled
            level["filled"] = True

            # Update inventory after fill
            if self.inventory_manager:
                self.inventory_manager.update_after_fill(
                    symbol, "BUY", level["quantity"], level["price"]
                )

            # Log trade execution
            self.trade_repo.log_trade_execution(
                client_id=self.client_id,
                symbol=symbol,
                side="BUY",
                quantity=level["quantity"],
                price=level["price"],
                order_id=level["order_id"],
            )

            self.logger.info(
                f"💰 Enhanced BUY fill: Level {level['level']} - {level['quantity']:.4f} @ ${level['price']:.2f}"
            )

            # Send notification
            await self.fifo_service.on_order_filled(
                symbol, "BUY", level["quantity"], level["price"], level.get("level")
            )

            # Create replacement sell order with enhanced error handling
            await self.create_replacement_sell_order_enhanced(
                symbol, level, grid_config
            )

        except Exception as e:
            self.logger.error(f"❌ Enhanced BUY fill handling error: {e}")

    async def _handle_sell_order_fill_enhanced(
        self, symbol: str, level: Dict, grid_config: SingleAdvancedGridConfig
    ):
        """Enhanced SELL order fill handling"""
        try:
            # Mark as filled
            level["filled"] = True

            # Update inventory after fill
            if self.inventory_manager:
                self.inventory_manager.update_after_fill(
                    symbol, "SELL", level["quantity"], level["price"]
                )

            # Log trade execution
            self.trade_repo.log_trade_execution(
                client_id=self.client_id,
                symbol=symbol,
                side="SELL",
                quantity=level["quantity"],
                price=level["price"],
                order_id=level["order_id"],
            )

            self.logger.info(
                f"💰 Enhanced SELL fill: Level {level['level']} - {level['quantity']:.4f} @ ${level['price']:.2f}"
            )

            # Send notification
            await self.fifo_service.on_order_filled(
                symbol, "SELL", level["quantity"], level["price"], level.get("level")
            )

            # Create replacement buy order with enhanced error handling
            await self.create_replacement_buy_order_enhanced(symbol, level, grid_config)

        except Exception as e:
            self.logger.error(f"❌ Enhanced SELL fill handling error: {e}")

    async def create_replacement_sell_order_enhanced(
        self, symbol: str, filled_buy_level: Dict, grid_config: SingleAdvancedGridConfig
    ):
        """Enhanced replacement sell order creation with error recovery"""
        try:
            # Get exchange rules
            rules = await self.utility.get_exchange_rules_simple(symbol)

            # Calculate new sell price
            spacing = grid_config.grid_spacing
            raw_sell_price = filled_buy_level["price"] * (1 + spacing)
            valid_sell_price = self._make_valid_price(
                raw_sell_price, rules["tick_size"], rules["price_precision"]
            )

            # Get enhanced order size with compound growth
            if self.compound_manager:
                compound_order_size = (
                    await self.compound_manager.get_current_order_size(
                        self.client_id, symbol, grid_config.total_capital
                    )
                )
            else:
                compound_order_size = grid_config.total_capital / 10

            # Calculate quantity with enhanced error prevention
            order_usd = compound_order_size
            raw_quantity = order_usd / valid_sell_price

            # Apply enhanced quantity calculation
            optimal_quantity = await self._calculate_optimal_order_quantity(
                {
                    "price": valid_sell_price,
                    "order_size_usd": order_usd,
                    "level": filled_buy_level["level"],
                },
                rules,
                999999,  # Large available balance for calculation
                "SELL",
            )

            if optimal_quantity is None:
                self.logger.warning(
                    "⚠️ Cannot create replacement SELL order: optimal quantity calculation failed"
                )
                return

            # Check inventory constraints
            if self.inventory_manager:
                can_place, reason = self.inventory_manager.can_place_sell_order(
                    symbol, optimal_quantity
                )
                if not can_place:
                    self.logger.warning(
                        f"⚠️ Cannot place replacement SELL order: {reason}"
                    )
                    return

                # Reserve inventory
                if not self.inventory_manager.reserve_for_order(
                    symbol, "SELL", optimal_quantity, valid_sell_price
                ):
                    self.logger.warning(
                        "⚠️ Could not reserve inventory for replacement SELL order"
                    )
                    return

            # Place order with enhanced retry mechanism
            order_result = await self._place_order_with_intelligent_retry(
                symbol, "SELL", optimal_quantity, valid_sell_price, rules
            )

            if order_result["success"]:
                # Create new sell level
                new_sell_level = {
                    "level": filled_buy_level["level"]
                    + 100,  # Offset to avoid conflicts
                    "side": "SELL",
                    "price": valid_sell_price,
                    "quantity": optimal_quantity,
                    "order_size_usd": optimal_quantity * valid_sell_price,
                    "order_id": order_result["order_id"],
                    "filled": False,
                    "created_from_buy": filled_buy_level["level"],
                    "enhanced": True,
                }

                # Add to grid config
                grid_config.sell_levels.append(new_sell_level)

                recovery_info = (
                    " (RECOVERED)" if order_result.get("recovered", False) else ""
                )
                self.logger.info(
                    f"✅ Enhanced replacement SELL{recovery_info}: {optimal_quantity:.4f} @ ${valid_sell_price:.4f}"
                )

            else:
                # Release reservation if order failed
                if self.inventory_manager:
                    self.inventory_manager.release_reservation(
                        symbol, "SELL", optimal_quantity, valid_sell_price
                    )
                self.logger.error(
                    f"❌ Enhanced replacement SELL order failed: {order_result.get('error')}"
                )

        except Exception as e:
            self.logger.error(f"❌ Enhanced replacement sell order error: {e}")

    async def create_replacement_buy_order_enhanced(
        self,
        symbol: str,
        filled_sell_level: Dict,
        grid_config: SingleAdvancedGridConfig,
    ):
        """Enhanced replacement buy order creation with error recovery"""
        try:
            # Get exchange rules
            rules = await self.utility.get_exchange_rules_simple(symbol)

            # Calculate new buy price
            spacing = grid_config.grid_spacing
            raw_buy_price = filled_sell_level["price"] * (1 - spacing)
            valid_buy_price = self._make_valid_price(
                raw_buy_price, rules["tick_size"], rules["price_precision"]
            )

            # Get enhanced order size with compound growth
            if self.compound_manager:
                compound_order_size = (
                    await self.compound_manager.get_current_order_size(
                        self.client_id, symbol, grid_config.total_capital
                    )
                )
            else:
                compound_order_size = grid_config.total_capital / 10

            # Calculate quantity with enhanced error prevention
            order_usd = compound_order_size
            raw_quantity = order_usd / valid_buy_price

            # Apply enhanced quantity calculation
            optimal_quantity = await self._calculate_optimal_order_quantity(
                {
                    "price": valid_buy_price,
                    "order_size_usd": order_usd,
                    "level": filled_sell_level["level"],
                },
                rules,
                999999,  # Large available balance for calculation
                "BUY",
            )

            if optimal_quantity is None:
                self.logger.warning(
                    "⚠️ Cannot create replacement BUY order: optimal quantity calculation failed"
                )
                return

            # Calculate actual order value
            actual_order_value = optimal_quantity * valid_buy_price

            # Check inventory constraints
            if self.inventory_manager:
                can_place, reason = self.inventory_manager.can_place_buy_order(
                    symbol, actual_order_value
                )
                if not can_place:
                    self.logger.warning(
                        f"⚠️ Cannot place replacement BUY order: {reason}"
                    )
                    return

                # Reserve inventory
                if not self.inventory_manager.reserve_for_order(
                    symbol, "BUY", optimal_quantity, valid_buy_price
                ):
                    self.logger.warning(
                        "⚠️ Could not reserve inventory for replacement BUY order"
                    )
                    return

            # Place order with enhanced retry mechanism
            order_result = await self._place_order_with_intelligent_retry(
                symbol, "BUY", optimal_quantity, valid_buy_price, rules
            )

            if order_result["success"]:
                # Create new buy level
                new_buy_level = {
                    "level": filled_sell_level["level"]
                    - 100,  # Offset to avoid conflicts
                    "side": "BUY",
                    "price": valid_buy_price,
                    "quantity": optimal_quantity,
                    "order_size_usd": actual_order_value,
                    "order_id": order_result["order_id"],
                    "filled": False,
                    "created_from_sell": filled_sell_level["level"],
                    "enhanced": True,
                }

                # Add to grid config
                grid_config.buy_levels.append(new_buy_level)

                recovery_info = (
                    " (RECOVERED)" if order_result.get("recovered", False) else ""
                )
                self.logger.info(
                    f"✅ Enhanced replacement BUY{recovery_info}: {optimal_quantity:.4f} @ ${valid_buy_price:.4f}"
                )

            else:
                # Release reservation if order failed
                if self.inventory_manager:
                    self.inventory_manager.release_reservation(
                        symbol, "BUY", optimal_quantity, valid_buy_price
                    )
                self.logger.error(
                    f"❌ Enhanced replacement BUY order failed: {order_result.get('error')}"
                )

        except Exception as e:
            self.logger.error(f"❌ Enhanced replacement buy order error: {e}")

    def _make_valid_price(
        self, price: float, tick_size: float, precision: int
    ) -> float:
        """Enhanced price validation with error handling"""
        try:
            # Round to tick size
            if tick_size > 0:
                price = round(price / tick_size) * tick_size

            # Apply precision
            return round(price, precision)
        except Exception as e:
            self.logger.error(f"❌ Enhanced price validation error: {e}")
            return price

    async def cancel_all_orders(
        self, symbol: str, grid_config: SingleAdvancedGridConfig
    ) -> int:
        """Enhanced order cancellation with retry mechanism"""
        cancelled_orders = 0

        try:
            for level in grid_config.buy_levels + grid_config.sell_levels:
                if level["order_id"] and not level["filled"]:
                    # Try cancelling with retry
                    for attempt in range(3):
                        try:
                            self.binance_client.cancel_order(
                                symbol=symbol, orderId=level["order_id"]
                            )
                            cancelled_orders += 1
                            level["order_id"] = None
                            break
                        except Exception as e:
                            if attempt == 2:  # Last attempt
                                self.logger.warning(
                                    f"⚠️ Failed to cancel order {level['order_id']} after 3 attempts: {e}"
                                )
                            else:
                                await self._async_sleep(0.5)  # Brief delay before retry

            self.logger.info(
                f"✅ Enhanced cancellation completed: {cancelled_orders} orders cancelled for {symbol}"
            )

        except Exception as e:
            self.logger.error(f"❌ Enhanced order cancellation error for {symbol}: {e}")

        return cancelled_orders

    def get_trading_stats(
        self, symbol: str, grid_config: SingleAdvancedGridConfig
    ) -> Dict:
        """Enhanced trading statistics with error handling metrics"""
        try:
            buy_orders_active = sum(
                1
                for level in grid_config.buy_levels
                if level["order_id"] and not level.get("filled", False)
            )
            sell_orders_active = sum(
                1
                for level in grid_config.sell_levels
                if level["order_id"] and not level.get("filled", False)
            )
            buy_orders_filled = sum(
                1 for level in grid_config.buy_levels if level.get("filled", False)
            )
            sell_orders_filled = sum(
                1 for level in grid_config.sell_levels if level.get("filled", False)
            )
            enhanced_orders = sum(
                1
                for level in grid_config.buy_levels + grid_config.sell_levels
                if level.get("enhanced", False)
            )
            fallback_orders = sum(
                1
                for level in grid_config.buy_levels + grid_config.sell_levels
                if level.get("fallback", False)
            )

            total_buy_value = sum(
                level["order_size_usd"]
                for level in grid_config.buy_levels
                if level["order_id"]
            )
            total_sell_value = sum(
                level["order_size_usd"]
                for level in grid_config.sell_levels
                if level["order_id"]
            )

            return {
                "symbol": symbol,
                "buy_orders_active": buy_orders_active,
                "sell_orders_active": sell_orders_active,
                "buy_orders_filled": buy_orders_filled,
                "sell_orders_filled": sell_orders_filled,
                "total_orders_active": buy_orders_active + sell_orders_active,
                "total_orders_filled": buy_orders_filled + sell_orders_filled,
                "enhanced_orders": enhanced_orders,
                "fallback_orders": fallback_orders,
                "total_buy_value": total_buy_value,
                "total_sell_value": total_sell_value,
                "grid_center_price": grid_config.center_price,
                "grid_spacing": grid_config.grid_spacing * 100,  # As percentage
                "error_handling_stats": self.error_stats.copy(),
                "recovery_rate": (
                    self.error_stats["successful_recoveries"]
                    / max(self.error_stats["total_retries"], 1)
                )
                * 100,
                "notional_recovery_rate": (
                    self.error_stats["notional_recoveries"]
                    / max(self.error_stats["notional_failures"], 1)
                )
                * 100,
            }

        except Exception as e:
            self.logger.error(f"❌ Enhanced trading stats error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "buy_orders_active": 0,
                "sell_orders_active": 0,
                "total_orders_active": 0,
                "error_handling_enabled": True,
            }

    def get_error_handling_summary(self) -> Dict:
        """Get comprehensive error handling summary"""
        return {
            "configuration": self.error_handling_config.copy(),
            "statistics": self.error_stats.copy(),
            "features": {
                "notional_error_recovery": True,
                "intelligent_retry_mechanism": True,
                "dynamic_quantity_adjustment": True,
                "fallback_strategies": True,
                "order_size_optimization": True,
                "enhanced_price_validation": True,
            },
            "performance_metrics": {
                "overall_recovery_rate": (
                    self.error_stats["successful_recoveries"]
                    / max(self.error_stats["total_retries"], 1)
                )
                * 100,
                "notional_recovery_rate": (
                    self.error_stats["notional_recoveries"]
                    / max(self.error_stats["notional_failures"], 1)
                )
                * 100,
                "fallback_usage_rate": self.error_stats["fallback_activations"],
            },
        }

    async def create_advanced_grid_levels(
        self,
        grid_config,  # Your original SingleAdvancedGridConfig
        current_price: float,
        optimal_config: Dict,
    ) -> Dict:
        """
        Your original method signature - 4 arguments (including self)

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
            symbol_info = await self.utility.get_symbol_precision_info(
                grid_config.symbol
            )
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
                price = self.utility.round_to_tick_size(raw_price, tick_size)

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
                price = self.utility.round_to_tick_size(raw_price, tick_size)

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
