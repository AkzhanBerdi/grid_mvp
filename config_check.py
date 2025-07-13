#!/usr/bin/env python3
"""Configuration check script"""

import os
import sys
from pathlib import Path

def check_environment_variables():
    """Check if required environment variables are set"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'BINANCE_API_KEY',
        'BINANCE_SECRET_KEY'
    ]
    
    optional_vars = [
        'ENVIRONMENT',
        'LOG_LEVEL',
        'TELEGRAM_CHAT_ID'
    ]
    
    print("🔍 Checking environment variables...")
    print("=" * 50)
    
    missing_required = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set (length: {len(value)})")
        else:
            print(f"❌ {var}: Not set")
            missing_required.append(var)
    
    print("\nOptional variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: Not set (using default)")
    
    return missing_required

def check_files():
    """Check if required files exist"""
    required_files = [
        'config.py',
        'database/db_setup.py',
        'handlers/complete_handler.py',
        'analytics/conversion_tracker.py'
    ]
    
    print("\n📁 Checking required files...")
    print("=" * 50)
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}: Exists")
        else:
            print(f"❌ {file_path}: Missing")
            missing_files.append(file_path)
    
    return missing_files

def check_directories():
    """Check if required directories exist"""
    required_dirs = [
        'data',
        'data/logs',
        'data/backups'
    ]
    
    print("\n📂 Checking directories...")
    print("=" * 50)
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}: Exists")
        else:
            print(f"⚠️  {dir_path}: Missing (will be created)")
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"✅ {dir_path}: Created")

def create_env_template():
    """Create .env template file"""
    template = """# GridTrader Pro Configuration
# Copy this file to .env and fill in your actual values

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Binance API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here

# Environment Settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database Settings (optional)
DATABASE_URL=sqlite:///data/gridtrader.db
"""
    
    if not Path('.env').exists():
        with open('.env', 'w') as f:
            f.write(template)
        print("✅ Created .env template file")
    else:
        print("⚠️  .env file already exists")

def main():
    """Main check function"""
    print("🔧 GridTrader Pro Configuration Check")
    print("=" * 50)
    
    # Check environment variables
    missing_vars = check_environment_variables()
    
    # Check files
    missing_files = check_files()
    
    # Check directories
    check_directories()
    
    # Create .env template if needed
    print("\n📝 Environment file...")
    print("=" * 50)
    create_env_template()
    
    # Summary
    print("\n📊 Summary")
    print("=" * 50)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("   Please set these in your .env file")
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        print("   Please ensure these files exist")
    
    if not missing_vars and not missing_files:
        print("✅ All checks passed! Ready to run the bot.")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
