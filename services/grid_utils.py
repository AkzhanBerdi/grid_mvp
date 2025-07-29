# services/grid_utils.py
"""
FIXED Grid Utility Service - Extracted from GridManager
==============================================================

Fixed the string formatting bug that was causing format_quantity_string(1000, 0)
to return "1" instead of "1000"

The issue was in the rstrip("0") logic which was too aggressive.
"""

import logging
from typing import Dict, Optional

from binance.client import Client


class GridUtilityService:
    """
    Pure utility functions for grid trading operations
    Extracted from GridManager for better organization
    """

    def __init__(self, binance_client: Optional[Client] = None):
        self.binance_client = binance_client
        self.logger = logging.getLogger(__name__)

        # Cache for exchange info to avoid repeated API calls
        self._exchange_info_cache: Dict[str, Dict] = {}

    # ========================================
    # PRICE AND QUANTITY VALIDATION METHODS
    # ========================================

    def round_to_tick_size(self, price: float, tick_size: float) -> float:
        """
        Round price to the nearest valid tick size

        Args:
            price: Raw price value
            tick_size: Minimum price increment from exchange

        Returns:
            Price rounded to valid tick size
        """
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

    def make_valid_price(self, price: float, tick_size: float, precision: int) -> float:
        """
        Make any price valid for Binance API

        Args:
            price: Raw price value
            tick_size: Minimum price increment
            precision: Decimal places for formatting

        Returns:
            Valid price formatted for Binance
        """
        try:
            # Round to tick size
            rounded = round(price / tick_size) * tick_size

            # Format with correct precision
            formatted = round(rounded, precision)

            return formatted

        except Exception:
            return round(price, precision)

    def make_valid_quantity(
        self, quantity: float, step_size: float, precision: int, min_qty: float
    ) -> float:
        """
        Make any quantity valid for Binance API

        Args:
            quantity: Raw quantity value
            step_size: Minimum quantity increment
            precision: Decimal places for formatting
            min_qty: Minimum allowed quantity

        Returns:
            Valid quantity formatted for Binance
        """
        try:
            # Round to step size
            rounded = round(quantity / step_size) * step_size

            # Ensure minimum quantity
            if rounded < min_qty:
                rounded = min_qty

            # Format with correct precision
            formatted = round(rounded, precision)

            return formatted

        except Exception:
            return max(round(quantity, precision), min_qty)

    def get_precision_from_step(self, step_size: float) -> int:
        """
        Calculate decimal precision from step size

        Args:
            step_size: Step size from exchange info

        Returns:
            Number of decimal places needed
        """
        try:
            if step_size >= 1:
                return 0

            # Convert to string and count decimal places
            step_str = f"{step_size:.10f}".rstrip("0")
            if "." in step_str:
                return len(step_str.split(".")[1])
            return 0

        except Exception:
            return 8  # Safe fallback

    # ========================================
    # EXCHANGE RULES AND API METHODS
    # ========================================

    async def get_exchange_rules_simple(self, symbol: str) -> Dict:
        """
        Get simplified exchange rules for a symbol

        Args:
            symbol: Trading pair (e.g., 'ETHUSDT')

        Returns:
            Dict with tick_size, step_size, min_qty, etc.
        """
        if not self.binance_client:
            return self._get_fallback_rules(symbol)

        # Check cache first
        if symbol in self._exchange_info_cache:
            return self._exchange_info_cache[symbol]

        try:
            # Get exchange info from Binance
            exchange_info = self.binance_client.get_exchange_info()

            for symbol_info in exchange_info["symbols"]:
                if symbol_info["symbol"] == symbol:
                    rules = self._parse_symbol_rules(symbol_info)

                    # Cache the result
                    self._exchange_info_cache[symbol] = rules

                    self.logger.info(f"✅ Exchange rules for {symbol}:")
                    self.logger.info(
                        f"   💲 Price: tick_size={rules['tick_size']}, precision={rules['price_precision']}"
                    )
                    self.logger.info(
                        f"   📦 Quantity: step_size={rules['step_size']}, precision={rules['quantity_precision']}"
                    )
                    self.logger.info(f"   💰 Min notional: ${rules['min_notional']}")

                    return rules

            raise ValueError(f"Symbol {symbol} not found")

        except Exception as e:
            self.logger.error(f"❌ Failed to get exchange rules for {symbol}: {e}")
            return self._get_fallback_rules(symbol)

    def _parse_symbol_rules(self, symbol_info: Dict) -> Dict:
        """Parse symbol rules from Binance exchange info"""
        rules = {
            "symbol": symbol_info["symbol"],
            "status": symbol_info["status"],
            "tick_size": 0.00000001,
            "step_size": 0.00000001,
            "min_qty": 0.00000001,
            "min_notional": 10.0,
            "price_precision": 8,
            "quantity_precision": 8,
        }

        # Parse filters
        for filter_info in symbol_info.get("filters", []):
            filter_type = filter_info["filterType"]

            if filter_type == "PRICE_FILTER":
                rules["tick_size"] = float(filter_info["tickSize"])
                rules["price_precision"] = self.get_precision_from_step(
                    rules["tick_size"]
                )

            elif filter_type == "LOT_SIZE":
                rules["step_size"] = float(filter_info["stepSize"])
                rules["min_qty"] = float(filter_info["minQty"])
                rules["quantity_precision"] = self.get_precision_from_step(
                    rules["step_size"]
                )

            elif filter_type == "MIN_NOTIONAL":
                rules["min_notional"] = float(filter_info["minNotional"])

        return rules

    def _get_fallback_rules(self, symbol: str) -> Dict:
        """Get fallback rules when API fails"""
        # Asset-specific fallbacks for better accuracy
        if symbol == "ADAUSDT":
            return {
                "symbol": symbol,
                "tick_size": 0.0001,
                "step_size": 0.1,
                "min_qty": 0.1,
                "min_notional": 5.0,
                "price_precision": 4,
                "quantity_precision": 1,
                "status": "TRADING",
            }
        elif symbol == "ETHUSDT":
            return {
                "symbol": symbol,
                "tick_size": 0.01,
                "step_size": 0.00001,
                "min_qty": 0.00001,
                "min_notional": 5.0,
                "price_precision": 2,
                "quantity_precision": 5,
                "status": "TRADING",
            }
        elif symbol == "SOLUSDT":
            return {
                "symbol": symbol,
                "tick_size": 0.001,
                "step_size": 0.01,
                "min_qty": 0.01,
                "min_notional": 5.0,
                "price_precision": 3,
                "quantity_precision": 2,
                "status": "TRADING",
            }
        else:
            # Generic fallback
            return {
                "symbol": symbol,
                "tick_size": 0.00000001,
                "step_size": 0.00000001,
                "min_qty": 0.00000001,
                "min_notional": 10.0,
                "price_precision": 8,
                "quantity_precision": 8,
                "status": "TRADING",
            }

    # ========================================
    # SYMBOL-SPECIFIC PRECISION METHODS
    # ========================================

    async def get_symbol_precision_info(self, symbol: str) -> Dict:
        """
        Get comprehensive precision info with asset-specific overrides

        Args:
            symbol: Trading pair

        Returns:
            Complete precision and formatting info
        """
        # Force overrides for known problematic symbols
        if symbol == "ADAUSDT":
            info = {
                "price_precision": 4,
                "quantity_precision": 1,
                "tick_size": 0.0001,
                "step_size": 0.1,
                "min_notional": 5.0,
                "status": "TRADING",
            }
            self.logger.info(f"🔒 FORCED ADA precision: {info}")
            return info

        elif symbol == "ETHUSDT":
            info = {
                "price_precision": 2,
                "quantity_precision": 5,
                "tick_size": 0.01,
                "step_size": 0.00001,
                "min_notional": 5.0,
                "status": "TRADING",
            }
            self.logger.info(f"🔒 FORCED ETH precision: {info}")
            return info

        elif symbol == "SOLUSDT":
            info = {
                "price_precision": 3,
                "quantity_precision": 2,
                "tick_size": 0.001,
                "step_size": 0.01,
                "min_notional": 5.0,
                "status": "TRADING",
            }
            self.logger.info(f"🔒 FORCED SOL precision: {info}")
            return info

        # For other symbols, get from exchange API
        return await self.get_exchange_rules_simple(symbol)

    # ========================================
    # FORMATTING UTILITIES - FIXED VERSION
    # ========================================

    def format_price_string(self, price: float, precision: int) -> str:
        """
        FIXED: Format price as string with correct precision

        The key fix: Only strip trailing zeros AFTER the decimal point,
        never strip all zeros which would break whole numbers.
        """
        try:
            if precision < 0:
                # Handle negative precision gracefully
                formatted = f"{price:.0f}"
            else:
                formatted = f"{price:.{precision}f}"

            # Only strip trailing zeros if there's a decimal point
            if "." in formatted:
                # Strip trailing zeros after decimal point
                formatted = formatted.rstrip("0")
                # If we stripped all decimal digits, remove the decimal point too
                if formatted.endswith("."):
                    formatted = formatted[:-1]

            # Ensure minimum decimal places for display (for prices)
            if "." not in formatted and precision > 0:
                formatted += ".00"

            return formatted

        except Exception as e:
            self.logger.error(f"Price formatting error: {e}")
            return f"{price:.{max(0, precision)}f}"

    def format_quantity_string(self, quantity: float, precision: int) -> str:
        """
        FIXED: Format quantity as string with correct precision

        The key fix: Only strip trailing zeros AFTER the decimal point,
        never strip all zeros which would break whole numbers like 1000.
        """
        try:
            if precision < 0:
                # Handle negative precision gracefully
                formatted = f"{quantity:.0f}"
            else:
                formatted = f"{quantity:.{precision}f}"

            # Only strip trailing zeros if there's a decimal point
            if "." in formatted:
                # Strip trailing zeros after decimal point
                formatted = formatted.rstrip("0")
                # If we stripped all decimal digits, remove the decimal point too
                if formatted.endswith("."):
                    formatted = formatted[:-1]

            # Ensure minimum formatting for quantities
            if "." not in formatted and precision > 0:
                formatted += ".0"

            return formatted

        except Exception as e:
            self.logger.error(f"Quantity formatting error: {e}")
            return f"{quantity:.{max(0, precision)}f}"

    # ========================================
    # VALIDATION UTILITIES
    # ========================================

    def validate_order_params(
        self, symbol: str, quantity: float, price: float, rules: Dict
    ) -> Dict:
        """
        Validate and fix order parameters

        Returns:
            Dict with valid_quantity, valid_price, and validation status
        """
        try:
            # Validate price
            valid_price = self.make_valid_price(
                price, rules["tick_size"], rules["price_precision"]
            )

            # Validate quantity
            valid_quantity = self.make_valid_quantity(
                quantity,
                rules["step_size"],
                rules["quantity_precision"],
                rules["min_qty"],
            )

            # Check notional value
            notional_value = valid_quantity * valid_price

            if notional_value < rules["min_notional"]:
                # Adjust quantity to meet minimum notional
                required_quantity = rules["min_notional"] / valid_price
                valid_quantity = self.make_valid_quantity(
                    required_quantity,
                    rules["step_size"],
                    rules["quantity_precision"],
                    rules["min_qty"],
                )
                notional_value = valid_quantity * valid_price

            return {
                "valid": True,
                "valid_price": valid_price,
                "valid_quantity": valid_quantity,
                "notional_value": notional_value,
                "price_string": self.format_price_string(
                    valid_price, rules["price_precision"]
                ),
                "quantity_string": self.format_quantity_string(
                    valid_quantity, rules["quantity_precision"]
                ),
            }

        except Exception as e:
            self.logger.error(f"Order validation error: {e}")
            return {
                "valid": False,
                "error": str(e),
                "valid_price": price,
                "valid_quantity": quantity,
            }

    # ========================================
    # CACHE MANAGEMENT
    # ========================================

    def clear_exchange_cache(self):
        """Clear the exchange info cache"""
        self._exchange_info_cache.clear()
        self.logger.info("🧹 Exchange info cache cleared")

    def get_cached_symbols(self) -> list:
        """Get list of symbols in cache"""
        return list(self._exchange_info_cache.keys())


# ========================================
# CONVENIENCE FUNCTIONS
# ========================================


def create_grid_utility(binance_client: Optional[Client] = None) -> GridUtilityService:
    """
    Convenience function to create GridUtilityService

    Args:
        binance_client: Optional Binance client for API calls

    Returns:
        Configured GridUtilityService instance
    """
    return GridUtilityService(binance_client)


# ========================================
# STANDALONE UTILITY FUNCTIONS
# ========================================


def quick_round_price(price: float, tick_size: float = 0.01) -> float:
    """Quick price rounding without class instantiation"""
    if tick_size <= 0:
        return round(price, 6)
    return round(price / tick_size) * tick_size


def quick_round_quantity(
    quantity: float, step_size: float = 0.1, min_qty: float = 0.1
) -> float:
    """Quick quantity rounding without class instantiation"""
    if step_size <= 0:
        return max(quantity, min_qty)
    rounded = round(quantity / step_size) * step_size
    return max(rounded, min_qty)
