#!/usr/bin/env python3
"""
Diagnose String Formatting Issues
Let's see exactly what's happening with the formatting methods
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


def diagnose_formatting_methods():
    """Diagnose what's actually happening with formatting methods"""
    print("🔍 DIAGNOSING FORMATTING METHODS")
    print("=" * 50)
    
    service = GridUtilityService()
    
    # Check if methods exist
    has_price_format = hasattr(service, 'format_price_string')
    has_qty_format = hasattr(service, 'format_quantity_string')
    
    print(f"✓ format_price_string exists: {has_price_format}")
    print(f"✓ format_quantity_string exists: {has_qty_format}")
    
    if not has_price_format:
        print("❌ format_price_string method is missing!")
        return False
    
    if not has_qty_format:
        print("❌ format_quantity_string method is missing!")
        return False
    
    print("\n🧪 TESTING PRICE FORMATTING:")
    print("-" * 30)
    
    # Test price formatting with detailed output
    price_tests = [
        (0.3457, 4),
        (1.2300, 4),
        (100.0, 2),
        (123, 0),
    ]
    
    for i, (price, precision) in enumerate(price_tests, 1):
        print(f"\nTest {i}: format_price_string({price}, {precision})")
        
        try:
            result = service.format_price_string(price, precision)
            print(f"  ✓ Returned: '{result}' (type: {type(result)})")
            
            # Check if it's a string
            if not isinstance(result, str):
                print(f"  ❌ Expected string, got {type(result)}")
                return False
            
            # Check if it can be parsed as float
            try:
                parsed = float(result)
                print(f"  ✓ Parsed as float: {parsed}")
                
                # Check tolerance
                tolerance = 10 ** (-precision) if precision > 0 else 1
                diff = abs(parsed - price)
                print(f"  ✓ Difference: {diff}, Tolerance: {tolerance}")
                
                if diff > tolerance:
                    print(f"  ❌ Difference {diff} exceeds tolerance {tolerance}")
                    return False
                else:
                    print(f"  ✓ Within tolerance")
                    
            except ValueError as e:
                print(f"  ❌ Cannot parse as float: {e}")
                return False
                
        except Exception as e:
            print(f"  ❌ Exception calling method: {e}")
            return False
    
    print("\n🧪 TESTING QUANTITY FORMATTING:")
    print("-" * 30)
    
    # Test quantity formatting with detailed output
    qty_tests = [
        (123.5, 1),
        (100.0, 2),
        (1000, 0),
    ]
    
    for i, (qty, precision) in enumerate(qty_tests, 1):
        print(f"\nTest {i}: format_quantity_string({qty}, {precision})")
        
        try:
            result = service.format_quantity_string(qty, precision)
            print(f"  ✓ Returned: '{result}' (type: {type(result)})")
            
            # Check if it's a string
            if not isinstance(result, str):
                print(f"  ❌ Expected string, got {type(result)}")
                return False
            
            # Check if it can be parsed as float
            try:
                parsed = float(result)
                print(f"  ✓ Parsed as float: {parsed}")
                
                # Check tolerance
                tolerance = 10 ** (-precision) if precision > 0 else 1
                diff = abs(parsed - qty)
                print(f"  ✓ Difference: {diff}, Tolerance: {tolerance}")
                
                if diff > tolerance:
                    print(f"  ❌ Difference {diff} exceeds tolerance {tolerance}")
                    return False
                else:
                    print(f"  ✓ Within tolerance")
                    
            except ValueError as e:
                print(f"  ❌ Cannot parse as float: {e}")
                return False
                
        except Exception as e:
            print(f"  ❌ Exception calling method: {e}")
            return False
    
    print("\n✅ All formatting tests passed!")
    return True


def check_method_signatures():
    """Check the actual method signatures"""
    print("\n🔍 CHECKING METHOD SIGNATURES:")
    print("-" * 30)
    
    service = GridUtilityService()
    
    import inspect
    
    try:
        sig = inspect.signature(service.format_price_string)
        print(f"format_price_string{sig}")
    except Exception as e:
        print(f"Could not get format_price_string signature: {e}")
    
    try:
        sig = inspect.signature(service.format_quantity_string)
        print(f"format_quantity_string{sig}")
    except Exception as e:
        print(f"Could not get format_quantity_string signature: {e}")


def test_edge_cases():
    """Test edge cases that might cause issues"""
    print("\n🧪 TESTING EDGE CASES:")
    print("-" * 30)
    
    service = GridUtilityService()
    
    edge_cases = [
        ("Zero price", 0.0, 2),
        ("Very small price", 0.0001, 4),
        ("Large price", 12345.67, 2),
        ("Negative precision", 1.23, -1),  # This might cause issues
        ("Large precision", 1.23, 10),
    ]
    
    for test_name, price, precision in edge_cases:
        print(f"\n{test_name}: format_price_string({price}, {precision})")
        
        try:
            result = service.format_price_string(price, precision)
            print(f"  ✓ Success: '{result}'")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            # This might be the issue - let's see what exceptions occur


def main():
    """Main diagnostic function"""
    print("🚀 GRID UTILITY FORMATTING DIAGNOSTIC")
    print("=" * 50)
    
    # Check method signatures first
    check_method_signatures()
    
    # Test edge cases to see what breaks
    test_edge_cases()
    
    # Run detailed diagnosis
    success = diagnose_formatting_methods()
    
    if success:
        print("\n🎉 DIAGNOSIS COMPLETE - NO ISSUES FOUND")
        print("The formatting methods appear to be working correctly.")
        print("The test failure might be due to a different issue.")
    else:
        print("\n❌ DIAGNOSIS FOUND ISSUES")
        print("The formatting methods have problems that need to be fixed.")
    
    return success


if __name__ == "__main__":
    main()
