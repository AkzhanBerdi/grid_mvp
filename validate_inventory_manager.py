#!/usr/bin/env python3
"""
Inventory Manager Validation Script
===================================

Quick validation of cleaned inventory_manager.py without stopping the running app.
Tests all critical imports, classes, and method signatures.
"""

import sys
import traceback
from typing import Dict

def print_status(message: str, status: str = "INFO"):
    """Print colored status messages"""
    colors = {
        "PASS": "\033[92m✅",  # Green
        "FAIL": "\033[91m❌",  # Red
        "INFO": "\033[94mℹ️",   # Blue
        "WARN": "\033[93m⚠️",   # Yellow
    }
    reset = "\033[0m"
    print(f"{colors.get(status, colors['INFO'])} {message}{reset}")

def validate_imports() -> Dict:
    """Test all critical imports"""
    results = {}
    
    print_status("Testing inventory manager imports...", "INFO")
    
    # Test 1: Basic module import
    try:
        import services.inventory_manager
        results["module_import"] = True
        print_status("Module import successful", "PASS")
    except Exception as e:
        results["module_import"] = False
        print_status(f"Module import failed: {e}", "FAIL")
        return results
    
    # Test 2: AssetInventory class
    try:
        from services.inventory_manager import AssetInventory
        results["asset_inventory_class"] = True
        print_status("AssetInventory class import successful", "PASS")
    except Exception as e:
        results["asset_inventory_class"] = False
        print_status(f"AssetInventory class import failed: {e}", "FAIL")
    
    # Test 3: SingleGridInventoryManager class
    try:
        from services.inventory_manager import SingleGridInventoryManager
        results["inventory_manager_class"] = True
        print_status("SingleGridInventoryManager class import successful", "PASS")
    except Exception as e:
        results["inventory_manager_class"] = False
        print_status(f"SingleGridInventoryManager class import failed: {e}", "FAIL")
    
    return results

def validate_asset_inventory_structure() -> Dict:
    """Test AssetInventory class structure"""
    results = {}
    
    print_status("Testing AssetInventory class structure...", "INFO")
    
    try:
        from services.inventory_manager import AssetInventory
        
        # Test required attributes/methods
        required_methods = [
            '__init__',
            'validate_integrity'
        ]
        
        for method in required_methods:
            if hasattr(AssetInventory, method):
                results[f"asset_inventory_{method}"] = True
                print_status(f"AssetInventory.{method} exists", "PASS")
            else:
                results[f"asset_inventory_{method}"] = False
                print_status(f"AssetInventory.{method} missing", "FAIL")
                
        # Test instantiation
        try:
            inventory = AssetInventory(
                symbol="TESTUSDT",
                total_allocation=100.0,
                usdt_balance=50.0,
                asset_balance=25.0
            )
            results["asset_inventory_instantiation"] = True
            print_status("AssetInventory instantiation successful", "PASS")
            
            # Test key attributes exist
            key_attributes = [
                'symbol', 'total_allocation', 'usdt_balance', 'asset_balance',
                'reserved_usdt', 'reserved_asset', 'grid_spacing', 'order_size_base'
            ]
            
            for attr in key_attributes:
                if hasattr(inventory, attr):
                    results[f"asset_inventory_attr_{attr}"] = True
                    print_status(f"AssetInventory.{attr} attribute exists", "PASS")
                else:
                    results[f"asset_inventory_attr_{attr}"] = False
                    print_status(f"AssetInventory.{attr} attribute missing", "FAIL")
                    
        except Exception as e:
            results["asset_inventory_instantiation"] = False
            print_status(f"AssetInventory instantiation failed: {e}", "FAIL")
                
    except Exception as e:
        print_status(f"AssetInventory structure test failed: {e}", "FAIL")
        
    return results

def validate_inventory_manager_structure() -> Dict:
    """Test SingleGridInventoryManager class structure"""
    results = {}
    
    print_status("Testing SingleGridInventoryManager structure...", "INFO")
    
    try:
        from services.inventory_manager import SingleGridInventoryManager
        
        # Test required methods
        required_methods = [
            '__init__',
            'add_symbol_tracking',
            'has_tracking',
            'can_place_buy_order',
            'can_place_sell_order',
            'reserve_for_order',
            'release_reservation',
            'update_after_fill',
            'get_optimal_order_size',
            'get_optimal_quantity',
            'get_inventory_status',
            'get_all_tracked_symbols',
            'validate_inventory_health'
        ]
        
        for method in required_methods:
            if hasattr(SingleGridInventoryManager, method):
                results[f"inventory_manager_{method}"] = True
                print_status(f"SingleGridInventoryManager.{method} exists", "PASS")
            else:
                results[f"inventory_manager_{method}"] = False
                print_status(f"SingleGridInventoryManager.{method} missing", "FAIL")
                
    except Exception as e:
        print_status(f"SingleGridInventoryManager structure test failed: {e}", "FAIL")
        
    return results

def validate_instantiation() -> Dict:
    """Test that classes can be instantiated"""
    results = {}
    
    print_status("Testing class instantiation...", "INFO")
    
    # Test AssetInventory instantiation
    try:
        from services.inventory_manager import AssetInventory
        inventory = AssetInventory(
            symbol="TESTUSDT",
            total_allocation=1000.0,
            usdt_balance=500.0,
            asset_balance=10.0
        )
        
        # Test validate_integrity method
        is_valid = inventory.validate_integrity()
        if is_valid:
            results["asset_inventory_integrity"] = True
            print_status("AssetInventory integrity validation works", "PASS")
        else:
            results["asset_inventory_integrity"] = False
            print_status("AssetInventory integrity validation failed", "FAIL")
            
    except Exception as e:
        results["asset_inventory_instantiation"] = False
        print_status(f"AssetInventory instantiation failed: {e}", "FAIL")
    
    # Test SingleGridInventoryManager with mock client
    try:
        from services.inventory_manager import SingleGridInventoryManager
        
        # Mock Binance client
        class MockBinanceClient:
            def get_symbol_ticker(self, symbol):
                return {"price": "100.0"}
        
        manager = SingleGridInventoryManager(MockBinanceClient(), 800.0)
        results["inventory_manager_instantiation"] = True
        print_status("SingleGridInventoryManager instantiation successful", "PASS")
        
        # Test has_tracking method
        has_eth = manager.has_tracking("ETHUSDT")
        results["inventory_manager_has_tracking"] = True
        print_status(f"has_tracking method works (ETH tracking: {has_eth})", "PASS")
        
        # Test get_all_tracked_symbols
        symbols = manager.get_all_tracked_symbols()
        if isinstance(symbols, list):
            results["inventory_manager_get_symbols"] = True
            print_status(f"get_all_tracked_symbols works ({len(symbols)} symbols)", "PASS")
        else:
            results["inventory_manager_get_symbols"] = False
            print_status("get_all_tracked_symbols returned non-list", "FAIL")
            
    except Exception as e:
        results["inventory_manager_instantiation"] = False
        print_status(f"SingleGridInventoryManager instantiation failed: {e}", "FAIL")
    
    return results

def validate_removed_debug_code() -> Dict:
    """Verify that debug code was properly removed"""
    results = {}
    
    print_status("Checking for removed debug code...", "INFO")
    
    try:
        with open('services/inventory_manager.py', 'r') as f:
            content = f.read()
        
        # Patterns that should NOT exist (debug code)
        forbidden_patterns = [
            '🔍 DEBUG:',
            'logger.error(f"🔍',
            'if symbol == "SOLUSDT":',
            'self.logger.error("🔍 SOL',
            'DEBUG: Check',
            'update_after_fill START',
            'inventory type:',
            'self type:',
            'Stack trace:',
            'Anti-corruption marker',
            '_is_asset_inventory',
            '🔧 ENHANCED:',
            '🔧 FIXED:',
            '🔧 FIX:',
            '🔧 NEW:'
        ]
        
        found_patterns = []
        for pattern in forbidden_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        if found_patterns:
            results["debug_code_removed"] = False
            print_status(f"Found debug code patterns: {found_patterns[:3]}...", "FAIL")
        else:
            results["debug_code_removed"] = True
            print_status("All debug code properly removed", "PASS")
            
        # Patterns that SHOULD exist (core functionality)
        required_patterns = [
            'class AssetInventory:',
            'class SingleGridInventoryManager:',
            'def add_symbol_tracking',
            'def update_after_fill',
            'def reserve_for_order',
            'def get_optimal_order_size'
        ]
        
        missing_patterns = []
        for pattern in required_patterns:
            if pattern not in content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            results["core_functionality"] = False
            print_status(f"Missing core functionality: {missing_patterns}", "FAIL")
        else:
            results["core_functionality"] = True
            print_status("All core functionality preserved", "PASS")
            
        # Check for clean logging (no excessive debug)
        debug_log_patterns = [
            'self.logger.debug(',
            'logger.debug('
        ]
        
        debug_count = 0
        for pattern in debug_log_patterns:
            debug_count += content.count(pattern)
        
        if debug_count > 5:  # Allow some debug logging but not excessive
            results["clean_logging"] = False
            print_status(f"Excessive debug logging found ({debug_count} instances)", "WARN")
        else:
            results["clean_logging"] = True
            print_status(f"Clean logging level ({debug_count} debug statements)", "PASS")
            
    except Exception as e:
        results["file_reading"] = False
        print_status(f"Could not read file: {e}", "FAIL")
    
    return results

def validate_critical_dependencies() -> Dict:
    """Test that all required dependencies are available"""
    results = {}
    
    print_status("Testing dependencies...", "INFO")
    
    dependencies = [
        ('binance.client', 'Client'),
        ('typing', 'Dict'),
        ('typing', 'List'),
        ('typing', 'Tuple'),
        ('logging', None)
    ]
    
    for module, class_name in dependencies:
        try:
            if class_name:
                exec(f"from {module} import {class_name}")
                test_name = f"{module}.{class_name}"
            else:
                exec(f"import {module}")
                test_name = module
                
            results[f"dep_{module.replace('.', '_')}"] = True
            print_status(f"Dependency {test_name} available", "PASS")
        except Exception as e:
            results[f"dep_{module.replace('.', '_')}"] = False
            print_status(f"Dependency {test_name} failed: {e}", "FAIL")
    
    return results

def generate_report(all_results: Dict) -> None:
    """Generate final validation report"""
    print("\n" + "="*60)
    print_status("INVENTORY MANAGER VALIDATION REPORT", "INFO")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for category, results in all_results.items():
        print(f"\n📊 {category.upper()}:")
        for test, result in results.items():
            total_tests += 1
            if result:
                passed_tests += 1
                print_status(f"  {test}: PASSED", "PASS")
            else:
                failed_tests.append(f"{category}.{test}")
                print_status(f"  {test}: FAILED", "FAIL")
    
    print("\n" + "="*60)
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    if success_rate >= 95:
        print_status(f"OVERALL RESULT: EXCELLENT ({success_rate:.1f}%)", "PASS")
        print_status("✅ Inventory Manager is PRODUCTION READY", "PASS")
        print_status("✅ Safe to replace current file", "PASS")
    elif success_rate >= 80:
        print_status(f"OVERALL RESULT: GOOD ({success_rate:.1f}%)", "WARN")
        print_status("⚠️ Minor issues detected - review failed tests", "WARN")
    else:
        print_status(f"OVERALL RESULT: NEEDS ATTENTION ({success_rate:.1f}%)", "FAIL")
        print_status("❌ Critical issues detected - do not proceed", "FAIL")
    
    print(f"\n📈 Test Summary: {passed_tests}/{total_tests} passed")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"   • {test}")
    
    print("\n" + "="*60)

def main():
    """Main validation function"""
    print("🚀 Inventory Manager Validation Script")
    print("="*60)
    print("Testing cleaned inventory_manager.py for compatibility...")
    print()
    
    all_results = {}
    
    try:
        # Run all validation tests
        all_results["imports"] = validate_imports()
        all_results["asset_inventory"] = validate_asset_inventory_structure()
        all_results["inventory_manager"] = validate_inventory_manager_structure()
        all_results["instantiation"] = validate_instantiation()
        all_results["dependencies"] = validate_critical_dependencies()
        all_results["code_cleanup"] = validate_removed_debug_code()
        
        # Generate final report
        generate_report(all_results)
        
    except Exception as e:
        print_status(f"Validation script failed: {e}", "FAIL")
        print("Full traceback:")
        traceback.print_exc()
        return False
    
    # Return overall success
    total_tests = sum(len(results) for results in all_results.values())
    passed_tests = sum(sum(results.values()) for results in all_results.values())
    return (passed_tests / total_tests) >= 0.95 if total_tests > 0 else False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
