#!/usr/bin/env python3
"""
Quick Grid Utility Test Runner
Simple validation of GridUtilityService functionality
"""

import sys
import asyncio
import time
from pathlib import Path
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from services.grid_utility_service import GridUtilityService, create_grid_utility
    from services.grid_utility_service import quick_round_price, quick_round_quantity
except ImportError as e:
    print(f"❌ Failed to import GridUtilityService: {e}")
    print("Make sure the services directory is in your project root")
    sys.exit(1)


class QuickGridUtilityTester:
    """Quick tester for GridUtilityService core functionality"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []

    def test(self, test_name: str, test_func):
        """Run a single test with error handling"""
        try:
            print(f"⏳ Testing {test_name}...", end=" ")
            start_time = time.time()
            
            result = test_func()
            
            # Handle async functions
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)
            
            end_time = time.time()
            
            if result:
                print(f"✅ PASS ({end_time - start_time:.3f}s)")
                self.tests_passed += 1
            else:
                print(f"❌ FAIL ({end_time - start_time:.3f}s)")
                self.tests_failed += 1
                self.errors.append(f"{test_name}: Test returned False")
        
        except Exception as e:
            duration = time.time() - start_time
            print(f"🚨 ERROR ({duration:.3f}s)")
            self.tests_failed += 1
            self.errors.append(f"{test_name}: {str(e)}")
            print(f"    Details: {str(e)[:80]}...")

    def test_basic_initialization(self):
        """Test 1: Basic service initialization"""
        try:
            # Test without client
            service1 = GridUtilityService()
            if service1.binance_client is not None:
                return False
            
            # Test with mock client
            mock_client = Mock()
            service2 = GridUtilityService(mock_client)
            if service2.binance_client != mock_client:
                return False
            
            # Test convenience function
            service3 = create_grid_utility()
            if not isinstance(service3, GridUtilityService):
                return False
            
            return True
        except Exception:
            return False

    def test_price_rounding(self):
        """Test 2: Price and quantity rounding"""
        try:
            service = GridUtilityService()
            
            # Test tick size rounding
            price_tests = [
                (0.3456789, 0.0001, 0.3457),
                (1.235, 0.01, 1.24),
                (100.555, 0.1, 100.6),
            ]
            
            for price, tick_size, expected in price_tests:
                result = service.round_to_tick_size(price, tick_size)
                if abs(result - expected) > 0.000001:
                    return False
            
            # Test quantity rounding
            qty_tests = [
                (123.456, 0.1, 1, 0.1, 123.5),
                (0.05, 0.1, 1, 0.1, 0.1),  # Below minimum
            ]
            
            for qty, step, precision, min_qty, expected in qty_tests:
                result = service.make_valid_quantity(qty, step, precision, min_qty)
                if abs(result - expected) > 0.01:
                    return False
            
            return True
        except Exception:
            return False

    def test_precision_calculation(self):
        """Test 3: Precision calculation from step sizes"""
        try:
            service = GridUtilityService()
            
            precision_tests = [
                (0.1, 1),
                (0.01, 2),
                (0.001, 3),
                (0.0001, 4),
                (1.0, 0),
            ]
            
            for step_size, expected_precision in precision_tests:
                result = service.get_precision_from_step(step_size)
                if result != expected_precision:
                    return False
            
            return True
        except Exception:
            return False

    def test_standalone_functions(self):
        """Test 4: Standalone utility functions"""
        try:
            # Test quick_round_price
            price_result = quick_round_price(1.234567, 0.01)
            if abs(price_result - 1.23) > 0.001:
                return False
            
            # Test quick_round_quantity
            qty_result = quick_round_quantity(123.456, 0.1, 0.1)
            if abs(qty_result - 123.5) > 0.01:
                return False
            
            # Test with defaults
            default_price = quick_round_price(1.234567)  # Default tick 0.01
            if abs(default_price - 1.23) > 0.001:
                return False
            
            return True
        except Exception:
            return False

    def test_fallback_rules(self):
        """Test 5: Fallback exchange rules"""
        try:
            service = GridUtilityService()  # No client
            
            # Test known symbols
            known_symbols = ["ADAUSDT", "ETHUSDT", "SOLUSDT"]
            
            for symbol in known_symbols:
                rules = service._get_fallback_rules(symbol)
                
                # Check required fields
                required_fields = [
                    "symbol", "tick_size", "step_size", "min_qty",
                    "min_notional", "price_precision", "quantity_precision"
                ]
                
                for field in required_fields:
                    if field not in rules:
                        return False
                
                # Check values are reasonable
                if rules["tick_size"] <= 0 or rules["step_size"] <= 0:
                    return False
            
            # Test unknown symbol (should use generic fallback)
            unknown_rules = service._get_fallback_rules("UNKNOWNUSDT")
            if unknown_rules["tick_size"] != 0.00000001:
                return False
            
            return True
        except Exception:
            return False

    async def test_exchange_rules_async(self):
        """Test 6: Async exchange rules (with mocked client)"""
        try:
            # Create mock client
            mock_client = Mock()
            mock_client.get_exchange_info.return_value = {
                "symbols": [
                    {
                        "symbol": "TESTUSDT",
                        "status": "TRADING",
                        "filters": [
                            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                            {"filterType": "LOT_SIZE", "stepSize": "0.1", "minQty": "0.1"},
                            {"filterType": "MIN_NOTIONAL", "minNotional": "10.0"}
                        ]
                    }
                ]
            }
            
            service = GridUtilityService(mock_client)
            
            # Test async rules retrieval
            rules = await service.get_exchange_rules_simple("TESTUSDT")
            
            # Verify parsed rules
            expected_rules = {
                "symbol": "TESTUSDT",
                "tick_size": 0.01,
                "step_size": 0.1,
                "min_qty": 0.1,
                "min_notional": 10.0,
                "price_precision": 2,
                "quantity_precision": 1,
            }
            
            for key, expected_value in expected_rules.items():
                if rules.get(key) != expected_value:
                    return False
            
            return True
        except Exception:
            return False

    def test_order_validation(self):
        """Test 7: Complete order parameter validation"""
        try:
            service = GridUtilityService()
            
            # Test rules for validation
            rules = {
                "tick_size": 0.0001,
                "step_size": 0.1,
                "min_qty": 0.1,
                "min_notional": 5.0,
                "price_precision": 4,
                "quantity_precision": 1,
            }
            
            # Test valid order
            result = service.validate_order_params(
                symbol="TESTUSDT",
                quantity=50.0,
                price=0.3456789,
                rules=rules
            )
            
            if not result["valid"]:
                return False
            
            # Check formatted values
            if abs(result["valid_price"] - 0.3457) > 0.0001:
                return False
            
            if abs(result["valid_quantity"] - 50.0) > 0.1:
                return False
            
            # Check notional value
            expected_notional = result["valid_price"] * result["valid_quantity"]
            if abs(result["notional_value"] - expected_notional) > 0.01:
                return False
            
            # Test minimum notional adjustment
            small_order = service.validate_order_params(
                symbol="TESTUSDT",
                quantity=1.0,
                price=0.1,  # Very low price
                rules=rules
            )
            
            if not small_order["valid"]:
                return False
            
            # Should adjust quantity to meet minimum notional
            if small_order["notional_value"] < rules["min_notional"]:
                return False
            
            return True
        except Exception:
            return False

    def test_string_formatting(self):
        """Test 8: Price and quantity string formatting"""
        try:
            service = GridUtilityService()
            
            # Test price formatting
            price_tests = [
                (0.3457, 4, "0.3457"),
                (1.2300, 4, "1.23"),
                (100.0, 2, "100.00"),
                (123, 0, "123"),
            ]
            
            for price, precision, expected in price_tests:
                result = service.format_price_string(price, precision)
                if result != expected:
                    return False
            
            # Test quantity formatting
            qty_tests = [
                (123.5, 1, "123.5"),
                (100.0, 2, "100.0"),
                (1000, 0, "1000"),
            ]
            
            for qty, precision, expected in qty_tests:
                result = service.format_quantity_string(qty, precision)
                if result != expected:
                    return False
            
            return True
        except Exception:
            return False

    def test_cache_operations(self):
        """Test 9: Cache management"""
        try:
            service = GridUtilityService()
            
            # Add test data to cache
            test_data = {"test": "data", "symbol": "TESTUSDT"}
            service._exchange_info_cache["TESTUSDT"] = test_data
            service._exchange_info_cache["ETHUSDT"] = {"symbol": "ETHUSDT"}
            
            # Test cache retrieval
            cached_symbols = service.get_cached_symbols()
            if set(cached_symbols) != {"TESTUSDT", "ETHUSDT"}:
                return False
            
            # Test cache clearing
            service.clear_exchange_cache()
            if len(service._exchange_info_cache) != 0:
                return False
            
            if len(service.get_cached_symbols()) != 0:
                return False
            
            return True
        except Exception:
            return False

    async def test_symbol_precision_overrides(self):
        """Test 10: Symbol-specific precision overrides"""
        try:
            service = GridUtilityService()
            
            # Test forced overrides for known symbols
            override_tests = [
                ("ADAUSDT", 4, 1),  # price_precision, quantity_precision
                ("ETHUSDT", 2, 5),
                ("SOLUSDT", 3, 2),
            ]
            
            for symbol, expected_price_prec, expected_qty_prec in override_tests:
                precision_info = await service.get_symbol_precision_info(symbol)
                
                if precision_info["price_precision"] != expected_price_prec:
                    return False
                
                if precision_info["quantity_precision"] != expected_qty_prec:
                    return False
            
            return True
        except Exception:
            return False

    def run_all_tests(self):
        """Run all quick tests"""
        print("🚀 GRID UTILITY SERVICE - QUICK TEST SUITE")
        print("=" * 50)
        print("Testing core functionality of GridUtilityService...")
        print()

        # Define tests in logical order
        tests = [
            ("Basic Initialization", self.test_basic_initialization),
            ("Price & Quantity Rounding", self.test_price_rounding),
            ("Precision Calculation", self.test_precision_calculation),
            ("Standalone Functions", self.test_standalone_functions),
            ("Fallback Exchange Rules", self.test_fallback_rules),
            ("Async Exchange Rules", self.test_exchange_rules_async),
            ("Order Parameter Validation", self.test_order_validation),
            ("String Formatting", self.test_string_formatting),
            ("Cache Operations", self.test_cache_operations),
            ("Symbol Precision Overrides", self.test_symbol_precision_overrides),
        ]

        # Run all tests
        for test_name, test_func in tests:
            self.test(test_name, test_func)

        # Print summary
        self.print_summary()
        
        return self.tests_failed == 0

    def print_summary(self):
        """Print test results summary"""
        print()
        print("=" * 50)
        print("📊 GRID UTILITY TEST RESULTS")
        print("=" * 50)
        
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {self.tests_passed}/{total_tests}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            print()
            print("🎉 ALL TESTS PASSED!")
            print("✅ GridUtilityService is working correctly")
            print()
            print("🔧 WHAT WAS TESTED:")
            print("   ✓ Service initialization and setup")
            print("   ✓ Price and quantity rounding algorithms")
            print("   ✓ Precision calculations from step sizes")
            print("   ✓ Standalone utility functions")
            print("   ✓ Exchange rules fallback system")
            print("   ✓ Async API integration (mocked)")
            print("   ✓ Order parameter validation")
            print("   ✓ String formatting for Binance API")
            print("   ✓ Cache management operations")
            print("   ✓ Symbol-specific precision overrides")
            print()
            print("🚀 READY FOR INTEGRATION:")
            print("   1. Import GridUtilityService in your grid managers")
            print("   2. Use validate_order_params() before placing orders")
            print("   3. Use get_exchange_rules_simple() for symbol info")
            print("   4. Use convenience functions for quick operations")
        else:
            print()
            print("⚠️  ISSUES FOUND")
            print("❌ Fix these issues before using in production:")
            print()
            
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
            
            print()
            print("🔧 TROUBLESHOOTING TIPS:")
            print("   1. Check import paths are correct")
            print("   2. Verify all required dependencies are installed")
            print("   3. Check for syntax errors in grid_utility_service.py")
            print("   4. Run individual test functions to isolate issues")


def main():
    """Main test runner function"""
    try:
        tester = QuickGridUtilityTester()
        success = tester.run_all_tests()
        
        if success:
            print("\n🎯 NEXT STEPS:")
            print("   1. Run the full test suite: python test_grid_utility_service.py")
            print("   2. Integrate GridUtilityService into your grid managers")
            print("   3. Test with real Binance API calls")
            return 0
        else:
            print("\n🔧 FIX ISSUES AND RE-RUN TESTS")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
