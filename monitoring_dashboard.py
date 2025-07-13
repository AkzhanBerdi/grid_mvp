# monitoring_dashboard.py
"""Simple monitoring dashboard for MVP analytics"""

import time
from datetime import datetime

from analytics.conversion_tracker import ConversionTracker
from repositories.user_repository import UserRepository
from services.bot_orchestrator import BotOrchestrator


class MVPMonitoringDashboard:
    """Real-time monitoring dashboard for MVP metrics"""

    def __init__(self):
        self.conversion_tracker = ConversionTracker()
        self.user_repo = UserRepository()
        self.bot_orchestrator = BotOrchestrator()

    def display_realtime_metrics(self):
        """Display real-time MVP metrics"""
        while True:
            try:
                # Clear screen
                print("\033[2J\033[H")

                # Header
                print("=" * 80)
                print("🚀 GRIDTRADER PRO MVP - REAL-TIME DASHBOARD")
                print("=" * 80)
                print(
                    f"⏰ Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print()

                # Get metrics
                conversion_metrics = self.conversion_tracker.get_conversion_metrics(
                    days=7
                )
                business_metrics = self.conversion_tracker.get_business_metrics()
                active_bots = self.bot_orchestrator.get_all_active_bots()

                # Conversion Funnel (Last 7 days)
                print("📊 CONVERSION FUNNEL (Last 7 Days)")
                print("-" * 40)
                print(f"👥 Visitors:      {conversion_metrics.get('started', 0):>6}")
                print(
                    f"✅ Registered:    {conversion_metrics.get('registered', 0):>6} ({conversion_metrics.get('registration_rate', 0):>5.1f}%)"
                )
                print(
                    f"🆓 Trial Started: {conversion_metrics.get('trial', 0):>6} ({conversion_metrics.get('trial_rate', 0):>5.1f}%)"
                )
                print(
                    f"⚙️  Setup Done:    {conversion_metrics.get('setup_complete', 0):>6} ({conversion_metrics.get('setup_rate', 0):>5.1f}%)"
                )
                print(
                    f"🚀 Active Users:  {conversion_metrics.get('active_user', 0):>6} ({conversion_metrics.get('activation_rate', 0):>5.1f}%)"
                )
                print(f"💳 Paid Users:    {conversion_metrics.get('paid_user', 0):>6}")
                print()

                # Business Metrics
                print("💰 BUSINESS METRICS")
                print("-" * 40)
                print(f"Monthly Revenue:     ${business_metrics.get('mrr', 0):>8}")
                print(
                    f"Total Users:         {business_metrics.get('total_users', 0):>8}"
                )
                print(
                    f"Active Trials:       {business_metrics.get('active_trials', 0):>8}"
                )
                print(
                    f"Paying Customers:    {business_metrics.get('paying_customers', 0):>8}"
                )

                if business_metrics.get("paying_customers", 0) > 0:
                    arpu = business_metrics.get("mrr", 0) / business_metrics.get(
                        "paying_customers", 1
                    )
                    print(f"Avg Revenue/User:    ${arpu:>8.2f}")
                print()

                # Technical Metrics
                print("🤖 TECHNICAL METRICS")
                print("-" * 40)
                print(f"Active Bots:         {len(active_bots):>8}")
                total_orders = sum(
                    bot.get("active_orders", 0) for bot in active_bots.values()
                )
                print(f"Total Active Orders: {total_orders:>8}")
                print()

                # MVP Success Status
                trial_to_paid = conversion_metrics.get("trial_to_paid", 0)
                print("🎯 MVP SUCCESS STATUS")
                print("-" * 40)
                print(f"Trial→Paid Rate:     {trial_to_paid:>6.1f}%")

                if trial_to_paid >= 25:
                    status = "✅ EXCELLENT"
                elif trial_to_paid >= 15:
                    status = "⚠️  GOOD"
                elif trial_to_paid >= 10:
                    status = "⚠️  NEEDS WORK"
                else:
                    status = "❌ CRITICAL"

                print(f"Status:              {status}")
                print()

                # Quick Actions
                print("🔧 QUICK ACTIONS")
                print("-" * 40)
                print("Press Ctrl+C to exit")
                print("Check logs: tail -f data/logs/gridtrader.log")
                print("Health check: python health_check.py")
                print()

                # Sleep for 30 seconds before refresh
                time.sleep(30)

            except KeyboardInterrupt:
                print("\n👋 Dashboard stopped by user")
                break
            except Exception as e:
                print(f"Error updating dashboard: {e}")
                time.sleep(10)


if __name__ == "__main__":
    dashboard = MVPMonitoringDashboard()
    dashboard.display_realtime_metrics()
