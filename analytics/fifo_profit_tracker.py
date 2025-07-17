# analytics/fifo_profit_tracker.py
"""
Enhanced FIFO-based profit tracking and performance monitoring
Integrates with your existing GridTrader Pro setup
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import sqlite3

from dataclasses import dataclass

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


class FIFOProfitCalculator:
    """Simple but effective FIFO profit calculator"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
    
    def calculate_fifo_profit(self, client_id: int) -> Dict:
        """Calculate FIFO-based profit for client"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT side, quantity, price, total_value, executed_at, symbol
                    FROM trades 
                    WHERE client_id = ?
                    ORDER BY executed_at ASC
                """, (client_id,))
                
                trades = cursor.fetchall()
                
                if not trades:
                    return {
                        'total_profit': 0.0,
                        'total_trades': 0,
                        'completed_cycles': 0,
                        'win_rate': 0.0,
                        'avg_profit_per_trade': 0.0,
                        'best_trade': 0.0,
                        'worst_trade': 0.0,
                        'total_volume': 0.0,
                        'profit_factor': 0.0,
                        'current_multiplier': 1.0,
                        'recent_24h_profit': 0.0
                    }
                
                # Simple profit calculation (enhanced FIFO can be added later)
                total_buy = sum(row[3] for row in trades if row[0] == 'BUY')
                total_sell = sum(row[3] for row in trades if row[0] == 'SELL')
                total_profit = total_sell - total_buy
                
                # Calculate basic metrics
                buy_trades = [t for t in trades if t[0] == 'BUY']
                sell_trades = [t for t in trades if t[0] == 'SELL']
                
                # Win rate calculation (simplified)
                winning_trades = len([t for t in sell_trades if len(buy_trades) > 0])
                total_completed = min(len(buy_trades), len(sell_trades))
                win_rate = (winning_trades / max(total_completed, 1)) * 100
                
                # Volume calculation
                total_volume = total_buy + total_sell
                
                # Current multiplier (simplified compound logic)
                base_profit_threshold = 25.0  # $25 per multiplier increase
                current_multiplier = 1.0 + (max(total_profit, 0) / base_profit_threshold) * 0.1
                current_multiplier = min(current_multiplier, 3.0)  # Max 3x multiplier
                
                # Recent 24h profit (simplified)
                recent_24h_profit = self.get_recent_profit(client_id, 24)
                
                return {
                    'total_profit': round(total_profit, 2),
                    'total_trades': len(trades),
                    'completed_cycles': total_completed,
                    'win_rate': round(win_rate, 1),
                    'avg_profit_per_trade': round(total_profit / max(len(trades), 1), 2),
                    'best_trade': round(max([t[3] for t in sell_trades] + [0]), 2),
                    'worst_trade': round(min([t[3] for t in buy_trades] + [0]), 2),
                    'total_volume': round(total_volume, 2),
                    'profit_factor': round(total_sell / max(total_buy, 1), 2),
                    'current_multiplier': round(current_multiplier, 2),
                    'recent_24h_profit': round(recent_24h_profit, 2)
                }
                
        except Exception as e:
            self.logger.error(f"Error calculating FIFO profit for client {client_id}: {e}")
            return {
                'total_profit': 0.0,
                'total_trades': 0,
                'completed_cycles': 0,
                'win_rate': 0.0,
                'avg_profit_per_trade': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'total_volume': 0.0,
                'profit_factor': 0.0,
                'current_multiplier': 1.0,
                'recent_24h_profit': 0.0
            }
    
    def get_recent_profit(self, client_id: int, hours: int = 24) -> float:
        """Get profit from recent hours"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT side, total_value
                    FROM trades 
                    WHERE client_id = ? 
                    AND executed_at > datetime('now', '-{} hours')
                    ORDER BY executed_at ASC
                """.format(hours), (client_id,))
                
                recent_trades = cursor.fetchall()
                
                recent_buy = sum(row[1] for row in recent_trades if row[0] == 'BUY')
                recent_sell = sum(row[1] for row in recent_trades if row[0] == 'SELL')
                
                return recent_sell - recent_buy
                
        except Exception as e:
            self.logger.error(f"Error getting recent profit: {e}")
            return 0.0
    
    def get_trade_history(self, client_id: int, limit: int = 100) -> List[Dict]:
        """Get recent trade history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT executed_at, symbol, side, quantity, price, total_value
                    FROM trades 
                    WHERE client_id = ?
                    ORDER BY executed_at DESC
                    LIMIT ?
                """, (client_id, limit))
                
                trades = []
                for row in cursor.fetchall():
                    trades.append({
                        'timestamp': row[0],
                        'symbol': row[1],
                        'side': row[2],
                        'quantity': row[3],
                        'price': row[4],
                        'total_value': row[5]
                    })
                
                return trades
                
        except Exception as e:
            self.logger.error(f"Error getting trade history: {e}")
            return []


class FIFOProfitTracker:
    """Advanced FIFO-based profit tracking with compound integration"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        self.calculator = FIFOProfitCalculator(db_path)
        
        # FIFO queues for each symbol: {symbol: deque of buy trades}
        self.buy_queues: Dict[str, deque] = defaultdict(deque)
        
        # Completed FIFO matches for profit calculation
        self.completed_matches: List[FIFOMatch] = []

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
                    trade = Trade(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        symbol=row[2],
                        side=row[3],
                        quantity=row[4],
                        price=row[5],
                        total_value=row[6]
                    )
                    trades.append(trade)
                
                return trades
                
        except Exception as e:
            self.logger.error(f"Error loading trades for client {client_id}: {e}")
            return []

    def process_fifo_matches(self, trades: List[Trade]) -> List[FIFOMatch]:
        """Process trades using FIFO methodology"""
        matches = []
        
        # Group trades by symbol
        symbol_trades = defaultdict(list)
        for trade in trades:
            symbol_trades[trade.symbol].append(trade)
        
        # Process each symbol separately
        for symbol, symbol_trade_list in symbol_trades.items():
            buy_queue = deque()
            
            for trade in symbol_trade_list:
                if trade.side == 'BUY':
                    buy_queue.append(trade)
                elif trade.side == 'SELL' and buy_queue:
                    # Match with oldest buy (FIFO)
                    while buy_queue and trade.quantity > 0:
                        buy_trade = buy_queue[0]
                        
                        if buy_trade.quantity <= trade.quantity:
                            # Full match
                            quantity_matched = buy_trade.quantity
                            profit = (trade.price - buy_trade.price) * quantity_matched
                            profit_percentage = (profit / (buy_trade.price * quantity_matched)) * 100
                            
                            match = FIFOMatch(
                                buy_trade=buy_trade,
                                sell_trade=trade,
                                quantity_matched=quantity_matched,
                                profit=profit,
                                profit_percentage=profit_percentage
                            )
                            matches.append(match)
                            
                            trade.quantity -= quantity_matched
                            buy_queue.popleft()
                        else:
                            # Partial match
                            quantity_matched = trade.quantity
                            profit = (trade.price - buy_trade.price) * quantity_matched
                            profit_percentage = (profit / (buy_trade.price * quantity_matched)) * 100
                            
                            match = FIFOMatch(
                                buy_trade=buy_trade,
                                sell_trade=trade,
                                quantity_matched=quantity_matched,
                                profit=profit,
                                profit_percentage=profit_percentage
                            )
                            matches.append(match)
                            
                            buy_trade.quantity -= quantity_matched
                            trade.quantity = 0
        
        return matches

    def calculate_performance_metrics(self, client_id: int) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        try:
            trades = self.load_client_trades(client_id)
            matches = self.process_fifo_matches(trades)
            
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
            
            # Calculate metrics from FIFO matches
            total_profit = sum(match.profit for match in matches)
            winning_matches = [m for m in matches if m.profit > 0]
            losing_matches = [m for m in matches if m.profit < 0]
            
            gross_profit = sum(m.profit for m in winning_matches)
            gross_loss = abs(sum(m.profit for m in losing_matches))
            
            win_rate = (len(winning_matches) / len(matches)) * 100
            avg_profit = total_profit / len(matches)
            best_trade = max(match.profit for match in matches)
            worst_trade = min(match.profit for match in matches)
            
            total_volume = sum(trade.total_value for trade in trades)
            profit_factor = gross_profit / max(gross_loss, 1)
            
            # Calculate compound multiplier
            base_profit_threshold = 25.0
            current_multiplier = 1.0 + (max(total_profit, 0) / base_profit_threshold) * 0.1
            current_multiplier = min(current_multiplier, 3.0)
            
            # Recent 24h profit
            recent_24h_profit = self.calculator.get_recent_profit(client_id, 24)
            
            return PerformanceMetrics(
                total_realized_profit=round(total_profit, 2),
                total_trades=len(matches),
                winning_trades=len(winning_matches),
                losing_trades=len(losing_matches),
                win_rate=round(win_rate, 1),
                average_profit_per_trade=round(avg_profit, 2),
                best_trade=round(best_trade, 2),
                worst_trade=round(worst_trade, 2),
                total_volume=round(total_volume, 2),
                profit_factor=round(profit_factor, 2),
                current_multiplier=round(current_multiplier, 2),
                recent_24h_profit=round(recent_24h_profit, 2)
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
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
