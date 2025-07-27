#!/usr/bin/env python3
"""
Test the Fixed String Formatting
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the fixed version
from services.grid_utility_service import GridUtilityService


def test_fixed_formatting():
    """Test the fixed formatting methods"""
    print("🧪 TESTING FIXED FORMATTING METHODS")
    print("=" * 40)

    service = GridUtilityService()

    print("\n📊 PRICE FORMATTING TESTS:")
    print("-" * 30)

    price_tests = [
        (0.3457, 4, "0.3457"),
        (1.2300, 4, "1.23"),
        (100.0, 2, "100.00"),
        (123, 0, "123"),
    ]

    all_price_passed = True
    for i, (price, precision, expected) in enumerate(price_tests, 1):
        result = service.format_price_string(price, precision)
        passed = result == expected
        status = "✅ PASS" if passed else "❌ FAIL"

        print(f"Test {i}: {status}")
        print(f"  format_price_string({price}, {precision})")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        print(f"  Match: {passed}")

        if not passed:
            all_price_passed = False
        print()

    print("\n📦 QUANTITY FORMATTING TESTS:")
    print("-" * 30)

    qty_tests = [
        (123.5, 1, "123.5"),
        (100.0, 2, "100.0"),
        (1000, 0, "1000"),  # This was the failing test!
    ]

    all_qty_passed = True
    for i, (qty, precision, expected) in enumerate(qty_tests, 1):
        result = service.format_quantity_string(qty, precision)
        passed = result == expected
        status = "✅ PASS" if passed else "❌ FAIL"

        print(f"Test {i}: {status}")
        print(f"  format_quantity_string({qty}, {precision})")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        print(f"  Match: {passed}")

        if not passed:
            all_qty_passed = False
        print()

    print("=" * 40)
    print("🎯 SUMMARY:")

    if all_price_passed and all_qty_passed:
        print("🎉 ALL FORMATTING TESTS PASSED!")
        print("✅ The fix resolves the formatting issue")
        print()
        print("🔧 KEY FIXES APPLIED:")
        print("   • Only strip trailing zeros AFTER decimal point")
        print("   • Never strip all zeros from whole numbers")
        print("   • Handle edge cases like negative precision")
        print("   • Preserve whole numbers like 1000 correctly")
        return True
    else:
        print("❌ Some tests still failing")
        if not all_price_passed:
            print("   • Price formatting issues remain")
        if not all_qty_passed:
            print("   • Quantity formatting issues remain")
        return False


if __name__ == "__main__":
    success = test_fixed_formatting()
    if success:
        print("\n🚀 READY TO APPLY FIX:")
        print("   1. Replace your grid_utility_service.py with the fixed version")
        print("   2. Re-run your tests")
        print("   3. All tests should now pass!")
    else:
        print("\n🔧 FIX NEEDS REFINEMENT")

    sys.exit(0 if success else 1)
