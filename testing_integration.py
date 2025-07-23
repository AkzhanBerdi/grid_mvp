# tests/test_pure_usdt_integration_fixed.py

import asyncio
import os
import sqlite3
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance.client import Client

from repositories.enhanced_trade_repository import EnhancedTradeRepository
from services.enhanced_fifo_service import EnhancedFIFOService
from services.pure_usdt_grid_initializer import GridInitializationOrchestrator


async def test_pure_usdt_integration():
    """Test the pure USDT grid initialization with proper components"""

    print("🧪 Testing Pure USDT Integration (Fixed)")
    print("=" * 50)

    try:
        # Use enhanced components
        enhanced_trade_repo = EnhancedTradeRepository()
        enhanced_fifo_service = EnhancedFIFOService()

        # Check schema first
        print("1️⃣ Checking database schema...")
        schema_check = enhanced_trade_repo.verify_database_schema()

        if not schema_check["schema_valid"]:
            print(f"❌ Schema invalid: {schema_check['recommendation']}")
            return False

        print("✅ Database schema is ready")

        # Create binance client (use your actual credentials or testnet)
        print("\n2️⃣ Setting up Binance client...")
        binance_client = Client("test_key", "test_secret")  # Replace with your keys

        # Create orchestrator
        orchestrator = GridInitializationOrchestrator(
            binance_client, enhanced_trade_repo, enhanced_fifo_service
        )

        print("✅ Components initialized")

        # Test initialization
        print("\n3️⃣ Testing grid initialization...")
        test_client_id = 12345

        result = await orchestrator.start_client_grid_from_usdt(
            client_id=test_client_id, symbol="ADAUSDT", usdt_amount=1000.0
        )

        print("\n🧪 Test Results:")
        print(f"Success: {result['success']}")

        if result["success"]:
            print(f"USDT Investment: ${result['total_usdt_invested']}")
            print(f"FIFO Tracking: {result['fifo_tracking']}")
            print(f"Message: {result['message']}")

            # Test FIFO calculations
            print("\n4️⃣ Testing FIFO profit calculations...")
            fifo_performance = (
                enhanced_fifo_service.calculate_fifo_profit_with_cost_basis(
                    test_client_id
                )
            )

            print(f"Total Profit: ${fifo_performance['total_profit']:.2f}")
            print(f"Cost Basis Used: {fifo_performance['cost_basis_used']}")
            print(f"Calculation Method: {fifo_performance['calculation_method']}")

        else:
            print(f"Error: {result['error']}")
            print(f"Details: {result.get('details', 'No additional details')}")

        # Clean up test data - FIXED VERSION
        print("\n5️⃣ Cleaning up test data...")

        # Clean up trades
        enhanced_trade_repo.delete_test_trades(test_client_id)

        # Clean up FIFO cost basis test data - CORRECTED
        try:
            with sqlite3.connect(enhanced_fifo_service.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM fifo_cost_basis WHERE client_id = ?", (test_client_id,)
                )
                deleted_count = cursor.rowcount
                print(f"   🗑️ Deleted {deleted_count} FIFO cost basis records")
        except Exception as cleanup_error:
            print(f"   ⚠️ FIFO cleanup warning: {cleanup_error}")

        print("✅ Test data cleaned up")

        return result["success"]

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_fifo_validation():
    """Test FIFO validation for existing clients"""

    print("\n🔍 Testing FIFO Validation")
    print("=" * 30)

    try:
        enhanced_fifo_service = EnhancedFIFOService()

        # Test validation on a test client
        test_client_id = 12345

        validation = await enhanced_fifo_service.validate_fifo_integrity(test_client_id)

        print(f"Client: {test_client_id}")
        print(f"Validation Passed: {validation['validation_passed']}")
        print(f"Issues Found: {len(validation['issues'])}")

        for issue in validation["issues"]:
            print(f"  - {issue['type']}: {issue['message']}")

        print("\n📋 Recommendations:")
        for rec in validation["recommendations"]:
            print(f"  {rec}")

        return validation["validation_passed"]

    except Exception as e:
        print(f"❌ FIFO validation failed: {e}")
        return False


async def test_complete_fifo_cycle():
    """Test a complete FIFO cycle: initialization → buy → sell → profit calculation"""

    print("\n🔄 Testing Complete FIFO Cycle")
    print("=" * 40)

    try:
        enhanced_trade_repo = EnhancedTradeRepository()
        enhanced_fifo_service = EnhancedFIFOService()
        test_client_id = 88888  # Different client ID for this test

        print("1️⃣ Recording initial cost basis...")

        # Record initial cost basis (simulating Pure USDT initialization)
        cost_basis_id = await enhanced_fifo_service.record_initial_cost_basis(
            client_id=test_client_id,
            symbol="ADAUSDT",
            quantity=1000.0,  # 1000 ADA
            cost_per_unit=0.45,  # Bought at $0.45
            total_cost=450.0,  # $450 total
            timestamp=1640995200.0,  # Jan 1, 2022
            trade_id="init_test_88888",
        )

        print(f"   ✅ Cost basis recorded: ID={cost_basis_id}")

        print("\n2️⃣ Recording additional buy...")

        # Record an additional buy trade
        buy_trade_id = await enhanced_trade_repo.create_trade(
            client_id=test_client_id,
            symbol="ADAUSDT",
            side="BUY",
            quantity=200.0,
            price=0.50,
            total_value=100.0,
            is_initialization=False,
        )

        print(f"   ✅ Buy trade recorded: ID={buy_trade_id}")

        print("\n3️⃣ Recording sell trades...")

        # Record first sell (should use FIFO - oldest cost basis first)
        sell1_trade_id = await enhanced_trade_repo.create_trade(
            client_id=test_client_id,
            symbol="ADAUSDT",
            side="SELL",
            quantity=300.0,  # Sell 300 ADA
            price=0.55,  # At $0.55
            total_value=165.0,
            is_initialization=False,
        )

        print(f"   ✅ First sell recorded: ID={sell1_trade_id}")

        # Record second sell
        sell2_trade_id = await enhanced_trade_repo.create_trade(
            client_id=test_client_id,
            symbol="ADAUSDT",
            side="SELL",
            quantity=100.0,  # Sell 100 ADA
            price=0.60,  # At $0.60
            total_value=60.0,
            is_initialization=False,
        )

        print(f"   ✅ Second sell recorded: ID={sell2_trade_id}")

        print("\n4️⃣ Calculating FIFO profit...")

        # Calculate FIFO profit
        fifo_performance = enhanced_fifo_service.calculate_fifo_profit_with_cost_basis(
            test_client_id, "ADAUSDT"
        )

        print(f"   Total Profit: ${fifo_performance['total_profit']:.2f}")
        print(f"   Realized Profit: ${fifo_performance['realized_profit']:.2f}")
        print(f"   Unrealized Profit: ${fifo_performance['unrealized_profit']:.2f}")
        print(f"   Total Trades: {fifo_performance['total_trades']}")
        print(f"   Win Rate: {fifo_performance['win_rate']:.1f}%")
        print(f"   Cost Basis Used: {fifo_performance['cost_basis_used']}")

        print("\n5️⃣ Detailed breakdown:")

        # Expected calculation:
        # Initial: 1000 ADA @ $0.45 = $450
        # Buy: 200 ADA @ $0.50 = $100
        # Total inventory: 1200 ADA, cost = $550
        #
        # Sell 1: 300 ADA @ $0.55 = $165 revenue
        #   - Uses 300 from initial (300 × $0.45 = $135 cost)
        #   - Profit = $165 - $135 = $30
        #   - Remaining initial: 700 ADA @ $0.45
        #
        # Sell 2: 100 ADA @ $0.60 = $60 revenue
        #   - Uses 100 from remaining initial (100 × $0.45 = $45 cost)
        #   - Profit = $60 - $45 = $15
        #   - Remaining initial: 600 ADA @ $0.45
        #
        # Total realized profit: $30 + $15 = $45
        # Remaining inventory: 600 ADA @ $0.45 + 200 ADA @ $0.50

        print("   Expected realized profit: ~$45.00")
        print(f"   Actual realized profit: ${fifo_performance['realized_profit']:.2f}")

        accuracy_check = abs(fifo_performance["realized_profit"] - 45.0) < 1.0
        print(f"   Accuracy check: {'✅ PASSED' if accuracy_check else '❌ FAILED'}")

        print("\n6️⃣ Cleaning up test data...")

        # Cleanup
        enhanced_trade_repo.delete_test_trades(test_client_id)

        with sqlite3.connect(enhanced_fifo_service.db_path) as conn:
            conn.execute(
                "DELETE FROM fifo_cost_basis WHERE client_id = ?", (test_client_id,)
            )

        print("   ✅ Test data cleaned up")

        return accuracy_check

    except Exception as e:
        print(f"❌ FIFO cycle test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 GridTrader Pro - Pure USDT Integration Test Suite")
    print("=" * 60)

    # Test 1: Pure USDT integration
    print("\n" + "=" * 20 + " TEST 1: PURE USDT INTEGRATION " + "=" * 20)
    success1 = asyncio.run(test_pure_usdt_integration())

    # Test 2: FIFO validation
    print("\n" + "=" * 20 + " TEST 2: FIFO VALIDATION " + "=" * 20)
    success2 = asyncio.run(test_fifo_validation())

    # Test 3: Complete FIFO cycle
    print("\n" + "=" * 20 + " TEST 3: COMPLETE FIFO CYCLE " + "=" * 20)
    success3 = asyncio.run(test_complete_fifo_cycle())

    # Final results
    print("\n" + "=" * 60)
    print("🎯 FINAL TEST RESULTS")
    print("=" * 60)
    print(f"✅ Pure USDT Integration: {'PASSED' if success1 else 'FAILED'}")
    print(f"✅ FIFO Validation: {'PASSED' if success2 else 'FAILED'}")
    print(f"✅ Complete FIFO Cycle: {'PASSED' if success3 else 'FAILED'}")

    overall_success = success1 and success2 and success3

    if overall_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 Your Pure USDT Grid system is ready for production!")
        print("\n📋 Next Steps:")
        print("1. Test with small real amounts ($50-100)")
        print("2. Update your Telegram handlers")
        print("3. Migrate existing clients gradually")
        print("4. Monitor FIFO integrity regularly")
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Review the errors above and fix before proceeding to production.")

    print("\n" + "=" * 60)
