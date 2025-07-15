#!/usr/bin/env python3
"""
Test FIFO Implementation for GridTrader Pro
Quick test script to verify FIFO tracking works with your current data
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Test the FIFO system with a simplified version first
def test_fifo_simple(client_id: int = 485825055):
    """Test FIFO calculation with your current client data"""
    
    print("🧪 **TESTING FIFO PROFIT CALCULATION**")
    print("=" * 50)
    print(f"Testing with Client ID: {client_id}")
    print()
    
    try:
        # Connect to your database
        db_path = "data/gridtrader_clients.db"
        
        # Check if database exists
        if not Path(db_path).exists():
            print("❌ Database not found. Make sure bot has been running.")
            return
        
        with sqlite3.connect(db_path) as conn:
            # Get all trades for the client
            cursor = conn.execute("""
                SELECT executed_at, symbol, side, quantity, price, total_value
                FROM trades 
                WHERE client_id = ?
                ORDER BY executed_at ASC
            """, (client_id,))
            
            trades = cursor.fetchall()
            
            if not trades:
                print(f"❌ No trades found for client {client_id}")
                print("Make sure the client has some trading history.")
                return
            
            print(f"📊 Found {len(trades)} trades")
            print()
            
            # Simple FIFO calculation
            buy_queue = []  # Queue of buy orders (FIFO)
            total_profit = 0.0
            completed_cycles = 0
            winning_trades = 0
            
            print("🔄 **PROCESSING TRADES (FIFO)**")
            print("-" * 40)
            
            for trade in trades:
                timestamp, symbol, side, quantity, price, total_value = trade
                
                print(f"{timestamp[:19]} | {symbol:8} | {side:4} | {quantity:8.3f} @ ${price:8.4f}")
                
                if side == 'BUY':
                    # Add to buy queue
                    buy_queue.append({
                        'symbol': symbol,
                        'quantity': quantity,
                        'price': price,
                        'timestamp': timestamp
                    })
                    
                elif side == 'SELL':
                    # Match with oldest buys (FIFO)
                    remaining_sell = quantity
                    
                    while remaining_sell > 0 and buy_queue:
                        oldest_buy = buy_queue[0]
                        
                        if oldest_buy['symbol'] != symbol:
                            break  # Different symbol
                        
                        # How much to match
                        match_qty = min(remaining_sell, oldest_buy['quantity'])
                        
                        # Calculate profit for this match
                        buy_cost = match_qty * oldest_buy['price']
                        sell_revenue = match_qty * price
                        profit = sell_revenue - buy_cost
                        
                        total_profit += profit
                        completed_cycles += 1
                        
                        if profit > 0:
                            winning_trades += 1
                        
                        print(f"   💰 MATCH: {match_qty:.3f} {symbol} | Buy @${oldest_buy['price']:.4f} → Sell @${price:.4f} = ${profit:.2f}")
                        
                        # Update quantities
                        remaining_sell -= match_qty
                        oldest_buy['quantity'] -= match_qty
                        
                        # Remove buy if fully consumed
                        if oldest_buy['quantity'] <= 0:
                            buy_queue.pop(0)
            
            print()
            print("📈 **FIFO RESULTS**")
            print("-" * 30)
            print(f"Total Trades:           {len(trades)}")
            print(f"Completed Cycles:       {completed_cycles}")
            print(f"Winning Cycles:         {winning_trades}")
            print(f"Win Rate:              {(winning_trades/completed_cycles*100):.1f}%" if completed_cycles > 0 else "Win Rate: N/A")
            print(f"Total Realized Profit:  ${total_profit:.2f}")
            print(f"Avg Profit/Cycle:      ${(total_profit/completed_cycles):.2f}" if completed_cycles > 0 else "Avg Profit/Cycle: N/A")
            
            # Remaining positions
            if buy_queue:
                remaining_value = sum(pos['quantity'] * pos['price'] for pos in buy_queue)
                print(f"Remaining Positions:    ${remaining_value:.2f} (unrealized)")
            
            print()
            
            # Calculate compound multiplier
            base_order_size = 50.0
            if total_profit >= 100:  # Minimum threshold
                multiplier = 1.0 + (total_profit * 0.5 / base_order_size)  # 50% reinvestment
                multiplier = min(multiplier, 3.0)  # Cap at 3x
                new_order_size = base_order_size * multiplier
                
                print("🚀 **COMPOUND SYSTEM**")
                print("-" * 25)
                print(f"Current Profit:         ${total_profit:.2f}")
                print(f"Multiplier:            {multiplier:.2f}x")
                print(f"New Order Size:        ${new_order_size:.2f}")
                print(f"Status:                {'ACTIVE' if multiplier > 1.0 else 'INACTIVE'}")
            else:
                print("🔄 **COMPOUND SYSTEM**")
                print("-" * 25)
                print(f"Current Profit:         ${total_profit:.2f}")
                print(f"Threshold:             $100.00")
                print(f"Status:                INACTIVE (need ${100-total_profit:.2f} more)")
            
            print()
            print("✅ **FIFO TEST COMPLETED**")
            
            # Compare with simple calculation
            cursor = conn.execute("""
                SELECT 
                    SUM(CASE WHEN side = 'SELL' THEN total_value ELSE 0 END) as sell_total,
                    SUM(CASE WHEN side = 'BUY' THEN total_value ELSE 0 END) as buy_total
                FROM trades WHERE client_id = ?
            """, (client_id,))
            
            row = cursor.fetchone()
            simple_profit = (row[0] or 0) - (row[1] or 0)
            
            print("🆚 **COMPARISON**")
            print("-" * 20)
            print(f"Simple Method:     ${simple_profit:.2f}")
            print(f"FIFO Method:       ${total_profit:.2f}")
            print(f"Difference:        ${abs(total_profit - simple_profit):.2f}")
            print(f"FIFO is more accurate for tax and accounting purposes!")
            
    except Exception as e:
        print(f"❌ Error testing FIFO: {e}")
        import traceback
        traceback.print_exc()


def generate_integration_instructions():
    """Generate step-by-step integration instructions"""
    
    print("\n🔧 **INTEGRATION INSTRUCTIONS**")
    print("=" * 50)
    
    print("""
1️⃣ **Create Analytics Directory:**
   mkdir -p analytics
   touch analytics/__init__.py

2️⃣ **Add FIFO Tracker Files:**
   - Copy the FIFOProfitTracker code to: analytics/fifo_profit_tracker.py
   - Copy the integration code to: integration/fifo_integration.py

3️⃣ **Update Your TradeRepository:**
   Replace in repositories/trade_repository.py:
   
   ```python
   from integration.fifo_integration import EnhancedTradeRepository
   
   # Use EnhancedTradeRepository instead of TradeRepository
   ```

4️⃣ **Update Grid Orchestrator:**
   In services/grid_orchestrator.py, replace trade logging:
   
   ```python
   # OLD:
   self.trade_repo.log_trade_execution(...)
   
   # NEW:
   self.trade_repo.log_trade_execution_with_fifo(...)
   ```

5️⃣ **Update Monitoring Dashboard:**
   In monitoring_dashboard.py:
   
   ```python
   from integration.fifo_integration import EnhancedMonitoringDashboard
   
   dashboard = EnhancedMonitoringDashboard()
   ```

6️⃣ **Update Main Handler:**
   In main.py:
   
   ```python
   from integration.fifo_integration import EnhancedClientHandler
   
   self.handler = EnhancedClientHandler(self.grid_orchestrator)
   ```

✅ **Benefits After Integration:**
   - Accurate FIFO profit calculation
   - Tax-compliant accounting
   - Real-time compound multiplier updates
   - Enhanced performance monitoring
   - Professional profit tracking
""")


def quick_performance_check():
    """Quick performance check for all clients"""
    
    print("\n📊 **QUICK PERFORMANCE OVERVIEW**")
    print("=" * 40)
    
    try:
        db_path = "data/gridtrader_clients.db"
        
        with sqlite3.connect(db_path) as conn:
            # Get all clients with trades
            cursor = conn.execute("""
                SELECT client_id, COUNT(*) as trade_count,
                       SUM(CASE WHEN side = 'SELL' THEN total_value ELSE -total_value END) as simple_profit
                FROM trades 
                GROUP BY client_id
                ORDER BY trade_count DESC
            """)
            
            client_stats = cursor.fetchall()
            
            if not client_stats:
                print("❌ No trading data found")
                return
            
            print(f"Found {len(client_stats)} clients with trading activity:")
            print()
            
            total_profit = 0
            for client_id, trade_count, simple_profit in client_stats:
                total_profit += simple_profit or 0
                status = "🟢" if simple_profit > 0 else "🔴"
                print(f"{status} Client {client_id}: {trade_count} trades, ${simple_profit:.2f} profit")
            
            print()
            print(f"💰 Total Simple Profit: ${total_profit:.2f}")
            print("📝 Note: FIFO calculation will be more accurate")
            
    except Exception as e:
        print(f"❌ Error checking performance: {e}")


if __name__ == "__main__":
    print("🤖 **GRIDTRADER PRO - FIFO TESTING TOOL**")
    print("=" * 50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Quick overview first
    quick_performance_check()
    
    # Test FIFO with your client
    test_fifo_simple()
    
    # Show integration instructions
    generate_integration_instructions()
    
    print("\n🎯 **NEXT STEPS:**")
    print("1. Review the FIFO results above")
    print("2. Follow integration instructions")
    print("3. Test with your live trading data")
    print("4. Enjoy accurate profit tracking!")
    print()
    print("🚀 Your bot will have professional-grade accounting!")
