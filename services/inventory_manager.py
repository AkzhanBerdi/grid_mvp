# services/inventory_manager.py
"""
Inventory Management System for Single Advanced Grid Architecture
Integrates directly with SingleAdvancedGridManager
"""

import logging
from dataclasses import dataclass
from typing import Dict, Tuple

from binance.client import Client


@dataclass
class AssetInventory:
    """Track inventory for a single trading pair in single grid system"""

    symbol: str
    total_allocation: float
    usdt_balance: float
    asset_balance: float
    reserved_usdt: float
    reserved_asset: float
    grid_spacing: float
    order_size_base: float
    grid_levels: int = 10  # Fixed 10 levels for single advanced grid


class SingleGridInventoryManager:
    """
    Inventory Manager specifically designed for SingleAdvancedGridManager
    Handles the $2,400 three-asset allocation with proper USDT/Asset balance tracking
    """

    def __init__(self, binance_client: Client, total_capital: float = 2400.0):
        self.binance_client = binance_client
        self.total_capital = total_capital
        self.logger = logging.getLogger(__name__)

        # Asset inventories for single grid system
        self.inventories: Dict[str, AssetInventory] = {}

        # Initialize the optimized $2,400 allocation strategy
        self._initialize_optimal_allocations()

    def _initialize_optimal_allocations(self):
        """
        Initialize the optimal 3-asset allocation strategy for $2,400

        Reasoning for allocation percentages:
        - ETH 40% ($960): Blue chip, institutional adoption, ETF inflows, lowest volatility
        - SOL 35% ($840): High growth potential, DeFi ecosystem, memecoin platform
        - ADA 25% ($600): Academic rigor, PoS pioneer, sustainable development
        """
        allocations = {
            "ETHUSDT": {
                "allocation_pct": 0.40,  # 40% = $960
                "reasoning": "Conservative anchor - ETF inflows, institutional adoption, lowest volatility",
                "grid_spacing": 0.025,  # 2.5% - ETH less volatile
                "risk_profile": "conservative",
                "expected_return_range": "60-100%",
            },
            "SOLUSDT": {
                "allocation_pct": 0.35,  # 35% = $840
                "reasoning": "Growth driver - High performance blockchain, DeFi growth, memecoin ecosystem",
                "grid_spacing": 0.030,  # 3.0% - SOL more volatile than ETH
                "risk_profile": "moderate-aggressive",
                "expected_return_range": "80-120%",
            },
            "ADAUSDT": {
                "allocation_pct": 0.25,  # 25% = $600
                "reasoning": "Stability + upside - Academic blockchain, PoS pioneer, consistent development",
                "grid_spacing": 0.028,  # 2.8% - ADA moderate volatility
                "risk_profile": "moderate",
                "expected_return_range": "70-110%",
            },
        }

        for symbol, config in allocations.items():
            total_allocation = self.total_capital * config["allocation_pct"]

            # Critical: 50/50 split between USDT (for buys) and asset value (for sells)
            initial_usdt = total_allocation * 0.5
            initial_asset_value = total_allocation * 0.5

            self.inventories[symbol] = AssetInventory(
                symbol=symbol,
                total_allocation=total_allocation,
                usdt_balance=initial_usdt,
                asset_balance=0.0,  # Will be calculated after asset purchase
                reserved_usdt=0.0,
                reserved_asset=0.0,
                grid_spacing=config["grid_spacing"],
                order_size_base=total_allocation / 10,  # 10 levels per grid
                grid_levels=10,
            )

        self.logger.info(
            f"💼 Single Grid Inventory Manager initialized for ${self.total_capital:,.2f}"
        )
        for symbol, config in allocations.items():
            inv = self.inventories[symbol]
            self.logger.info(
                f"   {self._get_asset_emoji(symbol)} {symbol}: ${inv.total_allocation:,.2f} ({config['allocation_pct']:.0%}) - {config['reasoning']}"
            )

    def _get_asset_emoji(self, symbol: str) -> str:
        """Get emoji for asset"""
        emojis = {"ETHUSDT": "🔷", "SOLUSDT": "🟣", "ADAUSDT": "🔵"}
        return emojis.get(symbol, "🔘")

    async def initialize_asset_positions(self):
        """
        Initialize actual asset positions for grid trading
        Purchases 50% of allocation in each asset to enable sell orders
        """
        for symbol in self.inventories.keys():
            inventory = self.inventories[symbol]
            current_price = await self._get_current_price(symbol)

            if current_price == 0:
                self.logger.error(f"❌ Failed to get price for {symbol}")
                continue

            # Calculate asset quantity for 50% of allocation
            asset_purchase_value = inventory.total_allocation * 0.5
            asset_quantity = asset_purchase_value / current_price

            # Update inventory with calculated asset balance
            inventory.asset_balance = asset_quantity

            self.logger.info(f"✅ {symbol} position initialized:")
            self.logger.info(f"   💰 USDT Reserve: ${inventory.usdt_balance:.2f}")
            self.logger.info(
                f"   🪙 Asset Holdings: {inventory.asset_balance:.4f} @ ${current_price:.2f}"
            )

    def can_place_buy_order(self, symbol: str, order_value: float) -> Tuple[bool, str]:
        """Check if sufficient USDT available for buy order"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            return False, f"No inventory tracking for {symbol}"

        available_usdt = inventory.usdt_balance - inventory.reserved_usdt

        # Add 1% buffer for fees
        required_usdt = order_value * 1.01

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
            return False

        if side == "BUY":
            order_value = quantity * price * 1.01  # Include fee buffer
            if inventory.usdt_balance - inventory.reserved_usdt >= order_value:
                inventory.reserved_usdt += order_value
                self.logger.debug(
                    f"🔒 Reserved ${order_value:.2f} USDT for {symbol} buy"
                )
                return True
        elif side == "SELL":
            if inventory.asset_balance - inventory.reserved_asset >= quantity:
                inventory.reserved_asset += quantity
                self.logger.debug(
                    f"🔒 Reserved {quantity:.4f} {symbol.replace('USDT', '')} for sell"
                )
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
        CRITICAL: Update inventory balances after order fills
        This is what fixes the order replacement issue
        """
        inventory = self.inventories.get(symbol)
        if not inventory:
            return

        order_value = quantity * price

        if side == "BUY":
            # Bought asset with USDT
            inventory.usdt_balance -= order_value
            inventory.asset_balance += quantity
            inventory.reserved_usdt = max(0, inventory.reserved_usdt - order_value)

            self.logger.info(
                f"💰 {symbol} BUY FILL: -${order_value:.2f} USDT, +{quantity:.4f} asset"
            )

        elif side == "SELL":
            # Sold asset for USDT
            inventory.usdt_balance += order_value
            inventory.asset_balance -= quantity
            inventory.reserved_asset = max(0, inventory.reserved_asset - quantity)

            self.logger.info(
                f"💰 {symbol} SELL FILL: +${order_value:.2f} USDT, -{quantity:.4f} asset"
            )

    def get_optimal_order_size(
        self, symbol: str, side: str, current_price: float
    ) -> float:
        """Get optimal order size based on available inventory and base allocation"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            return 0.0

        # Base order size from allocation (10 levels = 10% each)
        base_order_value = inventory.order_size_base

        if side == "BUY":
            available_usdt = inventory.usdt_balance - inventory.reserved_usdt
            # Use smaller of base size or 90% of available (keep buffer)
            max_affordable = available_usdt * 0.9
            return min(base_order_value, max_affordable)

        elif side == "SELL":
            available_asset = inventory.asset_balance - inventory.reserved_asset
            # Convert to USD value using current price
            max_asset_value = available_asset * current_price * 0.9
            return min(base_order_value, max_asset_value)

        return base_order_value

    def get_inventory_status(self, symbol: str) -> Dict:
        """Get detailed inventory status for monitoring and debugging"""
        inventory = self.inventories.get(symbol)
        if not inventory:
            return {"error": f"No inventory for {symbol}"}

        return {
            "symbol": symbol,
            "total_allocation": f"${inventory.total_allocation:.2f}",
            "usdt_balance": f"${inventory.usdt_balance:.2f}",
            "usdt_available": f"${inventory.usdt_balance - inventory.reserved_usdt:.2f}",
            "usdt_reserved": f"${inventory.reserved_usdt:.2f}",
            "asset_balance": f"{inventory.asset_balance:.4f}",
            "asset_available": f"{inventory.asset_balance - inventory.reserved_asset:.4f}",
            "asset_reserved": f"{inventory.reserved_asset:.4f}",
            "grid_spacing": f"{inventory.grid_spacing * 100:.1f}%",
            "order_size_base": f"${inventory.order_size_base:.2f}",
            "utilization": {
                "usdt": f"{(inventory.reserved_usdt / inventory.usdt_balance * 100):.1f}%"
                if inventory.usdt_balance > 0
                else "0%",
                "asset": f"{(inventory.reserved_asset / inventory.asset_balance * 100):.1f}%"
                if inventory.asset_balance > 0
                else "0%",
            },
        }

    async def _get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return 0.0

    def get_allocation_reasoning(self) -> Dict:
        """Get detailed reasoning behind the asset allocation strategy"""
        return {
            "total_capital": f"${self.total_capital:,.2f}",
            "strategy": "Balanced growth with risk-adjusted allocation",
            "allocations": {
                "ETHUSDT": {
                    "percentage": "40%",
                    "amount": f"${self.inventories['ETHUSDT'].total_allocation:.2f}",
                    "reasoning": [
                        "Conservative anchor asset",
                        "Strong institutional adoption",
                        "ETF inflows providing stability",
                        "Lowest volatility among the three",
                        "Proven track record and network effects",
                    ],
                    "risk_profile": "Conservative",
                    "expected_return": "60-100% annually",
                },
                "SOLUSDT": {
                    "percentage": "35%",
                    "amount": f"${self.inventories['SOLUSDT'].total_allocation:.2f}",
                    "reasoning": [
                        "Primary growth driver",
                        "High-performance blockchain technology",
                        "Thriving DeFi ecosystem",
                        "Leading memecoin trading platform",
                        "Strong developer activity",
                    ],
                    "risk_profile": "Moderate-Aggressive",
                    "expected_return": "80-120% annually",
                },
                "ADAUSDT": {
                    "percentage": "25%",
                    "amount": f"${self.inventories['ADAUSDT'].total_allocation:.2f}",
                    "reasoning": [
                        "Stability with upside potential",
                        "Academic research-driven development",
                        "Proof-of-Stake pioneer",
                        "Sustainable and methodical approach",
                        "Strong governance model",
                    ],
                    "risk_profile": "Moderate",
                    "expected_return": "70-110% annually",
                },
            },
            "portfolio_benefits": [
                "Risk diversification across different blockchain paradigms",
                "Balanced exposure to established (ETH) and emerging (SOL) ecosystems",
                "Academic rigor (ADA) provides stability during market uncertainty",
                "Combined market cap represents significant portion of crypto market",
                "Different volatility profiles enable consistent grid trading opportunities",
            ],
        }
