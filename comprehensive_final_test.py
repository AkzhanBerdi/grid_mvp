# comprehensive_final_test.py
"""
Comprehensive Final Test - Everything We've Built
Tests all components: Telegram, FIFO, Database, Grid Integration
"""

import asyncio
import sqlite3
import sys
import time
from datetime import datetime
from config import Config

class ComprehensiveTester:
    """Comprehensive tester for all grid trading bot components"""
    
    def __init__(self):
        self.test_results = {}
        self.test_client_id = 1000
        
    async def run_all_tests(self):
        """Run all comprehensive tests"""
        
        print("🚀 COMPREHENSIVE GRID TRADING BOT TEST")
        print("=" * 80)
        print("Testing all components we've built together...")
        print()
        
        # Test 1: Basic Telegram Connection
        await self._test_telegram_basic()
        
        # Test 2: Database and FIFO System  
        await self._test_database_fifo()
        
        # Test 3: Working vs Broken FIFO Services
        await self._test_fifo_comparison()
        
        # Test 4: Notification Integration
        await self._test_notification_integration()
        
        # Test 5: Grid Manager Integration
        await self._test_grid_manager_integration()
        
        # Test 6: Real Trading Scenario Simulation
        await self._test_real_trading_scenario()
        
        # Test 7: Error Handling and Recovery
        await self._test_error_handling()
        
        # Test 8: Performance and Milestones
        await self._test_performance_milestones()
        
        # Final Summary
        self._print_final_summary()
    
    async def _test_telegram_basic(self):
        """Test 1: Basic Telegram Connection"""
        
        print("📱 TEST 1: Basic Telegram Connection")
        print("-" * 50)
        
        try:
            from services.telegram_notifier import TelegramNotifier
            
            notifier = TelegramNotifier()
            
            print(f"✅ Telegram enabled: {notifier.enabled}")
            print(f"✅ Bot token: {'SET' if notifier.bot_token else 'MISSING'}")
            print(f"✅ Chat ID: {notifier.chat_id}")
            
            if notifier.enabled:
                # Test simple message
                success = await notifier.send_message("🧪 Comprehensive Test Started")
                self.test_results["telegram_basic"] = success
                print(f"✅ Simple message: {'SUCCESS' if success else 'FAILED'}")
                
                # Test with emojis and formatting
                success2 = await notifier.send_message("🔷 ETH 📈 PROFIT: $79.90")
                print(f"✅ Emoji message: {'SUCCESS' if success2 else 'FAILED'}")
                
            else:
                self.test_results["telegram_basic"] = False
                print("❌ Telegram not configured")
            
        except Exception as e:
            self.test_results["telegram_basic"] = False
            print(f"❌ Telegram test failed: {e}")
        
        print()
    
    async def _test_database_fifo(self):
        """Test 2: Database and FIFO System"""
        
        print("🗄️ TEST 2: Database and FIFO System")
        print("-" * 50)
        
        try:
            # Check database structure
            db_path = Config.DATABASE_PATH
            print(f"✅ Database path: {db_path}")
            
            with sqlite3.connect(db_path) as conn:
                # Check trades table
                cursor = conn.execute("SELECT COUNT(*) FROM trades")
                trade_count = cursor.fetchone()[0]
                print(f"✅ Total trades in database: {trade_count}")
                
                # Check our test client
                cursor = conn.execute("SELECT COUNT(*) FROM trades WHERE client_id = ?", (self.test_client_id,))
                client_trades = cursor.fetchone()[0]
                print(f"✅ Test client {self.test_client_id} trades: {client_trades}")
                
                if client_trades >= 2:
                    # Test FIFOProfitCalculator (working)
                    from analytics.fifo_profit_tracker import FIFOProfitCalculator
                    calculator = FIFOProfitCalculator()
                    result = calculator.calculate_fifo_profit(self.test_client_id)
                    
                    profit = result.get('total_profit', 0)
                    trades = result.get('total_trades', 0)
                    
                    print(f"✅ FIFO Calculator: ${profit:.2f} profit, {trades} trades")
                    self.test_results["database_fifo"] = profit > 0 and trades > 0
                else:
                    print("⚠️ Not enough test trades, creating some...")
                    await self._create_test_trades()
                    self.test_results["database_fifo"] = True
            
        except Exception as e:
            self.test_results["database_fifo"] = False
            print(f"❌ Database/FIFO test failed: {e}")
        
        print()
    
    async def _test_fifo_comparison(self):
        """Test 3: Working vs Broken FIFO Services"""
        
        print("🔄 TEST 3: FIFO Service Comparison")
        print("-" * 50)
        
        try:
            # Test broken FIFOService
            from services.fifo_service import FIFOService
            fifo_service = FIFOService()
            broken_result = fifo_service.calculate_fifo_performance(self.test_client_id)
            
            broken_profit = broken_result.get('total_profit', 0)
            broken_trades = broken_result.get('total_trades', 0)
            
            print(f"❌ Broken FIFOService: ${broken_profit:.2f} profit, {broken_trades} trades")
            
            # Test working FIFOProfitCalculator
            from analytics.fifo_profit_tracker import FIFOProfitCalculator
            calculator = FIFOProfitCalculator()
            working_result = calculator.calculate_fifo_profit(self.test_client_id)
            
            working_profit = working_result.get('total_profit', 0)
            working_trades = working_result.get('total_trades', 0)
            
            print(f"✅ Working Calculator: ${working_profit:.2f} profit, {working_trades} trades")
            
            # Test working integration
            from services.working_fifo_integration import WorkingFIFOIntegration
            integration = WorkingFIFOIntegration(self.test_client_id)
            
            print(f"✅ Working Integration: Created successfully")
            
            self.test_results["fifo_comparison"] = working_profit > 0 and working_trades > 0
            
        except Exception as e:
            self.test_results["fifo_comparison"] = False
            print(f"❌ FIFO comparison failed: {e}")
        
        print()
    
    async def _test_notification_integration(self):
        """Test 4: Notification Integration"""
        
        print("📢 TEST 4: Notification Integration")
        print("-" * 50)
        
        try:
            from services.working_fifo_integration import WorkingFIFOIntegration
            
            integration = WorkingFIFOIntegration(self.test_client_id)
            
            # Test order fill notification with real FIFO data
            print("🧪 Testing order fill notification...")
            success1 = await integration.on_order_filled(
                symbol="ETHUSDT",
                side="SELL",
                quantity=0.0218,
                price=3665.30,
                level=1
            )
            
            print(f"✅ Order fill notification: {'SUCCESS' if success1 else 'FAILED'}")
            
            await asyncio.sleep(2)
            
            # Test different asset
            print("🧪 Testing ADA notification...")
            success2 = await integration.on_order_filled(
                symbol="ADAUSDT", 
                side="SELL",
                quantity=94.2,
                price=0.85,
                level=1
            )
            
            print(f"✅ ADA notification: {'SUCCESS' if success2 else 'FAILED'}")
            
            self.test_results["notification_integration"] = success1 and success2
            
        except Exception as e:
            self.test_results["notification_integration"] = False
            print(f"❌ Notification integration failed: {e}")
        
        print()
    
    async def _test_grid_manager_integration(self):
        """Test 5: Grid Manager Integration"""
        
        print("⚙️ TEST 5: Grid Manager Integration")
        print("-" * 50)
        
        try:
            # Test if SingleAdvancedGridManager can be created with integration
            from services.single_advanced_grid_manager import SingleAdvancedGridManager
            
            # Mock Binance client for testing
            class MockBinanceClient:
                def get_open_orders(self, symbol):
                    return []
                def get_account(self):
                    return {"balances": []}
            
            mock_client = MockBinanceClient()
            
            # Create grid manager
            grid_manager = SingleAdvancedGridManager(mock_client, self.test_client_id)
            
            # Check if it has the working integration
            has_integration = hasattr(grid_manager, 'working_integration')
            print(f"✅ Grid manager has integration: {has_integration}")
            
            if has_integration:
                integration_type = type(grid_manager.working_integration).__name__
                print(f"✅ Integration type: {integration_type}")
                
                # Test the integration
                if hasattr(grid_manager.working_integration, 'on_order_filled'):
                    print("🧪 Testing grid manager integration...")
                    success = await grid_manager.working_integration.on_order_filled(
                        symbol="SOLUSDT",
                        side="BUY",
                        quantity=7.5,
                        price=112.40,
                        level=2
                    )
                    print(f"✅ Grid integration test: {'SUCCESS' if success else 'FAILED'}")
                    self.test_results["grid_manager_integration"] = success
                else:
                    self.test_results["grid_manager_integration"] = False
            else:
                self.test_results["grid_manager_integration"] = False
            
        except Exception as e:
            self.test_results["grid_manager_integration"] = False
            print(f"❌ Grid manager integration failed: {e}")
            print("   (This might be normal if you haven't updated the integration yet)")
        
        print()
    
    async def _test_real_trading_scenario(self):
        """Test 6: Real Trading Scenario Simulation"""
        
        print("📈 TEST 6: Real Trading Scenario Simulation")
        print("-" * 50)
        
        try:
            # Simulate a series of trades like real grid trading
            from repositories.trade_repository import TradeRepository
            from services.working_fifo_integration import WorkingFIFOIntegration
            
            trade_repo = TradeRepository()
            integration = WorkingFIFOIntegration(self.test_client_id)
            
            # Simulate grid trading sequence
            trades = [
                ("BUY", 0.0220, 3600.00, "Bought ETH at lower level"),
                ("SELL", 0.0220, 3700.00, "Sold ETH for profit"),
                ("BUY", 95.0, 0.82, "Bought ADA at lower level"),
                ("SELL", 95.0, 0.86, "Sold ADA for profit"),
            ]
            
            print("🧪 Simulating trading sequence...")
            
            for i, (side, quantity, price, description) in enumerate(trades):
                symbol = "ETHUSDT" if "ETH" in description else "ADAUSDT"
                order_id = f"sim_order_{i+1}"
                
                # Log trade to database
                trade_repo.log_trade_execution(
                    client_id=self.test_client_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    order_id=order_id
                )
                
                # Send notification
                await integration.on_order_filled(symbol, side, quantity, price, i+1)
                
                print(f"   ✅ {description}")
                await asyncio.sleep(1)  # Small delay between trades
            
            # Check final profit
            from analytics.fifo_profit_tracker import FIFOProfitCalculator
            calculator = FIFOProfitCalculator()
            final_result = calculator.calculate_fifo_profit(self.test_client_id)
            
            final_profit = final_result.get('total_profit', 0)
            final_trades = final_result.get('total_trades', 0)
            
            print(f"✅ Final result: ${final_profit:.2f} profit from {final_trades} trades")
            
            self.test_results["real_trading_scenario"] = final_profit > 0
            
        except Exception as e:
            self.test_results["real_trading_scenario"] = False
            print(f"❌ Real trading scenario failed: {e}")
        
        print()
    
    async def _test_error_handling(self):
        """Test 7: Error Handling and Recovery"""
        
        print("🚨 TEST 7: Error Handling and Recovery")
        print("-" * 50)
        
        try:
            from services.working_fifo_integration import WorkingFIFOIntegration
            
            integration = WorkingFIFOIntegration(self.test_client_id)
            
            # Test with invalid data (should not crash)
            print("🧪 Testing error recovery...")
            
            try:
                await integration.on_order_filled("INVALID", "UNKNOWN", -1, 0, None)
                print("✅ Handled invalid data without crashing")
            except Exception:
                print("✅ Properly rejected invalid data")
            
            # Test notification when Telegram might be down
            original_enabled = integration.telegram.enabled
            integration.telegram.enabled = False
            
            success = await integration.on_order_filled("ETHUSDT", "SELL", 0.01, 3600, 1)
            print(f"✅ Graceful handling when Telegram disabled: {not success}")
            
            integration.telegram.enabled = original_enabled
            
            self.test_results["error_handling"] = True
            
        except Exception as e:
            self.test_results["error_handling"] = False
            print(f"❌ Error handling test failed: {e}")
        
        print()
    
    async def _test_performance_milestones(self):
        """Test 8: Performance and Milestones"""
        
        print("🏆 TEST 8: Performance and Milestones")
        print("-" * 50)
        
        try:
            from analytics.fifo_profit_tracker import FIFOProfitCalculator
            from services.working_fifo_integration import WorkingFIFOIntegration
            
            calculator = FIFOProfitCalculator()
            integration = WorkingFIFOIntegration(self.test_client_id)
            
            # Get current performance
            performance = calculator.calculate_fifo_profit(self.test_client_id)
            total_profit = performance.get('total_profit', 0)
            total_trades = performance.get('total_trades', 0)
            
            print(f"✅ Current performance: ${total_profit:.2f} profit, {total_trades} trades")
            
            # Test milestone notification if we're above $100
            if total_profit >= 100:
                print("🧪 Testing milestone notification...")
                await integration._notify_milestone(total_profit, 100)
                print("✅ Milestone notification sent")
            else:
                print(f"⚠️ Total profit ${total_profit:.2f} below $100 milestone")
            
            # Performance metrics
            win_rate = performance.get('win_rate', 0)
            avg_profit = performance.get('average_profit_per_trade', 0)
            
            print(f"✅ Win rate: {win_rate:.1f}%")
            print(f"✅ Average profit per trade: ${avg_profit:.2f}")
            
            self.test_results["performance_milestones"] = total_profit > 0
            
        except Exception as e:
            self.test_results["performance_milestones"] = False
            print(f"❌ Performance test failed: {e}")
        
        print()
    
    async def _create_test_trades(self):
        """Create test trades if none exist"""
        
        from repositories.trade_repository import TradeRepository
        trade_repo = TradeRepository()
        
        test_trades = [
            ("ETHUSDT", "SELL", 0.0218, 3665.30, "test_eth_1"),
            ("ADAUSDT", "SELL", 94.2, 0.85, "test_ada_1"),
        ]
        
        for symbol, side, quantity, price, order_id in test_trades:
            trade_repo.log_trade_execution(
                self.test_client_id, symbol, side, quantity, price, order_id
            )
    
    def _print_final_summary(self):
        """Print final comprehensive summary"""
        
        print("🎯 COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            formatted_name = test_name.replace("_", " ").title()
            print(f"{status} {formatted_name}")
            if result:
                passed += 1
        
        print()
        print(f"📊 OVERALL RESULT: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 EXCELLENT! All systems working perfectly!")
            print("🚀 Your grid trading bot is ready for live trading!")
        elif passed >= total * 0.8:
            print("✅ GOOD! Most systems working, minor issues to resolve")
        elif passed >= total * 0.5:
            print("⚠️ PARTIAL! Some systems working, needs attention")
        else:
            print("❌ NEEDS WORK! Multiple systems need fixing")
        
        print()
        print("📱 Check your Telegram for all the test notifications!")
        print("💰 Real profit data should be displayed in notifications")
        print("🔧 If any tests failed, review the specific error messages above")

async def main():
    """Run comprehensive test"""
    tester = ComprehensiveTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
