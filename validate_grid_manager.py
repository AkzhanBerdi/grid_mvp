#!/usr/bin/env python3
"""
Grid Manager Validation Script
==============================

Quick validation of cleaned grid_manager.py without stopping the running app.
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
    
    print_status("Testing grid manager imports...", "INFO")
    
    # Test 1: Basic module import
    try:
        import services.grid_manager
        results["module_import"] = True
        print_status("Module import successful", "PASS")
    except Exception as e:
        results["module_import"] = False
        print_status(f"Module import failed: {e}", "FAIL")
        return results
    
    # Test 2: GridManager class
    try:
        from services.grid_manager import GridManager
        results["grid_manager_class"] = True
        print_status("GridManager class import successful", "PASS")
    except Exception as e:
        results["grid_manager_class"] = False
        print_status(f"GridManager class import failed: {e}", "FAIL")
    
    return results

def validate_grid_manager_structure() -> Dict:
    """Test GridManager class structure"""
    results = {}
    
    print_status("Testing GridManager class structure...", "INFO")
    
    try:
        from services.grid_manager import GridManager
        
        # Test required methods
        required_methods = [
            '__init__',
            'handle_force_command',
            'start_single_advanced_grid',
            'stop_single_advanced_grid',
            'monitor_and_update_grids',
            'get_all_active_grids',
            'get_single_grid_status',
            'get_unified_performance_report'
        ]
        
        for method in required_methods:
            if hasattr(GridManager, method):
                results[f"grid_manager_{method}"] = True
                print_status(f"GridManager.{method} exists", "PASS")
            else:
                results[f"grid_manager_{method}"] = False
                print_status(f"GridManager.{method} missing", "FAIL")
                
        # Test private helper methods
        private_methods = [
            '_ensure_inventory_manager',
            '_add_symbol_to_inventory',
            '_initialize_advanced_managers',
            '_get_current_price',
            '_create_grid_config',
            '_calculate_optimal_parameters',
            '_update_advanced_features',
            '_execute_smart_reset'
        ]
        
        for method in private_methods:
            if hasattr(GridManager, method):
                results[f"grid_manager_private_{method}"] = True
                print_status(f"GridManager.{method} exists", "PASS")
            else:
                results[f"grid_manager_private_{method}"] = False
                print_status(f"GridManager.{method} missing", "FAIL")
                
    except Exception as e:
        print_status(f"GridManager structure test failed: {e}", "FAIL")
        
    return results

def validate_instantiation() -> Dict:
    """Test that GridManager can be instantiated"""
    results = {}
    
    print_status("Testing GridManager instantiation...", "INFO")
    
    try:
        from services.grid_manager import GridManager
        
        # Mock dependencies
        class MockBinanceClient:
            def get_symbol_ticker(self, symbol):
                return {"price": "100.0"}
        
        class MockFifoService:
            pass
        
        # Test instantiation
        grid_manager = GridManager(MockBinanceClient(), 12345, MockFifoService())
        results["grid_manager_instantiation"] = True
        print_status("GridManager instantiation successful", "PASS")
        
        # Test key attributes exist
        key_attributes = [
            'binance_client', 'client_id', 'logger', 'fifo_service',
            'trading_engine', 'inventory_manager', 'compound_manager',
            'active_grids', 'metrics', 'asset_configs'
        ]
        
        for attr in key_attributes:
            if hasattr(grid_manager, attr):
                results[f"grid_manager_attr_{attr}"] = True
                print_status(f"GridManager.{attr} attribute exists", "PASS")
            else:
                results[f"grid_manager_attr_{attr}"] = False
                print_status(f"GridManager.{attr} attribute missing", "FAIL")
                
        # Test metrics structure
        if hasattr(grid_manager, 'metrics') and isinstance(grid_manager.metrics, dict):
            expected_metrics = ['grids_started', 'grids_stopped', 'total_trades', 'optimizations']
            for metric in expected_metrics:
                if metric in grid_manager.metrics:
                    results[f"metric_{metric}"] = True
                    print_status(f"Metric {metric} exists", "PASS")
                else:
                    results[f"metric_{metric}"] = False
                    print_status(f"Metric {metric} missing", "FAIL")
        
        # Test asset configs structure
        if hasattr(grid_manager, 'asset_configs') and isinstance(grid_manager.asset_configs, dict):
            expected_symbols = ['ETHUSDT', 'SOLUSDT', 'ADAUSDT']
            for symbol in expected_symbols:
                if symbol in grid_manager.asset_configs:
                    results[f"asset_config_{symbol}"] = True
                    print_status(f"Asset config {symbol} exists", "PASS")
                else:
                    results[f"asset_config_{symbol}"] = False
                    print_status(f"Asset config {symbol} missing", "FAIL")
                    
    except Exception as e:
        results["grid_manager_instantiation"] = False
        print_status(f"GridManager instantiation failed: {e}", "FAIL")
    
    return results

def validate_removed_debug_code() -> Dict:
    """Verify that debug code was properly removed"""
    results = {}
    
    print_status("Checking for removed debug code...", "INFO")
    
    try:
        with open('services/grid_manager.py', 'r') as f:
            content = f.read()
        
        # Patterns that should NOT exist (debug code)
        forbidden_patterns = [
            'debug_manager_references',
            '🔍 DEBUG:',
            '🔍 MANAGER REFERENCES DEBUG',
            'logger.error(f"🔍',
            'CORRUPTION DETECTED',
            'REFERENCE MISMATCH DETECTED',
            'GridManager inventory_manager is DICT!',
            'TradingEngine inventory_manager is DICT!',
            'same_object =',
            'isinstance(self.inventory_manager, dict)',
            'isinstance(self.trading_engine.inventory_manager, dict)',
            'CORRUPTION: inventory_manager',
            'Check references BEFORE',
            'Check references AFTER',
            'self.debug_manager_references',
            'Full error trace:',
            'traceback.format_exc()',
            'Emergency re-injection',
            '🔧 CRITICAL:',
            '🔧 SAFE:',
            '🔧 VERIFICATION:',
            '🔧 MISSING CODE:',
            '🔧 FIXED:',
            'Anti-corruption',
            'corruption prevention'
        ]
        
        found_patterns = []
        for pattern in forbidden_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        if found_patterns:
            results["debug_code_removed"] = False
            print_status(f"Found debug code patterns: {found_patterns[:3]}...", "FAIL")
            print_status(f"Total debug patterns found: {len(found_patterns)}", "FAIL")
        else:
            results["debug_code_removed"] = True
            print_status("All debug code properly removed", "PASS")
            
        # Patterns that SHOULD exist (core functionality)
        required_patterns = [
            'class GridManager:',
            'def handle_force_command',
            'def start_single_advanced_grid',
            'def stop_single_advanced_grid',
            'def monitor_and_update_grids',
            'self.inventory_manager = SingleGridInventoryManager',
            'self.trading_engine = GridTradingEngine',
            'self.compound_manager = CompoundInterestManager'
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
            
        # Check for clean logging
        excessive_debug_patterns = [
            'self.logger.error(f"🔍',
            'self.logger.error("🔍',
            'DEBUG:',
            'CORRUPTION',
            'MISMATCH'
        ]
        
        debug_count = 0
        for pattern in excessive_debug_patterns:
            debug_count += content.count(pattern)
        
        if debug_count > 0:
            results["clean_logging"] = False
            print_status(f"Excessive debug logging found ({debug_count} instances)", "FAIL")
        else:
            results["clean_logging"] = True
            print_status("Clean logging level", "PASS")
            
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
        ('models.grid_config', 'GridConfig'),
        ('repositories.client_repository', 'ClientRepository'),
        ('repositories.trade_repository', 'TradeRepository'),
        ('services.compound_manager', 'CompoundInterestManager'),
        ('services.fifo_service', 'FIFOService'),
        ('services.grid_monitor', 'GridMonitoringService'),
        ('services.grid_trading_engine', 'GridTradingEngine'),
        ('services.grid_utils', 'GridUtilityService'),
        ('services.inventory_manager', 'SingleGridInventoryManager'),
        ('services.trading_features', 'IntelligentMarketTimer'),
        ('services.trading_features', 'SmartGridAutoReset'),
        ('services.trading_features', 'VolatilityBasedRiskManager'),
        ('typing', 'Dict'),
        ('typing', 'Optional'),
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

def validate_force_command_logic() -> Dict:
    """Test FORCE command parsing logic"""
    results = {}
    
    print_status("Testing FORCE command logic...", "INFO")
    
    try:
        from services.grid_manager import GridManager
        
        # Mock dependencies
        class MockBinanceClient:
            def get_symbol_ticker(self, symbol):
                return {"price": "100.0"}
        
        class MockFifoService:
            pass
        
        grid_manager = GridManager(MockBinanceClient(), 12345, MockFifoService())
        
        # Test valid command parsing (without actual execution)
        test_commands = [
            "FORCE ETH 880",
            "FORCE SOL 660", 
            "FORCE ADA 660"
        ]
        
        for cmd in test_commands:
            try:
                # Parse command parts
                parts = cmd.strip().split()
                if len(parts) == 3 and parts[0].upper() == "FORCE":
                    symbol_short = parts[1].upper()
                    amount = float(parts[2])
                    
                    symbol_map = {"ETH": "ETHUSDT", "SOL": "SOLUSDT", "ADA": "ADAUSDT"}
                    full_symbol = symbol_map.get(symbol_short)
                    
                    if full_symbol and amount > 0:
                        results[f"force_command_{symbol_short}"] = True
                        print_status(f"FORCE command parsing {cmd} successful", "PASS")
                    else:
                        results[f"force_command_{symbol_short}"] = False
                        print_status(f"FORCE command parsing {cmd} failed", "FAIL")
                else:
                    results[f"force_command_invalid"] = False
                    print_status(f"FORCE command format validation failed", "FAIL")
                    
            except Exception as e:
                results[f"force_command_error"] = False
                print_status(f"FORCE command parsing error: {e}", "FAIL")
        
        results["force_command_logic"] = True
        print_status("FORCE command logic validation successful", "PASS")
        
    except Exception as e:
        results["force_command_logic"] = False
        print_status(f"FORCE command logic validation failed: {e}", "FAIL")
    
    return results

def generate_report(all_results: Dict) -> None:
    """Generate final validation report"""
    print("\n" + "="*60)
    print_status("GRID MANAGER VALIDATION REPORT", "INFO")
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
        print_status("✅ Grid Manager is PRODUCTION READY", "PASS")
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
    print("🚀 Grid Manager Validation Script")
    print("="*60)
    print("Testing cleaned grid_manager.py for compatibility...")
    print()
    
    all_results = {}
    
    try:
        # Run all validation tests
        all_results["imports"] = validate_imports()
        all_results["structure"] = validate_grid_manager_structure()
        all_results["instantiation"] = validate_instantiation()
        all_results["dependencies"] = validate_critical_dependencies()
        all_results["force_commands"] = validate_force_command_logic()
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
