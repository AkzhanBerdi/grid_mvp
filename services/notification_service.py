# services/notification_service.py
"""Notification service for user alerts"""

import logging
from typing import Dict

from telegram import Bot

from config import Config


class NotificationService:
    """Service for sending notifications to users"""

    def __init__(self):
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        self.logger = logging.getLogger(__name__)

    async def send_trade_notification(self, telegram_id: int, trade_data: Dict):
        """Send trade execution notification"""
        try:
            side_emoji = "🟢" if trade_data["side"] == "BUY" else "🔴"

            message = f"""{side_emoji} **Trade Executed**

{trade_data["side"]} {trade_data["quantity"]} {trade_data["symbol"]}
Price: ${trade_data["price"]:.4f}
Value: ${trade_data["value"]:.2f}"""

            if trade_data.get("profit"):
                profit_emoji = "💰" if trade_data["profit"] > 0 else "📉"
                message += f"\n{profit_emoji} Profit: ${trade_data['profit']:.2f}"

            await self.bot.send_message(
                chat_id=telegram_id, text=message, parse_mode="Markdown"
            )

        except Exception as e:
            self.logger.error(f"Error sending trade notification to {telegram_id}: {e}")

    async def send_bot_status_notification(
        self, telegram_id: int, status: str, message: str = None
    ):
        """Send bot status change notification"""
        try:
            status_messages = {
                "started": "🚀 **Bot Started**\n\nYour trading bot is now active!",
                "stopped": "🛑 **Bot Stopped**\n\nYour trading bot has been stopped.",
                "error": "❌ **Bot Error**\n\nYour bot encountered an error and has been stopped.",
            }

            notification = status_messages.get(status, f"Bot status: {status}")

            if message:
                notification += f"\n\n{message}"

            await self.bot.send_message(
                chat_id=telegram_id, text=notification, parse_mode="Markdown"
            )

        except Exception as e:
            self.logger.error(
                f"Error sending bot status notification to {telegram_id}: {e}"
            )

    async def send_trial_expiry_warning(self, telegram_id: int, days_left: int):
        """Send trial expiry warning"""
        try:
            message = f"""⏰ **Trial Expiring Soon**

Your free trial expires in {days_left} day{"s" if days_left != 1 else ""}.

Upgrade now to continue automated trading!"""

            await self.bot.send_message(
                chat_id=telegram_id, text=message, parse_mode="Markdown"
            )

        except Exception as e:
            self.logger.error(f"Error sending trial warning to {telegram_id}: {e}")
