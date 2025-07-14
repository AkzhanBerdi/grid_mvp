# services/grid_orchestrator.py
"""Grid Orchestrator - Manages all client grid trading operations"""

import logging
from typing import Dict, List

from binance.client import Client

from models.client import GridStatus
from models.grid_config import GridConfig
from repositories.client_repository import ClientRepository
from repositories.trade_repository import TradeRepository
from utils.crypto import CryptoUtils


class GridOrchestrator:
    """Manages grid trading for all clients"""

    def __init__(self):
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()
        self.crypto_utils = CryptoUtils()
        self.logger = logging.getLogger(__name__)

        # Active grids: {client_id: {symbol: GridConfig}}
        self.active_grids: Dict[int, Dict[str, GridConfig]] = {}

        # Binance clients: {client_id: Client}
        self.binance_clients: Dict[int, Client] = {}

    # services/grid_orchestrator.py - Fixed test_client_api method

    # services/grid_orchestrator.py - Fixed test_client_api method

    async def test_client_api(self, client_id: int) -> Dict:
        """Test client's Binance API connection with proper decryption"""
        try:
            client = self.client_repo.get_client(client_id)
            if (
                not client
                or not client.binance_api_key
                or not client.binance_secret_key
            ):
                return {"success": False, "error": "API keys not configured"}

            self.logger.info(f"Testing API connection for client {client_id}")

            # Use the repository's decryption method
            try:
                api_key, secret_key = self.client_repo.get_decrypted_api_keys(client)

                if not api_key or not secret_key:
                    return {"success": False, "error": "Failed to decrypt API keys"}

                self.logger.info(
                    f"API keys decrypted successfully for client {client_id}"
                )
                self.logger.debug(
                    f"API key length: {len(api_key)}, Secret key length: {len(secret_key)}"
                )

            except Exception as decrypt_error:
                self.logger.error(
                    f"Decryption error for client {client_id}: {decrypt_error}"
                )
                return {
                    "success": False,
                    "error": f"Key decryption failed: {str(decrypt_error)}",
                }

            # Create Binance client with better error handling
            try:
                from binance.client import Client

                binance_client = Client(api_key, secret_key, testnet=False)

                self.logger.info(f"Binance client created for client {client_id}")

            except Exception as client_error:
                self.logger.error(
                    f"Binance client creation error for client {client_id}: {client_error}"
                )
                return {
                    "success": False,
                    "error": f"Failed to create Binance client: {str(client_error)}",
                }

            # Test connection with timeout and better error handling
            try:
                # Test with ping first (lightweight)
                ping_result = binance_client.ping()
                self.logger.info(f"Binance ping successful for client {client_id}")

                # Test with account info (requires valid API keys)
                account = binance_client.get_account()

                # Store client for later use
                self.binance_clients[client_id] = binance_client

                self.logger.info(f"✅ API connection successful for client {client_id}")
                return {
                    "success": True,
                    "account_type": account.get("accountType"),
                    "can_trade": account.get("canTrade", False),
                    "permissions": account.get("permissions", []),
                    "balances_count": len(account.get("balances", [])),
                }

            except Exception as api_error:
                error_msg = str(api_error)
                self.logger.error(
                    f"❌ Binance API test failed for client {client_id}: {error_msg}"
                )

                # Parse common Binance API errors
                if "Invalid API-key" in error_msg:
                    return {
                        "success": False,
                        "error": "Invalid API key - please check your Binance API key",
                    }
                elif "Signature for this request is not valid" in error_msg:
                    return {
                        "success": False,
                        "error": "Invalid secret key - please check your Binance secret key",
                    }
                elif "IP address" in error_msg:
                    return {
                        "success": False,
                        "error": "IP restriction - add your server IP to Binance API whitelist",
                    }
                elif "permission" in error_msg.lower():
                    return {
                        "success": False,
                        "error": "API permissions - ensure 'Spot Trading' is enabled",
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Binance API error: {error_msg}",
                    }

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ API test failed for client {client_id}: {error_msg}")
            return {"success": False, "error": f"System error: {error_msg}"}

    async def start_client_grid(
        self, client_id: int, symbol: str, capital: float
    ) -> Dict:
        """Start grid trading for a client on a specific symbol - FIXED ORDER SIZING"""
        try:
            client = self.client_repo.get_client(client_id)
            if not client or not client.can_start_grid():
                return {"success": False, "error": "Client cannot start grid trading"}

            # Ensure we have a Binance client
            if client_id not in self.binance_clients:
                api_test = await self.test_client_api(client_id)
                if not api_test["success"]:
                    return {"success": False, "error": "Failed to connect to Binance"}

            binance_client = self.binance_clients[client_id]
            symbol_pair = f"{symbol}USDT"

            # Get current price
            try:
                ticker = binance_client.get_symbol_ticker(symbol=symbol_pair)
                current_price = float(ticker["price"])
            except Exception:
                return {
                    "success": False,
                    "error": f"Failed to get price for {symbol_pair}",
                }

            # FIXED: Proper order size calculation
            # Use the capital provided directly, not the client's default order size
            order_size_usd = (
                capital / client.grid_levels
            )  # Divide capital by number of levels

            self.logger.info("🔧 Order sizing calculation:")
            self.logger.info(f"   Total capital: ${capital}")
            self.logger.info(f"   Grid levels: {client.grid_levels}")
            self.logger.info(f"   Order size per level: ${order_size_usd:.2f}")

            # Create grid configuration with FIXED order size
            grid_config = GridConfig(
                symbol=symbol_pair,
                client_id=client_id,
                grid_spacing=client.grid_spacing,
                grid_levels=client.grid_levels,
                order_size=order_size_usd,  # Use calculated order size, not client.order_size
            )

            # Calculate and set grid levels
            grid_config.calculate_grid_levels(current_price)

            # Log the calculated grid for verification
            self.logger.info(f"📊 Grid setup for {symbol_pair}:")
            self.logger.info(f"   Current price: ${current_price:.4f}")
            self.logger.info(f"   Order size USD: ${order_size_usd:.2f}")
            self.logger.info(
                f"   Sample buy order: {order_size_usd / current_price:.3f} {symbol} at ${grid_config.buy_levels[0]['price']:.4f}"
            )
            self.logger.info(
                f"   Sample sell order: {order_size_usd / current_price:.3f} {symbol} at ${grid_config.sell_levels[0]['price']:.4f}"
            )

            # Execute initial grid setup
            setup_result = await self._execute_grid_setup(binance_client, grid_config)

            if setup_result["success"]:
                # Store active grid
                if client_id not in self.active_grids:
                    self.active_grids[client_id] = {}
                self.active_grids[client_id][symbol_pair] = grid_config

                # Update client status
                client.grid_status = GridStatus.ACTIVE
                self.client_repo.update_client(client)

                self.logger.info(
                    f"✅ Grid started for client {client_id}: {symbol_pair}"
                )

                return {
                    "success": True,
                    "status": {
                        "symbol": symbol_pair,
                        "center_price": current_price,
                        "buy_levels": len(grid_config.buy_levels),
                        "sell_levels": len(grid_config.sell_levels),
                        "total_orders": len(grid_config.buy_levels)
                        + len(grid_config.sell_levels),
                        "order_size": order_size_usd,
                        "total_capital": capital,
                    },
                }
            else:
                return {"success": False, "error": setup_result["error"]}

        except Exception as e:
            self.logger.error(f"❌ Error starting grid for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_grid_setup(
        self, binance_client: Client, grid_config: GridConfig
    ) -> Dict:
        """Execute the initial grid setup with proper price/quantity formatting"""
        try:
            # Get exchange info for the symbol to understand filters
            exchange_info = binance_client.get_exchange_info()
            symbol_info = None

            for symbol in exchange_info["symbols"]:
                if symbol["symbol"] == grid_config.symbol:
                    symbol_info = symbol
                    break

            if not symbol_info:
                return {
                    "success": False,
                    "error": f"Symbol {grid_config.symbol} not found",
                }

            # Extract filters
            price_filter = None
            lot_size_filter = None
            min_notional_filter = None

            for filter_info in symbol_info["filters"]:
                if filter_info["filterType"] == "PRICE_FILTER":
                    price_filter = filter_info
                elif filter_info["filterType"] == "LOT_SIZE":
                    lot_size_filter = filter_info
                elif filter_info["filterType"] == "MIN_NOTIONAL":
                    min_notional_filter = filter_info

            self.logger.info(f"Symbol filters for {grid_config.symbol}:")
            self.logger.info(f"  Price filter: {price_filter}")
            self.logger.info(f"  Lot size filter: {lot_size_filter}")
            self.logger.info(f"  Min notional filter: {min_notional_filter}")

            orders_placed = 0
            failed_orders = 0

            # Place buy orders (limit orders below current price)
            for level in grid_config.buy_levels:
                try:
                    # Format price according to Binance requirements
                    raw_price = level["price"]
                    raw_quantity = level["quantity"]

                    # Format price with proper precision
                    if price_filter:
                        tick_size = float(price_filter["tickSize"])
                        formatted_price = round(raw_price / tick_size) * tick_size

                        # Ensure price is within min/max bounds
                        min_price = float(price_filter["minPrice"])
                        max_price = float(price_filter["maxPrice"])
                        formatted_price = max(
                            min_price, min(max_price, formatted_price)
                        )
                    else:
                        formatted_price = round(raw_price, 8)

                    # Format quantity according to lot size
                    if lot_size_filter:
                        step_size = float(lot_size_filter["stepSize"])
                        formatted_quantity = round(raw_quantity / step_size) * step_size

                        # Ensure quantity is within min/max bounds
                        min_qty = float(lot_size_filter["minQty"])
                        max_qty = float(lot_size_filter["maxQty"])
                        formatted_quantity = max(
                            min_qty, min(max_qty, formatted_quantity)
                        )
                    else:
                        # Default formatting based on symbol
                        if grid_config.symbol == "ADAUSDT":
                            formatted_quantity = int(raw_quantity)
                        else:
                            formatted_quantity = round(raw_quantity, 6)

                    # Check minimum notional value
                    notional_value = formatted_price * formatted_quantity
                    if min_notional_filter:
                        min_notional = float(min_notional_filter["minNotional"])
                        if notional_value < min_notional:
                            self.logger.warning(
                                f"Order value ${notional_value:.2f} below minimum ${min_notional:.2f}"
                            )
                            # Increase quantity to meet minimum
                            formatted_quantity = (
                                min_notional / formatted_price * 1.01
                            )  # Add 1% buffer
                            if lot_size_filter:
                                step_size = float(lot_size_filter["stepSize"])
                                formatted_quantity = (
                                    round(formatted_quantity / step_size) * step_size
                                )

                    self.logger.info(
                        f"Buy order: {formatted_quantity} at ${formatted_price:.8f} (notional: ${notional_value:.2f})"
                    )

                    order = binance_client.order_limit_buy(
                        symbol=grid_config.symbol,
                        quantity=f"{formatted_quantity:.8f}".rstrip("0").rstrip("."),
                        price=f"{formatted_price:.8f}".rstrip("0").rstrip("."),
                    )

                    if order and order.get("status") in ["NEW", "PARTIALLY_FILLED"]:
                        level["order_id"] = order["orderId"]
                        orders_placed += 1

                        # Log to database
                        self.trade_repo.log_grid_order(
                            client_id=grid_config.client_id,
                            symbol=grid_config.symbol,
                            side="BUY",
                            quantity=formatted_quantity,
                            price=formatted_price,
                            order_id=order["orderId"],
                            grid_level=level["level"],
                        )

                except Exception as e:
                    self.logger.warning(f"Failed to place buy order: {e}")
                    failed_orders += 1

            # Place sell orders (limit orders above current price)
            for level in grid_config.sell_levels:
                try:
                    # Format price according to Binance requirements
                    raw_price = level["price"]
                    raw_quantity = level["quantity"]

                    # Format price with proper precision
                    if price_filter:
                        tick_size = float(price_filter["tickSize"])
                        formatted_price = round(raw_price / tick_size) * tick_size

                        # Ensure price is within min/max bounds
                        min_price = float(price_filter["minPrice"])
                        max_price = float(price_filter["maxPrice"])
                        formatted_price = max(
                            min_price, min(max_price, formatted_price)
                        )
                    else:
                        formatted_price = round(raw_price, 8)

                    # Format quantity according to lot size
                    if lot_size_filter:
                        step_size = float(lot_size_filter["stepSize"])
                        formatted_quantity = round(raw_quantity / step_size) * step_size

                        # Ensure quantity is within min/max bounds
                        min_qty = float(lot_size_filter["minQty"])
                        max_qty = float(lot_size_filter["maxQty"])
                        formatted_quantity = max(
                            min_qty, min(max_qty, formatted_quantity)
                        )
                    else:
                        # Default formatting based on symbol
                        if grid_config.symbol == "ADAUSDT":
                            formatted_quantity = int(raw_quantity)
                        else:
                            formatted_quantity = round(raw_quantity, 6)

                    # Check minimum notional value
                    notional_value = formatted_price * formatted_quantity
                    if min_notional_filter:
                        min_notional = float(min_notional_filter["minNotional"])
                        if notional_value < min_notional:
                            self.logger.warning(
                                f"Sell order value ${notional_value:.2f} below minimum ${min_notional:.2f}"
                            )
                            # Increase quantity to meet minimum
                            formatted_quantity = (
                                min_notional / formatted_price * 1.01
                            )  # Add 1% buffer
                            if lot_size_filter:
                                step_size = float(lot_size_filter["stepSize"])
                                formatted_quantity = (
                                    round(formatted_quantity / step_size) * step_size
                                )

                    self.logger.info(
                        f"Sell order: {formatted_quantity} at ${formatted_price:.8f} (notional: ${notional_value:.2f})"
                    )

                    order = binance_client.order_limit_sell(
                        symbol=grid_config.symbol,
                        quantity=f"{formatted_quantity:.8f}".rstrip("0").rstrip("."),
                        price=f"{formatted_price:.8f}".rstrip("0").rstrip("."),
                    )

                    if order and order.get("status") in ["NEW", "PARTIALLY_FILLED"]:
                        level["order_id"] = order["orderId"]
                        orders_placed += 1

                        # Log to database
                        self.trade_repo.log_grid_order(
                            client_id=grid_config.client_id,
                            symbol=grid_config.symbol,
                            side="SELL",
                            quantity=formatted_quantity,
                            price=formatted_price,
                            order_id=order["orderId"],
                            grid_level=level["level"],
                        )

                except Exception as e:
                    self.logger.warning(f"Failed to place sell order: {e}")
                    failed_orders += 1

            if orders_placed > 0:
                grid_config.active = True
                self.logger.info(
                    f"✅ Grid setup completed: {orders_placed} orders placed, {failed_orders} failed"
                )
                return {
                    "success": True,
                    "orders_placed": orders_placed,
                    "failed_orders": failed_orders,
                }
            else:
                return {"success": False, "error": "No orders could be placed"}

        except Exception as e:
            self.logger.error(f"❌ Grid setup execution error: {e}")
            return {"success": False, "error": str(e)}

    async def update_all_grids(self):
        """Update all active grids - check for filled orders and manage positions"""
        for client_id, client_grids in list(self.active_grids.items()):
            try:
                # Ensure we have a Binance client
                if client_id not in self.binance_clients:
                    # Try to reconnect
                    api_test = await self.test_client_api(client_id)
                    if not api_test["success"]:
                        self.logger.warning(
                            f"Cannot update grids for client {client_id}: API connection failed"
                        )
                        continue

                binance_client = self.binance_clients[client_id]

                for symbol, grid_config in client_grids.items():
                    await self._update_grid(binance_client, grid_config)

            except Exception as e:
                self.logger.error(
                    f"❌ Error updating grids for client {client_id}: {e}"
                )

    async def _update_grid(self, binance_client: Client, grid_config: GridConfig):
        """Update a specific grid - check orders and replace filled ones"""
        try:
            # Get current price
            ticker = binance_client.get_symbol_ticker(symbol=grid_config.symbol)
            current_price = float(ticker["price"])

            # Check if grid needs reset
            if grid_config.should_reset_grid(current_price):
                self.logger.info(f"🔄 Resetting grid for {grid_config.symbol}")
                await self._reset_grid(binance_client, grid_config, current_price)
                return

            # Check for filled orders
            filled_orders = await self._check_filled_orders(binance_client, grid_config)

            # Replace filled orders with new ones
            for filled_order in filled_orders:
                await self._replace_filled_order(
                    binance_client, grid_config, filled_order, current_price
                )

        except Exception as e:
            self.logger.error(f"❌ Error updating grid {grid_config.symbol}: {e}")

    async def _check_filled_orders(
        self, binance_client: Client, grid_config: GridConfig
    ) -> List[Dict]:
        """Check for filled orders in the grid"""
        filled_orders = []

        try:
            # Get all open orders for the symbol
            open_orders = binance_client.get_open_orders(symbol=grid_config.symbol)
            open_order_ids = {order["orderId"] for order in open_orders}

            # Check buy levels
            for level in grid_config.buy_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level["filled"]
                ):
                    # Order was filled
                    level["filled"] = True
                    filled_orders.append(
                        {"side": "BUY", "level": level, "grid_config": grid_config}
                    )

            # Check sell levels
            for level in grid_config.sell_levels:
                if (
                    level["order_id"]
                    and level["order_id"] not in open_order_ids
                    and not level["filled"]
                ):
                    # Order was filled
                    level["filled"] = True
                    filled_orders.append(
                        {"side": "SELL", "level": level, "grid_config": grid_config}
                    )

        except Exception as e:
            self.logger.error(f"❌ Error checking filled orders: {e}")

        return filled_orders

    async def _replace_filled_order(
        self,
        binance_client: Client,
        grid_config: GridConfig,
        filled_order: Dict,
        current_price: float,
    ):
        """Replace a filled order with a new one on the opposite side"""
        try:
            side = filled_order["side"]
            level_data = filled_order["level"]

            # Log the filled trade
            self.trade_repo.log_trade_execution(
                client_id=grid_config.client_id,
                symbol=grid_config.symbol,
                side=side,
                quantity=level_data["quantity"],
                price=level_data["price"],
                order_id=level_data["order_id"],
            )

            # Calculate profit (simplified - sell price minus buy price)
            if side == "SELL":
                # This was a sell, calculate profit
                profit = (level_data["price"] - grid_config.center_price) * level_data[
                    "quantity"
                ]
                self.logger.info(
                    f"💰 Profit captured: ${profit:.2f} on {grid_config.symbol}"
                )

            # Place new order on opposite side
            if side == "BUY":
                # Original buy was filled, place new sell order above current price
                new_price = current_price * (
                    1 + grid_config.grid_spacing * level_data["level"]
                )
                new_side = "SELL"
            else:
                # Original sell was filled, place new buy order below current price
                new_price = current_price * (
                    1 - grid_config.grid_spacing * level_data["level"]
                )
                new_side = "BUY"

            # Place the new order
            quantity = level_data["quantity"]
            if grid_config.symbol == "ADAUSDT":
                quantity = int(quantity)

            if new_side == "BUY":
                order = binance_client.order_limit_buy(
                    symbol=grid_config.symbol,
                    quantity=str(quantity),
                    price=f"{new_price:.8f}",
                )
            else:
                order = binance_client.order_limit_sell(
                    symbol=grid_config.symbol,
                    quantity=str(quantity),
                    price=f"{new_price:.8f}",
                )

            if order and order.get("status") in ["NEW", "PARTIALLY_FILLED"]:
                # Update the level with new order info
                level_data["price"] = new_price
                level_data["order_id"] = order["orderId"]
                level_data["filled"] = False

                self.logger.info(
                    f"🔄 Replaced {side} with {new_side} order at ${new_price:.4f}"
                )

        except Exception as e:
            self.logger.error(f"❌ Error replacing filled order: {e}")

    async def _reset_grid(
        self, binance_client: Client, grid_config: GridConfig, new_price: float
    ):
        """Reset grid with new center price"""
        try:
            # Cancel all existing orders
            await self._cancel_all_grid_orders(binance_client, grid_config)

            # Reset grid configuration
            grid_config.reset_grid(new_price)

            # Place new orders
            await self._execute_grid_setup(binance_client, grid_config)

            self.logger.info(
                f"✅ Grid reset completed for {grid_config.symbol} at ${new_price:.4f}"
            )

        except Exception as e:
            self.logger.error(f"❌ Error resetting grid: {e}")

    async def _cancel_all_grid_orders(
        self, binance_client: Client, grid_config: GridConfig
    ):
        """Cancel all orders for a grid"""
        try:
            open_orders = binance_client.get_open_orders(symbol=grid_config.symbol)

            for order in open_orders:
                try:
                    binance_client.cancel_order(
                        symbol=grid_config.symbol, orderId=order["orderId"]
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to cancel order {order['orderId']}: {e}"
                    )

        except Exception as e:
            self.logger.error(f"❌ Error cancelling grid orders: {e}")

    async def stop_all_client_grids(self, client_id: int) -> Dict:
        """Stop all grids for a specific client"""
        try:
            if client_id not in self.active_grids:
                return {"success": True, "orders_cancelled": 0}

            if client_id not in self.binance_clients:
                return {"success": False, "error": "No API connection"}

            binance_client = self.binance_clients[client_id]
            orders_cancelled = 0

            # Cancel orders for each active grid
            for symbol, grid_config in self.active_grids[client_id].items():
                try:
                    await self._cancel_all_grid_orders(binance_client, grid_config)
                    grid_config.active = False
                    orders_cancelled += len(grid_config.buy_levels) + len(
                        grid_config.sell_levels
                    )
                except Exception as e:
                    self.logger.error(f"Error stopping grid {symbol}: {e}")

            # Clear active grids
            del self.active_grids[client_id]

            # Update client status
            client = self.client_repo.get_client(client_id)
            client.grid_status = GridStatus.INACTIVE
            self.client_repo.update_client(client)

            self.logger.info(f"🛑 All grids stopped for client {client_id}")
            return {"success": True, "orders_cancelled": orders_cancelled}

        except Exception as e:
            self.logger.error(f"❌ Error stopping grids for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_client_grid_status(self, client_id: int) -> Dict:
        """Get grid status for a specific client"""
        if client_id not in self.active_grids:
            return {"active_grids": {}, "total_grids": 0}

        status = {"active_grids": {}, "total_grids": len(self.active_grids[client_id])}

        for symbol, grid_config in self.active_grids[client_id].items():
            status["active_grids"][symbol] = grid_config.get_grid_status()

        return status

    def get_all_active_grids(self) -> Dict:
        """Get all active grids across all clients"""
        all_grids = {}
        for client_id, client_grids in self.active_grids.items():
            all_grids[client_id] = {}
            for symbol, grid_config in client_grids.items():
                all_grids[client_id][symbol] = grid_config.get_grid_status()
        return all_grids

    async def get_client_performance(self, client_id: int) -> Dict:
        """Get performance statistics for a client"""
        try:
            # Get trade statistics from database
            stats = self.trade_repo.get_client_trade_stats(client_id)

            # Get current grid status
            grid_status = self.get_client_grid_status(client_id)

            return {
                "client_id": client_id,
                "total_trades": stats.get("total_trades", 0),
                "total_profit": stats.get("total_profit", 0.0),
                "total_volume": stats.get("total_volume", 0.0),
                "win_rate": stats.get("win_rate", 0.0),
                "active_grids": grid_status.get("active_grids", {}),
                "recent_trades": stats.get("recent_trades", []),
            }

        except Exception as e:
            self.logger.error(
                f"❌ Error getting performance for client {client_id}: {e}"
            )
            return {"error": str(e)}

    async def shutdown_all_grids(self):
        """Gracefully shutdown all grids"""
        self.logger.info("🛑 Shutting down all grids...")

        for client_id in list(self.active_grids.keys()):
            try:
                await self.stop_all_client_grids(client_id)
            except Exception as e:
                self.logger.error(
                    f"Error shutting down grids for client {client_id}: {e}"
                )

        # Clear all clients
        self.binance_clients.clear()
        self.active_grids.clear()

        self.logger.info("✅ All grids shut down")
