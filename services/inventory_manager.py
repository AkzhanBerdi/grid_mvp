# services/inventory_manager.py
import logging
from typing import Dict, Tuple

from binance.client import Client


class AssetInventory:
    """
    🔧 FIXED: Track inventory for a single trading pair - NO @dataclass
    """

    def __init__(
        self,
        symbol: str,
        total_allocation: float,
        usdt_balance: float,
        asset_balance: float,
        reserved_usdt: float = 0.0,
        reserved_asset: float = 0.0,
        grid_spacing: float = 0.025,
        order_size_base: float = 50.0,
        grid_levels: int = 10,
    ):
        self.symbol = symbol
        self.total_allocation = total_allocation
        self.usdt_balance = usdt_balance
        self.asset_balance = asset_balance
        self.reserved_usdt = reserved_usdt
        self.reserved_asset = reserved_asset
        self.grid_spacing = grid_spacing
        self.order_size_base = order_size_base
        self.grid_levels = grid_levels

        # Anti-corruption marker
        self._is_asset_inventory = True

    def validate_integrity(self) -> bool:
        """Validate that this object hasn't been corrupted"""
        return (
            hasattr(self, "_is_asset_inventory")
            and hasattr(self, "usdt_balance")
            and hasattr(self, "asset_balance")
            and not isinstance(self, dict)
        )


class SingleGridInventoryManager:
    """Clean inventory manager with dynamic symbol support"""

    def __init__(self, binance_client: Client, total_capital: float = 2400.0):
        self.binance_client = binance_client
        self.total_capital = total_capital
        self.logger = logging.getLogger(__name__)
        self.inventories: Dict[str, AssetInventory] = {}

        # Initialize default allocations for multi-asset mode
        self._initialize_default_allocations()

    def _initialize_default_allocations(self):
        """Initialize default 3-asset allocation strategy"""
        allocations = {
            "ETHUSDT": {
                "allocation_pct": 0.40,
                "reasoning": "Conservative anchor - ETF inflows, institutional adoption, lowest volatility",
                "grid_spacing": 0.025,
            },
            "SOLUSDT": {
                "allocation_pct": 0.35,
                "reasoning": "Growth driver - High performance blockchain, DeFi growth, memecoin ecosystem",
                "grid_spacing": 0.030,
            },
            "ADAUSDT": {
                "allocation_pct": 0.25,
                "reasoning": "Stability + upside - Academic blockchain, PoS pioneer, consistent development",
                "grid_spacing": 0.028,
            },
        }

        for symbol, config in allocations.items():
            total_allocation = self.total_capital * config["allocation_pct"]
            initial_usdt = total_allocation * 0.5

            self.inventories[symbol] = AssetInventory(
                symbol=symbol,
                total_allocation=total_allocation,
                usdt_balance=initial_usdt,
                asset_balance=0.0,
                reserved_usdt=0.0,
                reserved_asset=0.0,
                grid_spacing=config["grid_spacing"],
                order_size_base=total_allocation / 10,
            )

        self.logger.info(
            f"💼 Single Grid Inventory Manager initialized for ${self.total_capital:,.2f}"
        )
        for symbol, config in allocations.items():
            inv = self.inventories[symbol]
            emoji = self._get_asset_emoji(symbol)
            self.logger.info(
                f"   {emoji} {symbol}: ${inv.total_allocation:,.2f} ({config['allocation_pct']:.0%}) - {config['reasoning']}"
            )

    def _get_asset_emoji(self, symbol: str) -> str:
        """Get emoji for asset"""
        emojis = {
            "ETHUSDT": "🔷",
            "SOLUSDT": "🟣",
            "ADAUSDT": "🔵",
            "BTCUSDT": "🟠",
            "AVAXUSDT": "🏔️",
        }
        return emojis.get(symbol, "🔘")

    async def add_symbol_tracking(self, symbol: str, total_capital: float) -> bool:
        """
        🔧 FIX: Add tracking for individual symbols (FORCE commands)
        This is the key fix for the "No inventory tracking" error
        """
        try:
            if symbol in self.inventories:
                self.logger.info(f"✅ {symbol} already has inventory tracking")
                return True

            # Create inventory for this specific symbol with full capital allocation
            current_price = await self._get_current_price(symbol)
            if current_price <= 0:
                self.logger.error(f"❌ Failed to get price for {symbol}")
                return False

            # For individual symbols, use 100% of provided capital
            initial_usdt = total_capital * 0.5
            asset_value = total_capital * 0.5
            asset_quantity = asset_value / current_price

            # Get default grid spacing or use conservative default
            default_spacing = 0.025  # 2.5% default
            if symbol == "SOLUSDT":
                default_spacing = 0.030
            elif symbol == "ADAUSDT":
                default_spacing = 0.028

            self.inventories[symbol] = AssetInventory(
                symbol=symbol,
                total_allocation=total_capital,
                usdt_balance=initial_usdt,
                asset_balance=asset_quantity,  # Start with asset balance for sells
                reserved_usdt=0.0,
                reserved_asset=0.0,
                grid_spacing=default_spacing,
                order_size_base=total_capital / 10,
            )

            emoji = self._get_asset_emoji(symbol)
            self.logger.info(f"✅ {emoji} {symbol} inventory tracking added:")
            self.logger.info(f"   💰 USDT Balance: ${initial_usdt:.2f}")
            self.logger.info(
                f"   🪙 Asset Balance: {asset_quantity:.4f} @ ${current_price:.2f}"
            )
            self.logger.info(f"   📊 Order Size Base: ${total_capital / 10:.2f}")

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to add {symbol} tracking: {e}")
            return False

    def has_tracking(self, symbol: str) -> bool:
        """Check if symbol has inventory tracking"""
        return symbol in self.inventories

    async def initialize_asset_positions(self):
        """Initialize asset positions for existing tracked symbols"""
        for symbol in list(self.inventories.keys()):
            try:
                inventory = self.inventories[symbol]
                current_price = await self._get_current_price(symbol)

                if current_price <= 0:
                    self.logger.error(f"❌ Failed to get price for {symbol}")
                    continue

                # Only initialize if asset balance is zero (not already set)
                if inventory.asset_balance == 0:
                    asset_purchase_value = inventory.total_allocation * 0.5
                    asset_quantity = asset_purchase_value / current_price
                    inventory.asset_balance = asset_quantity

                emoji = self._get_asset_emoji(symbol)
                self.logger.info(f"✅ {symbol} position initialized:")
                self.logger.info(f"   💰 USDT Reserve: ${inventory.usdt_balance:.2f}")
                self.logger.info(
                    f"   🪙 Asset Holdings: {inventory.asset_balance:.4f} @ ${current_price:.2f}"
                )

            except Exception as e:
                self.logger.error(f"❌ Error initializing {symbol}: {e}")

    def can_place_buy_order(self, symbol: str, order_value: float) -> Tuple[bool, str]:
        """Check if sufficient USDT available for buy order"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            return False, f"No inventory tracking for {symbol}"

        available_usdt = inventory.usdt_balance - inventory.reserved_usdt
        required_usdt = order_value * 1.01  # 1% buffer for fees

        if available_usdt >= required_usdt:
            return True, f"Sufficient USDT: ${available_usdt:.2f} available"
        else:
            return (
                False,
                f"Insufficient USDT: ${available_usdt:.2f} < ${required_usdt:.2f}",
            )

    def can_place_sell_order(self, symbol: str, quantity: float) -> Tuple[bool, str]:
        """Check if sufficient asset available for sell order"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            return False, f"No inventory tracking for {symbol}"

        available_asset = inventory.asset_balance - inventory.reserved_asset

        if available_asset >= quantity:
            return True, f"Sufficient asset: {available_asset:.4f} available"
        else:
            return False, f"Insufficient asset: {available_asset:.4f} < {quantity:.4f}"

    def reserve_for_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> bool:
        """Reserve inventory when placing order"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            self.logger.warning(
                f"⚠️ No inventory tracking for {symbol} - cannot reserve"
            )
            return False

        if side == "BUY":
            order_value = quantity * price * 1.01
            if inventory.usdt_balance - inventory.reserved_usdt >= order_value:
                inventory.reserved_usdt += order_value
                self.logger.debug(
                    f"🔒 Reserved ${order_value:.2f} USDT for {symbol} buy"
                )
                return True
        elif side == "SELL":
            if inventory.asset_balance - inventory.reserved_asset >= quantity:
                inventory.reserved_asset += quantity
                asset_name = symbol.replace("USDT", "")
                self.logger.debug(f"🔒 Reserved {quantity:.4f} {asset_name} for sell")
                return True

        return False

    def release_reservation(
        self, symbol: str, side: str, quantity: float, price: float
    ):
        """Release reserved inventory when order fails or is cancelled"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            return

        if side == "BUY":
            order_value = quantity * price * 1.01
            inventory.reserved_usdt = max(0, inventory.reserved_usdt - order_value)
            self.logger.debug(
                f"🔓 Released ${order_value:.2f} USDT reservation for {symbol}"
            )
        elif side == "SELL":
            inventory.reserved_asset = max(0, inventory.reserved_asset - quantity)
            self.logger.debug(
                f"🔓 Released {quantity:.4f} asset reservation for {symbol}"
            )

    def update_after_fill(self, symbol: str, side: str, quantity: float, price: float):
        """
        🔧 ENHANCED: Update inventory balances with corruption debugging
        """
        try:
            # 🔍 DEBUG: Check self integrity at start
            if symbol == "SOLUSDT":
                self.logger.error(f"🔍 update_after_fill START - symbol: {symbol}")
                self.logger.error(f"   self type: {type(self)}")
                self.logger.error(f"   self id: {id(self)}")
                self.logger.error(f"   inventories type: {type(self.inventories)}")

            inventory = self.inventories.get(symbol)
            if not inventory:
                self.logger.warning(
                    f"⚠️ No inventory tracking for {symbol} - cannot update after fill"
                )
                return

            # 🔍 DEBUG: Check inventory object type
            if symbol == "SOLUSDT":
                self.logger.error("🔍 SOL inventory object:")
                self.logger.error(f"   inventory type: {type(inventory)}")
                self.logger.error(f"   inventory id: {id(inventory)}")

            order_value = quantity * price

            if side == "BUY":
                # 🔍 DEBUG: Before BUY operations
                if symbol == "SOLUSDT":
                    self.logger.error("🔍 SOL BUY - Before operations:")
                    self.logger.error(f"   usdt_balance: {inventory.usdt_balance}")
                    self.logger.error(f"   asset_balance: {inventory.asset_balance}")

                # Bought asset with USDT
                inventory.usdt_balance -= order_value
                inventory.asset_balance += quantity
                inventory.reserved_usdt = max(
                    0, inventory.reserved_usdt - order_value * 1.01
                )

                # 🔍 DEBUG: After BUY operations
                if symbol == "SOLUSDT":
                    self.logger.error("🔍 SOL BUY - After operations:")
                    self.logger.error(f"   usdt_balance: {inventory.usdt_balance}")
                    self.logger.error(f"   asset_balance: {inventory.asset_balance}")
                    self.logger.error(f"   self type after BUY: {type(self)}")

                self.logger.info(
                    f"💰 {symbol} BUY FILL: -${order_value:.2f} USDT, +{quantity:.4f} asset"
                )

            elif side == "SELL":
                # 🔍 DEBUG: Before SELL operations
                if symbol == "SOLUSDT":
                    self.logger.error("🔍 SOL SELL - Before operations:")
                    self.logger.error(f"   usdt_balance: {inventory.usdt_balance}")
                    self.logger.error(f"   asset_balance: {inventory.asset_balance}")

                # Sold asset for USDT
                inventory.usdt_balance += order_value
                inventory.asset_balance -= quantity
                inventory.reserved_asset = max(0, inventory.reserved_asset - quantity)

                # 🔍 DEBUG: After SELL operations
                if symbol == "SOLUSDT":
                    self.logger.error("🔍 SOL SELL - After operations:")
                    self.logger.error(f"   usdt_balance: {inventory.usdt_balance}")
                    self.logger.error(f"   asset_balance: {inventory.asset_balance}")
                    self.logger.error(f"   self type after SELL: {type(self)}")

                self.logger.info(
                    f"💰 {symbol} SELL FILL: +${order_value:.2f} USDT, -{quantity:.4f} asset"
                )

            # 🔍 DEBUG: Final check
            if symbol == "SOLUSDT":
                self.logger.error("🔍 update_after_fill END:")
                self.logger.error(f"   self type: {type(self)}")
                self.logger.error(f"   self id: {id(self)}")

            # Log updated balances for debugging
            self.logger.debug(
                f"📊 {symbol} Updated: USDT=${inventory.usdt_balance:.2f}, Asset={inventory.asset_balance:.4f}"
            )

        except Exception as e:
            self.logger.error(f"❌ Error in update_after_fill for {symbol}: {e}")

            # 🔍 DEBUG: Check state during error
            if symbol == "SOLUSDT":
                self.logger.error("🔍 update_after_fill ERROR:")
                self.logger.error(f"   self type: {type(self)}")
                import traceback

                self.logger.error(f"   Stack trace: {traceback.format_exc()}")

    def get_optimal_order_size(
        self, symbol: str, side: str, current_price: float
    ) -> float:
        """Get optimal order size based on available inventory"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            self.logger.warning(
                f"⚠️ No inventory tracking for {symbol} - using fallback order size"
            )
            return 50.0  # Fallback to $50 orders

        base_order_value = inventory.order_size_base

        if side == "BUY":
            available_usdt = inventory.usdt_balance - inventory.reserved_usdt
            max_affordable = available_usdt * 0.9  # Keep 10% buffer
            optimal_size = min(base_order_value, max_affordable)

            # Ensure minimum viable order
            return max(optimal_size, 10.0)  # Minimum $10 order

        elif side == "SELL":
            available_asset = inventory.asset_balance - inventory.reserved_asset
            max_asset_value = available_asset * current_price * 0.9  # Keep 10% buffer
            optimal_size = min(base_order_value, max_asset_value)

            # Ensure minimum viable order
            return max(optimal_size, 10.0)  # Minimum $10 order

        return base_order_value

    def get_optimal_quantity(
        self, symbol: str, side: str, current_price: float
    ) -> float:
        """
        🔧 NEW: Get optimal quantity (not value) for orders
        This fixes the quantity calculation error
        """
        optimal_value = self.get_optimal_order_size(symbol, side, current_price)

        if current_price <= 0:
            self.logger.error(f"❌ Invalid price for {symbol}: {current_price}")
            return 0.0

        optimal_quantity = optimal_value / current_price

        # Validate quantity
        if optimal_quantity <= 0:
            self.logger.error(
                f"❌ Invalid quantity calculated for {symbol}: {optimal_quantity}"
            )
            return 0.0

        return optimal_quantity

    def get_inventory_status(self, symbol: str) -> Dict:
        """Get detailed inventory status"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            return {"error": f"No inventory for {symbol}"}

        usdt_available = inventory.usdt_balance - inventory.reserved_usdt
        asset_available = inventory.asset_balance - inventory.reserved_asset

        return {
            "symbol": symbol,
            "total_allocation": f"${inventory.total_allocation:.2f}",
            "usdt_balance": f"${inventory.usdt_balance:.2f}",
            "usdt_available": f"${usdt_available:.2f}",
            "usdt_reserved": f"${inventory.reserved_usdt:.2f}",
            "asset_balance": f"{inventory.asset_balance:.4f}",
            "asset_available": f"{asset_available:.4f}",
            "asset_reserved": f"{inventory.reserved_asset:.4f}",
            "grid_spacing": f"{inventory.grid_spacing * 100:.1f}%",
            "order_size_base": f"${inventory.order_size_base:.2f}",
            "can_buy": usdt_available >= 10.0,
            "can_sell": asset_available > 0,
        }

    async def _get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"❌ Error getting price for {symbol}: {e}")
            return 0.0

    def get_all_tracked_symbols(self) -> list:
        """Get list of all tracked symbols"""
        return list(self.inventories.keys())

    def validate_inventory_health(self) -> Dict:
        """Validate inventory health across all symbols"""
        health_report = {
            "overall_health": "healthy",
            "total_symbols": len(self.inventories),
            "issues": [],
            "symbols": {},
        }

        for symbol, inventory in self.inventories.items():
            symbol_health = {
                "usdt_balance": inventory.usdt_balance,
                "asset_balance": inventory.asset_balance,
                "has_buy_capacity": (inventory.usdt_balance - inventory.reserved_usdt)
                >= 10.0,
                "has_sell_capacity": (
                    inventory.asset_balance - inventory.reserved_asset
                )
                > 0,
                "status": "healthy",
            }

            # Check for issues
            if symbol_health["usdt_balance"] < 10:
                symbol_health["status"] = "low_usdt"
                health_report["issues"].append(f"{symbol}: Low USDT balance")

            if symbol_health["asset_balance"] <= 0:
                symbol_health["status"] = "no_assets"
                health_report["issues"].append(f"{symbol}: No asset balance")

            health_report["symbols"][symbol] = symbol_health

        if health_report["issues"]:
            health_report["overall_health"] = "warning"

        return health_report
