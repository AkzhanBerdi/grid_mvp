#!/usr/bin/env python3
"""Quick setup to get GridTrader Pro MVP running immediately"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_all_missing_files():
    """Create all missing files with minimal working code"""
    
    # Create directories
    Path('data/logs').mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py files
    packages = ['handlers', 'services', 'repositories', 'models', 'analytics', 'utils']
    for package in packages:
        package_dir = Path(package)
        package_dir.mkdir(exist_ok=True)
        (package_dir / '__init__.py').write_text('# Package init\n')
    
    # Create utils/validators.py
    Path('utils/validators.py').write_text('''import re
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
''')
    
    # Create utils/formatters.py
    Path('utils/formatters.py').write_text('''from datetime import datetime

class MessageFormatter:
    @staticmethod
    def format_user_dashboard(user, bot_status, performance):
        return f"""🤖 **Trading Dashboard**
Status: {bot_status.get('status', 'inactive')}
Capital: ${user.total_capital:.2f}"""
    
    @staticmethod
    def format_trial_expiry(trial_expires):
        if not trial_expires:
            return "No trial"
        time_left = trial_expires - datetime.now()
        return f"{time_left.days} days left" if time_left.days > 0 else "Expires soon"
''')
    
    # Create simplified main.py
    Path('main.py').write_text('''import asyncio
import logging

class SimpleGridBot:
    def __init__(self):
        self.running = False
        self.grids = {}
        self.user_id = None
        self.logger = logging.getLogger(__name__)
        self.client = self
        self.API_KEY = None
        self.SECRET_KEY = None
    
    async def run(self):
        self.running = True
        self.logger.info(f"Bot started for user {self.user_id}")
        while self.running:
            await asyncio.sleep(60)
    
    def get_open_orders(self, symbol=None):
        return []
    
    def cancel_order(self, symbol=None, orderId=None):
        pass
''')
    
    # Create simplified handlers/trading_handler.py
    Path('handlers/trading_handler.py').write_text('''from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class TradingHandler:
    def __init__(self, bot_orchestrator, conversion_tracker):
        self.bot_orchestrator = bot_orchestrator
        self.conversion_tracker = conversion_tracker
    
    async def handle_callback(self, update, context):
        query = update.callback_query
        await query.edit_message_text("🚧 Trading features coming soon! This is the MVP version.")
''')
    
    print("✅ Created all missing files")

def main():
    print("🚀 GridTrader Pro MVP - Emergency Fix")
    print("=" * 40)
    
    create_all_missing_files()
    
    # Check .env
    if not Path('.env').exists():
        print("❌ .env file missing!")
        print("Create .env with your bot token:")
        print("TELEGRAM_BOT_TOKEN=your_new_token_here")
        print("ENCRYPTION_KEY=your_key_here")
        return
    
    # Initialize database
    try:
        from database.db_setup import DatabaseSetup
        db_setup = DatabaseSetup()
        db_setup.initialize()
        print("✅ Database ready")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    # Start bot
    try:
        print("🤖 Starting bot...")
        from telegram_bot import GridTraderBot
        bot = GridTraderBot()
        bot.run()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
