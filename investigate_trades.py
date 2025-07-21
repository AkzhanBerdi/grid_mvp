# investigate_trades.py
"""
Investigate the suspicious trades from last night
"""

import sqlite3
from datetime import datetime, timedelta
from config import Config

def investigate_recent_trades():
    """Investigate trades from last night"""
    
    print("🔍 INVESTIGATING LAST NIGHT'S TRADES")
    print("=" * 60)
    
    try:
        db_path = Config.DATABASE_PATH
        
        with sqlite3.connect(db_path) as conn:
            # Get trades from last night (around 03:16-03:19)
            cursor = conn.execute("""
                SELECT 
                    id,
                    client_id,
                    symbol,
                    side,
                    quantity,
                    price,
                    total_value,
                    order_id,
                    executed_at
                FROM trades 
                WHERE executed_at LIKE '2025-07-21%'
                   OR executed_at LIKE '%03:1%'
                   OR executed_at >= datetime('now', '-12 hours')
                ORDER BY executed_at ASC
            """)
            
            suspicious_trades = cursor.fetchall()
            
            if not suspicious_trades:
                print("❌ No trades found from last night")
                
                # Check all recent trades
                cursor = conn.execute("""
                    SELECT executed_at, COUNT(*) 
                    FROM trades 
                    GROUP BY DATE(executed_at)
                    ORDER BY executed_at DESC 
                    LIMIT 5
                """)
                
                print("\n📅 Recent trade dates:")
                for date, count in cursor.fetchall():
                    print(f"   {date}: {count} trades")
                return
            
            print(f"🚨 Found {len(suspicious_trades)} trades from last night\n")
            
            # Analyze the trades
            print("📊 TRADE ANALYSIS:")
            print("-" * 60)
            print(f"{'Time':<19} {'Symbol':<8} {'Side':<4} {'Qty':<10} {'Price':<8} {'Value':<8} {'Order ID':<15}")
            print("-" * 60)
            
            ada_buys = []
            ada_sells = []
            
            for trade in suspicious_trades:
                trade_id, client_id, symbol, side, quantity, price, total_value, order_id, executed_at = trade
                
                print(f"{executed_at:<19} {symbol:<8} {side:<4} {quantity:<10.1f} ${price:<7.4f} ${total_value:<7.2f} {order_id:<15}")
                
                if symbol == "ADAUSDT":
                    if side == "BUY":
                        ada_buys.append((quantity, price, total_value, executed_at))
                    else:
                        ada_sells.append((quantity, price, total_value, executed_at))
            
            # Analyze ADA trading pattern
            print(f"\n🔵 ADA TRADING ANALYSIS:")
            print(f"   📈 Buy orders: {len(ada_buys)}")
            print(f"   📉 Sell orders: {len(ada_sells)}")
            
            if ada_buys and ada_sells:
                # Check if these are profitable cycles
                print(f"\n💰 PROFITABILITY CHECK:")
                
                for i, (buy_qty, buy_price, buy_value, buy_time) in enumerate(ada_buys):
                    if i < len(ada_sells):
                        sell_qty, sell_price, sell_value, sell_time = ada_sells[i]
                        
                        # Calculate actual profit (simplified)
                        if buy_qty > 0 and sell_qty > 0:
                            # Assume quantities are roughly matched
                            avg_qty = min(buy_qty, sell_qty)
                            profit = (sell_price - buy_price) * avg_qty
                            profit_pct = (sell_price - buy_price) / buy_price * 100
                            
                            print(f"   Cycle {i+1}: Buy ${buy_price:.4f} → Sell ${sell_price:.4f}")
                            print(f"            Profit: ${profit:.4f} ({profit_pct:.2f}%)")
            
            # Check for duplicates
            print(f"\n🔍 DUPLICATE CHECK:")
            
            # Group by time windows to find potential duplicates
            time_groups = {}
            for trade in suspicious_trades:
                executed_at = trade[8]
                minute = executed_at[:16]  # Group by minute
                
                if minute not in time_groups:
                    time_groups[minute] = []
                time_groups[minute].append(trade)
            
            duplicates_found = False
            for minute, trades in time_groups.items():
                if len(trades) > 2:  # More than 2 trades per minute is suspicious
                    print(f"   ⚠️ {minute}: {len(trades)} trades (possible duplicates)")
                    duplicates_found = True
            
            if not duplicates_found:
                print("   ✅ No obvious duplicates detected")
            
            # Test current FIFO calculation
            print(f"\n📊 CURRENT FIFO CALCULATION:")
            
            from analytics.fifo_profit_tracker import FIFOProfitCalculator
            calculator = FIFOProfitCalculator()
            
            # Test with different client IDs
            for client_id in [1000, 12345]:
                result = calculator.calculate_fifo_profit(client_id)
                trades_count = result.get('total_trades', 0)
                if trades_count > 0:
                    print(f"   Client {client_id}: ${result.get('total_profit', 0):.2f} profit, {trades_count} trades")
            
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()

def check_notification_system():
    """Check if notification system is working correctly"""
    
    print(f"\n🔔 NOTIFICATION SYSTEM CHECK:")
    print("=" * 60)
    
    try:
        # Test working integration
        from services.working_fifo_integration import WorkingFIFOIntegration
        
        print("✅ WorkingFIFOIntegration: Available")
        
        # Test with a client that has trades
        integration = WorkingFIFOIntegration(1000)
        
        # Check what profit it would show
        performance = integration.calculator.calculate_fifo_profit(1000)
        print(f"   Current calculation: ${performance.get('total_profit', 0):.2f} profit")
        
        # The negative profits in notifications suggest the calculation is wrong
        # or there's a bug in the integration
        
    except Exception as e:
        print(f"❌ Notification system check failed: {e}")

def recommended_actions():
    """Provide recommended actions based on investigation"""
    
    print(f"\n📋 RECOMMENDED ACTIONS:")
    print("=" * 60)
    
    print("1. 🛑 **IMMEDIATE**: Stop the bot until we fix the issues")
    print("   - Negative profits indicate serious calculation error")
    print("   - Rapid trading could be draining your balance")
    
    print("\n2. 🔍 **INVESTIGATE**: Check actual Binance trades")
    print("   - Login to Binance and check your actual trade history")
    print("   - Compare with the database trades")
    print("   - Verify if trades were actually profitable")
    
    print("\n3. 🔧 **FIX FIFO**: The profit calculation is broken")
    print("   - Negative profits from completed cycles is impossible")
    print("   - Need to implement the true_profit_fix.py we created earlier")
    
    print("\n4. 📱 **FIX NOTIFICATIONS**: Level numbers are wrong")
    print("   - Level -1 and 99 are not valid grid levels")
    print("   - Should be 1, 2, 3, 4, 5")
    
    print("\n5. ⏱️ **CHECK TIMING**: 12 trades in 3 minutes is suspicious")
    print("   - Could be duplicate notifications")
    print("   - Could be runaway trading loop")
    
    print("\n6. 💰 **VERIFY BALANCE**: Check your actual Binance balance")
    print("   - Compare with what the system thinks you have")
    print("   - Look for discrepancies")

if __name__ == "__main__":
    investigate_recent_trades()
    check_notification_system()
    recommended_actions()
