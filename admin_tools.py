# admin_tools.py
#!/usr/bin/env python3
"""Administrative tools for GridTrader Pro Service"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
from database.db_setup import DatabaseSetup
from repositories.client_repository import ClientRepository
from repositories.trade_repository import TradeRepository


class AdminTools:
    """Administrative utilities for GridTrader Pro Service"""

    def __init__(self):
        self.db_setup = DatabaseSetup()
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()

    def show_service_stats(self):
        """Show comprehensive service statistics"""
        print("\n📊 GRIDTRADER PRO SERVICE STATISTICS")
        print("=" * 60)

        # Database stats
        db_stats = self.db_setup.get_database_stats()
        print("🗄️  DATABASE:")
        print(f"   Total Clients: {db_stats.get('total_clients', 0)}")
        print(f"   Active Clients: {db_stats.get('active_clients', 0)}")
        print(f"   Total Trades: {db_stats.get('total_trades', 0)}")
        print(f"   Active Grids: {db_stats.get('active_grids', 0)}")

        # Client breakdown
        active_clients = self.client_repo.get_all_active_clients()
        print("\n👥 ACTIVE CLIENTS:")
        print(f"   Connected: {len(active_clients)}")

        # Recent activity
        print("\n📈 RECENT ACTIVITY:")
        for client_id in active_clients[:5]:  # Show top 5 active clients
            client = self.client_repo.get_client(client_id)
            if client:
                stats = self.trade_repo.get_client_trade_stats(client_id)
                print(
                    f"   {client.first_name or client_username or client_id}: "
                    f"{stats['total_trades']} trades, "
                    f"${stats['total_profit']:.2f} profit"
                )

    def show_client_details(self, client_id: int):
        """Show detailed information for a specific client"""
        client = self.client_repo.get_client(client_id)
        if not client:
            print(f"❌ Client {client_id} not found")
            return

        print(f"\n👤 CLIENT DETAILS: {client.first_name or 'Unknown'}")
        print("=" * 40)
        print(f"   Telegram ID: {client.telegram_id}")
        print(f"   Username: {client.username or 'N/A'}")
        print(f"   Status: {client.status.value}")
        print(f"   Grid Status: {client.grid_status.value}")
        print(f"   Capital: ${client.total_capital:,.2f}")
        print(f"   Trading Pairs: {', '.join(client.trading_pairs)}")
        print(f"   API Keys: {'✅ Set' if client.binance_api_key else '❌ Missing'}")
        print(f"   Created: {client.created_at}")

        # Trading statistics
        stats = self.trade_repo.get_client_trade_stats(client_id)
        print("\n📊 TRADING STATS:")
        print(f"   Total Trades: {stats['total_trades']}")
        print(f"   Total Profit: ${stats['total_profit']:.2f}")
        print(f"   Win Rate: {stats['win_rate']:.1f}%")
        print(f"   Total Volume: ${stats['total_volume']:,.2f}")

        # Recent trades
        recent_trades = stats.get("recent_trades", [])[:5]
        if recent_trades:
            print("\n📋 RECENT TRADES:")
            for trade in recent_trades:
                symbol = trade["symbol"].replace("USDT", "")
                side = trade["side"]
                value = trade["total_value"]
                print(f"   {symbol} {side}: ${value:.2f}")

    def export_client_data(self, output_file: str = None):
        """Export client data to CSV"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"client_export_{timestamp}.csv"

        try:
            import csv

            active_clients = self.client_repo.get_all_active_clients()

            with open(output_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(
                    [
                        "telegram_id",
                        "username",
                        "first_name",
                        "status",
                        "grid_status",
                        "total_capital",
                        "trading_pairs",
                        "total_trades",
                        "total_profit",
                        "win_rate",
                        "created_at",
                    ]
                )

                # Data
                for client_id in active_clients:
                    client = self.client_repo.get_client(client_id)
                    if client:
                        stats = self.trade_repo.get_client_trade_stats(client_id)

                        writer.writerow(
                            [
                                client.telegram_id,
                                client.username or "",
                                client.first_name or "",
                                client.status.value,
                                client.grid_status.value,
                                client.total_capital,
                                ";".join(client.trading_pairs),
                                stats["total_trades"],
                                stats["total_profit"],
                                stats["win_rate"],
                                client.created_at.isoformat()
                                if client.created_at
                                else "",
                            ]
                        )

            print(f"✅ Client data exported to {output_file}")

        except Exception as e:
            print(f"❌ Export failed: {e}")

    def backup_database(self):
        """Create database backup"""
        backup_path = self.db_setup.backup_database()
        if backup_path:
            print(f"✅ Database backed up to {backup_path}")
        else:
            print("❌ Backup failed")

    def cleanup_old_data(self, days: int = 90):
        """Clean up old data"""
        try:
            self.db_setup.cleanup_old_data(days)
            print(f"✅ Cleaned up data older than {days} days")
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")

    def reset_client_grid_status(self, client_id: int):
        """Reset a client's grid status (emergency use)"""
        client = self.client_repo.get_client(client_id)
        if not client:
            print(f"❌ Client {client_id} not found")
            return

        from models.client import GridStatus

        client.grid_status = GridStatus.INACTIVE

        if self.client_repo.update_client(client):
            print(f"✅ Reset grid status for client {client_id}")
        else:
            print(f"❌ Failed to reset grid status for client {client_id}")

    def show_performance_summary(self, days: int = 7):
        """Show service performance summary"""
        print(f"\n📈 PERFORMANCE SUMMARY (Last {days} days)")
        print("=" * 50)

        # Get all active clients
        active_clients = self.client_repo.get_all_active_clients()

        total_trades = 0
        total_profit = 0.0
        total_volume = 0.0

        for client_id in active_clients:
            stats = self.trade_repo.get_client_trade_stats(client_id)
            total_trades += stats["total_trades"]
            total_profit += stats["total_profit"]
            total_volume += stats["total_volume"]

        print(f"   📊 Total Trades: {total_trades}")
        print(f"   💰 Total Profit: ${total_profit:,.2f}")
        print(f"   💵 Total Volume: ${total_volume:,.2f}")
        print(
            f"   📈 Profit Margin: {(total_profit / total_volume * 100):.2f}%"
            if total_volume > 0
            else "   📈 Profit Margin: 0%"
        )
        print(f"   👥 Active Clients: {len(active_clients)}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="GridTrader Pro Administrative Tools")

    parser.add_argument("--stats", action="store_true", help="Show service statistics")
    parser.add_argument(
        "--client", type=int, metavar="ID", help="Show details for specific client"
    )
    parser.add_argument(
        "--export", action="store_true", help="Export client data to CSV"
    )
    parser.add_argument("--backup", action="store_true", help="Backup database")
    parser.add_argument(
        "--cleanup", type=int, metavar="DAYS", help="Cleanup data older than DAYS"
    )
    parser.add_argument(
        "--reset-grid",
        type=int,
        metavar="CLIENT_ID",
        help="Reset grid status for client",
    )
    parser.add_argument(
        "--performance",
        type=int,
        metavar="DAYS",
        nargs="?",
        const=7,
        help="Show performance summary",
    )
    parser.add_argument("--health", action="store_true", help="Run health check")

    args = parser.parse_args()

    admin = AdminTools()

    if args.stats:
        admin.show_service_stats()

    elif args.client:
        admin.show_client_details(args.client)

    elif args.export:
        admin.export_client_data()

    elif args.backup:
        admin.backup_database()

    elif args.cleanup:
        admin.cleanup_old_data(args.cleanup)

    elif args.reset_grid:
        confirm = input(f"Reset grid status for client {args.reset_grid}? (y/N): ")
        if confirm.lower() == "y":
            admin.reset_client_grid_status(args.reset_grid)
        else:
            print("Operation cancelled")

    elif args.performance is not None:
        admin.show_performance_summary(args.performance)

    elif args.health:
        from health_check import HealthCheck

        health_check = HealthCheck()
        status = asyncio.run(health_check.check_system_health())
        print(f"Health Status: {status['status']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

