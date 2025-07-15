#!/usr/bin/env python3
"""
Client Data Cleanup & Calculation Refactor Script
Fixes corrupted data and rebuilds performance calculations
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from repositories.client_repository import ClientRepository
from repositories.trade_repository import TradeRepository


class ClientDataCleanup:
    """Clean and rebuild client data and calculations"""
    
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()
        
    def cleanup_client_data(self, client_id: int, correct_capital: float = 500.0):
        """Clean and fix client data"""
        print(f"🧹 Cleaning client data for {client_id}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 1. Fix client capital
                conn.execute("""
                    UPDATE clients 
                    SET total_capital = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """, (correct_capital, client_id))
                
                print(f"✅ Updated capital to ${correct_capital}")
                
                # 2. Reset grid status to active
                conn.execute("""
                    UPDATE clients 
                    SET grid_status = 'active', updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """, (client_id,))
                
                print(f"✅ Reset grid status to active")
                
                # 3. Clean corrupted performance data
                conn.execute("""
                    DELETE FROM client_events 
                    WHERE client_id = ? AND event_type LIKE '%performance%'
                """, (client_id,))
                
                print(f"✅ Cleaned corrupted performance events")
                
        except Exception as e:
            print(f"❌ Error cleaning client data: {e}")
            return False
            
        return True
    
    def rebuild_trade_calculations(self, client_id: int):
        """Rebuild trade calculations with proper profit logic"""
        print(f"🔄 Rebuilding trade calculations for {client_id}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all trades for the client
                cursor = conn.execute("""
                    SELECT id, symbol, side, quantity, price, total_value, executed_at
                    FROM trades 
                    WHERE client_id = ?
                    ORDER BY executed_at ASC
                """, (client_id,))
                
                trades = cursor.fetchall()
                print(f"📊 Found {len(trades)} trades to analyze")
                
                if not trades:
                    print("ℹ️  No trades found")
                    return True
                
                # Calculate proper profits
                self._recalculate_trade_profits(conn, trades, client_id)
                
        except Exception as e:
            print(f"❌ Error rebuilding calculations: {e}")
            return False
            
        return True
    
    def _recalculate_trade_profits(self, conn, trades, client_id):
        """Recalculate trade profits with proper grid trading logic"""
        
        # Grid trading profit calculation:
        # Profit = (Sell Price - Buy Price) * Quantity - Fees
        # For grid trading, we need to match buy/sell pairs
        
        symbol_positions = {}  # Track positions per symbol
        total_profit = 0.0
        profitable_trades = 0
        total_trades = len(trades)
        
        print(f"🔍 Analyzing {total_trades} trades...")
        
        for trade_id, symbol, side, quantity, price, total_value, executed_at in trades:
            
            if symbol not in symbol_positions:
                symbol_positions[symbol] = {
                    'quantity': 0.0,
                    'cost_basis': 0.0,
                    'realized_profit': 0.0
                }
            
            position = symbol_positions[symbol]
            
            # Estimate trading fees (0.1% per trade)
            fee = total_value * 0.001
            
            if side == 'BUY':
                # Add to position
                position['quantity'] += quantity
                position['cost_basis'] += (total_value + fee)
                trade_profit = -fee  # Fee cost only
                
            else:  # SELL
                if position['quantity'] > 0:
                    # Calculate profit on sold portion
                    avg_cost_per_unit = position['cost_basis'] / position['quantity']
                    sell_quantity = min(quantity, position['quantity'])
                    
                    cost_of_sold = avg_cost_per_unit * sell_quantity
                    revenue = (price * sell_quantity) - fee
                    trade_profit = revenue - cost_of_sold
                    
                    # Update position
                    position['quantity'] -= sell_quantity
                    if position['quantity'] > 0:
                        position['cost_basis'] -= cost_of_sold
                    else:
                        position['cost_basis'] = 0.0
                        
                    position['realized_profit'] += trade_profit
                    
                    if trade_profit > 0:
                        profitable_trades += 1
                        
                else:
                    # Selling without position (shouldn't happen in grid)
                    trade_profit = -(total_value + fee)
            
            total_profit += trade_profit
            
            # Update trade record with calculated profit
            conn.execute("""
                UPDATE trades 
                SET profit = ?
                WHERE id = ?
            """, (trade_profit, trade_id))
        
        # Calculate win rate
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        print(f"📈 Recalculated Performance:")
        print(f"   Total Profit: ${total_profit:.2f}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Avg Profit/Trade: ${avg_profit:.2f}")
        print(f"   Profitable Trades: {profitable_trades}/{total_trades}")
        
        # Update client performance cache
        conn.execute("""
            INSERT OR REPLACE INTO client_events (
                client_id, event_type, event_data, timestamp
            ) VALUES (?, 'performance_update', ?, CURRENT_TIMESTAMP)
        """, (client_id, f"total_profit:{total_profit},win_rate:{win_rate},avg_profit:{avg_profit}"))
        
        return total_profit, win_rate, avg_profit
    
    def fix_grid_state_tracking(self, client_id: int):
        """Fix grid state tracking issues"""
        print(f"🔧 Fixing grid state tracking for {client_id}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create grid instances record if missing
                conn.execute("""
                    INSERT OR REPLACE INTO grid_instances (
                        client_id, symbol, status, started_at, total_trades, total_profit
                    ) VALUES (?, 'ADAUSDT', 'active', CURRENT_TIMESTAMP, 0, 0.0)
                """, (client_id,))
                
                # Update grid orders status
                conn.execute("""
                    UPDATE grid_orders 
                    SET status = 'ACTIVE'
                    WHERE client_id = ? AND status = 'PLACED'
                """, (client_id,))
                
                print(f"✅ Fixed grid state tracking")
                
        except Exception as e:
            print(f"❌ Error fixing grid state: {e}")
            return False
            
        return True
    
    def verify_binance_synchronization(self, client_id: int):
        """Provide instructions to verify Binance synchronization"""
        print(f"🔍 Binance Synchronization Check for {client_id}")
        print("=" * 50)
        print("Please manually verify the following in Binance:")
        print("")
        print("1. Go to Binance → Spot Trading → Open Orders")
        print("   Expected: ~26 orders for ADAUSDT")
        print("   Should see: Mix of buy orders (below current price)")
        print("               Mix of sell orders (above current price)")
        print("")
        print("2. Check Order Sizes:")
        print("   Base Grid: ~$17.50 per order (smaller orders)")  
        print("   Enhanced Grid: ~$20.31 per order (larger orders)")
        print("")
        print("3. Price Distribution:")
        print("   Buy orders: Spread below current ADA price")
        print("   Sell orders: Spread above current ADA price")
        print("")
        print("4. If orders are missing:")
        print("   - Bot may need restart to reconnect")
        print("   - Grid may need to be stopped and restarted")
        print("")
        
    def generate_health_report(self, client_id: int):
        """Generate comprehensive health report"""
        print(f"📋 Health Report for Client {client_id}")
        print("=" * 50)
        
        try:
            # Get current client data
            client = self.client_repo.get_client(client_id)
            if not client:
                print("❌ Client not found in database")
                return
                
            print(f"👤 Client: {client.first_name}")
            print(f"💰 Capital: ${client.total_capital}")
            print(f"📊 Grid Status: {client.grid_status.value}")
            print(f"⚙️ Trading Pairs: {', '.join(client.trading_pairs)}")
            print("")
            
            # Get trade statistics
            stats = self.trade_repo.get_client_trade_stats(client_id)
            print(f"📈 Trading Statistics:")
            print(f"   Total Trades: {stats['total_trades']}")
            print(f"   Total Profit: ${stats['total_profit']:.2f}")
            print(f"   Win Rate: {stats['win_rate']:.1f}%")
            print(f"   Avg Profit/Trade: ${stats['total_profit']/max(1, stats['total_trades']):.2f}")
            print("")
            
            # Database integrity check
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM grid_orders WHERE client_id = ?
                """, (client_id,))
                grid_orders = cursor.fetchone()[0]
                
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM trades WHERE client_id = ?
                """, (client_id,))
                total_trades = cursor.fetchone()[0]
                
                print(f"🗄️  Database Status:")
                print(f"   Grid Orders: {grid_orders}")
                print(f"   Trade Records: {total_trades}")
                print("")
                
        except Exception as e:
            print(f"❌ Error generating health report: {e}")
    
    def full_cleanup(self, client_id: int, capital: float = 500.0):
        """Perform full cleanup and rebuild"""
        print("🚀 Starting Full Client Data Cleanup")
        print("=" * 60)
        
        # Step 1: Clean client data
        if not self.cleanup_client_data(client_id, capital):
            print("❌ Failed at client data cleanup")
            return False
            
        # Step 2: Rebuild calculations
        if not self.rebuild_trade_calculations(client_id):
            print("❌ Failed at calculation rebuild")
            return False
            
        # Step 3: Fix grid state
        if not self.fix_grid_state_tracking(client_id):
            print("❌ Failed at grid state fix")
            return False
            
        # Step 4: Generate health report
        self.generate_health_report(client_id)
        
        # Step 5: Binance verification instructions
        self.verify_binance_synchronization(client_id)
        
        print("")
        print("✅ Full cleanup completed successfully!")
        print("")
        print("🔄 Next Steps:")
        print("1. Restart the bot: python main.py")
        print("2. Verify dashboard shows correct capital ($500)")
        print("3. Check grid status shows: Base ✅ Enhanced ✅")
        print("4. Verify 26 orders in Binance")
        print("5. Monitor for positive performance metrics")
        print("")
        
        return True


def main():
    """Main cleanup function"""
    client_id = 485825055  # Your client ID
    correct_capital = 500.0  # Correct capital amount
    
    cleanup = ClientDataCleanup()
    
    print("🧹 GridTrader Pro - Client Data Cleanup")
    print("=" * 50)
    print(f"Client ID: {client_id}")
    print(f"Correct Capital: ${correct_capital}")
    print("")
    
    # Perform full cleanup
    success = cleanup.full_cleanup(client_id, correct_capital)
    
    if success:
        print("🎉 Cleanup completed successfully!")
        print("Your bot should now show correct data and calculations.")
    else:
        print("❌ Cleanup failed. Check error messages above.")
        
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
