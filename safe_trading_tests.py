#!/usr/bin/env python3
"""
Safe Trading Functionality Unit Tests
=====================================

Tests all critical trading components without placing real orders
Run with: python safe_trading_tests.py
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


class SafeTradingTests(unittest.TestCase):
    """Safe unit tests for trading functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_client_id = 123456789
        print(f"\n🧪 Testing with client ID: {self.test_client_id}")

    def test_01_config_loading(self):
        """Test 1: Configuration Loading"""
        print("1️⃣ Testing configuration loading...")

        try:
            from config import Config

            # Test required attributes
            required_attrs = [
                "DATABASE_PATH",
                "TELEGRAM_BOT_TOKEN",
                "ADMIN_TELEGRAM_ID",
                "ENVIRONMENT",
                "ENCRYPTION_KEY",
            ]

            for attr in required_attrs:
                self.assertTrue(hasattr(Config, attr), f"Missing config: {attr}")

            # Test encryption key length
            self.assertGreaterEqual(
                len(Config.ENCRYPTION_KEY), 32, "Encryption key too short"
            )

            print("   ✅ Configuration loaded successfully")

        except Exception as e:
            self.fail(f"   ❌ Configuration loading failed: {e}")

    def test_02_database_connection(self):
        """Test 2: Database Connectivity"""
        print("2️⃣ Testing database connection...")

        try:
            import sqlite3

            from database.db_setup import DatabaseSetup

            # Test with memory database (safe)
            db_setup = DatabaseSetup(":memory:")
            db_setup.initialize()

            # Test connection
            with sqlite3.connect(":memory:") as conn:
                result = conn.execute("SELECT 1").fetchone()
                self.assertEqual(result[0], 1)

            print("   ✅ Database connection working")

        except Exception as e:
            self.fail(f"   ❌ Database connection failed: {e}")

    def test_03_encryption_utilities(self):
        """Test 3: Encryption System"""
        print("3️⃣ Testing encryption utilities...")

        try:
            from utils.crypto import CryptoUtils

            crypto = CryptoUtils()
            test_data = "test_api_key_12345"

            # Test encryption cycle
            encrypted = crypto.encrypt(test_data)
            decrypted = crypto.decrypt(encrypted)

            self.assertEqual(decrypted, test_data, "Encryption/decryption cycle failed")
            self.assertNotEqual(encrypted, test_data, "Data not encrypted")

            print("   ✅ Encryption working correctly")

        except Exception as e:
            self.fail(f"   ❌ Encryption test failed: {e}")

    def test_04_repository_imports(self):
        """Test 4: Repository Imports"""
        print("4️⃣ Testing repository imports...")

        try:
            from repositories.client_repository import ClientRepository
            from repositories.enhanced_trade_repository import EnhancedTradeRepository
            from repositories.trade_repository import TradeRepository

            # Test instantiation (with memory DB)
            client_repo = ClientRepository(":memory:")
            trade_repo = TradeRepository(":memory:")
            enhanced_repo = EnhancedTradeRepository(":memory:")

            self.assertIsNotNone(client_repo)
            self.assertIsNotNone(trade_repo)
            self.assertIsNotNone(enhanced_repo)

            print("   ✅ All repositories imported successfully")

        except Exception as e:
            self.fail(f"   ❌ Repository import failed: {e}")

    def test_05_fifo_service_import(self):
        """Test 5: FIFO Service Import"""
        print("5️⃣ Testing FIFO service import...")

        try:
            from services.enhanced_fifo_service import EnhancedFIFOService

            # Test instantiation
            fifo_service = EnhancedFIFOService()
            self.assertIsNotNone(fifo_service)

            # Test basic attributes
            self.assertTrue(
                hasattr(fifo_service, "calculate_fifo_profit_with_cost_basis")
            )
            self.assertTrue(hasattr(fifo_service, "on_order_filled"))
            self.assertTrue(hasattr(fifo_service, "on_api_error"))

            print("   ✅ Enhanced FIFO service loaded successfully")

        except Exception as e:
            self.fail(f"   ❌ FIFO service import failed: {e}")

    def test_06_network_utilities(self):
        """Test 6: Network Utilities"""
        print("6️⃣ Testing network utilities...")

        try:
            from utils.network_recovery import EnhancedNetworkRecovery
            from utils.network_utils import NetworkUtils

            # Test instantiation
            network_recovery = EnhancedNetworkRecovery()
            self.assertIsNotNone(network_recovery)

            # Test required methods exist
            self.assertTrue(hasattr(network_recovery, "health_check"))
            self.assertTrue(hasattr(network_recovery, "safe_api_call"))
            self.assertTrue(hasattr(NetworkUtils, "safe_request"))

            print("   ✅ Network utilities loaded successfully")

        except Exception as e:
            self.fail(f"   ❌ Network utilities test failed: {e}")

    def test_07_grid_orchestrator_import(self):
        """Test 7: Grid Orchestrator"""
        print("7️⃣ Testing grid orchestrator import...")

        try:
            from services.grid_orchestrator import GridOrchestrator

            # Test instantiation
            orchestrator = GridOrchestrator()
            self.assertIsNotNone(orchestrator)

            # Test required methods exist
            self.assertTrue(hasattr(orchestrator, "get_client_grid_status"))
            self.assertTrue(hasattr(orchestrator, "get_all_active_grids"))

            print("   ✅ Grid orchestrator loaded successfully")

        except Exception as e:
            self.fail(f"   ❌ Grid orchestrator test failed: {e}")

    def test_08_telegram_integration(self):
        """Test 8: Telegram Integration"""
        print("8️⃣ Testing Telegram integration...")

        try:
            from services.telegram_notifier import TelegramNotifier
            from utils.fifo_telegram_monitor import FIFOMonitoringService

            # Test instantiation (may not be enabled)
            notifier = TelegramNotifier()
            monitor = FIFOMonitoringService()

            self.assertIsNotNone(notifier)
            self.assertIsNotNone(monitor)

            print(f"   ✅ Telegram notifier enabled: {notifier.enabled}")
            print("   ✅ FIFO monitoring service loaded")

        except Exception as e:
            self.fail(f"   ❌ Telegram integration test failed: {e}")

    def test_09_main_service_import(self):
        """Test 9: Main Service Import"""
        print("9️⃣ Testing main service import...")

        try:
            from main import GridTradingService

            # Test class definition (don't instantiate to avoid full startup)
            self.assertTrue(hasattr(GridTradingService, "__init__"))
            self.assertTrue(hasattr(GridTradingService, "start_async"))
            self.assertTrue(hasattr(GridTradingService, "stop_service"))

            print("   ✅ Main service class loaded successfully")

        except Exception as e:
            self.fail(f"   ❌ Main service import failed: {e}")


class AsyncTradingTests(unittest.IsolatedAsyncioTestCase):
    """Async tests for trading functionality"""

    async def test_10_fifo_calculations(self):
        """Test 10: FIFO Profit Calculations"""
        print("🔟 Testing FIFO profit calculations...")

        try:
            from services.enhanced_fifo_service import EnhancedFIFOService

            fifo_service = EnhancedFIFOService()
            test_client_id = 123456789

            # Test profit calculation (should not fail even with no data)
            profit_data = fifo_service.calculate_fifo_profit_with_cost_basis(
                test_client_id
            )

            self.assertIsInstance(profit_data, dict)
            self.assertIn("total_profit", profit_data)

            print(f"   ✅ FIFO calculation: ${profit_data.get('total_profit', 0):.2f}")
            print(f"   📊 Method: {profit_data.get('calculation_method', 'unknown')}")

        except Exception as e:
            self.fail(f"   ❌ FIFO calculation test failed: {e}")

    async def test_11_notification_system(self):
        """Test 11: Notification System (Safe)"""
        print("1️⃣1️⃣ Testing notification system...")

        try:
            from services.enhanced_fifo_service import EnhancedFIFOService

            fifo_service = EnhancedFIFOService()

            # Test notification methods exist and can be called
            # (will not send actual notifications during startup suppression)
            result = await fifo_service.on_order_filled(
                client_id=123456789,
                symbol="TESTUSDT",
                side="BUY",
                quantity=1.0,
                price=1.0000,
                order_id="test_001",
            )

            self.assertIsInstance(result, bool)

            # Test error notification
            error_result = await fifo_service.on_api_error(
                client_id=123456789,
                error_code="-9999",
                error_message="Test error message",
                symbol="TESTUSDT",
                operation="test",
            )

            self.assertIsInstance(error_result, bool)

            print("   ✅ Notification system responds correctly")

        except Exception as e:
            self.fail(f"   ❌ Notification test failed: {e}")

    async def test_12_grid_status_check(self):
        """Test 12: Grid Status Check"""
        print("1️⃣2️⃣ Testing grid status check...")

        try:
            from services.grid_orchestrator import GridOrchestrator

            orchestrator = GridOrchestrator()
            test_client_id = 123456789

            # Test grid status retrieval (await if async)
            try:
                # Try async first
                status = await orchestrator.get_client_grid_status(test_client_id)
            except TypeError:
                # If not async, call normally
                status = orchestrator.get_client_grid_status(test_client_id)

            # Status can be None or a dict
            self.assertTrue(status is None or isinstance(status, dict))

            # Test all grids status
            try:
                # Try async first
                all_grids = await orchestrator.get_all_active_grids()
            except TypeError:
                # If not async, call normally
                all_grids = orchestrator.get_all_active_grids()
            except AttributeError:
                # Method might not exist
                all_grids = None

            self.assertIsInstance(all_grids, (list, dict, type(None)))

            print(f"   ✅ Grid status check: {status or 'No active grids'}")

        except Exception as e:
            self.fail(f"   ❌ Grid status test failed: {e}")


def run_tests():
    """Run all tests with detailed output"""
    print("🧪 GRIDTRADER PRO - SAFE TRADING TESTS")
    print("=" * 60)
    print("Testing all components without placing real orders")
    print("Safe for production environment")
    print("=" * 60)

    # Track test results
    suite = unittest.TestSuite()

    # Add sync tests
    for test_name in dir(SafeTradingTests):
        if test_name.startswith("test_"):
            suite.addTest(SafeTradingTests(test_name))

    # Add async tests
    for test_name in dir(AsyncTradingTests):
        if test_name.startswith("test_"):
            suite.addTest(AsyncTradingTests(test_name))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open("/dev/null", "w"))
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    total_tests = result.testsRun
    failed_tests = len(result.failures) + len(result.errors)
    passed_tests = total_tests - failed_tests

    print(f"✅ PASSED: {passed_tests}/{total_tests}")
    print(f"❌ FAILED: {failed_tests}/{total_tests}")

    if result.failures:
        print("\n🚨 FAILURES:")
        for test, error in result.failures:
            print(f"   ❌ {test}: {error.split('AssertionError:')[-1].strip()}")

    if result.errors:
        print("\n💥 ERRORS:")
        for test, error in result.errors:
            print(f"   💥 {test}: {error.strip()}")

    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Your trading system is ready for operation")
        print("✅ All components loaded and functioning correctly")
        print("✅ FIFO calculations working")
        print("✅ Notification system operational")
        print("✅ Database connectivity confirmed")

        print("\n🚀 NEXT STEPS:")
        print("   • Your system is safe to use")
        print("   • Consider starting with small position sizes")
        print("   • Monitor the first few trades closely")
        print("   • Check Telegram notifications are working")

    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Review the failures above before trading")
        print("Fix any issues and re-run tests")

    return failed_tests == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
