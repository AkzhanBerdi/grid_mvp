#!/usr/bin/env python3
"""Cleanup script to remove empty files and redundant handlers"""

import os
import shutil
from pathlib import Path

def remove_empty_files():
    """Remove empty Python files"""
    empty_files = [
        'analytics/dashboard.py',
        'analytics/performance_monitor.py',
        'models/trade.py',
        'repositories/analytics_repository.py',
        'repositories/trade_repository.py',
        'services/subscription_service.py'
    ]
    
    for file_path in empty_files:
        if os.path.exists(file_path):
            print(f"Removing empty file: {file_path}")
            os.remove(file_path)

def remove_redundant_handlers():
    """Remove redundant handler files"""
    redundant_handlers = [
        'handlers/onboarding_handler.py',
        'handlers/setup_handler.py',
        'handlers/smooth_onboarding_handler.py',
        'handlers/smooth_trading_handler.py',
        'handlers/trading_handler_fixed.py',
        'handlers/trading_handler.py'
    ]
    
    for handler_path in redundant_handlers:
        if os.path.exists(handler_path):
            print(f"Removing redundant handler: {handler_path}")
            os.remove(handler_path)

def remove_redundant_telegram_bots():
    """Remove redundant telegram bot files"""
    redundant_bots = [
        'telegram_bot_fixed.py',
        'telegram_bot.py'
    ]
    
    for bot_path in redundant_bots:
        if os.path.exists(bot_path):
            print(f"Removing redundant bot file: {bot_path}")
            os.remove(bot_path)

def clean_pycache():
    """Remove all __pycache__ directories"""
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_path = os.path.join(root, dir_name)
                print(f"Removing __pycache__: {pycache_path}")
                shutil.rmtree(pycache_path)

def main():
    print("🧹 Starting cleanup process...")
    
    # Remove empty files
    remove_empty_files()
    
    # Remove redundant handlers
    remove_redundant_handlers()
    
    # Remove redundant telegram bots
    remove_redundant_telegram_bots()
    
    # Clean __pycache__
    clean_pycache()
    
    print("✅ Cleanup complete!")
    print("\nRemaining structure:")
    print("- Keep: handlers/complete_handler.py (main handler)")
    print("- Keep: main.py (main bot entry point)")
    print("- Keep: config.py (configuration)")
    print("- Keep: services/simple_trading_engine.py")
    print("- Keep: analytics/conversion_tracker.py")

if __name__ == "__main__":
    main()
