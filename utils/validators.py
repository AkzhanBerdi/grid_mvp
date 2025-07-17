# utils/validators.py
"""Input validation utilities"""

from typing import Optional, Tuple
import re


class Validators:
    """Validation utilities for client inputs"""

    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
        """Validate Binance API key format"""
        if not api_key:
            return False, "API key cannot be empty"

        if len(api_key) < 20:
            return False, "API key too short (minimum 20 characters)"

        if len(api_key) > 100:
            return False, "API key too long (maximum 100 characters)"

        # Basic alphanumeric check
        if not re.match(r"^[A-Za-z0-9]+$", api_key):
            return False, "API key contains invalid characters"

        return True, None

    @staticmethod
    def validate_capital_amount(
        amount_str: str,
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """Validate trading capital amount"""
        try:
            # Clean the input
            clean_amount = amount_str.replace("$", "").replace(",", "").strip()
            amount = float(clean_amount)

            if amount < 100:
                return False, None, "Minimum capital: $100"

            if amount > 1000000:
                return False, None, "Maximum capital: $1,000,000"

            return True, amount, None

        except ValueError:
            return False, None, "Invalid amount format"

    @staticmethod
    def validate_trading_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
        """Validate trading symbol"""
        symbol = symbol.upper().strip()

        valid_symbols = ["ADA", "AVAX", "BTC", "ETH"]

        if symbol not in valid_symbols:
            return False, f"Symbol not supported. Available: {', '.join(valid_symbols)}"

        return True, None
