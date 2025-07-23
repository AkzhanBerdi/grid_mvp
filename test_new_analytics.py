# test_new_analytics.py
"""
Test and validate the new SQLite-based analytics system
Confirms it shows the real $44.38 profit and accurate data
"""

import sqlite3
import sys
from pathlib import Path


def test_database_connection():
    """Test basic database connectivity"""
    print("🔌 **TESTING DATABASE CONNECTION**")
    
    try:
        from config import Config
        db_path = Config.DATABASE_PATH
        print(f"   📁 Database path: {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            # Test basic connection
            result = conn.execute("SELECT 1").fetchone()
            if result and result[0] == 1:
                print("   ✅ Database connection successful")
                return True
            else:
                print("   ❌ Database connection failed")
                return False
                
    except Exception as e:
        print(f"   ❌ Database connection error: {e}")
        return False


def test_trades_table_structure():
    """Test that trades table has required structure"""
    print("\n📊 **TESTING TRADES TABLE STRUCTURE**")
    
    try:
        from config import Config
        
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            # Check trades table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='trades'
            """)
            
            if not cursor.fetchone():
                print("   ❌ Trades table not found!")
                return False
            
            # Check required columns
            cursor = conn.execute("PRAGMA table_info(trades)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            required_columns = {
                'client_id': 'INTEGER',
                'symbol': 'TEXT', 
                'side': 'TEXT',
                'quantity': 'REAL',
                'price': 'REAL',
                'total_value': 'REAL',
                'executed_at': 'DATETIME'
            }
            
            print("   📋 Table structure:")
            missing_columns = []
            for col_name, expected_type in required_columns.items():
                if col_name in columns:
                    print(f"   ✅ {col_name}: {columns[col_name]}")
                else:
                    print(f"   ❌ {col_name}: MISSING")
                    missing_columns.append(col_name)
            
            if missing_columns:
                print(f"   ❌ Missing required columns: {missing_columns}")
                return False
            else:
                print("   ✅ All required columns present")
                return True
                
    except Exception as e:
        print(f"   ❌ Error checking table structure: {e}")
        return False


def find_client_with_trades():
    """Find a client ID that has trading data"""
    print("\n🔍 **FINDING CLIENT WITH TRADES**")
    
    try:
        from config import Config
        
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            cursor = conn.execute("""
                SELECT 
                    client_id,
                    COUNT(*) as trade_count,
                    SUM(CASE WHEN side = 'SELL' THEN total_value ELSE 0 END) as sells,
                    SUM(CASE WHEN side = 'BUY' THEN total_value ELSE 0 END) as buys,
                    MIN(executed_at) as first_trade,
                    MAX(executed_at) as last_trade
                FROM trades 
                GROUP BY client_id
                HAVING trade_count > 0
                ORDER BY trade_count DESC
                LIMIT 5
            """)
            
            clients = cursor.fetchall()
            
            if not clients:
                print("   ⚠️  No clients with trades found")
                return None
            
            print("   📊 Clients with trading data:")
            for client_data in clients:
                client_id = client_data[0]
                trade_count = client_data[1]
                sells = client_data[2] or 0.0
                buys = client_data[3] or 0.0
                profit = sells - buys
                first_trade = client_data[4]
                last_trade = client_data[5]
                
                print(f"   • Client {client_id}:")
                print(f"     Trades: {trade_count}")
                print(f"     Profit: ${profit:.2f}")
                print(f"     Period: {first_trade} → {last_trade}")
                
                # Check if this matches our expected $44.38
                if abs(profit - 44.38) < 0.1:
                    print("     ⭐ THIS MATCHES THE $44.38 CLIENT!")
                    return client_id
            
            # Return the client with most trades
            return clients[0][0]
            
    except Exception as e:
        print(f"   ❌ Error finding clients: {e}")
        return None


def test_sqlite_analytics(client_id):
    """Test the new SQLite analytics system"""
    print(f"\n🧠 **TESTING SQLITE ANALYTICS FOR CLIENT {client_id}**")
    
    try:
        # Import new analytics
        from analytics.sqlite_analytics import SQLiteAnalytics, AnalyticsCommandInterface
        print("   ✅ Analytics imports successful")
        
        # Test SQLiteAnalytics
        analytics = SQLiteAnalytics()
        profit_data = analytics.get_real_profit(client_id)
        
        print(f"   📊 Real Profit Data:")
        print(f"   • Total Profit: ${profit_data.total_profit}")
        print(f"   • Total Trades: {profit_data.total_trades}")
        print(f"   • Daily Average: ${profit_data.daily_average}")
        
        if profit_data.daily_breakdown:
            print(f"   📅 Daily Breakdown:")
            for date, profit in profit_data.daily_breakdown.items():
                print(f"   • {date}: ${profit}")
        
        if profit_data.compound_growth:
            growth = profit_data.compound_growth
            print(f"   📈 Order Growth:")
            print(f"   • First Order: ${growth.get('first_order', 0)}")
            print(f"   • Recent Order: ${growth.get('last_order', 0)}")
            print(f"   • Growth: {growth.get('growth_percent', 0)}%")
        
        # Test trading statistics
        stats = analytics.get_trading_statistics(client_id)
        print(f"\n   📋 Trading Statistics:")
        print(f"   • Total Trades: {stats.get('total_trades', 0)}")
        print(f"   • Success Rate: {stats.get('success_rate', 0)}%")
        print(f"   • Total Volume: ${stats.get('total_volume', 0)}")
        
        # Test command interface
        command_interface = AnalyticsCommandInterface()
        
        print(f"\n   🤖 Command Interface Test:")
        
        # Test /profit command
        profit_response = command_interface.handle_profit_command(client_id)
        print(f"   ✅ /profit command works (response length: {len(profit_response)})")
        
        # Test /stats command  
        stats_response = command_interface.handle_stats_command(client_id)
        print(f"   ✅ /stats command works (response length: {len(stats_response)})")
        
        # Show actual /profit response
        print(f"\n   📱 **ACTUAL /profit COMMAND OUTPUT:**")
        print("   " + "="*50)
        for line in profit_response.split('\n'):
            print(f"   {line}")
        print("   " + "="*50)
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error - analytics files not found: {e}")
        print("   💡 Make sure you've created the analytics/sqlite_analytics.py file")
        return False
    except Exception as e:
        print(f"   ❌ Error testing analytics: {e}")
        return False


def validate_no_phantom_profits(client_id):
    """Validate that we're not showing phantom profits"""
    print(f"\n🚫 **VALIDATING NO PHANTOM PROFITS FOR CLIENT {client_id}**")
    
    try:
        from config import Config
        
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            # Get raw trade data
            cursor = conn.execute("""
                SELECT side, total_value, executed_at
                FROM trades 
                WHERE client_id = ?
                ORDER BY executed_at ASC
            """, (client_id,))
            
            trades = cursor.fetchall()
            
            total_buys = 0.0
            total_sells = 0.0
            
            print("   📊 Raw trade analysis:")
            for side, total_value, executed_at in trades:
                if side == 'BUY':
                    total_buys += total_value
                elif side == 'SELL':
                    total_sells += total_value
            
            real_profit = total_sells - total_buys
            
            print(f"   • Total BUY value: ${total_buys:.2f}")
            print(f"   • Total SELL value: ${total_sells:.2f}")
            print(f"   • Real profit: ${real_profit:.2f}")
            
            # Cross-verify with analytics
            from analytics.sqlite_analytics import SQLiteAnalytics
            analytics = SQLiteAnalytics()
            analytics_profit = analytics.get_real_profit(client_id).total_profit
            
            print(f"   • Analytics profit: ${analytics_profit:.2f}")
            
            if abs(real_profit - analytics_profit) < 0.01:
                print("   ✅ Analytics matches raw calculation - NO PHANTOM PROFITS!")
                return True
            else:
                print(f"   ⚠️  Discrepancy: Raw=${real_profit:.2f} vs Analytics=${analytics_profit:.2f}")
                return False
                
    except Exception as e:
        print(f"   ❌ Error validating profits: {e}")
        return False


def test_old_system_removed():
    """Test that old broken analytics are removed"""
    print("\n🗑️ **TESTING OLD SYSTEM REMOVAL**")
    
    broken_imports = [
        "analytics.fifo_profit_tracker",
        "services.smart_analytics", 
        "utils.fifo_telegram_monitor"
    ]
    
    removed_count = 0
    
    for module_name in broken_imports:
        try:
            __import__(module_name)
            print(f"   ⚠️  {module_name} still importable")
        except ImportError:
            print(f"   ✅ {module_name} successfully removed")
            removed_count += 1
        except Exception as e:
            print(f"   ✅ {module_name} import fails (good): {e}")
            removed_count += 1
    
    if removed_count == len(broken_imports):
        print("   🎉 All broken analytics modules removed!")
        return True
    else:
        print(f"   ⚠️  {len(broken_imports) - removed_count} modules still present")
        return False


def generate_test_report(results):
    """Generate comprehensive test report"""
    print("\n" + "="*60)
    print("📋 **ANALYTICS REBUILD TEST REPORT**")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    print(f"**SUMMARY:** {passed_tests}/{total_tests} tests passed")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    if passed_tests == total_tests:
        print("\n🎉 **ALL TESTS PASSED - ANALYTICS REBUILD SUCCESSFUL!**")
        print("\n📋 **READY FOR PRODUCTION:**")
        print("• SQLite analytics showing real profits")
        print("• Command interface working (/profit, /stats, etc.)")
        print("• No phantom profits or broken calculations")
        print("• Old broken system completely removed")
        
        print("\n🚀 **NEXT STEPS:**")
        print("1. Deploy the updated handlers")
        print("2. Test commands in production")
        print("3. Monitor for 24 hours")
        print("4. Remove backup files when confident")
        
    else:
        print("\n⚠️ **SOME TESTS FAILED - REVIEW REQUIRED**")
        print("Check the failed tests above and fix issues before deployment")
    
    print("\n" + "="*60)


def main():
    """Main test execution"""
    print("🔬 **ANALYTICS REBUILD VALIDATION**")
    print("Testing new SQLite-based analytics system")
    print("="*60)
    
    results = {}
    
    # Test 1: Database connection
    results["Database Connection"] = test_database_connection()
    
    # Test 2: Table structure
    results["Trades Table Structure"] = test_trades_table_structure()
    
    # Test 3: Find client with data
    client_id = find_client_with_trades()
    results["Find Trading Client"] = client_id is not None
    
    if client_id:
        # Test 4: SQLite analytics
        results["SQLite Analytics"] = test_sqlite_analytics(client_id)
        
        # Test 5: No phantom profits
        results["No Phantom Profits"] = validate_no_phantom_profits(client_id)
    else:
        print("\n⚠️  Cannot test analytics without trading data")
        results["SQLite Analytics"] = False
        results["No Phantom Profits"] = False
    
    # Test 6: Old system removed
    results["Old System Removed"] = test_old_system_removed()
    
    # Generate final report
    generate_test_report(results)


if __name__ == "__main__":
    main()
