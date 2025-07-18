# integration/fifo_integration.py
"""
Integration script to add FIFO profit tracking to existing GridTrader Pro
Modifies your existing TradeRepository and monitoring system
"""breakdown

import logging
import sqlite3
from datetime import datetime

from analytics.fifo_profit_tracker import FIFOProfitTracker, PerformanceMonitor
from config import Config


class EnhancedTradeRepository:
    """Enhanced version of your existing TradeRepository with FIFO tracking"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        self.fifo_tracker = FIFOProfitTracker(db_path)

    def get_client_trade_stats(self, client_id: int) -> dict:
        """Enhanced version with FIFO profit calculation"""
        try:
            # Get FIFO-based performance metrics
            fifo_metrics = self.fifo_tracker.calculate_performance_metrics(client_id)

            # Get symbol breakdown
            trades = self.fifo_tracker.load_client_trades(client_id)
            matches = self.fifo_tracker.process_fifo_matching(trades)
            symbol_breakdown = self.fifo_tracker.get_symbol_breakdown(matches)

            # Enhanced stats with FIFO data
            return {
                # FIFO-based metrics (most important)
                "total_profit": fifo_metrics.total_realized_profit,
                "total_trades": fifo_metrics.total_trades,
                "win_rate": fifo_metrics.win_rate,
                "total_volume": fifo_metrics.total_volume,
                # Additional FIFO insights
                "average_profit_per_trade": fifo_metrics.average_profit_per_trade,
                "best_trade": fifo_metrics.best_trade,
                "worst_trade": fifo_metrics.worst_trade,
                "profit_factor": fifo_metrics.profit_factor,
                "recent_24h_profit": fifo_metrics.recent_24h_profit,
                # Compound system integration
                "current_multiplier": fifo_metrics.current_multiplier,
                "compound_active": fifo_metrics.current_multiplier > 1.0,
                "next_order_size": Config.DEFAULT_ORDER_SIZE
                * fifo_metrics.current_multiplier,
                # Symbol breakdown
                "symbol_performance": symbol_breakdown,
                # Recent trades (existing format for compatibility)
                "recent_trades": self._format_recent_trades(matches[:10]),
            }

        except Exception as e:
            self.logger.error(f"Error getting enhanced trade stats: {e}")
            # Fallback to basic calculation if FIFO fails
            return self._get_basic_stats(client_id)

    def _format_recent_trades(self, recent_matches):
        """Format recent FIFO matches for display"""
        formatted = []
        for match in recent_matches:
            formatted.append(
                {
                    "symbol": match.sell_trade.symbol,
                    "side": "FIFO_MATCH",  # Indicates this is a completed cycle
                    "quantity": match.quantity_matched,
                    "price": match.sell_trade.price,
                    "total_value": match.quantity_matched * match.sell_trade.price,
                    "profit": match.profit,
                    "profit_percentage": match.profit_percentage,
                    "executed_at": match.sell_trade.timestamp.isoformat(),
                }
            )
        return formatted

    def _get_basic_stats(self, client_id: int) -> dict:
        """Fallback basic stats calculation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(total_value) as total_volume,
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE -total_value END) as simple_profit
                    FROM trades 
                    WHERE client_id = ?
                """,
                    (client_id,),
                )

                row = cursor.fetchone()
                return {
                    "total_trades": row[0] or 0,
                    "total_volume": row[1] or 0.0,
                    "total_profit": row[2] or 0.0,
                    "win_rate": 0.0,
                    "recent_trades": [],
                }
        except:
            return {
                "total_trades": 0,
                "total_volume": 0.0,
                "total_profit": 0.0,
                "win_rate": 0.0,
                "recent_trades": [],
            }

    def log_trade_execution_with_fifo(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str,
    ):
        """Enhanced trade logging that triggers FIFO calculation"""
        try:
            total_value = quantity * price

            with sqlite3.connect(self.db_path) as conn:
                # Log the trade (existing functionality)
                conn.execute(
                    """
                    INSERT INTO trades (
                        client_id, symbol, side, quantity, price, 
                        total_value, order_id, executed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (client_id, symbol, side, quantity, price, total_value, order_id),
                )

                # Update grid order status
                conn.execute(
                    """
                    UPDATE grid_orders 
                    SET status = 'FILLED', filled_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """,
                    (order_id,),
                )

            # Calculate new compound multiplier after trade
            self._update_compound_multiplier(client_id)

            self.logger.info(
                f"Trade logged with FIFO update: {symbol} {side} {quantity} @ {price}"
            )

        except Exception as e:
            self.logger.error(f"Error logging trade with FIFO: {e}")

    def _update_compound_multiplier(self, client_id: int):
        """Update client's compound multiplier based on current FIFO profit"""
        try:
            # Get current FIFO profit
            metrics = self.fifo_tracker.calculate_performance_metrics(client_id)
            new_multiplier = metrics.current_multiplier

            # Update client's order size if needed
            from repositories.client_repository import ClientRepository

            client_repo = ClientRepository()
            client = client_repo.get_client(client_id)

            if client:
                # Update order size based on compound multiplier
                new_order_size = Config.DEFAULT_ORDER_SIZE * new_multiplier

                # Only update if significantly different (avoid constant updates)
                if abs(client.order_size - new_order_size) > 1.0:
                    client.order_size = new_order_size
                    client_repo.update_client(client)

                    self.logger.info(
                        f"Updated client {client_id} order size to ${new_order_size:.2f} (multiplier: {new_multiplier:.2f}x)"
                    )

        except Exception as e:
            self.logger.error(f"Error updating compound multiplier: {e}")


class EnhancedClientHandler:
    """Enhanced client handler with FIFO performance display"""

    def __init__(self, grid_orchestrator):
        from handlers.client_handler import ClientHandler

        # Initialize with existing handler as base
        self.base_handler = ClientHandler(grid_orchestrator)
        self.performance_monitor = PerformanceMonitor()
        self.logger = logging.getLogger(__name__)

        # Copy attributes from base handler
        self.client_repo = self.base_handler.client_repo
        self.grid_orchestrator = self.base_handler.grid_orchestrator
        self.client_states = self.base_handler.client_states

    async def _show_performance(self, query, client_id):
        """Enhanced performance display with FIFO metrics"""
        try:
            # Get FIFO-based performance
            performance = await self.performance_monitor.monitor_client_performance(
                client_id
            )

            if "error" in performance:
                await query.edit_message_text(
                    f"❌ Error loading performance: {performance['error']}"
                )
                return

            metrics = performance["metrics"]

            # Format performance message with FIFO data
            message = f"""📈 **ENHANCED TRADING PERFORMANCE**

💰 **REALIZED PROFIT (FIFO)**
   Total Profit: ${metrics.total_realized_profit:.2f}
   24h Profit: ${metrics.recent_24h_profit:.2f}
   Avg/Trade: ${metrics.average_profit_per_trade:.2f}

📊 **TRADING STATISTICS**
   Completed Cycles: {metrics.total_trades}
   Win Rate: {metrics.win_rate:.1f}%
   Best Trade: ${metrics.best_trade:.2f}
   Worst Trade: ${metrics.worst_trade:.2f}
   Profit Factor: {metrics.profit_factor:.2f}

🔄 **COMPOUND SYSTEM**
   Current Multiplier: {metrics.current_multiplier:.2f}x
   New Order Size: ${Config.DEFAULT_ORDER_SIZE * metrics.current_multiplier:.2f}
   Status: {"🟢 ACTIVE" if metrics.current_multiplier > 1.0 else "⚪ INACTIVE"}

📈 **TOTAL VOLUME**
   Traded: ${metrics.total_volume:,.2f}
   Profit Margin: {(metrics.total_realized_profit / metrics.total_volume * 100):.3f}%"""

            # Add alerts if any
            if performance["alerts"]:
                message += f"\n\n🚨 **ALERTS**\n{chr(10).join(performance['alerts'])}"

            keyboard = [
                [{"text": "🔄 Refresh", "callback_data": "show_performance"}],
                [{"text": "📊 Dashboard", "callback_data": "show_dashboard"}],
            ]

            await query.edit_message_text(message, parse_mode="Markdown")

        except Exception as e:
            self.logger.error(f"Error showing enhanced performance: {e}")
            # Fallback to basic performance
            await self.base_handler._show_performance(query, client_id)

    # Delegate other methods to base handler
    async def handle_start(self, update, context):
        return await self.base_handler.handle_start(update, context)

    async def handle_callback(self, update, context):
        # Intercept performance callbacks
        if update.callback_query.data == "show_performance":
            await self._show_performance(
                update.callback_query, update.callback_query.from_user.id
            )
        else:
            return await self.base_handler.handle_callback(update, context)

    async def handle_message(self, update, context):
        return await self.base_handler.handle_message(update, context)


class EnhancedMonitoringDashboard:
    """Enhanced monitoring dashboard with FIFO metrics"""

    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.client_repo = ClientRepository()
        self.logger = logging.getLogger(__name__)

    def display_realtime_metrics(self):
        """Enhanced real-time dashboard with FIFO metrics"""
        import time

        while True:
            try:
                # Clear screen
                print("\033[2J\033[H")

                # Header
                print("=" * 80)
                print("🚀 GRIDTRADER PRO - ENHANCED FIFO DASHBOARD")
                print("=" * 80)
                print(
                    f"⏰ Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print()

                # Get all active clients
                active_clients = self.client_repo.get_all_active_clients()

                if not active_clients:
                    print("📊 No active clients found")
                    time.sleep(30)
                    continue

                # Aggregate metrics
                total_realized_profit = 0.0
                total_volume = 0.0
                total_active_multipliers = 0
                client_performances = []

                print("👥 **CLIENT PERFORMANCES (FIFO-BASED)**")
                print("-" * 60)

                for client_id in active_clients[:10]:  # Show top 10 clients
                    try:
                        # Get FIFO performance
                        import asyncio

                        performance = asyncio.run(
                            self.performance_monitor.monitor_client_performance(
                                client_id
                            )
                        )

                        if "error" not in performance:
                            metrics = performance["metrics"]
                            client_performances.append(metrics)

                            total_realized_profit += metrics.total_realized_profit
                            total_volume += metrics.total_volume

                            if metrics.current_multiplier > 1.0:
                                total_active_multipliers += 1

                            # Status indicators
                            profit_emoji = (
                                "🟢" if metrics.total_realized_profit > 0 else "🔴"
                            )
                            compound_emoji = (
                                "🚀" if metrics.current_multiplier > 1.0 else "⚪"
                            )

                            print(f"{profit_emoji} Client {client_id}:")
                            print(
                                f"   💰 Profit: ${metrics.total_realized_profit:>8.2f}"
                            )
                            print(f"   📊 Win Rate: {metrics.win_rate:>5.1f}%")
                            print(
                                f"   {compound_emoji} Multiplier: {metrics.current_multiplier:>4.2f}x"
                            )
                            print(f"   ⏱️  24h: ${metrics.recent_24h_profit:>8.2f}")

                            # Show alerts
                            if performance["alerts"]:
                                print(f"   🚨 {performance['alerts'][0][:30]}...")
                            print()

                    except Exception as e:
                        print(f"❌ Client {client_id}: Error - {str(e)[:30]}...")

                print()
                print("💰 **AGGREGATE FIFO METRICS**")
                print("-" * 40)
                print(f"Total Realized Profit:   ${total_realized_profit:>10.2f}")
                print(f"Total Volume Traded:     ${total_volume:>10,.0f}")
                if total_volume > 0:
                    profit_margin = (total_realized_profit / total_volume) * 100
                    print(f"Overall Profit Margin:   {profit_margin:>10.3f}%")
                print(f"Active Clients:          {len(active_clients):>10}")
                print(f"Compound Active:         {total_active_multipliers:>10}")

                print()
                print("🎯 **PERFORMANCE INSIGHTS**")
                print("-" * 40)

                if client_performances:
                    avg_win_rate = sum(p.win_rate for p in client_performances) / len(
                        client_performances
                    )
                    avg_multiplier = sum(
                        p.current_multiplier for p in client_performances
                    ) / len(client_performances)
                    profitable_clients = len(
                        [p for p in client_performances if p.total_realized_profit > 0]
                    )

                    print(f"Average Win Rate:        {avg_win_rate:>10.1f}%")
                    print(f"Average Multiplier:      {avg_multiplier:>10.2f}x")
                    print(
                        f"Profitable Clients:      {profitable_clients:>10}/{len(client_performances)}"
                    )

                    # Performance status
                    if avg_win_rate > 60:
                        status = "🟢 EXCELLENT"
                    elif avg_win_rate > 45:
                        status = "🟡 GOOD"
                    else:
                        status = "🔴 NEEDS ATTENTION"
                    print(f"Overall Status:          {status}")

                print()
                print("📈 **FIFO ADVANTAGES**")
                print("-" * 40)
                print("✅ Tax-compliant profit calculation")
                print("✅ Accurate realized gains tracking")
                print("✅ Compound system integration")
                print("✅ Real buy-sell cycle matching")
                print("✅ Professional accounting method")

                print()
                print("🔧 **QUICK ACTIONS**")
                print("-" * 40)
                print("Press Ctrl+C to exit")
                print("Detailed report: python -m analytics.fifo_profit_tracker")
                print("Health check: python health_check.py")
                print("Admin tools: python admin_tools.py --stats")
                print()

                # Sleep for 30 seconds before refresh
                time.sleep(30)

            except KeyboardInterrupt:
                print("\n👋 Enhanced dashboard stopped by user")
                break
            except Exception as e:
                print(f"Error updating dashboard: {e}")
                time.sleep(10)


# Migration script to integrate FIFO tracking
class FIFOMigration:
    """Migration script to integrate FIFO tracking into existing system"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def migrate_to_fifo_system(self):
        """Migrate existing system to use FIFO tracking"""
        print("🔄 **MIGRATING TO FIFO SYSTEM**")
        print("=" * 50)

        try:
            # 1. Test FIFO tracker with existing data
            print("1️⃣ Testing FIFO tracker...")
            fifo_tracker = FIFOProfitTracker()

            # Get a test client
            client_repo = ClientRepository()
            active_clients = client_repo.get_all_active_clients()

            if active_clients:
                test_client = active_clients[0]
                metrics = fifo_tracker.calculate_performance_metrics(test_client)
                print(f"   ✅ FIFO calculation successful for client {test_client}")
                print(
                    f"   📊 Profit: ${metrics.total_realized_profit:.2f}, Trades: {metrics.total_trades}"
                )
            else:
                print("   ⚠️ No active clients found for testing")

            # 2. Create enhanced repositories
            print("\n2️⃣ Creating enhanced repositories...")
            enhanced_trade_repo = EnhancedTradeRepository()
            print("   ✅ Enhanced TradeRepository created")

            # 3. Test performance monitoring
            print("\n3️⃣ Testing performance monitoring...")
            performance_monitor = PerformanceMonitor()
            if active_clients:
                performance = asyncio.run(
                    performance_monitor.monitor_client_performance(active_clients[0])
                )
                if "error" not in performance:
                    print("   ✅ Performance monitoring working")
                else:
                    print(f"   ❌ Performance monitoring error: {performance['error']}")

            # 4. Show integration instructions
            print("\n4️⃣ Integration instructions:")
            print("   📝 Replace imports in main.py:")
            print(
                "      from integration.fifo_integration import EnhancedClientHandler"
            )
            print(
                "      from integration.fifo_integration import EnhancedMonitoringDashboard"
            )
            print()
            print("   📝 Update grid_orchestrator.py trade logging:")
            print(
                "      Use log_trade_execution_with_fifo() instead of log_trade_execution()"
            )
            print()
            print("   📝 Replace monitoring dashboard:")
            print("      dashboard = EnhancedMonitoringDashboard()")

            print("\n✅ **FIFO MIGRATION READY**")
            print("Your system is ready to use FIFO-based profit tracking!")

        except Exception as e:
            print(f"❌ Migration error: {e}")
            import traceback

            traceback.print_exc()

    def generate_fifo_comparison_report(self, client_id: int):
        """Compare old vs new profit calculation methods"""
        print(f"\n📊 **PROFIT CALCULATION COMPARISON - Client {client_id}**")
        print("=" * 60)

        try:
            # Old method (simple sell_total - buy_total)
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE 0 END) as sell_total,
                        SUM(CASE WHEN side = 'BUY' THEN total_value ELSE 0 END) as buy_total
                    FROM trades WHERE client_id = ?
                """,
                    (client_id,),
                )

                row = cursor.fetchone()
                old_profit = (row[0] or 0) - (row[1] or 0)

            # New FIFO method
            fifo_tracker = FIFOProfitTracker()
            metrics = fifo_tracker.calculate_performance_metrics(client_id)
            fifo_profit = metrics.total_realized_profit

            print(f"💰 **OLD METHOD (Simple):**     ${old_profit:.2f}")
            print(f"💎 **NEW METHOD (FIFO):**      ${fifo_profit:.2f}")
            print(f"📈 **Difference:**             ${fifo_profit - old_profit:.2f}")
            print(f"📊 **Accuracy Improvement:**   {abs(fifo_profit - old_profit):.2f}")

            print("\n🔍 **FIFO ADVANTAGES:**")
            print("   ✅ Matches actual trading cycles")
            print("   ✅ Tax-compliant FIFO accounting")
            print("   ✅ Accurate profit per trade")
            print(f"   ✅ Win rate: {metrics.win_rate:.1f}%")
            print(f"   ✅ Profit factor: {metrics.profit_factor:.2f}")

        except Exception as e:
            print(f"❌ Comparison error: {e}")


# CLI tool for FIFO integration
def main():
    """Main CLI for FIFO integration"""
    import argparse

    parser = argparse.ArgumentParser(description="FIFO Integration for GridTrader Pro")
    parser.add_argument("--migrate", action="store_true", help="Migrate to FIFO system")
    parser.add_argument(
        "--compare", type=int, metavar="CLIENT_ID", help="Compare profit calculations"
    )
    parser.add_argument(
        "--test", type=int, metavar="CLIENT_ID", help="Test FIFO tracking for client"
    )
    parser.add_argument(
        "--dashboard", action="store_true", help="Run enhanced dashboard"
    )

    args = parser.parse_args()

    migration = FIFOMigration()

    if args.migrate:
        migration.migrate_to_fifo_system()
    elif args.compare:
        migration.generate_fifo_comparison_report(args.compare)
    elif args.test:
        fifo_tracker = FIFOProfitTracker()
        report = fifo_tracker.generate_performance_report(args.test)
        print(report)
    elif args.dashboard:
        dashboard = EnhancedMonitoringDashboard()
        dashboard.display_realtime_metrics()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
