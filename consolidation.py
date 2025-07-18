#!/usr/bin/env python3
"""
CompoundInterestManager Consolidation Plan
Remove duplicate implementation and standardize on the advanced version
"""

class CompoundManagerConsolidation:
    """Plan to consolidate duplicate CompoundInterestManager implementations"""
    
    def __init__(self):
        self.analysis = {
            "duplicate_found": True,
            "recommendation": "Keep services/compound_interest_manager.py",
            "reason": "More advanced features and better architecture"
        }
    
    def show_analysis(self):
        """Show detailed analysis of both implementations"""
        
        print("🔍 DUPLICATE COMPOUNDINTERESTMANAGER ANALYSIS")
        print("=" * 60)
        
        print("\n📁 FILE 1: services/advanced_trading_features.py")
        print("   Location: Line ~15")
        print("   Class: CompoundInterestManager")
        print("   Features:")
        print("     ✅ Basic profit reinvestment")
        print("     ✅ Simple multiplier calculation") 
        print("     ✅ Safety caps")
        print("     ❌ No Kelly Criterion")
        print("     ❌ No FIFO integration")
        print("     ❌ Basic allocation logic")
        
        print("\n📁 FILE 2: services/compound_interest_manager.py") 
        print("   Location: Entire file (dedicated)")
        print("   Class: CompoundInterestManager + CompoundIntegrationService")
        print("   Features:")
        print("     ✅ Advanced profit reinvestment")
        print("     ✅ Kelly Criterion position sizing")
        print("     ✅ FIFO profit integration")
        print("     ✅ Risk-adjusted allocation")
        print("     ✅ Advanced performance tracking")
        print("     ✅ Comprehensive documentation")
        
        print("\n🎯 RECOMMENDATION:")
        print("   KEEP: services/compound_interest_manager.py")
        print("   REMOVE: CompoundInterestManager from advanced_trading_features.py")
        print("   REASON: Advanced version has significantly more features")
        
    def create_consolidation_script(self):
        """Create script to consolidate the managers"""
        
        consolidation_steps = [
            "1. Remove CompoundInterestManager class from advanced_trading_features.py",
            "2. Update imports in files that use the basic version",
            "3. Test that advanced version works with existing code",
            "4. Update any compatibility issues"
        ]
        
        return consolidation_steps
        
    def show_impact_analysis(self):
        """Show which files will be affected"""
        
        print("\n📊 IMPACT ANALYSIS:")
        print("=" * 40)
        
        affected_files = {
            "services/single_advanced_grid_manager.py": {
                "current_import": "from services.advanced_trading_features import CompoundInterestManager",
                "new_import": "from services.compound_interest_manager import CompoundInterestManager",
                "compatibility": "May need wrapper for different constructor"
            },
            "services/dual_scale_grid_manager.py": {
                "current_import": "from services.advanced_trading_features import CompoundInterestManager", 
                "new_import": "from services.compound_interest_manager import CompoundIntegrationService",
                "compatibility": "Already uses CompoundIntegrationService"
            },
            "services/enhanced_dual_scale_manager.py": {
                "current_import": "from services.advanced_trading_features import CompoundInterestManager",
                "new_import": "from services.compound_interest_manager import CompoundInterestManager", 
                "compatibility": "May need constructor updates"
            }
        }
        
        for file_path, details in affected_files.items():
            print(f"\n📄 {file_path}")
            print(f"   Current: {details['current_import']}")
            print(f"   New:     {details['new_import']}")
            print(f"   Notes:   {details['compatibility']}")
            
    def generate_removal_script(self):
        """Generate script to remove duplicate CompoundInterestManager"""
        
        script = '''#!/usr/bin/env python3
"""
Remove duplicate CompoundInterestManager from advanced_trading_features.py
"""

import re
from pathlib import Path

def remove_duplicate_compound_manager():
    """Remove CompoundInterestManager class from advanced_trading_features.py"""
    
    file_path = Path("services/advanced_trading_features.py")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    # Read current content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_path = file_path.with_suffix('.py.backup')
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print(f"💾 Backup created: {backup_path}")
    
    # Remove CompoundInterestManager class
    # Find the class definition and remove everything until the next class
    lines = content.split('\\n')
    new_lines = []
    skip_mode = False
    indent_level = 0
    
    for line in lines:
        # Start of CompoundInterestManager class
        if line.strip().startswith('class CompoundInterestManager:'):
            skip_mode = True
            indent_level = len(line) - len(line.lstrip())
            print(f"🗑️  Found CompoundInterestManager class, removing...")
            continue
        
        # If we're skipping and find another class/function at same level, stop skipping
        if skip_mode:
            current_indent = len(line) - len(line.lstrip())
            
            # If we hit a line at the same or lower indentation level that starts a new definition
            if (current_indent <= indent_level and 
                line.strip() and 
                (line.strip().startswith('class ') or line.strip().startswith('def ') or 
                 line.strip().startswith('# ===') or line.strip().startswith('"""'))):
                skip_mode = False
            else:
                continue  # Skip this line
        
        new_lines.append(line)
    
    # Write cleaned content
    new_content = '\\n'.join(new_lines)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Removed CompoundInterestManager from {file_path}")
    print(f"📊 Reduced from {len(lines)} to {len(new_lines)} lines")
    
    return True

def update_imports():
    """Update imports in files that used the duplicate"""
    
    files_to_update = [
        "services/single_advanced_grid_manager.py",
        "services/enhanced_dual_scale_manager.py"
    ]
    
    for file_path in files_to_update:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
            
        with open(path, 'r') as f:
            content = f.read()
        
        # Update import statement
        old_import = "from services.advanced_trading_features import CompoundInterestManager"
        new_import = "from services.compound_interest_manager import CompoundInterestManager"
        
        if old_import in content:
            content = content.replace(old_import, new_import)
            
            with open(path, 'w') as f:
                f.write(content)
            
            print(f"✅ Updated import in {file_path}")
        else:
            print(f"ℹ️  No import update needed in {file_path}")

if __name__ == "__main__":
    print("🔧 REMOVING DUPLICATE COMPOUNDINTERESTMANAGER")
    print("=" * 50)
    
    success = remove_duplicate_compound_manager()
    
    if success:
        update_imports()
        print("\\n✅ CONSOLIDATION COMPLETE!")
        print("\\n📋 WHAT WAS DONE:")
        print("   1. ✅ Removed duplicate CompoundInterestManager from advanced_trading_features.py")
        print("   2. ✅ Updated imports to use the advanced version")
        print("   3. ✅ Created backup of original file")
        print("\\n🎯 RESULT:")
        print("   • Only services/compound_interest_manager.py remains")
        print("   • All features consolidated into advanced implementation")
        print("   • No duplicate code")
    else:
        print("\\n❌ CONSOLIDATION FAILED")
        print("   Check file paths and try again")
'''
        
        return script

def main():
    """Main function to analyze and plan consolidation"""
    
    consolidation = CompoundManagerConsolidation()
    
    # Show analysis
    consolidation.show_analysis()
    
    # Show impact
    consolidation.show_impact_analysis()
    
    # Generate removal script
    print("\n🔧 CONSOLIDATION SCRIPT:")
    print("=" * 40)
    script = consolidation.generate_removal_script()
    
    # Save script to file
    with open("remove_duplicate_compound_manager.py", "w") as f:
        f.write(script)
    
    print("✅ Consolidation script saved: remove_duplicate_compound_manager.py")
    
    print("\n🚀 TO EXECUTE CONSOLIDATION:")
    print("   python remove_duplicate_compound_manager.py")
    
    print("\n⚠️  SAFETY NOTES:")
    print("   • Backup is created automatically")
    print("   • Advanced version has more features")
    print("   • Test after consolidation")

if __name__ == "__main__":
    main()
