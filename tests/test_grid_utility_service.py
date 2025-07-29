# tests/test_grid_utility_service.py
"""
Comprehensive test suite for GridUtilityService
Tests all utility functions for grid trading operations
"""

import asyncio
import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.grid_utils import GridUtilityService, create_grid_utility
from services.grid_utils import quick_round_price, quick_round_quantity


class TestGridUtilityService(unittest.TestCase):
    """Test cases for GridUtilityService class"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock Binance client for testing
        self.mock_client = Mock()
        self.service = GridUtilityService(self.mock_client)
        
        # Test data
        self.test_symbol = "ADAUSDT"
        self.test_price = 0.3456789
        self.test_quantity = 123.456789
        
        # Mock exchange info response
        self.mock_exchange_info = {
            "symbols": [
                {
                    "symbol": "ADAUSDT",
                    "status": "TRADING",
                    "filters": [
                        {
                            "filterType": "PRICE_FILTER",
                            "tickSize": "0.0001"
                        },
                        {
                            "filterType": "LOT_SIZE",
                            "stepSize": "0.1",
                            "minQty": "0.1"
                        },
                        {
                            "filterType": "MIN_NOTIONAL",
                            "minNotional": "5.0"
                        }
                    ]
                }
            ]
        }

    def test_init_without_client(self):
        """Test initialization without Binance client"""
        service = GridUtilityService()
        self.assertIsNone(service.binance_client)
        self.assertIsInstance(service.logger, logging.Logger)
        self.assertIsInstance(service._exchange_info_cache, dict)

    def test_init_with_client(self):
        """Test initialization with Binance client"""
        service = GridUtilityService(self.mock_client)
        self.assertEqual(service.binance_client, self.mock_client)

    # ========================================
    # PRICE AND QUANTITY VALIDATION TESTS
    # ========================================

    def test_round_to_tick_size_normal(self):
        """Test normal tick size rounding"""
        # Test cases: (price, tick_size, expected)
        test_cases = [
            (0.3456789, 0.0001, 0.3457),
            (1.234567, 0.01, 1.23),
            (1.235, 0.01, 1.24),  # Round up
            (10.555, 0.1, 10.6),
            (100.0, 1.0, 100.0),
        ]
        
        for price, tick_size, expected in test_cases:
            with self.subTest(price=price, tick_size=tick_size):
                result = self.service.round_to_tick_size(price, tick_size)
                self.assertAlmostEqual(result, expected, places=8)

    def test_round_to_tick_size_edge_cases(self):
        """Test tick size rounding edge cases"""
        # Zero tick size should fallback
        result = self.service.round_to_tick_size(1.234567, 0)
        self.assertEqual(result, 1.234567)
        
        # Negative tick size should fallback
        result = self.service.round_to_tick_size(1.234567, -0.01)
        self.assertEqual(result, 1.234567)
        
        # Very small price should not round to zero
        result = self.service.round_to_tick_size(0.0001, 0.01)
        self.assertEqual(result, 0.01)  # Should be minimum tick

    def test_round_to_tick_size_error_handling(self):
        """Test tick size rounding with invalid inputs"""
        # Test with invalid price (should handle gracefully)
        with patch.object(self.service.logger, 'error') as mock_log:
            result = self.service.round_to_tick_size(float('inf'), 0.01)
            self.assertTrue(mock_log.called)
            # Should return a reasonable fallback
            self.assertTrue(isinstance(result, float))

    def test_make_valid_price(self):
        """Test price validation and formatting"""
        test_cases = [
            (0.3456789, 0.0001, 4, 0.3457),
            (1.234567, 0.01, 2, 1.23),
            (100.555, 0.1, 1, 100.6),
        ]
        
        for price, tick_size, precision, expected in test_cases:
            with self.subTest(price=price, tick_size=tick_size):
                result = self.service.make_valid_price(price, tick_size, precision)
                self.assertAlmostEqual(result, expected, places=precision)

    def test_make_valid_quantity(self):
        """Test quantity validation and formatting"""
        test_cases = [
            (123.456, 0.1, 1, 0.1, 123.5),  # Normal case
            (0.05, 0.1, 1, 0.1, 0.1),       # Below minimum
            (99.99, 1.0, 0, 1.0, 100.0),    # Round to step
        ]
        
        for quantity, step_size, precision, min_qty, expected in test_cases:
            with self.subTest(quantity=quantity, step_size=step_size):
                result = self.service.make_valid_quantity(
                    quantity, step_size, precision, min_qty
                )
                self.assertAlmostEqual(result, expected, places=precision)

    def test_make_valid_quantity_minimum_enforcement(self):
        """Test that minimum quantity is enforced"""
        result = self.service.make_valid_quantity(
            quantity=0.05,    # Very small
            step_size=0.1,
            precision=1,
            min_qty=0.5       # Larger minimum
        )
        self.assertEqual(result, 0.5)

    def test_get_precision_from_step(self):
        """Test precision calculation from step size"""
        test_cases = [
            (0.1, 1),
            (0.01, 2),
            (0.001, 3),
            (0.0001, 4),
            (0.00000001, 8),
            (1.0, 0),
            (10.0, 0),
        ]
        
        for step_size, expected_precision in test_cases:
            with self.subTest(step_size=step_size):
                result = self.service.get_precision_from_step(step_size)
                self.assertEqual(result, expected_precision)

    def test_get_precision_from_step_error_handling(self):
        """Test precision calculation error handling"""
        # Should return safe fallback for invalid input
        result = self.service.get_precision_from_step(float('inf'))
        self.assertEqual(result, 8)

    # ========================================
    # EXCHANGE RULES AND API TESTS
    # ========================================

    @patch('asyncio.iscoroutinefunction')
    def test_get_exchange_rules_simple_success(self, mock_iscoroutine):
        """Test successful exchange rules retrieval"""
        mock_iscoroutine.return_value = False
        self.mock_client.get_exchange_info.return_value = self.mock_exchange_info
        
        # Create new event loop for async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.service.get_exchange_rules_simple("ADAUSDT")
            )
            
            self.assertEqual(result["symbol"], "ADAUSDT")
            self.assertEqual(result["tick_size"], 0.0001)
            self.assertEqual(result["step_size"], 0.1)
            self.assertEqual(result["min_qty"], 0.1)
            self.assertEqual(result["min_notional"], 5.0)
            self.assertEqual(result["price_precision"], 4)
            self.assertEqual(result["quantity_precision"], 1)
            
        finally:
            loop.close()

    def test_get_exchange_rules_simple_cached(self):
        """Test that exchange rules are cached"""
        # Pre-populate cache
        cached_rules = {
            "symbol": "ADAUSDT",
            "tick_size": 0.0001,
            "step_size": 0.1,
        }
        self.service._exchange_info_cache["ADAUSDT"] = cached_rules
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.service.get_exchange_rules_simple("ADAUSDT")
            )
            
            # Should return cached result without calling API
            self.assertEqual(result, cached_rules)
            self.mock_client.get_exchange_info.assert_not_called()
            
        finally:
            loop.close()

    def test_get_exchange_rules_simple_no_client(self):
        """Test exchange rules without Binance client"""
        service = GridUtilityService()  # No client
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                service.get_exchange_rules_simple("ADAUSDT")
            )
            
            # Should return fallback rules
            self.assertEqual(result["symbol"], "ADAUSDT")
            self.assertEqual(result["tick_size"], 0.0001)
            self.assertEqual(result["step_size"], 0.1)
            
        finally:
            loop.close()

    def test_get_exchange_rules_simple_api_error(self):
        """Test exchange rules when API fails"""
        self.mock_client.get_exchange_info.side_effect = Exception("API Error")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.service.get_exchange_rules_simple("ADAUSDT")
            )
            
            # Should return fallback rules
            self.assertEqual(result["symbol"], "ADAUSDT")
            self.assertIn("tick_size", result)
            
        finally:
            loop.close()

    def test_parse_symbol_rules(self):
        """Test symbol rules parsing"""
        symbol_info = self.mock_exchange_info["symbols"][0]
        result = self.service._parse_symbol_rules(symbol_info)
        
        self.assertEqual(result["symbol"], "ADAUSDT")
        self.assertEqual(result["status"], "TRADING")
        self.assertEqual(result["tick_size"], 0.0001)
        self.assertEqual(result["step_size"], 0.1)
        self.assertEqual(result["min_qty"], 0.1)
        self.assertEqual(result["min_notional"], 5.0)

    def test_get_fallback_rules_known_symbols(self):
        """Test fallback rules for known symbols"""
        known_symbols = ["ADAUSDT", "ETHUSDT", "SOLUSDT"]
        
        for symbol in known_symbols:
            with self.subTest(symbol=symbol):
                result = self.service._get_fallback_rules(symbol)
                self.assertEqual(result["symbol"], symbol)
                self.assertIn("tick_size", result)
                self.assertIn("step_size", result)
                self.assertEqual(result["status"], "TRADING")

    def test_get_fallback_rules_unknown_symbol(self):
        """Test fallback rules for unknown symbols"""
        result = self.service._get_fallback_rules("UNKNOWNUSDT")
        
        self.assertEqual(result["symbol"], "UNKNOWNUSDT")
        self.assertEqual(result["tick_size"], 0.00000001)
        self.assertEqual(result["step_size"], 0.00000001)
        self.assertEqual(result["price_precision"], 8)
        self.assertEqual(result["quantity_precision"], 8)

    # ========================================
    # SYMBOL-SPECIFIC PRECISION TESTS
    # ========================================

    def test_get_symbol_precision_info_ada(self):
        """Test forced precision for ADA"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.service.get_symbol_precision_info("ADAUSDT")
            )
            
            # Should return forced ADA precision
            self.assertEqual(result["price_precision"], 4)
            self.assertEqual(result["quantity_precision"], 1)
            self.assertEqual(result["tick_size"], 0.0001)
            self.assertEqual(result["step_size"], 0.1)
            
        finally:
            loop.close()

    def test_get_symbol_precision_info_eth(self):
        """Test forced precision for ETH"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.service.get_symbol_precision_info("ETHUSDT")
            )
            
            # Should return forced ETH precision
            self.assertEqual(result["price_precision"], 2)
            self.assertEqual(result["quantity_precision"], 5)
            
        finally:
            loop.close()

    def test_get_symbol_precision_info_sol(self):
        """Test forced precision for SOL"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.service.get_symbol_precision_info("SOLUSDT")
            )
            
            # Should return forced SOL precision
            self.assertEqual(result["price_precision"], 3)
            self.assertEqual(result["quantity_precision"], 2)
            
        finally:
            loop.close()

    # ========================================
    # FORMATTING UTILITIES TESTS
    # ========================================

    def test_format_price_string(self):
        """Test price string formatting"""
        test_cases = [
            (0.3457, 4, "0.3457"),
            (1.2300, 4, "1.23"),
            (100.0, 2, "100.00"),
            (0.1000, 4, "0.1"),
            (123, 0, "123"),
        ]
        
        for price, precision, expected in test_cases:
            with self.subTest(price=price, precision=precision):
                result = self.service.format_price_string(price, precision)
                self.assertEqual(result, expected)

    def test_format_quantity_string(self):
        """Test quantity string formatting"""
        test_cases = [
            (123.5, 1, "123.5"),
            (100.0, 2, "100.0"),
            (0.1000, 4, "0.1"),
            (1000, 0, "1000"),
        ]
        
        for quantity, precision, expected in test_cases:
            with self.subTest(quantity=quantity, precision=precision):
                result = self.service.format_quantity_string(quantity, precision)
                self.assertEqual(result, expected)

    # ========================================
    # VALIDATION UTILITIES TESTS
    # ========================================

    def test_validate_order_params_success(self):
        """Test successful order parameter validation"""
        rules = {
            "tick_size": 0.0001,
            "step_size": 0.1,
            "min_qty": 0.1,
            "min_notional": 5.0,
            "price_precision": 4,
            "quantity_precision": 1,
        }
        
        result = self.service.validate_order_params(
            symbol="ADAUSDT",
            quantity=100.0,
            price=0.3456,
            rules=rules
        )
        
        self.assertTrue(result["valid"])
        self.assertAlmostEqual(result["valid_price"], 0.3456, places=4)
        self.assertAlmostEqual(result["valid_quantity"], 100.0, places=1)
        self.assertGreaterEqual(result["notional_value"], rules["min_notional"])

    def test_validate_order_params_adjust_quantity(self):
        """Test order validation with quantity adjustment for min notional"""
        rules = {
            "tick_size": 0.0001,
            "step_size": 0.1,
            "min_qty": 0.1,
            "min_notional": 10.0,  # Higher minimum
            "price_precision": 4,
            "quantity_precision": 1,
        }
        
        result = self.service.validate_order_params(
            symbol="ADAUSDT",
            quantity=1.0,      # Small quantity
            price=0.5000,      # Low price -> low notional
            rules=rules
        )
        
        self.assertTrue(result["valid"])
        # Quantity should be adjusted to meet min notional
        expected_min_qty = rules["min_notional"] / 0.5000  # 20.0
        self.assertGreaterEqual(result["valid_quantity"], expected_min_qty)
        self.assertGreaterEqual(result["notional_value"], rules["min_notional"])

    def test_validate_order_params_error_handling(self):
        """Test order validation error handling"""
        rules = {
            "tick_size": 0.0001,
            "step_size": 0.1,
            "min_qty": 0.1,
            "min_notional": 5.0,
            "price_precision": 4,
            "quantity_precision": 1,
        }
        
        # Test with invalid inputs that might cause exceptions
        result = self.service.validate_order_params(
            symbol="ADAUSDT",
            quantity=float('inf'),  # Invalid quantity
            price=0.3456,
            rules=rules
        )
        
        self.assertFalse(result["valid"])
        self.assertIn("error", result)

    # ========================================
    # CACHE MANAGEMENT TESTS
    # ========================================

    def test_clear_exchange_cache(self):
        """Test cache clearing"""
        # Add something to cache
        self.service._exchange_info_cache["TESTUSDT"] = {"test": "data"}
        
        # Clear cache
        self.service.clear_exchange_cache()
        
        # Cache should be empty
        self.assertEqual(len(self.service._exchange_info_cache), 0)

    def test_get_cached_symbols(self):
        """Test getting cached symbols list"""
        # Add test data to cache
        test_symbols = ["ADAUSDT", "ETHUSDT", "SOLUSDT"]
        for symbol in test_symbols:
            self.service._exchange_info_cache[symbol] = {"test": "data"}
        
        result = self.service.get_cached_symbols()
        
        self.assertEqual(set(result), set(test_symbols))


# ========================================
# STANDALONE FUNCTION TESTS
# ========================================

class TestStandaloneFunctions(unittest.TestCase):
    """Test standalone utility functions"""

    def test_create_grid_utility_without_client(self):
        """Test utility creation without client"""
        service = create_grid_utility()
        self.assertIsInstance(service, GridUtilityService)
        self.assertIsNone(service.binance_client)

    def test_create_grid_utility_with_client(self):
        """Test utility creation with client"""
        mock_client = Mock()
        service = create_grid_utility(mock_client)
        self.assertIsInstance(service, GridUtilityService)
        self.assertEqual(service.binance_client, mock_client)

    def test_quick_round_price(self):
        """Test quick price rounding function"""
        test_cases = [
            (0.3456, 0.01, 0.35),
            (1.234, 0.1, 1.2),
            (100.555, 1.0, 101.0),
        ]
        
        for price, tick_size, expected in test_cases:
            with self.subTest(price=price, tick_size=tick_size):
                result = quick_round_price(price, tick_size)
                self.assertAlmostEqual(result, expected, places=6)

    def test_quick_round_price_default_tick(self):
        """Test quick price rounding with default tick size"""
        result = quick_round_price(1.234567)  # Default tick_size=0.01
        self.assertAlmostEqual(result, 1.23, places=2)

    def test_quick_round_price_invalid_tick(self):
        """Test quick price rounding with invalid tick size"""
        result = quick_round_price(1.234567, 0)  # Invalid tick size
        self.assertAlmostEqual(result, 1.234567, places=6)

    def test_quick_round_quantity(self):
        """Test quick quantity rounding function"""
        test_cases = [
            (123.456, 0.1, 0.1, 123.5),
            (0.05, 0.1, 0.1, 0.1),     # Below minimum
            (99.9, 1.0, 1.0, 100.0),
        ]
        
        for quantity, step_size, min_qty, expected in test_cases:
            with self.subTest(quantity=quantity, step_size=step_size):
                result = quick_round_quantity(quantity, step_size, min_qty)
                self.assertAlmostEqual(result, expected, places=6)

    def test_quick_round_quantity_defaults(self):
        """Test quick quantity rounding with defaults"""
        result = quick_round_quantity(123.456)  # Default step=0.1, min=0.1
        self.assertAlmostEqual(result, 123.5, places=1)

    def test_quick_round_quantity_invalid_step(self):
        """Test quick quantity rounding with invalid step size"""
        result = quick_round_quantity(123.456, 0, 0.1)  # Invalid step
        self.assertEqual(result, 123.456)  # Should return max of input and min


# ========================================
# INTEGRATION TESTS
# ========================================

class TestGridUtilityIntegration(unittest.TestCase):
    """Integration tests for GridUtilityService"""

    def setUp(self):
        """Set up integration test fixtures"""
        self.mock_client = Mock()
        self.service = GridUtilityService(self.mock_client)

    def test_full_order_validation_workflow(self):
        """Test complete order validation workflow"""
        # Mock exchange info for ADAUSDT
        self.mock_client.get_exchange_info.return_value = {
            "symbols": [
                {
                    "symbol": "ADAUSDT",
                    "status": "TRADING",
                    "filters": [
                        {"filterType": "PRICE_FILTER", "tickSize": "0.0001"},
                        {"filterType": "LOT_SIZE", "stepSize": "0.1", "minQty": "0.1"},
                        {"filterType": "MIN_NOTIONAL", "minNotional": "5.0"}
                    ]
                }
            ]
        }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Step 1: Get exchange rules
            rules = loop.run_until_complete(
                self.service.get_exchange_rules_simple("ADAUSDT")
            )
            
            # Step 2: Validate order parameters
            validation_result = self.service.validate_order_params(
                symbol="ADAUSDT",
                quantity=50.0,
                price=0.3456789,
                rules=rules
            )
            
            # Verify complete workflow
            self.assertTrue(validation_result["valid"])
            self.assertEqual(validation_result["valid_price"], 0.3457)
            self.assertEqual(validation_result["valid_quantity"], 50.0)
            self.assertIn("price_string", validation_result)
            self.assertIn("quantity_string", validation_result)
            
        finally:
            loop.close()

    def test_error_recovery_workflow(self):
        """Test error recovery in full workflow"""
        # Simulate API failure
        self.mock_client.get_exchange_info.side_effect = Exception("API Error")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Should fallback to hardcoded rules
            rules = loop.run_until_complete(
                self.service.get_exchange_rules_simple("ADAUSDT")
            )
            
            # Should still work with fallback rules
            validation_result = self.service.validate_order_params(
                symbol="ADAUSDT",
                quantity=50.0,
                price=0.3456789,
                rules=rules
            )
            
            self.assertTrue(validation_result["valid"])
            
        finally:
            loop.close()


# ========================================
# PERFORMANCE TESTS
# ========================================

class TestGridUtilityPerformance(unittest.TestCase):
    """Performance tests for GridUtilityService"""

    def setUp(self):
        """Set up performance test fixtures"""
        self.service = GridUtilityService()

    def test_precision_calculation_performance(self):
        """Test performance of precision calculations"""
        import time
        
        test_steps = [0.1, 0.01, 0.001, 0.0001, 0.00001] * 1000
        
        start_time = time.time()
        for step in test_steps:
            self.service.get_precision_from_step(step)
        end_time = time.time()
        
        # Should complete quickly (under 1 second for 5000 operations)
        self.assertLess(end_time - start_time, 1.0)

    def test_price_rounding_performance(self):
        """Test performance of price rounding"""
        import time
        
        test_prices = [i * 0.001234 for i in range(1000)]
        tick_size = 0.0001
        
        start_time = time.time()
        for price in test_prices:
            self.service.round_to_tick_size(price, tick_size)
        end_time = time.time()
        
        # Should complete quickly
        self.assertLess(end_time - start_time, 0.5)

    def test_cache_performance(self):
        """Test cache lookup performance"""
        import time
        
        # Pre-populate cache
        for i in range(100):
            symbol = f"TEST{i}USDT"
            self.service._exchange_info_cache[symbol] = {"test": "data"}
        
        start_time = time.time()
        for i in range(1000):
            symbol = f"TEST{i % 100}USDT"
            # Simulate cache lookup
            _ = symbol in self.service._exchange_info_cache
        end_time = time.time()
        
        # Cache lookups should be very fast
        self.assertLess(end_time - start_time, 0.1)


# ========================================
# TEST RUNNER
# ========================================

if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestGridUtilityService,
        TestStandaloneFunctions,
        TestGridUtilityIntegration,
        TestGridUtilityPerformance
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print("GRID UTILITY SERVICE TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Exit with appropriate code
    exit_code = 0 if (len(result.failures) + len(result.errors)) == 0 else 1
    exit(exit_code)
