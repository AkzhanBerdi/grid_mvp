"""Trial limitations and validation for GridTrader Pro"""

from enum import Enum
from models.user import SubscriptionStatus

class TrialLimitations:
    """Define and validate trial limitations"""
    
    DEMO_TRIAL_LIMITS = {
        "max_capital_per_trade": 1000.0,  # $1000 per trade
        "max_total_capital": 5000.0,      # $5000 total across all pairs
        "max_trading_pairs": 3,           # 3 different pairs
        "allowed_pairs": ["BTC", "ETH", "ADA", "TUT", "AVAX"],  # Allowed symbols
        "min_trade_amount": 50.0,         # Minimum $50
    }
    
    REAL_TRIAL_LIMITS = {
        "max_capital_per_trade": 2000.0,  # $2000 per trade  
        "max_total_capital": 10000.0,     # $10000 total
        "max_trading_pairs": 5,           # 5 different pairs
        "allowed_pairs": ["BTC", "ETH", "ADA", "TUT", "AVAX", "DOGE", "SOL"],
        "min_trade_amount": 100.0,        # Minimum $100 for real trading
    }
    
    @classmethod
    def validate_trade(cls, user, symbol: str, amount: float) -> tuple:
        """Validate if trade is allowed for user's trial type"""
        
        # Get limits based on subscription status
        if user.subscription_status == SubscriptionStatus.DEMO_TRIAL:
            limits = cls.DEMO_TRIAL_LIMITS
            trial_type = "Demo Trial"
        elif user.subscription_status == SubscriptionStatus.REAL_TRIAL:
            limits = cls.REAL_TRIAL_LIMITS
            trial_type = "Real Trial"
        else:
            # Paid users have no limits
            return True, "No limits for paid subscription"
        
        # Check minimum amount
        if amount < limits["min_trade_amount"]:
            return False, f"{trial_type}: Minimum trade amount is ${limits['min_trade_amount']}"
        
        # Check maximum per trade
        if amount > limits["max_capital_per_trade"]:
            return False, f"{trial_type}: Maximum per trade is ${limits['max_capital_per_trade']}"
        
        # Check allowed symbols
        base_symbol = symbol.replace("USDT", "")
        if base_symbol not in limits["allowed_pairs"]:
            return False, f"{trial_type}: {base_symbol} not available. Available: {', '.join(limits['allowed_pairs'])}"
        
        # Check maximum trading pairs
        current_pairs = user.trading_pairs if user.trading_pairs else []
        if base_symbol not in current_pairs and len(current_pairs) >= limits["max_trading_pairs"]:
            return False, f"{trial_type}: Maximum {limits['max_trading_pairs']} trading pairs allowed"
        
        # Check total capital across all pairs
        total_capital = user.total_capital + (amount if base_symbol not in current_pairs else 0)
        if total_capital > limits["max_total_capital"]:
            return False, f"{trial_type}: Maximum total capital is ${limits['max_total_capital']}"
        
        return True, f"Trade approved for {trial_type}"

    @classmethod
    def get_limits_message(cls, user) -> str:
        """Get user-friendly limits message"""
        
        if user.subscription_status == SubscriptionStatus.DEMO_TRIAL:
            limits = cls.DEMO_TRIAL_LIMITS
            trial_type = "🎮 Demo Trial"
        elif user.subscription_status == SubscriptionStatus.REAL_TRIAL:
            limits = cls.REAL_TRIAL_LIMITS  
            trial_type = "🟢 Real Trial"
        else:
            return "💎 No trading limits for paid subscription!"
        
        current_pairs = len(user.trading_pairs) if user.trading_pairs else 0
        
        return f"""📋 **{trial_type} Limits**

💰 **Per Trade:** ${limits['min_trade_amount']} - ${limits['max_capital_per_trade']}
💼 **Total Capital:** ${user.total_capital:.0f} / ${limits['max_total_capital']}
📊 **Trading Pairs:** {current_pairs} / {limits['max_trading_pairs']}
🪙 **Available Coins:** {', '.join(limits['allowed_pairs'])}

**Your Pairs:** {', '.join(user.trading_pairs) if user.trading_pairs else 'None'}"""
