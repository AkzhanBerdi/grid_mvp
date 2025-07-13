#!/usr/bin/env python3
"""Simple Grid Trading Bot - Clean and Working Version"""

import asyncio
import logging
import sqlite3
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from analytics.conversion_tracker import ConversionTracker
from config import Config
from database.db_setup import DatabaseSetup
from handlers.complete_handler import CompleteHandler


class SimpleGridBot:
    """Simple grid trading bot with optional Telegram integration"""

    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()

        # Initialize components
        self.db_setup = DatabaseSetup()
        self.conversion_tracker = ConversionTracker()
        self.handler = CompleteHandler(self.conversion_tracker)

        # Bot state
        self.running = False
        self.grids: Dict[str, Dict] = {}

        # Initialize Binance client
        self.binance_client = self._init_binance_client()

        self.logger.info("🤖 Simple Grid Trading Bot initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        Path("data/logs").mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.config.LOG_FILE),
                logging.StreamHandler(sys.stdout),
            ],
        )
        return logging.getLogger(__name__)

    def _init_binance_client(self) -> Optional[Client]:
        """Initialize Binance client if API keys are available"""
        try:
            if hasattr(self.config, "BINANCE_API_KEY") and self.config.BINANCE_API_KEY:
                return Client(
                    self.config.BINANCE_API_KEY,
                    self.config.BINANCE_SECRET_KEY,
                    testnet=self.config.ENVIRONMENT == "development",
                )
            else:
                self.logger.warning(
                    "Binance API keys not configured - running in simulation mode"
                )
                return None
        except Exception as e:
            self.logger.error(f"Failed to initialize Binance client: {e}")
            return None

    def _init_database(self):
        """Initialize database tables"""
        try:
            self.db_setup.initialize()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a trading pair"""
        if not self.binance_client:
            # Return a fake price for simulation
            fake_prices = {
                "ADAUSDT": 0.50,
                "AVAXUSDT": 25.00,
                "BTCUSDT": 45000.00,
                "ETHUSDT": 3000.00,
            }
            return fake_prices.get(symbol, 1.00)

        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return None

    def place_grid_order(
        self, symbol: str, side: str, price: float, quantity: float
    ) -> Optional[Dict]:
        """Place a grid order"""
        if not self.binance_client:
            # Simulation mode
            self.logger.info(
                f"SIMULATION: {side} {quantity:.4f} {symbol} at ${price:.4f}"
            )
            return {"orderId": int(time.time() * 1000), "status": "NEW"}

        try:
            if side == "BUY":
                order = self.binance_client.order_limit_buy(
                    symbol=symbol, quantity=quantity, price=str(price)
                )
            else:
                order = self.binance_client.order_limit_sell(
                    symbol=symbol, quantity=quantity, price=str(price)
                )

            self.logger.info(
                f"✅ Order placed: {side} {quantity:.4f} {symbol} at ${price:.4f}"
            )
            return order

        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Order placement error: {e}")
            return None

    def log_trade(self, symbol: str, side: str, quantity: float, price: float):
        """Log trade to database"""
        try:
            with sqlite3.connect("data/gridtrader.db") as conn:
                # Check if the trades table has telegram_id column
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(trades)")
                columns = [column[1] for column in cursor.fetchall()]

                if "telegram_id" in columns:
                    # Table has telegram_id column - insert with NULL telegram_id
                    conn.execute(
                        """
                        INSERT INTO trades (symbol, side, quantity, price, value, timestamp, telegram_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            symbol,
                            side,
                            quantity,
                            price,
                            quantity * price,
                            time.time(),
                            None,
                        ),
                    )
                else:
                    # Table doesn't have telegram_id column - insert without it
                    conn.execute(
                        """
                        INSERT INTO trades (symbol, side, quantity, price, value, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (symbol, side, quantity, price, quantity * price, time.time()),
                    )

            self.logger.info(
                f"📊 Trade logged: {side} {quantity:.4f} {symbol} at ${price:.4f}"
            )
        except Exception as e:
            self.logger.error(f"Failed to log trade: {e}")

    def trading_loop(self):
        """Main trading loop (synchronous)"""
        self.logger.info("🔄 Starting trading loop")

        # Simple demo: just log some fake trades periodically
        trade_count = 0
        symbols = ["ADAUSDT", "AVAXUSDT"]

        while self.running:
            try:
                for symbol in symbols:
                    current_price = self.get_current_price(symbol)
                    if current_price:
                        # Simulate some trading activity
                        side = "BUY" if trade_count % 2 == 0 else "SELL"
                        quantity = 10.0 if symbol == "ADAUSDT" else 0.5

                        # Log a simulated trade every 10 cycles
                        if trade_count % 10 == 0:
                            self.log_trade(symbol, side, quantity, current_price)

                trade_count += 1
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                time.sleep(60)  # Wait longer on error

    async def telegram_start(self, update, context):
        """Handle /start command"""
        try:
            await self.handler.handle_start(update, context)
        except Exception as e:
            self.logger.error(f"Error in start handler: {e}")

    async def telegram_callback(self, update, context):
        """Handle callback queries"""
        try:
            await self.handler.handle_callback(update, context)
        except Exception as e:
            self.logger.error(f"Error in callback handler: {e}")

    async def telegram_message(self, update, context):
        """Handle text messages"""
        try:
            await self.handler.handle_message(update, context)
        except Exception as e:
            self.logger.error(f"Error in message handler: {e}")

    def start_telegram_bot(self):
        """Start Telegram bot in separate thread"""
        if not self.config.TELEGRAM_BOT_TOKEN:
            self.logger.warning(
                "Telegram bot token not configured - skipping Telegram bot"
            )
            return

        def run_telegram():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                app = (
                    Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
                )

                # Add handlers
                app.add_handler(CommandHandler("start", self.telegram_start))
                app.add_handler(CallbackQueryHandler(self.telegram_callback))
                app.add_handler(
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.telegram_message
                    )
                )

                self.logger.info("📱 Starting Telegram bot...")
                app.run_polling()

            except Exception as e:
                self.logger.error(f"Telegram bot error: {e}")

        # Start Telegram bot in a separate thread
        telegram_thread = threading.Thread(target=run_telegram, daemon=True)
        telegram_thread.start()
        self.logger.info("📱 Telegram bot started in background")

    def start(self):
        """Start the bot"""
        self.logger.info("🚀 Starting Simple Grid Trading Bot")

        try:
            # Initialize database
            self._init_database()

            # Start Telegram bot in background
            self.start_telegram_bot()

            # Start trading loop
            self.running = True
            self.trading_loop()

        except KeyboardInterrupt:
            self.logger.info("🛑 Bot stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Bot error: {e}")
        finally:
            self.running = False

    def stop(self):
        """Stop the bot"""
        self.logger.info("🛑 Stopping bot...")
        self.running = False


def main():
    """Entry point"""
    # Validate configuration
    if not Config.validate():
        print("❌ Invalid configuration. Please check your environment variables.")
        sys.exit(1)

    # Create and start bot
    bot = SimpleGridBot()
    bot.start()


if __name__ == "__main__":
    main()
