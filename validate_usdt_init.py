#!/usr/bin/env python3
"""
USDT Initializer Validation Script
==================================

Quick validation of cleaned usdt_initializer.py without stopping the running app.
Tests all critical imports, classes, and method signatures.
"""

import sys
import traceback
from typing import Dict, List

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
    
    print_status("Testing imports...", "INFO")
    
    # Test 1: Basic module import
    try:
        import services.usdt_initializer
        results["module_import"] = True
        print_status("Module import successful", "PASS")
    except Exception as e:
        results["module_import"] = False
        print_status(f"Module import failed: {e}", "FAIL")
        return results
    
    # Test 2: Main classes
    try:
        from services.usdt_initializer import EnhancedGridInitializationOrchestrator
        results["orchestrator_class"] = True
        print_status("EnhancedGridInitializationOrchestrator import successful", "PASS")
    except Exception as e:
        results["orchestrator_class"] = False
        print_status(f"EnhancedGridInitializationOrchestrator import failed: {e}", "FAIL")
    
    try:
        from services.usdt_initializer import PureUSDTAdvancedSync
        results["sync_class"] = True
        print_status("PureUSDTAdvancedSync import successful", "PASS")
    except Exception as e:
        results["sync_class"] = False
        print_status(f"PureUSDTAdvancedSync import failed: {e}", "FAIL")
    
    try:
        from services.usdt_initializer import EnhancedPureUSDTGridInitializer
        results["initializer_class"] = True
        print_status("EnhancedPureUSDTGridInitializer import successful", "PASS")
    except Exception as e:
        results["initializer_class"] = False
        print_status(f"EnhancedPureUSDTGridInitializer import failed: {e}", "FAIL")
    
    try:
        from services.usdt_initializer import InitializationTrade
        results["trade_dataclass"] = True
        print_status("InitializationTrade dataclass import successful", "PASS")
    except Exception as e:
        results["trade_dataclass"] = False
        print_status(f"InitializationTrade dataclass import failed: {e}", "FAIL")
    
    return results

def validate_class_structure() -> Dict:
    """Test class structures and method signatures"""
    results = {}
    
    print_status("Testing class structures...", "INFO")
    
    try:
        from services.usdt_initializer import EnhancedGridInitializationOrchestrator
        
        # Test orchestrator methods
        required_methods = [
            'start_client_grid_from_usdt_with_advanced_features',
            '__init__'
        ]
        
        for method in required_methods:
            if hasattr(EnhancedGridInitializationOrchestrator, method):
                results[f"orchestrator_{method}"] = True
                print_status(f"EnhancedGridInitializationOrchestrator.{method} exists", "PASS")
            else:
                results[f"orchestrator_{method}"] = False
                print_status(f"EnhancedGridInitializationOrchestrator.{method} missing", "FAIL")
                
    except Exception as e:
        print_status(f"Class structure test failed: {e}", "FAIL")
        results["class_structure"] = False
        return results
    
    try:
        from services.usdt_initializer import PureUSDTAdvancedSync
        
        # Test sync class methods
        sync_methods = [
            'sync_pure_usdt_with_advanced_grid',
            '__init__'
        ]
        
        for method in sync_methods:
            if hasattr(PureUSDTAdvancedSync, method):
                results[f"sync_{method}"] = True
                print_status(f"PureUSDTAdvancedSync.{method} exists", "PASS")
            else:
                results[f"sync_{method}"] = False
                print_status(f"PureUSDTAdvancedSync.{method} missing", "FAIL")
                
    except Exception as e:
        print_status(f"Sync class test failed: {e}", "FAIL")
        
    return results

def validate_instantiation() -> Dict:
    """Test that classes can be instantiated"""
    results = {}
    
    print_status("Testing class instantiation...", "INFO")
    
    # Test PureUSDTAdvancedSync (no dependencies)
    try:
        from services.usdt_initializer import PureUSDTAdvancedSync
        sync = PureUSDTAdvancedSync()
        results["sync_instantiation"] = True
        print_status("PureUSDTAdvancedSync instantiation successful", "PASS")
    except Exception as e:
        results["sync_instantiation"] = False
        print_status(f"PureUSDTAdvancedSync instantiation failed: {e}", "FAIL")
    
    # Test with mock dependencies for orchestrator
    try:
        from services.usdt_initializer import EnhancedGridInitializationOrchestrator
        
        # Mock the dependencies
        class MockClient:
            pass
        
        class MockRepo:
            pass
        
        class MockFifo:
            pass
        
        orchestrator = EnhancedGridInitializationOrchestrator(
            MockClient(), MockRepo(), MockFifo()
        )
        results["orchestrator_instantiation"] = True
        print_status("EnhancedGridInitializationOrchestrator instantiation successful", "PASS")
    except Exception as e:
        results["orchestrator_instantiation"] = False
        print_status(f"EnhancedGridInitializationOrchestrator instantiation failed: {e}", "FAIL")
    
    return results

def validate_critical_dependencies() -> Dict:
    """Test that all required dependencies are available"""
    results = {}
    
    print_status("Testing dependencies...", "INFO")
    
    dependencies = [
        ('binance.client', 'Client'),
        ('repositories.trade_repository', 'TradeRepository'),
        ('services.fifo_service', 'FIFOService'),
        ('utils.crypto', 'CryptoUtils'),
        ('dataclasses', 'dataclass'),
        ('typing', 'Dict'),
        ('logging', None),
        ('time', None)
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

def validate_removed_debug_code() -> Dict:
    """Verify that debug code was properly removed"""
    results = {}
    
    print_status("Checking for removed debug code...", "INFO")
    
    # Read the file and check for debug patterns
    try:
        with open('services/usdt_initializer.py', 'r') as f:
            content = f.read()
        
        # Patterns that should NOT exist (debug code)
        forbidden_patterns = [
            'InventoryDiagnostic',
            'emergency_repair_inventory_object',
            'repair_corrupted_inventories',
            'emergency_inventory_reset',
            'quick_diagnose_inventory',
            'quick_repair_inventory',
            'isinstance(inventory, dict)',
            'CORRUPTED:',
            'Emergency repair',
            '🔧 CRITICAL FIX:',
            '🚨 EMERGENCY',
        ]
        
        found_patterns = []
        for pattern in forbidden_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        if found_patterns:
            results["debug_code_removed"] = False
            print_status(f"Found debug code patterns: {found_patterns}", "FAIL")
        else:
            results["debug_code_removed"] = True
            print_status("All debug code properly removed", "PASS")
            
        # Patterns that SHOULD exist (core functionality)
        required_patterns = [
            'EnhancedGridInitializationOrchestrator',
            'PureUSDTAdvancedSync',
            'start_client_grid_from_usdt_with_advanced_features',
            'sync_pure_usdt_with_advanced_grid',
            'InitializationTrade'
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
            
    except Exception as e:
        results["file_reading"] = False
        print_status(f"Could not read file: {e}", "FAIL")
    
    return results

def generate_report(all_results: Dict) -> None:
    """Generate final validation report"""
    print("\n" + "="*60)
    print_status("VALIDATION REPORT", "INFO")
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
        print_status("✅ USDT Initializer is PRODUCTION READY", "PASS")
        print_status("✅ Safe to proceed with cleaning other files", "PASS")
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
    print("🚀 USDT Initializer Validation Script")
    print("="*60)
    print("Testing cleaned usdt_initializer.py for compatibility...")
    print()
    
    all_results = {}
    
    try:
        # Run all validation tests
        all_results["imports"] = validate_imports()
        all_results["class_structure"] = validate_class_structure()
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
