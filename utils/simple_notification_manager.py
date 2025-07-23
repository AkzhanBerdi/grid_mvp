# utils/simple_notification_manager.py
"""
Simple Notification Manager - Fallback for missing FIFOMonitoringService
"""

import logging
from analytics.sqlite_analytics import SQLiteAnalytics


class SimpleNotificationManager:
    """Simple fallback notification manager"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analytics = SQLiteAnalytics()
        
        try:
            from services.telegram_notifier import TelegramNotifier
            self.telegram = TelegramNotifier()
        except ImportError:
            self.telegram = None
    
    async def add_client_monitor(self, client_id: int):
        """Add client monitor (fallback - just log)"""
        self.logger.info(f"Monitoring client {client_id}")
        return True
    
    async def send_profit_status(self, client_id: int):
        """Send profit status using SQLite analytics"""
        try:
            profit_data = self.analytics.get_real_profit(client_id)
            
            message = f"""📊 Profit Status - Client {client_id}
💰 Total Profit: ${profit_data.total_profit:.2f}
📈 Total Trades: {profit_data.total_trades}
📅 Daily Average: ${profit_data.daily_average:.2f}"""
            
            if self.telegram:
                return await self.telegram.send_message(message)
            else:
                self.logger.info(f"Profit status: {message}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending profit status: {e}")
            return False
    
    async def send_message(self, message: str):
        """Send simple message"""
        try:
            if self.telegram:
                return await self.telegram.send_message(message)
            else:
                self.logger.info(f"Message: {message}")
                return True
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False
