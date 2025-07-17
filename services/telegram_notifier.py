# services/telegram_notifier.py
"""
Telegram Notifier Service for GridTrader Pro
"""

import logging

import requests

from config import Config


class TelegramNotifier:
    """Simple Telegram notification service"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or Config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or getattr(Config, "ADMIN_TELEGRAM_ID", None)
        self.enabled = bool(self.bot_token and self.chat_id)
        self.logger = logging.getLogger(__name__)

        if self.enabled:
            self.logger.info("✅ Telegram notifier initialized")
        else:
            self.logger.warning("⚠️ Telegram notifier disabled - missing credentials")

    async def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram"""
        if not self.enabled:
            self.logger.debug("Telegram notifier disabled, skipping message")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                self.logger.debug("📱 Telegram message sent successfully")
                return True
            else:
                self.logger.error(f"❌ Telegram send failed: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Telegram send error: {e}")
            return False
