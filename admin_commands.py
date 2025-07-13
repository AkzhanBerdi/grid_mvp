# admin_commands.py
"""Admin commands for MVP management"""

import sys
from datetime import datetime

from analytics.conversion_tracker import ConversionTracker
from repositories.user_repository import UserRepository
from services.bot_orchestrator import BotOrchestrator


class AdminCommands:
    """Admin utilities for MVP management"""

    def __init__(self):
        self.user_repo = UserRepository()
        self.conversion_tracker = ConversionTracker()
        self.bot_orchestrator = BotOrchestrator()

    def show_user_stats(self):
        """Show detailed user statistics"""
        print("\n📊 USER STATISTICS")
        print("=" * 50)

        # Total users by status
        with sqlite3.connect(self.user_repo.db_path) as conn:
            cursor = conn.execute("""
                SELECT subscription_status, COUNT(*) 
                FROM users 
                GROUP BY subscription_status
            """)

            for status, count in cursor.fetchall():
                print(f"{status.title()}: {count} users")

        # Recent signups
        cursor = conn.execute("""
            SELECT COUNT(*) FROM users 
            WHERE created_at >= datetime('now', '-24 hours')
        """)

        recent_signups = cursor.fetchone()[0]
        print(f"\nNew signups (24h): {recent_signups}")

        # Active bots
        active_bots = len(self.bot_orchestrator.get_all_active_bots())
        print(f"Active trading bots: {active_bots}")

    def export_analytics(self, filename=None):
        """Export analytics to CSV"""
        if not filename:
            filename = (
                f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

        conversion_metrics = self.conversion_tracker.get_conversion_metrics()
        business_metrics = self.conversion_tracker.get_business_metrics()

        # Create CSV content
        csv_content = [
            "Metric,Value",
            f"Total Users,{business_metrics.get('total_users', 0)}",
            f"Active Trials,{business_metrics.get('active_trials', 0)}",
            f"Paying Customers,{business_metrics.get('paying_customers', 0)}",
            f"MRR,{business_metrics.get('mrr', 0)}",
            f"Registration Rate,{conversion_metrics.get('registration_rate', 0)}",
            f"Trial Rate,{conversion_metrics.get('trial_rate', 0)}",
            f"Trial to Paid,{conversion_metrics.get('trial_to_paid', 0)}",
            f"Export Date,{datetime.now().isoformat()}",
        ]

        with open(filename, "w") as f:
            f.write("\n".join(csv_content))

        print(f"✅ Analytics exported to {filename}")

    def reset_demo_data(self):
        """Reset demo data (development only)"""
        if input("⚠️  Reset ALL data? Type 'CONFIRM' to proceed: ") != "CONFIRM":
            print("Operation cancelled")
            return

        with sqlite3.connect(self.user_repo.db_path) as conn:
            # Clear all tables
            tables = [
                "users",
                "user_events",
                "conversion_funnel",
                "trades",
                "bot_instances",
            ]
            for table in tables:
                conn.execute(f"DELETE FROM {table}")

        print("✅ All data reset")


def main():
    """Main CLI interface"""
    admin = AdminCommands()

    if len(sys.argv) < 2:
        print("Usage: python admin_commands.py <command>")
        print("\nAvailable commands:")
        print("  stats      - Show user statistics")
        print("  export     - Export analytics to CSV")
        print("  reset      - Reset demo data (dev only)")
        print("  dashboard  - Show analytics dashboard")
        return

    command = sys.argv[1]

    if command == "stats":
        admin.show_user_stats()
    elif command == "export":
        admin.export_analytics()
    elif command == "reset":
        admin.reset_demo_data()
    elif command == "dashboard":
        admin.conversion_tracker.print_mvp_report()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
