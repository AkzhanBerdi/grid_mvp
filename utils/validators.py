import re
from typing import Tuple, Optional

class Validators:
    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
        if not api_key or len(api_key) < 20:
            return False, "Invalid API key"
        return True, None
    
    @staticmethod
    def validate_capital_amount(amount_str: str) -> Tuple[bool, Optional[float], Optional[str]]:
        try:
            amount = float(amount_str.replace('$', '').replace(',', ''))
            if amount < 100:
                return False, None, "Minimum $100"
            return True, amount, None
        except:
            return False, None, "Invalid amount"
