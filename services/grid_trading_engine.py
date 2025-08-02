# services/grid_trading_engine.py

import logging
from typing import Dict, Optional

from binance.client import Client

from models.grid_config import validate_grid_config
from services.fifo_service import FIFOService
from services.grid_utils import GridUtilityService


class GridTradingEngine:
    """Clean grid trading engine with proper inventory integration"""

    def __init__(self, binance_client: Client, client_id: int):
        self.binance_client = binance_client
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        # Core services
        self.utility = GridUtilityService(binance_client)
        self.fifo_service = FIFOService()

        # Managers (set by GridManager)
        self.inventory_manager = None
        self.compound_manager = None

        self.logger.info("🔧 GridTradingEngine initialized")

    def set_managers(self, inventory_manager, compound_manager):
        """Set manager references from GridManager"""
        self.inventory_manager = inventory_manager
        self.compound_manager = compound_manager
        self.logger.info("✅ Managers set successfully")
        return True

    async def execute_initial_50_50_split(
        self, symbol: str, total_capital: float, current_price: float
    ) -> Dict:
        """Execute initial 50/50 split for Pure USDT allocation"""
        try:
            self.logger.info(f"💰 Executing enhanced 50/50 split for {symbol}")

            # Get exchange rules
            exchange_rules = await self.utility.get_exchange_rules_simple(symbol)
            if not exchange_rules:
                return {
                    "success": False,
                    "error": f"Could not get exchange info for {symbol}",
                }

            # Calculate asset purchase (50% of capital)
            asset_purchase_value = total_capital * 0.5
            asset_quantity = asset_purchase_value / current_price

            # Round to exchange precision
            precision = exchange_rules.get("quantity_precision", 4)
            asset_quantity = round(asset_quantity, precision)

            self.logger.info(
                f"🛒 Enhanced purchase: {asset_quantity} {symbol.replace('USDT', '')} @ ${current_price:.2f}"
            )

            try:
                # Execute the purchase
                order = self.binance_client.order_market_buy(
                    symbol=symbol, quantity=asset_quantity
                )

                # Get actual fill details
                filled_qty = float(order.get("executedQty", asset_quantity))
                filled_value = sum(
                    float(fill["price"]) * float(fill["qty"])
                    for fill in order.get("fills", [])
                )

                if not filled_value:  # Fallback calculation
                    filled_value = filled_qty * current_price

                self.logger.info("✅ Enhanced purchase completed:")
                self.logger.info(
                    f"   🪙 Asset acquired: {filled_qty:.4f} {symbol.replace('USDT', '')}"
                )
                self.logger.info(f"   💰 USDT spent: ${filled_value:.2f}")
                self.logger.info(
                    f"   💰 USDT remaining: ${total_capital - filled_value:.2f}"
                )

                return {
                    "success": True,
                    "asset_quantity": filled_qty,
                    "usdt_spent": filled_value,
                    "usdt_remaining": total_capital - filled_value,
                    "order_details": order,
                }

            except Exception as order_error:
                self.logger.error(f"❌ Order execution failed: {order_error}")
                return {
                    "success": False,
                    "error": f"Order execution failed: {order_error}",
                }

        except Exception as e:
            self.logger.error(f"❌ 50/50 split error: {e}")
            return {"success": False, "error": str(e)}

    async def create_advanced_grid_levels(
        self, grid_config, current_price: float, optimal_config: Dict
    ) -> Dict:
        """Create grid levels with guaranteed minimum notional compliance"""
        try:
            spacing = grid_config.grid_spacing
            base_order_size = optimal_config["base_order_size"]

            # Ensure ALL levels meet minimum notional
            min_notional = 10.0  # Binance minimum
            safety_margin = 1.2  # 20% safety margin
            minimum_order_size = min_notional * safety_margin  # $12 minimum

            # Adjust base order size if needed
            if base_order_size < minimum_order_size:
                base_order_size = minimum_order_size
                self.logger.info(
                    f"📈 Base order size adjusted to ${base_order_size:.2f} for notional compliance"
                )

            self.logger.info(
                f"🎯 Creating advanced grid levels for {grid_config.symbol}"
            )
            self.logger.info(f"   📊 Spacing: {spacing * 100:.2f}%")
            self.logger.info(f"   💰 Guaranteed order size: ${base_order_size:.2f}")
            self.logger.info(f"   💲 Current price: ${current_price:.6f}")

            # Get exchange rules
            exchange_rules = await self.utility.get_exchange_rules_simple(
                grid_config.symbol
            )
            if not exchange_rules:
                raise ValueError(
                    f"Could not get exchange info for {grid_config.symbol}"
                )

            price_precision = exchange_rules.get("price_precision", 2)
            tick_size = exchange_rules.get("tick_size", 0.01)

            # SELL LEVELS (5 levels above current price)
            sell_levels = []
            for i in range(1, 6):
                level_spacing = spacing * (1 + i * 0.1)
                raw_price = current_price * (1 + level_spacing)
                price = self.utility.round_to_tick_size(raw_price, tick_size)

                level_order_size = base_order_size
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
                    }
                )

            # BUY LEVELS (5 levels below current price)
            buy_levels = []
            for i in range(1, 6):
                level_spacing = spacing * (1 + i * 0.1)
                raw_price = current_price * (1 - level_spacing)
                price = self.utility.round_to_tick_size(raw_price, tick_size)

                level_order_size = base_order_size
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
                    }
                )

            # Update grid config
            grid_config.buy_levels = buy_levels
            grid_config.sell_levels = sell_levels

            # Verify ALL levels meet minimum notional
            failed_levels = []
            for level in buy_levels + sell_levels:
                notional_value = level["quantity"] * level["price"]
                if notional_value < min_notional:
                    failed_levels.append(
                        {
                            "level": level["level"],
                            "notional": notional_value,
                            "required": min_notional,
                        }
                    )

            if failed_levels:
                self.logger.error(
                    f"❌ {len(failed_levels)} levels still below minimum notional:"
                )
                for failed in failed_levels:
                    self.logger.error(
                        f"   Level {failed['level']}: ${failed['notional']:.2f} < ${failed['required']:.2f}"
                    )

                # Emergency fix: Increase base order size more aggressively
                emergency_base_size = min_notional * 1.5  # 50% safety margin
                self.logger.info(
                    f"🚨 Emergency adjustment: Using ${emergency_base_size:.2f} per order"
                )

                # Recalculate all levels with emergency size
                for level in buy_levels + sell_levels:
                    level["order_size_usd"] = emergency_base_size
                    level["quantity"] = emergency_base_size / level["price"]

            self.logger.info(
                "✅ Grid levels created with GUARANTEED notional compliance:"
            )
            self.logger.info(f"   📈 SELL levels: {len(sell_levels)}")
            self.logger.info(f"   📉 BUY levels: {len(buy_levels)}")
            self.logger.info(f"   💰 Order size per level: ${base_order_size:.2f}")

            # Log sample levels to verify
            for level in sell_levels[:2]:
                notional = level["quantity"] * level["price"]
                self.logger.info(
                    f"      SELL Level {level['level']}: ${notional:.2f} notional ✅"
                )

            for level in buy_levels[:2]:
                notional = level["quantity"] * level["price"]
                self.logger.info(
                    f"      BUY Level {level['level']}: ${notional:.2f} notional ✅"
                )

        except Exception as e:
            self.logger.error(f"❌ Grid level creation error: {e}")
            raise

    async def execute_enhanced_grid_setup(self, symbol: str, grid_config) -> Dict:
        """Execute enhanced grid setup with proper error handling"""
        try:
            self.logger.info(
                f"🎯 Executing enhanced grid setup with error recovery for {symbol}"
            )

            # Get account balances
            account = self.binance_client.get_account()
            usdt_balance = 0
            asset_balance = 0

            for balance in account["balances"]:
                if balance["asset"] == "USDT":
                    usdt_balance = float(balance["free"])
                elif balance["asset"] == symbol.replace("USDT", ""):
                    asset_balance = float(balance["free"])

            self.logger.info(
                f"📊 Actual balances: USDT=${usdt_balance:.2f}, {symbol.replace('USDT', '')}={asset_balance:.4f}"
            )

            orders_placed = 0
            failed_orders = 0

            # Get exchange rules for validation
            exchange_rules = await self.utility.get_exchange_rules_simple(symbol)

            # Place buy orders
            for level in grid_config.buy_levels:
                try:
                    raw_quantity = level["quantity"]

                    self.logger.debug(
                        f"🎯 BUY Level {level['level']}: Using grid quantity {raw_quantity:.6f} (${level['order_size_usd']:.2f})"
                    )

                    if raw_quantity <= 0:
                        self.logger.warning(
                            f"⚠️ BUY Level {level['level']}: Invalid quantity {raw_quantity}"
                        )
                        failed_orders += 1
                        continue

                    # Validate and format order parameters
                    validation_result = self.utility.validate_order_params(
                        symbol=symbol,
                        quantity=raw_quantity,
                        price=level["price"],
                        rules=exchange_rules,
                    )

                    if not validation_result.get("valid", False):
                        self.logger.warning(
                            f"⚠️ BUY Level {level['level']}: Order validation failed: {validation_result.get('error', 'Unknown error')}"
                        )
                        failed_orders += 1
                        continue

                    # Use validated parameters
                    quantity_string = validation_result["quantity_string"]
                    price_string = validation_result["price_string"]

                    # Verify notional value
                    if validation_result["notional_value"] < exchange_rules.get(
                        "min_notional", 10.0
                    ):
                        self.logger.warning(
                            f"⚠️ BUY Level {level['level']}: Order value ${validation_result['notional_value']:.2f} below minimum"
                        )
                        failed_orders += 1
                        continue

                    # Place order
                    order = self.binance_client.order_limit_buy(
                        symbol=symbol,
                        quantity=quantity_string,
                        price=price_string,
                    )

                    level["order_id"] = order["orderId"]
                    orders_placed += 1

                    self.logger.info(
                        f"✅ BUY Level {level['level']}: {quantity_string} @ ${price_string}"
                    )

                except Exception as e:
                    self.logger.error(f"❌ BUY Level {level['level']} failed: {e}")
                    failed_orders += 1

            # Place sell orders
            self.logger.info(
                f"💡 Attempting SELL orders with {asset_balance:.4f} {symbol.replace('USDT', '')} available"
            )

            for level in grid_config.sell_levels:
                try:
                    intended_quantity = level["quantity"]

                    self.logger.debug(
                        f"🎯 SELL Level {level['level']}: Intended quantity {intended_quantity:.6f} (${level['order_size_usd']:.2f})"
                    )

                    # Check if we have enough assets for this specific order
                    if intended_quantity > asset_balance:
                        self.logger.warning(
                            f"⚠️ SELL Level {level['level']}: Need {intended_quantity:.6f} but only have {asset_balance:.6f}"
                        )

                        # Try to use what we have if it's still meaningful
                        available_quantity = asset_balance * 0.8

                        # Check if this smaller quantity still meets minimum notional
                        test_notional = available_quantity * level["price"]
                        if test_notional >= exchange_rules.get("min_notional", 10.0):
                            raw_quantity = available_quantity
                            self.logger.info(
                                f"📉 SELL Level {level['level']}: Adjusted to available {raw_quantity:.6f}"
                            )
                        else:
                            self.logger.warning(
                                f"⚠️ SELL Level {level['level']}: Available quantity too small for min notional"
                            )
                            failed_orders += 1
                            continue
                    else:
                        raw_quantity = intended_quantity

                    if raw_quantity <= 0:
                        self.logger.warning(
                            f"⚠️ SELL Level {level['level']}: Invalid quantity {raw_quantity}"
                        )
                        failed_orders += 1
                        continue

                    # Validate and format order parameters
                    validation_result = self.utility.validate_order_params(
                        symbol=symbol,
                        quantity=raw_quantity,
                        price=level["price"],
                        rules=exchange_rules,
                    )

                    if not validation_result.get("valid", False):
                        self.logger.warning(
                            f"⚠️ SELL Level {level['level']}: Order validation failed: {validation_result.get('error', 'Unknown error')}"
                        )
                        failed_orders += 1
                        continue

                    # Use validated parameters
                    order_quantity = validation_result["valid_quantity"]
                    quantity_string = validation_result["quantity_string"]
                    price_string = validation_result["price_string"]

                    # Verify notional value
                    if validation_result["notional_value"] < exchange_rules.get(
                        "min_notional", 10.0
                    ):
                        self.logger.warning(
                            f"⚠️ SELL Level {level['level']}: Order value ${validation_result['notional_value']:.2f} below minimum"
                        )
                        failed_orders += 1
                        continue

                    # Place order
                    order = self.binance_client.order_limit_sell(
                        symbol=symbol,
                        quantity=quantity_string,
                        price=price_string,
                    )

                    level["order_id"] = order["orderId"]
                    orders_placed += 1

                    self.logger.info(
                        f"✅ SELL Level {level['level']}: {quantity_string} @ ${price_string} (${validation_result['notional_value']:.2f})"
                    )

                    # Reduce available balance
                    asset_balance -= order_quantity

                except Exception as e:
                    self.logger.error(f"❌ SELL Level {level['level']} failed: {e}")
                    failed_orders += 1

            # Calculate success rate
            total_attempted = len(grid_config.buy_levels) + len(grid_config.sell_levels)
            success_rate = (
                (orders_placed / total_attempted * 100) if total_attempted > 0 else 0
            )

            self.logger.info("✅ Enhanced grid setup completed:")
            self.logger.info(f"   🎯 Orders placed: {orders_placed}")
            self.logger.info("   🔄 Orders recovered: 0")
            self.logger.info(f"   ❌ Failed orders: {failed_orders}")
            self.logger.info(f"   📊 Success rate: {success_rate:.1f}%")

            return {
                "success": orders_placed > 0,
                "orders_placed": orders_placed,
                "failed_orders": failed_orders,
                "success_rate": success_rate,
                "total_attempted": total_attempted,
            }

        except Exception as e:
            self.logger.error(f"❌ Grid setup error: {e}")
            return {"success": False, "error": str(e)}

    async def check_and_replace_filled_orders(self, symbol: str, grid_config):
        """Check for filled orders and create replacements"""
        try:
            all_levels = grid_config.buy_levels + grid_config.sell_levels

            for level in all_levels:
                if not level.get("order_id") or level.get("filled"):
                    continue

                try:
                    # Check order status
                    order = self.binance_client.get_order(
                        symbol=symbol, orderId=level["order_id"]
                    )

                    if order["status"] == "FILLED":
                        self.logger.info(
                            f"🔍 Processing FILLED order {order['orderId']} for {symbol}"
                        )
                        await self._handle_filled_order(
                            symbol, level, order, grid_config
                        )

                except Exception as e:
                    self.logger.error(
                        f"❌ Error checking order {level.get('order_id')}: {e}"
                    )

        except Exception as e:
            self.logger.error(f"❌ Error checking filled orders for {symbol}: {e}")

    async def _handle_filled_order(
        self, symbol: str, level: dict, order: dict, grid_config
    ):
        """Handle filled order"""
        try:
            side = order["side"]
            quantity = float(order["executedQty"])
            price = float(order["price"])

            self.logger.info(
                f"💰 {side} fill: Level {level['level']} - {quantity:.4f} @ ${price:.2f}"
            )

            # Update inventory
            if self.inventory_manager and self.inventory_manager.has_tracking(symbol):
                self.inventory_manager.update_after_fill(symbol, side, quantity, price)
            else:
                self.logger.warning(
                    f"⚠️ No inventory tracking for {symbol} - cannot update balances"
                )

            # Record in FIFO
            try:
                await self.fifo_service.on_order_filled(
                    client_id=self.client_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    order_id=order["orderId"],
                    level=level.get("level"),
                )
            except Exception as fifo_error:
                self.logger.error(f"❌ FIFO recording error: {fifo_error}")

            # Mark level as filled
            level["filled"] = True
            level["order_id"] = None

            # Create replacement order
            await self._create_replacement_order(symbol, level, side, grid_config)

        except Exception as e:
            self.logger.error(f"❌ Error handling filled order: {e}")

    async def _create_replacement_order(
        self, symbol: str, level: dict, original_side: str, grid_config
    ):
        """Create replacement order with complete validation"""
        try:
            # Validate grid config before proceeding
            if not validate_grid_config(grid_config, f"replacement_{symbol}"):
                self.logger.error(
                    f"❌ Invalid grid_config - aborting replacement order for {symbol}"
                )
                return

            if not self.inventory_manager or not hasattr(
                self.inventory_manager, "has_tracking"
            ):
                self.logger.warning(
                    f"⚠️ Cannot create replacement {original_side} order: No inventory manager for {symbol}"
                )
                return

            if not self.inventory_manager.has_tracking(symbol):
                self.logger.warning(f"⚠️ No inventory tracking for {symbol}")
                return

            # Determine opposite side for replacement
            replacement_side = "SELL" if original_side == "BUY" else "BUY"

            # Get current price and exchange rules
            current_price = await self._get_current_price(symbol)
            if not current_price:
                self.logger.error(f"❌ Cannot get current price for {symbol}")
                return

            exchange_rules = await self.utility.get_exchange_rules_simple(symbol)
            if not exchange_rules:
                self.logger.error(f"❌ Cannot get exchange rules for {symbol}")
                return

            # Get optimal quantity using inventory manager
            optimal_quantity = self.inventory_manager.get_optimal_quantity(
                symbol, replacement_side, current_price
            )

            if optimal_quantity <= 0:
                self.logger.warning(
                    f"⚠️ Optimal quantity calculation failed for {symbol}"
                )
                return

            # Format quantity with proper precision
            quantity_precision = exchange_rules.get("quantity_precision", 4)
            formatted_quantity = round(optimal_quantity, quantity_precision)

            # Validate inventory availability
            if replacement_side == "BUY":
                can_place, reason = self.inventory_manager.can_place_buy_order(
                    symbol, formatted_quantity * current_price
                )
            else:
                can_place, reason = self.inventory_manager.can_place_sell_order(
                    symbol, formatted_quantity
                )

            if not can_place:
                self.logger.warning(
                    f"⚠️ Cannot place {replacement_side} order for {symbol}: {reason}"
                )
                return

            # Calculate replacement price
            grid_spacing = grid_config.grid_spacing
            level_number = abs(level["level"])

            if replacement_side == "BUY":
                replacement_price = current_price * (1 - (grid_spacing * level_number))
            else:
                replacement_price = current_price * (1 + (grid_spacing * level_number))

            # Round to proper precision
            tick_size = exchange_rules.get("tick_size", 0.01)
            replacement_price = self.utility.round_to_tick_size(
                replacement_price, tick_size
            )

            # Format strings for Binance API
            quantity_string = f"{formatted_quantity:.{quantity_precision}f}".rstrip(
                "0"
            ).rstrip(".")
            price_string = f"{replacement_price:.6f}".rstrip("0").rstrip(".")

            # Ensure minimum precision
            if "." not in quantity_string and quantity_precision > 0:
                quantity_string = f"{formatted_quantity:.1f}"
            if "." not in price_string:
                price_string = f"{replacement_price:.2f}"

            # Reserve inventory
            if not self.inventory_manager.reserve_for_order(
                symbol, replacement_side, formatted_quantity, replacement_price
            ):
                self.logger.warning(f"⚠️ Cannot reserve inventory for {symbol}")
                return

            # Place replacement order
            try:
                if replacement_side == "BUY":
                    order = self.binance_client.order_limit_buy(
                        symbol=symbol,
                        quantity=quantity_string,
                        price=price_string,
                    )
                else:
                    order = self.binance_client.order_limit_sell(
                        symbol=symbol,
                        quantity=quantity_string,
                        price=price_string,
                    )

                # Update level with new order
                level["order_id"] = order["orderId"]
                level["filled"] = False
                level["price"] = replacement_price

                self.logger.info(
                    f"✅ Replacement {replacement_side} order placed: {quantity_string} @ ${price_string} (ID: {order['orderId']})"
                )

            except Exception as order_error:
                # Release reservation on failure
                self.inventory_manager.release_reservation(
                    symbol, replacement_side, formatted_quantity, replacement_price
                )
                self.logger.error(
                    f"❌ Failed to place replacement order: {order_error}"
                )

        except Exception as e:
            self.logger.error(f"❌ Error creating replacement order: {e}")

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""
        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"❌ Error getting price for {symbol}: {e}")
            return None

    async def cancel_all_orders(self, symbol: str, grid_config) -> int:
        """Cancel all orders for a grid"""
        cancelled_count = 0

        try:
            # Cancel buy orders
            for level in grid_config.buy_levels:
                if level.get("order_id") and not level.get("filled"):
                    try:
                        self.binance_client.cancel_order(
                            symbol=symbol, orderId=level["order_id"]
                        )
                        level["order_id"] = None
                        cancelled_count += 1
                    except Exception as e:
                        self.logger.error(
                            f"❌ Failed to cancel buy order {level.get('order_id')}: {e}"
                        )

            # Cancel sell orders
            for level in grid_config.sell_levels:
                if level.get("order_id") and not level.get("filled"):
                    try:
                        self.binance_client.cancel_order(
                            symbol=symbol, orderId=level["order_id"]
                        )
                        level["order_id"] = None
                        cancelled_count += 1
                    except Exception as e:
                        self.logger.error(
                            f"❌ Failed to cancel sell order {level.get('order_id')}: {e}"
                        )

        except Exception as e:
            self.logger.error(f"❌ Error cancelling orders for {symbol}: {e}")

        return cancelled_count

    def get_trading_stats(self, symbol: str, grid_config) -> Dict:
        """Get trading statistics for a grid"""
        try:
            total_orders = len(grid_config.buy_levels) + len(grid_config.sell_levels)
            active_orders = 0
            filled_orders = 0

            for level in grid_config.buy_levels + grid_config.sell_levels:
                if level.get("filled"):
                    filled_orders += 1
                elif level.get("order_id"):
                    active_orders += 1

            return {
                "total_orders_configured": total_orders,
                "total_orders_active": active_orders,
                "total_orders_filled": filled_orders,
                "grid_utilization": (filled_orders / total_orders * 100)
                if total_orders > 0
                else 0,
                "replacement_system": "active" if self.inventory_manager else "limited",
            }

        except Exception as e:
            self.logger.error(f"❌ Error getting trading stats for {symbol}: {e}")
            return {
                "total_orders_configured": 0,
                "total_orders_active": 0,
                "total_orders_filled": 0,
                "grid_utilization": 0,
                "replacement_system": "error",
            }
