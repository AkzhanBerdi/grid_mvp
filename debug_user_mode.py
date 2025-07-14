#!/usr/bin/env python3
"""Debug script to check user trading mode detection"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from repositories.user_repository import UserRepository
from services.user_trading_bot import TradingMode

def debug_user_mode(user_id: int):
    """Debug why user is in demo mode when they should be in real mode"""
    
    user_repo = UserRepository()
    user = user_repo.get_user(user_id)
    
    if not user:
        print(f"❌ User {user_id} not found")
        return
    
    print(f"🔍 DEBUGGING USER {user_id} TRADING MODE")
    print("=" * 50)
    
    # Check API keys
    print(f"API Key: {user.binance_api_key[:20] if user.binance_api_key else 'None'}...")
    print(f"Secret Key: {user.binance_secret_key[:20] if user.binance_secret_key else 'None'}...")
    print(f"API Key Length: {len(user.binance_api_key) if user.binance_api_key else 0}")
    print(f"Secret Key Length: {len(user.binance_secret_key) if user.binance_secret_key else 0}")
    
    # Check for demo keywords
    if user.binance_api_key:
        api_key_lower = user.binance_api_key.lower()
        demo_keywords = ['demo', 'test', 'fake']
        found_keywords = [kw for kw in demo_keywords if kw in api_key_lower]
        print(f"Demo keywords found: {found_keywords}")
    
    # Determine mode using same logic as bot
    def determine_mode():
        if not user.binance_api_key or not user.binance_secret_key:
            return TradingMode.DEMO, "No API keys"
        
        api_key_lower = user.binance_api_key.lower()
        if any(keyword in api_key_lower for keyword in ['demo', 'test', 'fake']):
            return TradingMode.DEMO, "Demo keywords in API key"
        
        if len(user.binance_api_key) < 60:
            return TradingMode.DEMO, f"API key too short ({len(user.binance_api_key)} chars)"
        
        return TradingMode.REAL, "Real API keys detected"
    
    detected_mode, reason = determine_mode()
    
    print(f"\n📊 MODE DETECTION RESULT:")
    print(f"Detected Mode: {detected_mode.upper()}")
    print(f"Reason: {reason}")
    
    # Additional checks
    print(f"\n🔍 ADDITIONAL CHECKS:")
    print(f"User subscription active: {user.is_subscription_active()}")
    print(f"Can start bot: {user.can_start_bot()}")
    
    # Show what the user interface would display
    if user.binance_api_key:
        if "demo" in user.binance_api_key.lower():
            ui_mode = "🎮 Demo Mode"
        else:
            ui_mode = "🟢 Real Trading Mode"
    else:
        ui_mode = "❌ Not Setup"
    
    print(f"UI would show: {ui_mode}")
    
    print("\n💡 RECOMMENDATIONS:")
    if detected_mode == TradingMode.DEMO and "demo" not in user.binance_api_key.lower():
        print("• User appears to have real API keys but they're being detected as demo")
        print("• Check API key length and format")
        print("• Verify API keys are actual Binance keys")
    elif detected_mode == TradingMode.DEMO and "demo" in user.binance_api_key.lower():
        print("• User is correctly in demo mode")
        print("• To switch to real mode, they need to enter real API keys")
    else:
        print("• User should be in real trading mode")
        print("• Check if Binance API connection is working")

def fix_user_mode(user_id: int, force_real: bool = False):
    """Fix user's trading mode"""
    user_repo = UserRepository()
    user = user_repo.get_user(user_id)
    
    if not user:
        print(f"❌ User {user_id} not found")
        return
    
    if force_real:
        print("🔧 FORCING REAL MODE...")
        # You would need to prompt for real API keys here
        print("Please provide real Binance API keys:")
        api_key = input("API Key: ").strip()
        secret_key = input("Secret Key: ").strip()
        
        user.binance_api_key = api_key
        user.binance_secret_key = secret_key
        user_repo.update_user(user)
        
        print("✅ Updated user with real API keys")
        print("🔄 User should now be in real trading mode")
    else:
        print("Use --force-real flag to update API keys")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_user_mode.py <user_id> [--force-real]")
        print("Example: python debug_user_mode.py 485825055")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    force_real = "--force-real" in sys.argv
    
    debug_user_mode(user_id)
    
    if force_real:
        fix_user_mode(user_id, force_real=True)
