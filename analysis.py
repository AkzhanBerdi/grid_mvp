#!/usr/bin/env python3
"""
Method Usage Analysis Tool for SingleAdvancedGridManager
Analyzes which methods are actually called vs defined to identify dead code
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


class MethodUsageAnalyzer:
    """Analyzes method usage patterns in SingleAdvancedGridManager"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.defined_methods: Set[str] = set()
        self.called_methods: Set[str] = set()
        self.method_locations: Dict[str, List[str]] = {}
        self.external_calls: Dict[str, List[str]] = {}
        
    def analyze_single_advanced_grid_manager(self) -> Dict:
        """
        Main analysis method for SingleAdvancedGridManager
        Returns comprehensive usage analysis
        """
        print("🔍 **ANALYZING SingleAdvancedGridManager METHOD USAGE**")
        print("=" * 60)
        
        # Step 1: Extract all method definitions from the main file
        self._extract_method_definitions()
        
        # Step 2: Find all method calls throughout the project
        self._find_method_calls()
        
        # Step 3: Identify dead code
        dead_methods = self._identify_dead_methods()
        
        # Step 4: Categorize methods by usage pattern
        usage_categories = self._categorize_methods()
        
        # Step 5: Generate comprehensive report
        return self._generate_analysis_report(dead_methods, usage_categories)
    
    def _extract_method_definitions(self):
        """Extract all method definitions from SingleAdvancedGridManager"""
        print("\n1️⃣ **EXTRACTING METHOD DEFINITIONS**")
        
        sgm_file = self.project_root / "services/single_advanced_grid_manager.py"
        if not sgm_file.exists():
            print(f"❌ File not found: {sgm_file}")
            return
            
        with open(sgm_file, 'r') as f:
            content = f.read()
        
        # Pattern to match method definitions
        method_pattern = r'^\s*(async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        
        for line_num, line in enumerate(content.split('\n'), 1):
            match = re.match(method_pattern, line)
            if match:
                method_name = match.group(2)
                self.defined_methods.add(method_name)
                
                if method_name not in self.method_locations:
                    self.method_locations[method_name] = []
                
                self.method_locations[method_name].append(
                    f"single_advanced_grid_manager.py:{line_num}"
                )
        
        print(f"   ✅ Found {len(self.defined_methods)} method definitions")
        
        # Log some method names for verification
        print(f"   📝 Sample methods: {list(self.defined_methods)[:5]}...")
    
    def _find_method_calls(self):
        """Find all method calls throughout the project"""
        print("\n2️⃣ **SCANNING FOR METHOD CALLS**")
        
        # Files to scan for method usage
        scan_patterns = [
            "services/*.py",
            "handlers/*.py", 
            "utils/*.py",
            "main.py",
            "repositories/*.py"
        ]
        
        total_files_scanned = 0
        
        for pattern in scan_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and file_path.suffix == '.py':
                    self._scan_file_for_calls(file_path)
                    total_files_scanned += 1
        
        print(f"   ✅ Scanned {total_files_scanned} Python files")
        print(f"   📞 Found {len(self.called_methods)} unique method calls")
    
    def _scan_file_for_calls(self, file_path: Path):
        """Scan a single file for method calls"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Look for method calls in various patterns
            call_patterns = [
                # Direct method calls: self.method_name(
                r'self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                # Manager method calls: manager.method_name(
                r'manager\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                # Advanced manager calls: advanced_manager.method_name(
                r'advanced_manager\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                # await calls: await self.method_name(
                r'await\s+self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                r'await\s+manager\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
            ]
            
            for pattern in call_patterns:
                matches = re.findall(pattern, content)
                for method_name in matches:
                    if method_name in self.defined_methods:
                        self.called_methods.add(method_name)
                        
                        if method_name not in self.external_calls:
                            self.external_calls[method_name] = []
                        
                        self.external_calls[method_name].append(str(file_path))
        
        except Exception as e:
            print(f"   ⚠️ Error scanning {file_path}: {e}")
    
    def _identify_dead_methods(self) -> Set[str]:
        """Identify methods that are defined but never called"""
        dead_methods = self.defined_methods - self.called_methods
        
        # Remove special methods that shouldn't be considered dead
        special_methods = {
            '__init__', '__del__', '__str__', '__repr__',
            'get_force_command_allocation'  # Module-level function
        }
        
        # Remove obvious lifecycle methods that might not show up in basic scanning
        lifecycle_methods = {
            'start_single_advanced_grid',  # Main entry point
            'stop_single_advanced_grid',   # Main exit point
            'handle_force_command',        # Command handler
            'monitor_and_update_grids',    # Main monitoring loop
        }
        
        dead_methods = dead_methods - special_methods - lifecycle_methods
        
        return dead_methods
    
    def _categorize_methods(self) -> Dict:
        """Categorize methods by usage patterns"""
        categories = {
            'public_api': set(),      # Public interface methods
            'internal_only': set(),   # Called only within the class
            'external_only': set(),   # Called only from outside
            'mixed_usage': set(),     # Called both internally and externally
            'dead_code': set()        # Not called anywhere
        }
        
        for method in self.defined_methods:
            if method in self.called_methods:
                # Check if called externally
                external_callers = self.external_calls.get(method, [])
                has_external_calls = any(
                    'single_advanced_grid_manager.py' not in caller 
                    for caller in external_callers
                )
                
                # Check if called internally (this requires more complex analysis)
                # For now, assume methods starting with _ are internal
                if method.startswith('_'):
                    if has_external_calls:
                        categories['mixed_usage'].add(method)
                    else:
                        categories['internal_only'].add(method)
                else:
                    if has_external_calls:
                        categories['public_api'].add(method)
                    else:
                        categories['external_only'].add(method)
            else:
                categories['dead_code'].add(method)
        
        return categories
    
    def _generate_analysis_report(self, dead_methods: Set[str], categories: Dict) -> Dict:
        """Generate comprehensive analysis report"""
        print("\n3️⃣ **GENERATING ANALYSIS REPORT**")
        
        report = {
            'summary': {
                'total_methods_defined': len(self.defined_methods),
                'total_methods_called': len(self.called_methods),
                'dead_methods_count': len(dead_methods),
                'dead_code_percentage': len(dead_methods) / len(self.defined_methods) * 100,
            },
            'dead_methods': sorted(list(dead_methods)),
            'categories': {k: sorted(list(v)) for k, v in categories.items()},
            'detailed_analysis': self._generate_detailed_analysis(dead_methods),
            'refactoring_recommendations': self._generate_recommendations(dead_methods, categories)
        }
        
        # Print summary
        print(f"   📊 Total Methods: {report['summary']['total_methods_defined']}")
        print(f"   ✅ Called Methods: {report['summary']['total_methods_called']}")
        print(f"   💀 Dead Methods: {report['summary']['dead_methods_count']}")
        print(f"   📈 Dead Code %: {report['summary']['dead_code_percentage']:.1f}%")
        
        return report
    
    def _generate_detailed_analysis(self, dead_methods: Set[str]) -> Dict:
        """Generate detailed analysis of dead methods"""
        analysis = {
            'potentially_safe_to_remove': [],
            'needs_investigation': [],
            'might_be_event_handlers': []
        }
        
        for method in dead_methods:
            if method.startswith('_') and 'handle' not in method:
                analysis['potentially_safe_to_remove'].append(method)
            elif 'handle' in method or 'callback' in method:
                analysis['might_be_event_handlers'].append(method)
            else:
                analysis['needs_investigation'].append(method)
        
        return analysis
    
    def _generate_recommendations(self, dead_methods: Set[str], categories: Dict) -> List[str]:
        """Generate refactoring recommendations"""
        recommendations = []
        
        if len(dead_methods) > 10:
            recommendations.append(
                "🚨 HIGH PRIORITY: Remove dead methods to reduce file size significantly"
            )
        
        if len(categories['internal_only']) > 20:
            recommendations.append(
                "📦 REFACTOR: Extract internal utility methods to separate utility class"
            )
        
        if len(categories['public_api']) > 15:
            recommendations.append(
                "🎯 INTERFACE: Consider splitting public API across multiple service classes"
            )
        
        recommendations.extend([
            f"💀 Remove {len(dead_methods)} dead methods (~{len(dead_methods) * 10} lines)",
            "🔧 Extract utility methods to reduce complexity",
            "📚 Group related methods into focused service classes",
            "✅ Start with dead code removal (safest refactoring step)"
        ])
        
        return recommendations

def main():
    """Run the method usage analysis"""
    analyzer = MethodUsageAnalyzer()
    report = analyzer.analyze_single_advanced_grid_manager()
    
    print("\n" + "="*60)
    print("📋 **FINAL ANALYSIS REPORT**")
    print("="*60)
    
    print(f"\n📊 **SUMMARY**")
    for key, value in report['summary'].items():
        if isinstance(value, float):
            print(f"   {key}: {value:.1f}%")
        else:
            print(f"   {key}: {value}")
    
    print(f"\n💀 **DEAD METHODS** ({len(report['dead_methods'])}):")
    for method in report['dead_methods'][:10]:  # Show first 10
        print(f"   - {method}()")
    if len(report['dead_methods']) > 10:
        print(f"   ... and {len(report['dead_methods']) - 10} more")
    
    print(f"\n🎯 **REFACTORING RECOMMENDATIONS**:")
    for rec in report['refactoring_recommendations']:
        print(f"   • {rec}")
    
    print(f"\n⚡ **NEXT STEPS**:")
    print(f"   1. Remove dead methods first (safest)")
    print(f"   2. Extract utility methods to separate class")  
    print(f"   3. Split public API into focused services")
    print(f"   4. Test thoroughly after each change")
    
    return report

if __name__ == "__main__":
    main()
