# analytics/fifo_profit_tracker.py
"""
Enhanced FIFO-based profit tracking and performance monitoring
Integrates with your existing GridTrader Pro setup
"""

import logging
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from config import Config


@dataclass
class Trade:
    """Individual trade record"""
    id: int
    timestamp: datetime
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    total_value: float


@dataclass
class FIFOMatch:
    """FIFO matched buy-sell pair"""
    buy_trade: Trade
    sell_trade: Trade
    quantity_matched: float
    profit: float
    profit_percentage: float


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    total_realized_profit: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_profit_per_trade: float
    best_trade: float
    worst_trade: float
    total_volume: float
    profit_factor: float  # gross_profit / gross_loss
    current_multiplier: float
    recent_24h_profit: float


class FIFOProfitTracker:
    """Advanced FIFO-based profit tracking with compound integration"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        
        # FIFO queues for each symbol: {symbol: deque of buy trades}
        self.buy_queues: Dict[str, deque] = defaultdict(deque)
        
        # Completed FIFO matches for profit calculation
        self.completed_matches: List[FIFOMatch] = []
        
        # Base order size for compound calculations
        self.base_order_size = Config.DEFAULT_ORDER_SIZE

    def load_client_trades(self, client_id: int) -> List[Trade]:
        """Load all trades for a client from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, executed_at, symbol, side, quantity, price, total_value
                    FROM trades 
                    WHERE client_id = ?
                    ORDER BY executed_at ASC
                """, (client_id,))
                
                trades = []
                for row in cursor.fetchall():
                    trades.append(Trade(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        symbol=row[2],
                        side=row[3],
                        quantity=row[4],
                        price=row[5],
                        total_value=row[6]
                    ))
                
                self.logger.info(f"Loaded {len(trades)} trades for client {client_id}")
                return trades
                
        except Exception as e:
            self.logger.error(f"Error loading trades: {e}")
            return []

    def process_fifo_matching(self, trades: List[Trade]) -> List[FIFOMatch]:
        """Process all trades with FIFO matching algorithm"""
        # Reset state
        self.buy_queues.clear()
        matches = []
        
        for trade in trades:
            if trade.side == 'BUY':
                # Add to buy queue for this symbol
                self.buy_queues[trade.symbol].append(trade)
                
            elif trade.side == 'SELL':
                # Match with oldest buys (FIFO)
                remaining_sell_qty = trade.quantity
                
                while remaining_sell_qty > 0 and self.buy_queues[trade.symbol]:
                    oldest_buy = self.buy_queues[trade.symbol][0]
                    
                    # Determine how much to match
                    match_qty = min(remaining_sell_qty, oldest_buy.quantity)
                    
                    # Calculate profit for this match
                    buy_cost = match_qty * oldest_buy.price
                    sell_revenue = match_qty * trade.price
                    profit = sell_revenue - buy_cost
                    profit_percentage = (profit / buy_cost) * 100 if buy_cost > 0 else 0
                    
                    # Create FIFO match record
                    fifo_match = FIFOMatch(
                        buy_trade=oldest_buy,
                        sell_trade=trade,
                        quantity_matched=match_qty,
                        profit=profit,
                        profit_percentage=profit_percentage
                    )
                    matches.append(fifo_match)
                    
                    # Update quantities
                    remaining_sell_qty -= match_qty
                    oldest_buy.quantity -= match_qty
                    
                    # Remove buy trade if fully consumed
                    if oldest_buy.quantity <= 0:
                        self.buy_queues[trade.symbol].popleft()
        
        self.completed_matches = matches
        self.logger.info(f"Processed {len(matches)} FIFO matches")
        return matches

    def calculate_performance_metrics(self, client_id: int) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        # Load and process trades
        trades = self.load_client_trades(client_id)
        matches = self.process_fifo_matching(trades)
        
        if not matches:
            return PerformanceMetrics(
                total_realized_profit=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                average_profit_per_trade=0.0,
                best_trade=0.0,
                worst_trade=0.0,
                total_volume=0.0,
                profit_factor=0.0,
                current_multiplier=1.0,
                recent_24h_profit=0.0
            )
        
        # Calculate basic metrics
        total_profit = sum(match.profit for match in matches)
        winning_matches = [m for m in matches if m.profit > 0]
        losing_matches = [m for m in matches if m.profit < 0]
        
        win_rate = len(winning_matches) / len(matches) * 100 if matches else 0
        avg_profit = total_profit / len(matches) if matches else 0
        
        best_trade = max(match.profit for match in matches) if matches else 0
        worst_trade = min(match.profit for match in matches) if matches else 0
        
        # Calculate total volume
        total_volume = sum(trade.total_value for trade in trades)
        
        # Calculate profit factor (gross profit / gross loss)
        gross_profit = sum(m.profit for m in winning_matches)
        gross_loss = abs(sum(m.profit for m in losing_matches))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate compound multiplier
        current_multiplier = self.calculate_compound_multiplier(total_profit)
        
        # Calculate recent 24h profit
        recent_24h_profit = self.calculate_recent_profit(matches, hours=24)
        
        return PerformanceMetrics(
            total_realized_profit=total_profit,
            total_trades=len(matches),
            winning_trades=len(winning_matches),
            losing_trades=len(losing_matches),
            win_rate=win_rate,
            average_profit_per_trade=avg_profit,
            best_trade=best_trade,
            worst_trade=worst_trade,
            total_volume=total_volume,
            profit_factor=profit_factor,
            current_multiplier=current_multiplier,
            recent_24h_profit=recent_24h_profit
        )

    def calculate_compound_multiplier(self, total_profit: float) -> float:
        """Calculate current compound multiplier based on profit"""
        # Your compound system: 50% reinvestment rate, 3.0x max multiplier
        reinvestment_rate = 0.5
        max_multiplier = 3.0
        
        if total_profit < 100:  # Minimum threshold
            return 1.0
            
        # Formula: 1.0 + (total_profit × reinvestment_rate / base_order_size)
        multiplier = 1.0 + (total_profit * reinvestment_rate / self.base_order_size)
        
        return min(multiplier, max_multiplier)

    def calculate_recent_profit(self, matches: List[FIFOMatch], hours: int = 24) -> float:
        """Calculate profit from recent matches within time window"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_profit = sum(
            match.profit for match in matches 
            if match.sell_trade.timestamp >= cutoff_time
        )
        
        return recent_profit

    def get_symbol_breakdown(self, matches: List[FIFOMatch]) -> Dict[str, Dict]:
        """Get performance breakdown by symbol"""
        symbol_stats = defaultdict(lambda: {
            'profit': 0.0,
            'trades': 0,
            'volume': 0.0,
            'win_rate': 0.0
        })
        
        for match in matches:
            symbol = match.buy_trade.symbol
            symbol_stats[symbol]['profit'] += match.profit
            symbol_stats[symbol]['trades'] += 1
            symbol_stats[symbol]['volume'] += match.buy_trade.total_value
            
        # Calculate win rates
        for symbol in symbol_stats:
            symbol_matches = [m for m in matches if m.buy_trade.symbol == symbol]
            winning = len([m for m in symbol_matches if m.profit > 0])
            symbol_stats[symbol]['win_rate'] = winning / len(symbol_matches) * 100 if symbol_matches else 0
            
        return dict(symbol_stats)

    def generate_performance_report(self, client_id: int) -> str:
        """Generate comprehensive performance report"""
        metrics = self.calculate_performance_metrics(client_id)
        matches = self.completed_matches
        symbol_breakdown = self.get_symbol_breakdown(matches)
        
        report = f"""
📊 **GRIDTRADER PRO PERFORMANCE REPORT**
{'='*50}
⏰ **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 **Client ID:** {client_id}

💰 **REALIZED PROFIT (FIFO)**
   Total Profit: ${metrics.total_realized_profit:.2f}
   24h Profit: ${metrics.recent_24h_profit:.2f}
   Average/Trade: ${metrics.average_profit_per_trade:.2f}
   
📈 **TRADING STATISTICS**
   Total Completed Cycles: {metrics.total_trades}
   Winning Trades: {metrics.winning_trades}
   Losing Trades: {metrics.losing_trades}
   Win Rate: {metrics.win_rate:.1f}%
   
🎯 **PERFORMANCE METRICS**
   Best Trade: ${metrics.best_trade:.2f}
   Worst Trade: ${metrics.worst_trade:.2f}
   Profit Factor: {metrics.profit_factor:.2f}
   Total Volume: ${metrics.total_volume:,.2f}
   
🔄 **COMPOUND SYSTEM**
   Current Multiplier: {metrics.current_multiplier:.2f}x
   New Order Size: ${self.base_order_size * metrics.current_multiplier:.2f}
   Status: {'ACTIVE' if metrics.current_multiplier > 1.0 else 'INACTIVE'}

📊 **SYMBOL BREAKDOWN**"""
        
        for symbol, stats in symbol_breakdown.items():
            report += f"""
   {symbol}: ${stats['profit']:.2f} profit, {stats['trades']} trades, {stats['win_rate']:.1f}% win rate"""
        
        return report


class PerformanceMonitor:
    """Real-time performance monitoring and alerting"""
    
    def __init__(self):
        self.fifo_tracker = FIFOProfitTracker()
        self.logger = logging.getLogger(__name__)

    async def monitor_client_performance(self, client_id: int) -> Dict:
        """Monitor and return current performance status"""
        try:
            metrics = self.fifo_tracker.calculate_performance_metrics(client_id)
            
            # Generate alerts based on performance
            alerts = []
            
            if metrics.recent_24h_profit < -50:  # $50 loss in 24h
                alerts.append("⚠️ Significant 24h loss detected")
                
            if metrics.win_rate < 30:  # Less than 30% win rate
                alerts.append("⚠️ Low win rate - review grid spacing")
                
            if metrics.current_multiplier >= 2.5:  # High multiplier
                alerts.append("🚀 High compound multiplier active")
                
            return {
                'client_id': client_id,
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics,
                'alerts': alerts,
                'status': 'profitable' if metrics.total_realized_profit > 0 else 'unprofitable'
            }
            
        except Exception as e:
            self.logger.error(f"Error monitoring client {client_id}: {e}")
            return {'error': str(e)}

    def should_adjust_grid(self, metrics: PerformanceMetrics) -> Tuple[bool, str]:
        """Determine if grid parameters should be adjusted"""
        if metrics.win_rate < 25:
            return True, "Increase grid spacing - too many losing trades"
            
        if metrics.recent_24h_profit < -100:
            return True, "Reduce position size - excessive recent losses"
            
        if metrics.profit_factor < 1.2:
            return True, "Optimize grid levels - poor risk/reward ratio"
            
        return False, "Grid parameters optimal"


# Integration with your existing monitoring dashboard
class EnhancedMonitoringDashboard:
    """Enhanced version of your monitoring_dashboard.py with FIFO tracking"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.logger = logging.getLogger(__name__)

    async def display_enhanced_metrics(self, client_ids: List[int]):
        """Display enhanced metrics for all clients"""
        print("\033[2J\033[H")  # Clear screen
        
        print("=" * 80)
        print("🚀 GRIDTRADER PRO - ENHANCED PERFORMANCE DASHBOARD")
        print("=" * 80)
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        total_profit = 0.0
        total_volume = 0.0
        
        for client_id in client_ids:
            try:
                status = await self.performance_monitor.monitor_client_performance(client_id)
                
                if 'error' not in status:
                    metrics = status['metrics']
                    total_profit += metrics.total_realized_profit
                    total_volume += metrics.total_volume
                    
                    print(f"👤 **Client {client_id}**")
                    print(f"   💰 Realized Profit: ${metrics.total_realized_profit:.2f}")
                    print(f"   📊 Win Rate: {metrics.win_rate:.1f}%")
                    print(f"   🔄 Multiplier: {metrics.current_multiplier:.2f}x")
                    print(f"   ⏱️  24h Profit: ${metrics.recent_24h_profit:.2f}")
                    
                    if status['alerts']:
                        print(f"   🚨 Alerts: {', '.join(status['alerts'])}")
                    print()
                    
            except Exception as e:
                print(f"   ❌ Error monitoring client {client_id}: {e}")
        
        print("📈 **OVERALL PERFORMANCE**")
        print(f"   Total Realized Profit: ${total_profit:.2f}")
        print(f"   Total Volume Traded: ${total_volume:,.2f}")
        print(f"   Overall Profit Margin: {(total_profit/total_volume*100):.3f}%" if total_volume > 0 else "   No volume data")


# Usage example for integration
async def example_usage():
    """Example of how to integrate with your existing system"""
    
    # Initialize enhanced monitoring
    monitor = PerformanceMonitor()
    
    # Get performance for a specific client
    client_performance = await monitor.monitor_client_performance(485825055)  # Your test client
    
    if 'error' not in client_performance:
        metrics = client_performance['metrics']
        print(f"Client Profit: ${metrics.total_realized_profit:.2f}")
        print(f"Current Multiplier: {metrics.current_multiplier:.2f}x")
        print(f"Win Rate: {metrics.win_rate:.1f}%")
        
        # Check if adjustments needed
        fifo_tracker = FIFOProfitTracker()
        should_adjust, reason = monitor.should_adjust_grid(metrics)
        if should_adjust:
            print(f"⚠️ Recommendation: {reason}")
    
    # Generate detailed report
    fifo_tracker = FIFOProfitTracker()
    report = fifo_tracker.generate_performance_report(485825055)
    print(report)


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
