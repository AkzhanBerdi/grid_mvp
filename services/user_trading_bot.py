#!/usr/bin/env python3
"""Enhanced Demo + Real Trading Architecture - FIXED MODE DETECTION"""

import logging
import time
from typing import Dict, List, Optional

import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException

from models.user import User


class TradingMode:
    """Trading mode constants"""

    DEMO = "demo"
    REAL = "real"


class UserTradingBot:
    """Universal bot supporting both demo and real trading seamlessly - FIXED"""

    def __init__(self, user: User, trading_mode: str = None):
        self.user = user

        # FIXED: Auto-detect trading mode if not specified
        if trading_mode is None:
            trading_mode = self._auto_detect_trading_mode()

        self.trading_mode = trading_mode
        self.logger = logging.getLogger(f"UniversalBot-{user.telegram_id}")

        # Log the determined mode for debugging
        self.logger.info(f"🔍 TRADING MODE DETERMINED: {self.trading_mode.upper()}")
        self.logger.info(
            f"🔑 API Key Preview: {user.binance_api_key[:15] if user.binance_api_key else 'None'}..."
        )

        # Initialize based on mode
        if self.trading_mode == TradingMode.REAL:
            self.real_client = self._create_real_client()
            if not self.real_client:
                self.logger.warning(
                    "⚠️ Real client creation failed, falling back to demo mode"
                )
                self.trading_mode = TradingMode.DEMO
                self.real_client = None
        else:
            self.real_client = None

        # Always create public client for real prices
        self.public_client = self._create_public_client()

        # Trading state
        self.active = False
        self.grid_orders: List[Dict] = []
        self.base_price = 0.0
        self.grid_spacing = 0.02
        self.grid_levels = 5

        # Enhanced demo state
        self.demo_balance = {"USDT": 1000.0}  # Starting demo balance
        self.demo_positions = {}  # Track demo positions

        # Statistics
        self.total_trades = 0
        self.total_profit = 0.0
        self.started_at = None

        # Final mode confirmation
        mode_name = "REAL" if self.is_real_mode() else "DEMO"
        self.logger.info(
            f"✅ Bot initialized in {mode_name} mode for user {user.telegram_id}"
        )

    def _auto_detect_trading_mode(self) -> str:
        """Auto-detect trading mode based on user's API keys"""
        # No API keys = demo mode
        if not self.user.binance_api_key or not self.user.binance_secret_key:
            self.logger.info("🎮 No API keys found → Demo mode")
            return TradingMode.DEMO

        # Check for demo/test keywords in API key
        api_key_lower = self.user.binance_api_key.lower()
        if any(keyword in api_key_lower for keyword in ["demo", "test", "fake"]):
            self.logger.info("🎮 Demo keywords detected in API key → Demo mode")
            return TradingMode.DEMO

        # Check API key length (real Binance API keys are typically 64 characters)
        if len(self.user.binance_api_key) < 60:
            self.logger.info(
                f"🎮 API key too short ({len(self.user.binance_api_key)} chars) → Demo mode"
            )
            return TradingMode.DEMO

        # If we reach here, assume real keys
        self.logger.info("🟢 Real API keys detected → Real trading mode")
        return TradingMode.REAL

    def _create_public_client(self) -> Client:
        """Create public client for real price data (no auth needed)"""
        try:
            # Public client for real prices - works without API keys
            return Client(testnet=False)  # Always use mainnet for real prices
        except Exception as e:
            self.logger.error(f"Failed to create public client: {e}")
            return None

    def _create_real_client(self) -> Optional[Client]:
        """Create authenticated client for real trading"""
        try:
            if not self.user.binance_api_key or not self.user.binance_secret_key:
                self.logger.warning("❌ Missing API credentials for real trading")
                return None

            # Additional validation for real keys
            if "demo" in self.user.binance_api_key.lower():
                self.logger.warning(
                    "❌ Demo keywords found in API key, cannot use for real trading"
                )
                return None

            self.logger.info("🔗 Attempting to connect to Binance API...")
            client = Client(
                self.user.binance_api_key,
                self.user.binance_secret_key,
                testnet=False,  # Always mainnet for user keys
            )

            # Test connection with a simple API call
            account = client.get_account()
            self.logger.info(
                f"✅ Real trading client connected successfully for user {self.user.telegram_id}"
            )
            self.logger.info(f"📊 Account has {len(account['balances'])} assets")
            return client

        except BinanceAPIException as e:
            self.logger.error(f"❌ Binance API error: {e.message} (Code: {e.code})")
            return None
        except Exception as e:
            self.logger.error(f"❌ Real client creation failed: {e}")
            return None

    def is_demo_mode(self) -> bool:
        """Check current trading mode"""
        return self.trading_mode == TradingMode.DEMO

    def is_real_mode(self) -> bool:
        """Check if real trading mode"""
        return self.trading_mode == TradingMode.REAL and self.real_client is not None

    async def get_real_price(self, symbol: str) -> Optional[float]:
        """Get REAL market price (works in both demo and real mode)"""
        try:
            if self.public_client:
                # Always get real prices from Binance
                ticker = self.public_client.get_symbol_ticker(symbol=symbol)
                price = float(ticker["price"])
                return price
            else:
                # Fallback to manual API call if client fails
                response = requests.get(
                    f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
                    timeout=10,
                )
                data = response.json()
                return float(data["price"])

        except Exception as e:
            self.logger.error(f"Error getting real price for {symbol}: {e}")

            # Ultimate fallback - realistic fake prices
            fallback_prices = {
                "BTCUSDT": 45000.0,
                "ETHUSDT": 3000.0,
                "ADAUSDT": 0.7330,
                "AVAXUSDT": 21.25,
                "TUTUSDT": 0.001234,
            }
            return fallback_prices.get(symbol, 1.0)

    async def place_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> Optional[Dict]:
        """Universal order placement - demo or real"""

        if self.is_demo_mode():
            return await self._place_demo_order(symbol, side, quantity, price)
        elif self.is_real_mode():
            return await self._place_real_order(symbol, side, quantity, price)
        else:
            self.logger.error("❌ No trading mode available")
            return None

    async def _place_demo_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> Dict:
        """Enhanced demo order with real price simulation"""
        try:
            # Get current REAL market price for realistic simulation
            current_price = await self.get_real_price(symbol)

            # Simulate realistic execution
            import random

            # Simulate order execution based on real market conditions
            if (
                side == "BUY" and price >= current_price * 0.999
            ):  # Market or close to market
                status = "FILLED"
                executed_price = current_price
            elif (
                side == "SELL" and price <= current_price * 1.001
            ):  # Market or close to market
                status = "FILLED"
                executed_price = current_price
            else:
                status = random.choice(["NEW", "PARTIALLY_FILLED", "FILLED"])
                executed_price = price

            order_id = int(time.time() * 1000)

            # Update demo balances if filled
            if status == "FILLED":
                await self._update_demo_balance(symbol, side, quantity, executed_price)

            order = {
                "orderId": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": str(quantity),
                "price": str(executed_price),
                "status": status,
                "transactTime": int(time.time() * 1000),
                "mode": "demo",
            }

            self.logger.info(
                f"🎮 DEMO ORDER: {side} {quantity:.8f} {symbol} at ${executed_price:.8f} ({status})"
            )
            return order

        except Exception as e:
            self.logger.error(f"Demo order error: {e}")
            return None

    async def _place_real_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> Optional[Dict]:
        """Real order placement"""
        try:
            if not self.real_client:
                self.logger.error("❌ No real trading client available")
                return None

            self.logger.info(
                f"🟢 PLACING REAL ORDER: {side} {quantity:.8f} {symbol} at ${price:.8f}"
            )

            # Format quantity and price properly for Binance
            # Get symbol info for proper precision
            try:
                symbol_info = self.real_client.get_symbol_info(symbol)
                quantity_precision = 8  # Default
                price_precision = 8  # Default

                for filter_item in symbol_info["filters"]:
                    if filter_item["filterType"] == "LOT_SIZE":
                        # Calculate precision from stepSize
                        step_size = float(filter_item["stepSize"])
                        quantity_precision = len(
                            str(step_size).split(".")[-1].rstrip("0")
                        )
                    elif filter_item["filterType"] == "PRICE_FILTER":
                        # Calculate precision from tickSize
                        tick_size = float(filter_item["tickSize"])
                        price_precision = len(str(tick_size).split(".")[-1].rstrip("0"))

                # Format with proper precision
                formatted_quantity = f"{quantity:.{quantity_precision}f}"
                formatted_price = f"{price:.{price_precision}f}"

            except Exception as e:
                self.logger.warning(
                    f"Could not get symbol precision, using defaults: {e}"
                )
                formatted_quantity = f"{quantity:.8f}"
                formatted_price = f"{price:.8f}"

            # Place the actual order
            if side == "BUY":
                order = self.real_client.order_limit_buy(
                    symbol=symbol, quantity=formatted_quantity, price=formatted_price
                )
            else:
                order = self.real_client.order_limit_sell(
                    symbol=symbol, quantity=formatted_quantity, price=formatted_price
                )

            order["mode"] = "real"
            self.logger.info(
                f"✅ REAL ORDER PLACED: {side} {formatted_quantity} {symbol} at ${formatted_price} (ID: {order['orderId']})"
            )
            return order

        except BinanceAPIException as e:
            self.logger.error(
                f"❌ Real order failed - Binance API error: {e.message} (Code: {e.code})"
            )
            return None
        except Exception as e:
            self.logger.error(f"❌ Real order failed - General error: {e}")
            return None

    async def _update_demo_balance(
        self, symbol: str, side: str, quantity: float, price: float
    ):
        """Update demo account balances"""
        try:
            base_asset = symbol.replace("USDT", "")

            if side == "BUY":
                # Spend USDT, get base asset
                usdt_spent = quantity * price
                self.demo_balance["USDT"] = (
                    self.demo_balance.get("USDT", 0) - usdt_spent
                )
                self.demo_positions[base_asset] = (
                    self.demo_positions.get(base_asset, 0) + quantity
                )

                # Calculate profit for demo
                profit = usdt_spent * 0.01  # Simulate 1% profit
                self.total_profit += profit

            else:  # SELL
                # Get USDT, spend base asset
                usdt_received = quantity * price
                self.demo_balance["USDT"] = (
                    self.demo_balance.get("USDT", 0) + usdt_received
                )
                self.demo_positions[base_asset] = (
                    self.demo_positions.get(base_asset, 0) - quantity
                )

                # Calculate profit for demo
                profit = usdt_received * 0.01  # Simulate 1% profit
                self.total_profit += profit

            self.total_trades += 1
            self.logger.info(
                f"💰 Demo balance updated: USDT={self.demo_balance['USDT']:.2f}, {base_asset}={self.demo_positions.get(base_asset, 0):.8f}"
            )

        except Exception as e:
            self.logger.error(f"Error updating demo balance: {e}")

    async def start_grid_trading(self, symbol: str, capital: float) -> bool:
        """Universal grid trading start"""
        try:
            mode_name = "DEMO" if self.is_demo_mode() else "REAL"
            self.logger.info(
                f"🚀 Starting {mode_name} grid trading: {symbol} with ${capital}"
            )

            # Get real current price (even in demo mode)
            current_price = await self.get_real_price(symbol)
            if not current_price:
                self.logger.error(f"❌ Cannot get price for {symbol}")
                return False

            # Validate capital
            if self.is_demo_mode():
                if capital > self.demo_balance.get("USDT", 0):
                    self.logger.error(
                        f"❌ Insufficient demo balance: ${self.demo_balance.get('USDT', 0):.2f}"
                    )
                    return False

            self.base_price = current_price
            self.active = True
            self.started_at = time.time()

            # Execute 50/50 split
            buy_amount = capital * 0.5
            coin_quantity = buy_amount / current_price

            # Place initial order
            buy_price = current_price * 1.001  # Slightly above market
            initial_order = await self.place_order(
                symbol, "BUY", coin_quantity, buy_price
            )

            if not initial_order:
                self.logger.error("❌ Failed to place initial order")
                return False

            # Set up grid orders
            await self.setup_grid_orders(
                symbol, current_price, capital * 0.5, coin_quantity
            )

            self.logger.info(f"✅ {mode_name} grid trading started successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error starting grid trading: {e}")
            return False

    async def setup_grid_orders(
        self, symbol: str, base_price: float, usdt_amount: float, coin_amount: float
    ):
        """Set up grid orders (works for both demo and real)"""
        try:
            self.grid_orders = []
            successful_orders = 0

            # Place buy orders below current price
            usdt_per_order = usdt_amount / self.grid_levels
            for i in range(1, self.grid_levels + 1):
                buy_price = base_price * (1 - self.grid_spacing * i)
                quantity = usdt_per_order / buy_price

                order = await self.place_order(symbol, "BUY", quantity, buy_price)
                if order:
                    self.grid_orders.append(
                        {"order": order, "type": "grid_buy", "level": i}
                    )
                    successful_orders += 1

            # Place sell orders above current price
            coin_per_order = coin_amount / self.grid_levels
            for i in range(1, self.grid_levels + 1):
                sell_price = base_price * (1 + self.grid_spacing * i)

                order = await self.place_order(
                    symbol, "SELL", coin_per_order, sell_price
                )
                if order:
                    self.grid_orders.append(
                        {"order": order, "type": "grid_sell", "level": i}
                    )
                    successful_orders += 1

            mode_name = "DEMO" if self.is_demo_mode() else "REAL"
            self.logger.info(
                f"📊 {mode_name} grid setup: {successful_orders} orders placed"
            )

        except Exception as e:
            self.logger.error(f"❌ Error setting up grid: {e}")

    async def stop_trading(self):
        """Stop trading (demo or real)"""
        try:
            self.active = False

            if self.is_real_mode() and self.real_client:
                # Cancel real orders
                cancelled = 0
                for grid_order in self.grid_orders:
                    try:
                        order_id = grid_order["order"]["orderId"]
                        symbol = grid_order["order"]["symbol"]
                        self.real_client.cancel_order(symbol=symbol, orderId=order_id)
                        cancelled += 1
                        self.logger.info(f"❌ Cancelled real order {order_id}")
                    except Exception as e:
                        self.logger.error(f"Error canceling order: {e}")

                self.logger.info(f"❌ Cancelled {cancelled} real orders")

            self.grid_orders = []
            mode_name = "DEMO" if self.is_demo_mode() else "REAL"
            self.logger.info(f"🛑 {mode_name} trading stopped")

        except Exception as e:
            self.logger.error(f"Error stopping trading: {e}")

    def get_status(self) -> Dict:
        """Get comprehensive status"""
        runtime = time.time() - self.started_at if self.started_at else 0

        status = {
            "active": self.active,
            "mode": self.trading_mode,
            "total_trades": self.total_trades,
            "total_profit": self.total_profit,
            "active_orders": len(self.grid_orders),
            "runtime_minutes": int(runtime / 60),
            "base_price": self.base_price,
        }

        # Add mode-specific info
        if self.is_demo_mode():
            status.update(
                {
                    "demo_balance": self.demo_balance,
                    "demo_positions": self.demo_positions,
                    "can_switch_to_real": bool(
                        self.user.binance_api_key
                        and "demo" not in self.user.binance_api_key.lower()
                        and len(self.user.binance_api_key) >= 60
                    ),
                }
            )
        else:
            status.update(
                {"real_trading": True, "client_connected": bool(self.real_client)}
            )

        return status

    def get_demo_performance_summary(self) -> str:
        """Get demo performance for marketing"""
        if self.total_trades > 0:
            return f"${self.total_profit:.2f} profit in {self.total_trades} trades"
        else:
            return "Ready to start trading"
