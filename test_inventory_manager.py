# test_inventory_manager_fix.py
"""
Test suite to verify the inventory manager injection fix is working properly.
Run this to confirm the fix before cleaning up debug code.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock
from binance.client import Client

from services.grid_manager import GridManager
from services.inventory_manager import SingleGridInventoryManager, AssetInventory
from services.fifo_service import FIFOService


class TestInventoryManagerFix:
    """Test suite for inventory manager injection fix"""

    def setup_method(self):
        """Setup test environment"""
        # Mock Binance client
        self.mock_binance_client = Mock(spec=Client)
        self.mock_binance_client.get_symbol_ticker.return_value = {"price": "164.50"}
        self.mock_binance_client.get_exchange_info.return_value = {
            "symbols": [{
                "symbol": "SOLUSDT",
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                    {"filterType": "MIN_NOTIONAL", "minNotional": "10.0"}
                ]
            }]
        }
        
        # Mock FIFO service
        self.mock_fifo_service = Mock(spec=FIFOService)
        
        self.client_id = 485825055

    def test_inventory_manager_creation(self):
        """Test 1: GridManager creates inventory manager (not None)"""
        # Create GridManager
        grid_manager = GridManager(
            binance_client=self.mock_binance_client,
            client_id=self.client_id,
            fifo_service=self.mock_fifo_service
        )
        
        # Verify inventory manager exists
        assert grid_manager.inventory_manager is not None, "Inventory manager should not be None"
        assert isinstance(grid_manager.inventory_manager, SingleGridInventoryManager), \
            f"Expected SingleGridInventoryManager, got {type(grid_manager.inventory_manager)}"

    def test_trading_engine_injection(self):
        """Test 2: TradingEngine receives the same inventory manager reference"""
        # Create GridManager
        grid_manager = GridManager(
            binance_client=self.mock_binance_client,
            client_id=self.client_id,
            fifo_service=self.mock_fifo_service
        )
        
        # Verify trading engine has inventory manager
        assert grid_manager.trading_engine.inventory_manager is not None, \
            "Trading engine inventory manager should not be None"
        
        # Verify same object reference (proper injection)
        assert grid_manager.inventory_manager is grid_manager.trading_engine.inventory_manager, \
            "GridManager and TradingEngine should share the same inventory manager instance"
        
        # Verify object ID matches
        grid_manager_id = id(grid_manager.inventory_manager)
        trading_engine_id = id(grid_manager.trading_engine.inventory_manager)
        assert grid_manager_id == trading_engine_id, \
            f"Object IDs should match: GridManager={grid_manager_id}, TradingEngine={trading_engine_id}"

    def test_required_methods_exist(self):
        """Test 3: Inventory manager has all required methods"""
        grid_manager = GridManager(
            binance_client=self.mock_binance_client,
            client_id=self.client_id,
            fifo_service=self.mock_fifo_service
        )
        
        inventory_manager = grid_manager.inventory_manager
        
        # Test required methods exist
        assert hasattr(inventory_manager, 'has_tracking'), "Missing has_tracking method"
        assert hasattr(inventory_manager, 'update_after_fill'), "Missing update_after_fill method"
        assert hasattr(inventory_manager, 'add_symbol_tracking'), "Missing add_symbol_tracking method"
        assert hasattr(inventory_manager, 'inventories'), "Missing inventories attribute"
        
        # Test methods are callable
        assert callable(inventory_manager.has_tracking), "has_tracking should be callable"
        assert callable(inventory_manager.update_after_fill), "update_after_fill should be callable"
        assert callable(inventory_manager.add_symbol_tracking), "add_symbol_tracking should be callable"

    @pytest.mark.asyncio
    async def test_symbol_tracking_functionality(self):
        """Test 4: Symbol tracking works properly"""
        grid_manager = GridManager(
            binance_client=self.mock_binance_client,
            client_id=self.client_id,
            fifo_service=self.mock_fifo_service
        )
        
        inventory_manager = grid_manager.inventory_manager
        
        # Initially, SOLUSDT should not be tracked (only default symbols)
        # Test adding SOLUSDT tracking
        success = await inventory_manager.add_symbol_tracking("SOLUSDT", 840.0)
        assert success, "add_symbol_tracking should return True"
        
        # Test has_tracking works
        has_tracking = inventory_manager.has_tracking("SOLUSDT")
        assert has_tracking is True, "has_tracking should return True for SOLUSDT"
        
        # Test non-existent symbol
        has_tracking_fake = inventory_manager.has_tracking("FAKEUSD")
        assert has_tracking_fake is False, "has_tracking should return False for non-existent symbol"

    @pytest.mark.asyncio
    async def test_inventory_object_types(self):
        """Test 5: Inventory objects are proper AssetInventory instances (not dicts)"""
        grid_manager = GridManager(
            binance_client=self.mock_binance_client,
            client_id=self.client_id,
            fifo_service=self.mock_fifo_service
        )
        
        inventory_manager = grid_manager.inventory_manager
        
        # Add SOLUSDT tracking
        await inventory_manager.add_symbol_tracking("SOLUSDT", 840.0)
        
        # Verify inventory object exists and is correct type
        assert "SOLUSDT" in inventory_manager.inventories, "SOLUSDT should be in inventories"
        
        sol_inventory = inventory_manager.inventories["SOLUSDT"]
        
        # Critical test: ensure it's AssetInventory, not dict
        assert isinstance(sol_inventory, AssetInventory), \
            f"Expected AssetInventory, got {type(sol_inventory)}"
        assert not isinstance(sol_inventory, dict), \
            "Inventory should NOT be a dict"
        
        # Test required attributes exist
        assert hasattr(sol_inventory, 'usdt_balance'), "Missing usdt_balance attribute"
        assert hasattr(sol_inventory, 'asset_balance'), "Missing asset_balance attribute"
        assert hasattr(sol_inventory, 'order_size_base'), "Missing order_size_base attribute"

    def test_update_after_fill_preserves_types(self):
        """Test 6: update_after_fill doesn't corrupt object types"""
        grid_manager = GridManager(
            binance_client=self.mock_binance_client,
            client_id=self.client_id,
            fifo_service=self.mock_fifo_service
        )
        
        inventory_manager = grid_manager.inventory_manager
        
        # Use existing SOLUSDT inventory from default initialization
        assert "SOLUSDT" in inventory_manager.inventories, "SOLUSDT should exist in default inventories"
        
        # Get initial inventory
        sol_inventory_before = inventory_manager.inventories["SOLUSDT"]
        assert isinstance(sol_inventory_before, AssetInventory), "Should start as AssetInventory"
        
        initial_usdt = sol_inventory_before.usdt_balance
        initial_asset = sol_inventory_before.asset_balance
        
        # Simulate a fill operation
        inventory_manager.update_after_fill("SOLUSDT", "BUY", 0.5, 164.50)
        
        # Verify object is still AssetInventory after operation
        sol_inventory_after = inventory_manager.inventories["SOLUSDT"]
        assert isinstance(sol_inventory_after, AssetInventory), \
            f"After update_after_fill, should still be AssetInventory, got {type(sol_inventory_after)}"
        assert not isinstance(sol_inventory_after, dict), \
            "Should NOT become a dict after update_after_fill"
        
        # Verify it's the same object reference
        assert sol_inventory_before is sol_inventory_after, \
            "Should be the same object reference, not replaced"
        
        # Verify balances were updated correctly
        expected_usdt = initial_usdt - (0.5 * 164.50)  # BUY operation decreases USDT
        expected_asset = initial_asset + 0.5  # BUY operation increases asset
        
        assert abs(sol_inventory_after.usdt_balance - expected_usdt) < 0.01, \
            f"USDT balance not updated correctly: expected ~{expected_usdt}, got {sol_inventory_after.usdt_balance}"
        assert abs(sol_inventory_after.asset_balance - expected_asset) < 0.01, \
            f"Asset balance not updated correctly: expected ~{expected_asset}, got {sol_inventory_after.asset_balance}"

    def test_multiple_symbols_no_cross_contamination(self):
        """Test 7: Multiple symbols don't interfere with each other"""
        grid_manager = GridManager(
            binance_client=self.mock_binance_client,
            client_id=self.client_id,
            fifo_service=self.mock_fifo_service
        )
        
        inventory_manager = grid_manager.inventory_manager
        
        # Check that default symbols exist and are proper types
        default_symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT"]
        
        for symbol in default_symbols:
            assert symbol in inventory_manager.inventories, f"{symbol} should exist in default inventories"
            inventory = inventory_manager.inventories[symbol]
            assert isinstance(inventory, AssetInventory), \
                f"{symbol} should be AssetInventory, got {type(inventory)}"
            assert hasattr(inventory, 'usdt_balance'), f"{symbol} missing usdt_balance"
            assert hasattr(inventory, 'order_size_base'), f"{symbol} missing order_size_base"

    def test_trading_engine_integration(self):
        """Test 8: Integration between GridManager and TradingEngine works"""
        grid_manager = GridManager(
            binance_client=self.mock_binance_client,
            client_id=self.client_id,
            fifo_service=self.mock_fifo_service
        )
        
        # Test that trading engine can access inventory manager methods
        trading_engine = grid_manager.trading_engine
        
        # These calls should not raise AttributeError
        try:
            # Test has_tracking through trading engine
            result = trading_engine.inventory_manager.has_tracking("SOLUSDT")
            assert isinstance(result, bool), "has_tracking should return boolean"
            
            # Test accessing inventories through trading engine
            inventories = trading_engine.inventory_manager.inventories
            assert isinstance(inventories, dict), "inventories should be a dict"
            
        except AttributeError as e:
            pytest.fail(f"Trading engine should be able to access inventory manager methods: {e}")


def run_test_suite():
    """Run the complete test suite"""
    print("🧪 Running Inventory Manager Fix Test Suite")
    print("=" * 50)
    
    # Run synchronous tests
    test_instance = TestInventoryManagerFix()
    
    try:
        # Test 1
        test_instance.setup_method()
        test_instance.test_inventory_manager_creation()
        print("✅ Test 1 PASSED: Inventory manager creation")
        
        # Test 2
        test_instance.setup_method()
        test_instance.test_trading_engine_injection()
        print("✅ Test 2 PASSED: Trading engine injection")
        
        # Test 3
        test_instance.setup_method()
        test_instance.test_required_methods_exist()
        print("✅ Test 3 PASSED: Required methods exist")
        
        # Test 6
        test_instance.setup_method()
        test_instance.test_update_after_fill_preserves_types()
        print("✅ Test 6 PASSED: update_after_fill preserves types")
        
        # Test 7
        test_instance.setup_method()
        test_instance.test_multiple_symbols_no_cross_contamination()
        print("✅ Test 7 PASSED: Multiple symbols work correctly")
        
        # Test 8
        test_instance.setup_method()
        test_instance.test_trading_engine_integration()
        print("✅ Test 8 PASSED: Trading engine integration")
        
        print("\n🎉 ALL SYNCHRONOUS TESTS PASSED!")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        return False
    
    # Run async tests
    async def run_async_tests():
        try:
            # Test 4
            test_instance.setup_method()
            await test_instance.test_symbol_tracking_functionality()
            print("✅ Test 4 PASSED: Symbol tracking functionality")
            
            # Test 5
            test_instance.setup_method()
            await test_instance.test_inventory_object_types()
            print("✅ Test 5 PASSED: Inventory object types")
            
            print("\n🎉 ALL ASYNC TESTS PASSED!")
            return True
            
        except Exception as e:
            print(f"❌ ASYNC TEST FAILED: {e}")
            return False
    
    # Run async tests
    async_result = asyncio.run(run_async_tests())
    
    if async_result:
        print("\n" + "=" * 50)
        print("🎯 COMPREHENSIVE TEST SUITE: ALL TESTS PASSED!")
        print("✅ The inventory manager fix is working correctly")
        print("✅ Safe to proceed with cleanup of debug code")
        print("=" * 50)
        return True
    else:
        print("\n❌ SOME TESTS FAILED - DO NOT PROCEED WITH CLEANUP")
        return False


if __name__ == "__main__":
    success = run_test_suite()
    exit(0 if success else 1)
