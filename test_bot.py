#!/usr/bin/env python3
"""Test script to verify bot components work"""

import sys
import logging
from pathlib import Path

# Test imports
def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from config import Config
        print("✅ Config imported successfully")
    except ImportError as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    try:
        from database.db_setup import DatabaseSetup
        print("✅ DatabaseSetup imported successfully")
    except ImportError as e:
        print(f"❌ DatabaseSetup import failed: {e}")
        return False
    
    try:
        from analytics.conversion_tracker import ConversionTracker
        print("✅ ConversionTracker imported successfully")
    except ImportError as e:
        print(f"❌ ConversionTracker import failed: {e}")
        return False
    
    try:
        from handlers.complete_handler import CompleteHandler
        print("✅ CompleteHandler imported successfully")
    except ImportError as e:
        print(f"❌ CompleteHandler import failed: {e}")
        return False
    
    try:
        from binance.client import Client
        print("✅ Binance client imported successfully")
    except ImportError as e:
        print(f"❌ Binance client import failed: {e}")
        print("   Install with: pip install python-binance")
        return False
    
    try:
        from telegram.ext import Application
        print("✅ Telegram bot imported successfully")
    except ImportError as e:
        print(f"❌ Telegram bot import failed: {e}")
        print("   Install with: pip install python-telegram-bot")
        return False
    
    return True

def test_config():
    """Test configuration loading"""
    print("\n🔧 Testing configuration...")
    
    try:
        from config import Config
        config = Config()
        
        # Check if validate method exists
        if hasattr(config, 'validate'):
            is_valid = config.validate()
            print(f"✅ Config validation result: {is_valid}")
        else:
            print("⚠️  Config.validate() method not found")
        
        # Check for required attributes
        required_attrs = ['TELEGRAM_BOT_TOKEN', 'LOG_LEVEL', 'LOG_FILE']
        for attr in required_attrs:
            if hasattr(config, attr):
                value = getattr(config, attr)
                if value:
                    print(f"✅ {attr}: Set")
                else:
                    print(f"⚠️  {attr}: Empty")
            else:
                print(f"❌ {attr}: Missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("\n🗄️  Testing database...")
    
    try:
        from database.db_setup import DatabaseSetup
        
        # Create data directory if it doesn't exist
        Path("data").mkdir(exist_ok=True)
        
        db_setup = DatabaseSetup()
        db_setup.initialize()
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_bot_creation():
    """Test bot creation without starting it"""
    print("\n🤖 Testing bot creation...")
    
    try:
        # Import the fixed main script
        sys.path.insert(0, '.')
        
        # Test individual components
        from config import Config
        config = Config()
        print("✅ Config created")
        
        from database.db_setup import DatabaseSetup
        db_setup = DatabaseSetup()
        print("✅ DatabaseSetup created")
        
        from analytics.conversion_tracker import ConversionTracker
        conversion_tracker = ConversionTracker()
        print("✅ ConversionTracker created")
        
        from handlers.complete_handler import CompleteHandler
        handler = CompleteHandler(conversion_tracker)
        print("✅ CompleteHandler created")
        
        print("✅ All components created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Bot creation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 GridTrader Bot Component Tests")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
    
    # Test config
    if not test_config():
        all_passed = False
    
    # Test database
    if not test_database():
        all_passed = False
    
    # Test bot creation
    if not test_bot_creation():
        all_passed = False
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    if all_passed:
        print("✅ All tests passed! The bot should be ready to run.")
        print("\nTo start the bot:")
        print("  python main.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above before running the bot.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
