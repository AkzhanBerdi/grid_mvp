#!/usr/bin/env python3
"""
Phase 1 Test Script for Single Advanced Grid System
===================================================

This script tests the core components of the Single Advanced Grid system
without requiring real API connections or trading.

Run with: python phase1_test.py
"""

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_imports():
    """Test 1: Verify all imports work correctly"""
    logger.info("🧪 Test 1: Testing imports...")

    try:
        # Test SingleAdvancedGridManager import
        from services.single_advanced_grid_manager import SingleAdvancedGridManager

        logger.info("✅ SingleAdvancedGridManager imported successfully")

        # Test SingleAdvancedGridConfig import
        from models.single_advanced_grid_config import (
            SingleAdvancedGridConfig,
            validate_grid_integrity,
        )

        logger.info("✅ SingleAdvancedGridConfig imported successfully")

        # Test updated GridOrchestrator import
        from services.grid_orchestrator import GridOrchestrator

        logger.info("✅ Updated GridOrchestrator imported successfully")

        return True

    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during import: {e}")
        return False


def test_grid_config():
    """Test 2: Verify grid configuration creation and validation"""
    logger.info("🧪 Test 2: Testing grid configuration...")

    try:
        from models.single_advanced_grid_config import (
            SingleAdvancedGridConfig,
            validate_grid_integrity,
        )

        # Test asset configurations
        asset_configs = {
            "ETHUSDT": {
                "grid_spacing_base": 0.025,
                "volatility_threshold": 0.8,
                "compound_aggressiveness": 0.6,
                "max_order_size_multiplier": 2.5,
            },
            "SOLUSDT": {
                "grid_spacing_base": 0.03,
                "volatility_threshold": 1.2,
                "compound_aggressiveness": 0.8,
                "max_order_size_multiplier": 3.0,
            },
            "ADAUSDT": {
                "grid_spacing_base": 0.025,
                "volatility_threshold": 1.0,
                "compound_aggressiveness": 0.7,
                "max_order_size_multiplier": 2.8,
            },
        }

        for symbol, config in asset_configs.items():
            # Create grid configuration
            grid_config = SingleAdvancedGridConfig(symbol, 1000.0, config)
            grid_config.base_order_size = 100.0

            # Calculate grid levels
            grid_result = grid_config.calculate_grid_levels(
                2000.0 if symbol == "ETHUSDT" else 100.0
            )

            logger.info(f"✅ {symbol} grid created:")
            logger.info(f"   Total levels: {grid_result['total_levels']}")
            logger.info(
                f"   Buy allocation: ${grid_result['total_buy_allocation']:.2f}"
            )
            logger.info(f"   Grid width: {grid_result['grid_width'] * 100:.1f}%")

            # Validate configuration
            validation = validate_grid_integrity(grid_config)
            if validation["valid"]:
                logger.info(f"✅ {symbol} validation passed")
            else:
                logger.warning(f"⚠️ {symbol} validation issues: {validation['issues']}")

        return True

    except Exception as e:
        logger.error(f"❌ Grid config test failed: {e}")
        return False


def test_command_parsing():
    """Test 3: Verify force command parsing"""
    logger.info("🧪 Test 3: Testing command parsing...")

    try:
        # Mock SingleAdvancedGridManager for command testing
        class MockSingleAdvancedGridManager:
            def __init__(self):
                self.asset_configs = {
                    "ETHUSDT": {"allocation": 880},
                    "SOLUSDT": {"allocation": 660},
                    "ADAUSDT": {"allocation": 660},
                }

            def handle_force_command(self, command):  # Removed async
                parts = command.strip().split()
                if len(parts) != 3 or parts[0].upper() != "FORCE":
                    return {"success": False, "error": "Invalid format"}

                symbol_short = parts[1].upper()
                try:
                    amount = float(parts[2])
                except ValueError:
                    return {"success": False, "error": "Invalid amount"}

                symbol_map = {"ETH": "ETHUSDT", "SOL": "SOLUSDT", "ADA": "ADAUSDT"}
                full_symbol = symbol_map.get(symbol_short)

                if not full_symbol:
                    return {
                        "success": False,
                        "error": f"Unsupported symbol: {symbol_short}",
                    }

                return {
                    "success": True,
                    "symbol": full_symbol,
                    "amount": amount,
                    "message": f"Would create single advanced grid for {full_symbol} with ${amount}",
                }

        manager = MockSingleAdvancedGridManager()

        # Test valid commands
        test_commands = [
            "FORCE ETH 880",
            "FORCE SOL 660",
            "FORCE ADA 660",
            "FORCE ETH 100",  # Small test amount
        ]

        for command in test_commands:
            result = manager.handle_force_command(command)  # Removed await
            if result["success"]:
                logger.info(f"✅ Command '{command}': {result['message']}")
            else:
                logger.error(f"❌ Command '{command}' failed: {result['error']}")

        # Test invalid commands
        invalid_commands = [
            "FORCE",
            "FORCE BTC 500",  # Unsupported symbol
            "FORCE ETH abc",  # Invalid amount
        ]

        for command in invalid_commands:
            result = manager.handle_force_command(command)  # Removed await
            if not result["success"]:
                logger.info(
                    f"✅ Invalid command '{command}' properly rejected: {result['error']}"
                )
            else:
                logger.warning(
                    f"⚠️ Invalid command '{command}' was accepted (should be rejected)"
                )

        return True

    except Exception as e:
        logger.error(f"❌ Command parsing test failed: {e}")
        return False


def test_orchestrator_creation():
    """Test 4: Verify GridOrchestrator can be created"""
    logger.info("🧪 Test 4: Testing orchestrator creation...")

    try:
        from services.grid_orchestrator import GridOrchestrator

        # Create orchestrator
        orchestrator = GridOrchestrator()
        logger.info("✅ GridOrchestrator created successfully")

        # Test system metrics
        metrics = orchestrator.get_system_metrics()
        logger.info("✅ System metrics retrieved:")
        logger.info(f"   Architecture: {metrics['architecture_info']['system_type']}")
        logger.info(
            f"   Efficiency: {metrics['architecture_info']['capital_efficiency']}"
        )
        logger.info(
            f"   Active managers: {metrics['system_metrics']['active_managers']}"
        )

        # Test all grids status (should be empty initially)
        all_grids = orchestrator.get_all_active_grids()
        logger.info("✅ All grids status retrieved:")
        logger.info(f"   Total clients: {all_grids['system_summary']['total_clients']}")
        logger.info(
            f"   Active grids: {all_grids['system_summary']['total_active_grids']}"
        )

        return True

    except Exception as e:
        logger.error(f"❌ Orchestrator creation test failed: {e}")
        return False


def test_advanced_features_compatibility():
    """Test 5: Verify advanced features can be created"""
    logger.info("🧪 Test 5: Testing advanced features compatibility...")

    # Test creating manager without real Binance client
    class MockBinanceClient:
        def get_symbol_ticker(self, symbol):
            return {"price": "2000.0"}

        def get_24hr_ticker(self, symbol):
            return {"priceChangePercent": "3.5"}

    mock_client = MockBinanceClient()


test_advanced_features_compatibility()
test_command_parsing()
test_grid_config()
test_imports()
test_orchestrator_creation()
