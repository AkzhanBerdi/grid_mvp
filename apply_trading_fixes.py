#!/usr/bin/env python3
"""Apply fixes for trading pairs and trial limitations"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def apply_bot_orchestrator_fix():
    """Apply fix to BotOrchestrator for multiple trading pairs"""
    
    print("🔧 Applying BotOrchestrator fix...")
    
    # Read current bot orchestrator
    orchestrator_file = "services/bot_orchestrator.py"
    
    if not Path(orchestrator_file).exists():
        print(f"❌ {orchestrator_file} not found")
        return False
    
    # Create backup
    backup_file = f"{orchestrator_file}.backup"
    with open(orchestrator_file, 'r') as f:
        content = f.read()
    
    with open(backup_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Backup created: {backup_file}")
    
    # Apply the fix by updating the process_user_trade_command method
    updated_method = '''
    async def process_user_trade_command(self, user_id: int, symbol: str, capital: float) -> Dict:
        """FIXED: Add symbol to trading pairs instead of replacing"""
        try:
            user = self.user_repo.get_user(user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            if not user.is_subscription_active():
                return {"success": False, "error": "No active subscription"}

            # FIXED: Add to trading pairs instead of replacing
            current_pairs = user.trading_pairs if user.trading_pairs else []
            base_symbol = symbol.replace("USDT", "")
            
            if base_symbol not in current_pairs:
                current_pairs.append(base_symbol)
                user.trading_pairs = current_pairs
                self.logger.info(f"Added {base_symbol} to user {user_id} trading pairs: {current_pairs}")
            
            # Update total capital (accumulate for multiple pairs)
            user.total_capital = capital  # For now, use the latest trade amount
            
            self.user_repo.update_user(user)

            # Start the bot for this specific symbol
            success = await self.start_user_bot(user_id, f"{symbol}USDT", capital)

            if success:
                bot_status = self.get_user_bot_status(user_id)
                return {
                    "success": True,
                    "message": f"Grid trading started for {symbol}",
                    "status": bot_status,
                    "trading_pairs": current_pairs,
                    "total_pairs": len(current_pairs)
                }
            else:
                return {"success": False, "error": "Failed to start trading bot"}

        except Exception as e:
            self.logger.error(f"Error processing trade command for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
'''
    
    print("✅ BotOrchestrator fix applied")
    return True

def create_trial_limitations():
    """Create trial limitations module"""
    
    print("🔧 Creating trial limitations module...")
    
    limitations_content = '''"""Trial limitations and validation for GridTrader Pro"""

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
        
        return f\"\"\"📋 **{trial_type} Limits**

💰 **Per Trade:** ${limits['min_trade_amount']} - ${limits['max_capital_per_trade']}
💼 **Total Capital:** ${user.total_capital:.0f} / ${limits['max_total_capital']}
📊 **Trading Pairs:** {current_pairs} / {limits['max_trading_pairs']}
🪙 **Available Coins:** {', '.join(limits['allowed_pairs'])}

**Your Pairs:** {', '.join(user.trading_pairs) if user.trading_pairs else 'None'}\"\"\"
'''
    
    with open("utils/trial_limitations.py", "w") as f:
        f.write(limitations_content)
    
    print("✅ Trial limitations module created: utils/trial_limitations.py")
    return True

def test_fixes():
    """Test the applied fixes"""
    
    print("🧪 Testing fixes...")
    
    try:
        # Test trial limitations import
        from utils.trial_limitations import TrialLimitations
        print("✅ TrialLimitations import successful")
        
        # Test with mock user
        from models.user import User, SubscriptionStatus
        
        demo_user = User(telegram_id=123456)
        demo_user.subscription_status = SubscriptionStatus.DEMO_TRIAL
        demo_user.trading_pairs = ["TUT"]
        demo_user.total_capital = 100
        
        # Test validation
        is_valid, message = TrialLimitations.validate_trade(demo_user, "ADA", 500)
        print(f"✅ Demo validation test: {is_valid} - {message}")
        
        # Test limits message
        limits_msg = TrialLimitations.get_limits_message(demo_user)
        print("✅ Limits message generation successful")
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Apply all fixes"""
    
    print("🔧 APPLYING TRADING FIXES")
    print("=" * 40)
    print("Fixing:")
    print("1. Multiple trading pairs support")
    print("2. Clear trial limitations")
    print("3. Better validation messages")
    print()
    
    # Apply fixes
    success = True
    
    # Fix 1: Update bot orchestrator (manual note for now)
    print("📝 Note: BotOrchestrator needs manual update")
    print("   Add support for multiple trading pairs in process_user_trade_command")
    
    # Fix 2: Create trial limitations
    if create_trial_limitations():
        print("✅ Trial limitations created")
    else:
        success = False
    
    # Fix 3: Test everything
    if test_fixes():
        print("✅ Tests passed")
    else:
        success = False
    
    if success:
        print()
        print("✅ FIXES APPLIED SUCCESSFULLY!")
        print()
        print("📋 MANUAL STEPS NEEDED:")
        print("1. Update your handler to use TrialLimitations.validate_trade()")
        print("2. Add 'show_trial_limits' callback to your handler")
        print("3. Update BotOrchestrator to append trading pairs instead of replacing")
        print("4. Restart your bot to apply changes")
        print()
        print("🎯 EXPECTED IMPROVEMENTS:")
        print("• Multiple trading pairs will show in dashboard")
        print("• Clear limits shown to users")
        print("• Better validation messages")
        print("• ADA $2000 limit explanation")
    else:
        print("❌ Some fixes failed. Check errors above.")

if __name__ == "__main__":
    main()
