#!/usr/bin/env python3
"""
Debug String Formatting Test
Let's see exactly what's happening with the formatting functions
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from services.grid_utility_service import GridUtilityService
except ImportError as e:
    print(f"❌ Failed to import GridUtilityService: {e}")
    sys.exit(1)


def debug_string_formatting():
    """Debug the string formatting methods"""
    print("🔍 DEBUGGING STRING FORMATTING")
    print("=" * 40)
    
    service = GridUtilityService()
    
    # Test cases from the failing test
    price_tests = [
        (0.3457, 4, "0.3457"),
        (1.2300, 4, "1.23"),
        (100.0, 2, "100.00"),
        (123, 0, "123"),
    ]
    
    print("\n📊 PRICE FORMATTING TESTS:")
    print("-" * 30)
    
    all_passed = True
    
    for i, (price, precision, expected) in enumerate(price_tests, 1):
        try:
            result = service.format_price_string(price, precision)
            passed = result == expected
            status = "✅ PASS" if passed else "❌ FAIL"
            
            print(f"Test {i}: {status}")
            print(f"  Input: price={price}, precision={precision}")
            print(f"  Expected: '{expected}'")
            print(f"  Got:      '{result}'")
            print(f"  Match: {passed}")
            
            if not passed:
                all_passed = False
                print(f"  🔍 Analysis:")
                print(f"    - Expected type: {type(expected)}")
                print(f"    - Got type: {type(result)}")
                print(f"    - Expected length: {len(expected)}")
                print(f"    - Got length: {len(result)}")
                print(f"    - Character comparison:")
                max_len = max(len(expected), len(result))
                for j in range(max_len):
                    exp_char = expected[j] if j < len(expected) else "EOF"
                    got_char = result[j] if j < len(result) else "EOF"
                    match = "✓" if exp_char == got_char else "✗"
                    print(f"      [{j}]: '{exp_char}' vs '{got_char}' {match}")
            
            print()
            
        except Exception as e:
            print(f"Test {i}: 🚨 ERROR")
            print(f"  Input: price={price}, precision={precision}")
            print(f"  Error: {e}")
            print()
            all_passed = False
    
    print("\n📦 QUANTITY FORMATTING TESTS:")
    print("-" * 30)
    
    qty_tests = [
        (123.5, 1, "123.5"),
        (100.0, 2, "100.0"),
        (1000, 0, "1000"),
    ]
    
    for i, (qty, precision, expected) in enumerate(qty_tests, 1):
        try:
            result = service.format_quantity_string(qty, precision)
            passed = result == expected
            status = "✅ PASS" if passed else "❌ FAIL"
            
            print(f"Test {i}: {status}")
            print(f"  Input: quantity={qty}, precision={precision}")
            print(f"  Expected: '{expected}'")
            print(f"  Got:      '{result}'")
            print(f"  Match: {passed}")
            
            if not passed:
                all_passed = False
                print(f"  🔍 Analysis:")
                print(f"    - Expected type: {type(expected)}")
                print(f"    - Got type: {type(result)}")
                print(f"    - Expected length: {len(expected)}")
                print(f"    - Got length: {len(result)}")
            
            print()
            
        except Exception as e:
            print(f"Test {i}: 🚨 ERROR")
            print(f"  Input: quantity={qty}, precision={precision}")
            print(f"  Error: {e}")
            print()
            all_passed = False
    
    print("\n" + "=" * 40)
    print("🎯 SUMMARY:")
    if all_passed:
        print("✅ All formatting tests passed!")
    else:
        print("❌ Some formatting tests failed")
        print("\n🔧 LIKELY ISSUES:")
        print("1. The format_price_string method might have different logic")
        print("2. The format_quantity_string method might have different logic")
        print("3. Check the implementation in grid_utility_service.py")
    
    return all_passed


def check_actual_implementation():
    """Check what the actual methods look like"""
    print("\n🔍 CHECKING ACTUAL IMPLEMENTATION")
    print("=" * 40)
    
    service = GridUtilityService()
    
    # Check if methods exist
    has_price_format = hasattr(service, 'format_price_string')
    has_qty_format = hasattr(service, 'format_quantity_string')
    
    print(f"format_price_string exists: {has_price_format}")
    print(f"format_quantity_string exists: {has_qty_format}")
    
    if has_price_format:
        print(f"format_price_string type: {type(service.format_price_string)}")
        # Try to get method signature
        import inspect
        try:
            sig = inspect.signature(service.format_price_string)
            print(f"format_price_string signature: {sig}")
        except Exception as e:
            print(f"Could not get signature: {e}")
    
    if has_qty_format:
        print(f"format_quantity_string type: {type(service.format_quantity_string)}")
        try:
            sig = inspect.signature(service.format_quantity_string)
            print(f"format_quantity_string signature: {sig}")
        except Exception as e:
            print(f"Could not get signature: {e}")
    
    # Test simple cases
    print("\n🧪 SIMPLE TEST CASES:")
    if has_price_format:
        try:
            simple_result = service.format_price_string(1.23, 2)
            print(f"format_price_string(1.23, 2) = '{simple_result}' (type: {type(simple_result)})")
        except Exception as e:
            print(f"format_price_string(1.23, 2) failed: {e}")
    
    if has_qty_format:
        try:
            simple_result = service.format_quantity_string(123.5, 1)
            print(f"format_quantity_string(123.5, 1) = '{simple_result}' (type: {type(simple_result)})")
        except Exception as e:
            print(f"format_quantity_string(123.5, 1) failed: {e}")


if __name__ == "__main__":
    check_actual_implementation()
    debug_string_formatting()
