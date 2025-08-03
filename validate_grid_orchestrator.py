#!/usr/bin/env python3
"""
Grid Orchestrator Validation Script
===================================

Quick validation of cleaned grid_orchestrator.py without stopping the running app.
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
    
    print_status("Testing grid orchestrator imports...", "INFO")
    
    # Test 1: Basic module import
    try:
        import services.grid_orchestrator
        results["module_import"] = True
        print_status("Module import successful", "PASS")
    except Exception as e:
        results["module_import"] = False
        print_status(f"Module import failed: {e}", "FAIL")
        return results
    
    # Test 2: GridOrchestrator class
    try:
        from services.grid_orchestrator import GridOrchestrator
        results["grid_orchestrator_class"] = True
        print_status("GridOrchestrator class import successful", "PASS")
    except Exception as e:
        results["grid_orchestrator_class"] = False
        print_status(f"GridOrchestrator class import failed: {e}", "FAIL")
    
    return results

def validate_singleton_pattern() -> Dict:
    """Test singleton pattern implementation"""
    results = {}
    
    print_status("Testing singleton pattern...", "INFO")
    
    try:
        from services.grid_orchestrator import GridOrchestrator
        
        # Test singleton behavior
        instance1 = GridOrchestrator()
        instance2 = GridOrchestrator()
        
        if instance1 is instance2:
            results["singleton_pattern"] = True
            print_status("Singleton pattern working correctly", "PASS")
        else:
            results["singleton_pattern"] = False
            print_status("Singleton pattern broken - multiple instances created", "FAIL")
        
        # Test get_instance class method
        instance3 = GridOrchestrator.get_instance()
        if instance1 is instance3:
            results["get_instance_method"] = True
            print_status("get_instance() method working correctly", "PASS")
        else:
            results["get_instance_method"] = False
            print_status("get_instance() method broken", "FAIL")
        
        # Test reset_instance (should work without errors)
        try:
            GridOrchestrator.reset_instance()
            results["reset_instance_method"] = True
            print_status("reset_instance() method working correctly", "PASS")
        except Exception as e:
            results["reset_instance_method"] = False
            print_status(f"reset_instance() method failed: {e}", "FAIL")
            
    except Exception as e:
        results["singleton_test"] = False
        print_status(f"Singleton pattern test failed: {e}", "FAIL")
    
    return results

def validate_grid_orchestrator_structure() -> Dict:
    """Test GridOrchestrator class structure"""
    results = {}
    
    print_status("Testing GridOrchestrator class structure...", "INFO")
    
    try:
        from services.grid_orchestrator import GridOrchestrator
        
        # Test required methods
        required_methods = [
            '__init__',
            'ensure_initialized',
            'get_client_binance_client',
            'create_advanced_manager',
            'force_start_grid',
            'stop_grid',
            'stop_all_client_grids',
            'get_all_active_grids',
            'update_all_grids',
            'get_client_grid_status',
            'start_monitoring',
            'stop_monitoring',
            'get_system_metrics'
        ]
        
        for method in required_methods:
            if hasattr(GridOrchestrator, method):
                results[f"grid_orchestrator_{method}"] = True
                print_status(f"GridOrchestrator.{method} exists", "PASS")
            else:
                results[f"grid_orchestrator_{method}"] = False
                print_status(f"GridOrchestrator.{method} missing", "FAIL")
                
        # Test private methods
        private_methods = [
            '_monitor_all_grids',
            '_perform_health_check'
        ]
        
        for method in private_methods:
            if hasattr(GridOrchestrator, method):
                results[f"grid_orchestrator_private_{method}"] = True
                print_status(f"GridOrchestrator.{method} exists", "PASS")
            else:
                results[f"grid_orchestrator_private_{method}"] = False
                print_status(f"GridOrchestrator.{method} missing", "FAIL")
        
        # Test compatibility methods
        compatibility_methods = [
            'start_client_grid',
            'stop_client_grid'
        ]
        
        for method in compatibility_methods:
            if hasattr(GridOrchestrator, method):
                results[f"compatibility_{method}"] = True
                print_status(f"Compatibility method {method} exists", "PASS")
            else:
                results[f"compatibility_{method}"] = False
                print_status(f"Compatibility method {method} missing", "FAIL")
                
    except Exception as e:
        print_status(f"GridOrchestrator structure test failed: {e}", "FAIL")
        
    return results

def validate_instantiation() -> Dict:
    """Test that GridOrchestrator can be instantiated"""
    results = {}
    
    print_status("Testing GridOrchestrator instantiation...", "INFO")
    
    try:
        from services.grid_orchestrator import GridOrchestrator
        
        # Reset singleton for clean test
        GridOrchestrator.reset_instance()
        
        # Test instantiation
        orchestrator = GridOrchestrator()
        results["grid_orchestrator_instantiation"] = True
        print_status("GridOrchestrator instantiation successful", "PASS")
        
        # Test key attributes exist
        key_attributes = [
            'logger', 'creation_id', 'client_repo', 'crypto_utils',
            'advanced_managers', 'binance_clients', 'fifo_service',
            'monitoring_active', 'last_health_check', 'system_metrics'
        ]
        
        for attr in key_attributes:
            if hasattr(orchestrator, attr):
                results[f"grid_orchestrator_attr_{attr}"] = True
                print_status(f"GridOrchestrator.{attr} attribute exists", "PASS")
            else:
                results[f"grid_orchestrator_attr_{attr}"] = False
                print_status(f"GridOrchestrator.{attr} attribute missing", "FAIL")
                
        # Test system_metrics structure
        if hasattr(orchestrator, 'system_metrics') and isinstance(orchestrator.system_metrics, dict):
            expected_metrics = [
                'total_grids_started', 'total_grids_stopped', 
                'total_force_commands', 'system_uptime_start'
            ]
            for metric in expected_metrics:
                if metric in orchestrator.system_metrics:
                    results[f"metric_{metric}"] = True
                    print_status(f"System metric {metric} exists", "PASS")
                else:
                    results[f"metric_{metric}"] = False
                    print_status(f"System metric {metric} missing", "FAIL")
        
        # Test collections are initialized as dicts
        dict_attributes = ['advanced_managers', 'binance_clients']
        for attr in dict_attributes:
            if hasattr(orchestrator, attr) and isinstance(getattr(orchestrator, attr), dict):
                results[f"dict_{attr}"] = True
                print_status(f"{attr} initialized as dict", "PASS")
            else:
                results[f"dict_{attr}"] = False
                print_status(f"{attr} not initialized as dict", "FAIL")
                
        # Test ensure_initialized method
        try:
            orchestrator.ensure_initialized()
            results["ensure_initialized_works"] = True
            print_status("ensure_initialized() method works", "PASS")
        except Exception as e:
            results["ensure_initialized_works"] = False
            print_status(f"ensure_initialized() failed: {e}", "FAIL")
            
    except Exception as e:
        results["grid_orchestrator_instantiation"] = False
        print_status(f"GridOrchestrator instantiation failed: {e}", "FAIL")
    
    return results

def validate_removed_debug_code() -> Dict:
    """Verify that debug code was properly removed"""
    results = {}
    
    print_status("Checking for removed debug code...", "INFO")
    
    try:
        with open('services/grid_orchestrator.py', 'r') as f:
            content = f.read()
        
        # Patterns that should NOT exist (debug code)
        forbidden_patterns = [
            '_log_access',
            'self._log_access(',
            '🔍 GridOrchestrator',
            '🔍 DEBUG:',
            'DEBUG 2:',
            'Before executing force command',
            'After error for client',
            'logger.debug(f"🔍',
            'with corruption detection',
            'Enhanced update_all_grids method with debugging',
            'corruption prevention',
            '🔧 FIXED:',
            'corruption detection'
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
            'class GridOrchestrator:',
            'def force_start_grid',
            'def stop_grid',
            'def get_all_active_grids',
            'def update_all_grids',
            'def start_monitoring',
            'def stop_monitoring',
            'Singleton pattern',
            'self.advanced_managers: Dict[int, GridManager]',
            'self.system_metrics'
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
            'self.logger.debug(',
            'logger.debug(',
            '🔍 DEBUG',
            'After error'
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
        ('models.client', 'GridStatus'),
        ('repositories.client_repository', 'ClientRepository'),
        ('services.fifo_service', 'FIFOService'),
        ('services.grid_manager', 'GridManager'),
        ('utils.crypto', 'CryptoUtils'),
        ('typing', 'Dict'),
        ('typing', 'Optional'),
        ('asyncio', None),
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

def validate_force_command_integration() -> Dict:
    """Test FORCE command integration logic"""
    results = {}
    
    print_status("Testing FORCE command integration...", "INFO")
    
    try:
        from services.grid_orchestrator import GridOrchestrator
        
        # Reset singleton for clean test
        GridOrchestrator.reset_instance()
        orchestrator = GridOrchestrator()
        
        # Test that force_start_grid method exists and accepts correct parameters
        try:
            # We won't actually call it, just verify the method signature
            import inspect
            sig = inspect.signature(orchestrator.force_start_grid)
            params = list(sig.parameters.keys())
            
            if 'client_id' in params and 'command' in params:
                results["force_command_signature"] = True
                print_status("force_start_grid method signature correct", "PASS")
            else:
                results["force_command_signature"] = False
                print_status(f"force_start_grid method signature incorrect: {params}", "FAIL")
                
        except Exception as e:
            results["force_command_signature"] = False
            print_status(f"force_start_grid method signature check failed: {e}", "FAIL")
        
        # Test compatibility methods exist
        compatibility_methods = ['start_client_grid', 'stop_client_grid']
        for method in compatibility_methods:
            if hasattr(orchestrator, method):
                results[f"compatibility_{method}"] = True
                print_status(f"Compatibility method {method} exists", "PASS")
            else:
                results[f"compatibility_{method}"] = False
                print_status(f"Compatibility method {method} missing", "FAIL")
        
        results["force_command_integration"] = True
        print_status("FORCE command integration validation successful", "PASS")
        
    except Exception as e:
        results["force_command_integration"] = False
        print_status(f"FORCE command integration validation failed: {e}", "FAIL")
    
    return results

def validate_monitoring_system() -> Dict:
    """Test monitoring system components"""
    results = {}
    
    print_status("Testing monitoring system...", "INFO")
    
    try:
        from services.grid_orchestrator import GridOrchestrator
        
        # Reset singleton for clean test
        GridOrchestrator.reset_instance()
        orchestrator = GridOrchestrator()
        
        # Test monitoring attributes
        if hasattr(orchestrator, 'monitoring_active'):
            if isinstance(orchestrator.monitoring_active, bool):
                results["monitoring_active_attr"] = True
                print_status("monitoring_active attribute exists and is boolean", "PASS")
            else:
                results["monitoring_active_attr"] = False
                print_status("monitoring_active attribute exists but is not boolean", "FAIL")
        else:
            results["monitoring_active_attr"] = False
            print_status("monitoring_active attribute missing", "FAIL")
        
        # Test monitoring methods
        monitoring_methods = ['start_monitoring', 'stop_monitoring', '_monitor_all_grids', '_perform_health_check']
        for method in monitoring_methods:
            if hasattr(orchestrator, method):
                results[f"monitoring_{method}"] = True
                print_status(f"Monitoring method {method} exists", "PASS")
            else:
                results[f"monitoring_{method}"] = False
                print_status(f"Monitoring method {method} missing", "FAIL")
        
        # Test health check attributes
        if hasattr(orchestrator, 'last_health_check'):
            results["health_check_attr"] = True
            print_status("last_health_check attribute exists", "PASS")
        else:
            results["health_check_attr"] = False
            print_status("last_health_check attribute missing", "FAIL")
        
        results["monitoring_system"] = True
        print_status("Monitoring system validation successful", "PASS")
        
    except Exception as e:
        results["monitoring_system"] = False
        print_status(f"Monitoring system validation failed: {e}", "FAIL")
    
    return results

def generate_report(all_results: Dict) -> None:
    """Generate final validation report"""
    print("\n" + "="*60)
    print_status("GRID ORCHESTRATOR VALIDATION REPORT", "INFO")
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
        print_status("✅ Grid Orchestrator is PRODUCTION READY", "PASS")
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
    print("🚀 Grid Orchestrator Validation Script")
    print("="*60)
    print("Testing cleaned grid_orchestrator.py for compatibility...")
    print()
    
    all_results = {}
    
    try:
        # Run all validation tests
        all_results["imports"] = validate_imports()
        all_results["singleton"] = validate_singleton_pattern()
        all_results["structure"] = validate_grid_orchestrator_structure()
        all_results["instantiation"] = validate_instantiation()
        all_results["dependencies"] = validate_critical_dependencies()
        all_results["force_commands"] = validate_force_command_integration()
        all_results["monitoring"] = validate_monitoring_system()
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
