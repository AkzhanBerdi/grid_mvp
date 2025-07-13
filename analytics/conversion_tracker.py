import logging
import sqlite3
from typing import Dict

from config import Config


class ConversionTracker:
    """Track user conversion funnel and business metrics"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

    def track_event(self, telegram_id: int, event_type: str, event_data: str = ""):
        """Track a user event for conversion analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Insert event
                conn.execute(
                    """
                    INSERT INTO user_events (telegram_id, event_type, event_data)
                    VALUES (?, ?, ?)
                """,
                    (telegram_id, event_type, event_data),
                )

                # Update conversion funnel
                self._update_funnel_step(conn, telegram_id, event_type)

        except Exception as e:
            self.logger.error(
                f"Error tracking event {event_type} for user {telegram_id}: {e}"
            )

    def _update_funnel_step(self, conn, telegram_id: int, event_type: str):
        """Update conversion funnel based on event type"""
        funnel_mapping = {
            "bot_start": "started",
            "user_registered": "registered",
            "trial_started": "trial",
            "api_credentials_complete": "setup_complete",
            "bot_started_successfully": "active_user",
            "subscription_upgraded": "paid_user",
        }

        if event_type in funnel_mapping:
            step_name = funnel_mapping[event_type]

            conn.execute(
                """
                INSERT OR REPLACE INTO conversion_funnel (telegram_id, step_name)
                VALUES (?, ?)
            """,
                (telegram_id, step_name),
            )

    def get_conversion_metrics(self, days: int = 30) -> Dict:
        """Get conversion funnel metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                steps = [
                    "started",
                    "registered",
                    "trial",
                    "setup_complete",
                    "active_user",
                    "paid_user",
                ]
                metrics = {}

                for step in steps:
                    cursor = conn.execute(
                        """
                        SELECT COUNT(DISTINCT telegram_id) 
                        FROM conversion_funnel 
                        WHERE step_name = ? 
                        AND completed_at >= datetime('now', '-{} days')
                    """.format(days),
                        (step,),
                    )

                    metrics[step] = cursor.fetchone()[0]

                return metrics

        except Exception as e:
            self.logger.error(f"Error getting conversion metrics: {e}")
            return {}

    def print_mvp_report(self):
        """Print basic MVP analytics report"""
        metrics = self.get_conversion_metrics()

        print("\n📊 MVP ANALYTICS REPORT")
        print("=" * 30)
        print(f"👥 Visitors: {metrics.get('started', 0)}")
        print(f"✅ Registered: {metrics.get('registered', 0)}")
        print(f"🆓 Trials: {metrics.get('trial', 0)}")
        print(f"⚙️ Setup Complete: {metrics.get('setup_complete', 0)}")
        print(f"🚀 Active Users: {metrics.get('active_user', 0)}")
        print(f"💳 Paid Users: {metrics.get('paid_user', 0)}")
        print("=" * 30)
