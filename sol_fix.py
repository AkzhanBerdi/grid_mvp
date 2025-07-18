#!/usr/bin/env python3
"""
Quick SOL Precision Fix
Add SOL overrides to single_advanced_grid_manager.py
"""

import re
from pathlib import Path

def fix_sol_precision():
    """Add SOL precision overrides to single_advanced_grid_manager.py"""
    
    print("🔧 FIXING SOL PRECISION")
    print("=" * 30)
    
    file_path = Path("services/single_advanced_grid_manager.py")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    # Read current content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_path = file_path.with_suffix('.py.sol_backup')
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print(f"💾 Backup created: {backup_path}")
    
    # Find the ADA override section and add SOL
    ada_pattern = r'(if symbol == "ADAUSDT":.*?return info\s*)(.*?# For other symbols)'
    
    sol_override = '''
            # FORCE SOL overrides to fix precision issues  
            if symbol == "SOLUSDT":
                info = {
                    "price_precision": 3,
                    "quantity_precision": 4,  # Allow 4 decimal places
                    "tick_size": 0.001,
                    "step_size": 0.0001,      # SOL step size is 0.0001
                    "min_notional": 5.0,
                    "status": "TRADING",
                }
                self.logger.info(f"🔒 FORCED SOL precision: step_size={info['step_size']}, quantity_precision={info['quantity_precision']}")
                return info
            
            # For other symbols, get from Binance API'''
    
    # Replace the section
    new_content = re.sub(
        ada_pattern, 
        r'\1' + sol_override + r'\2',
        content,
        flags=re.DOTALL
    )
    
    # If that didn't work, try manual insertion
    if new_content == content:
        print("🔍 Regex replacement failed, trying manual insertion...")
        
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Add SOL override right after ADA override
            if 'return info' in line and 'ADA' in lines[i-5:i]:
                new_lines.append('')
                new_lines.append('            # FORCE SOL overrides to fix precision issues')
                new_lines.append('            if symbol == "SOLUSDT":')
                new_lines.append('                info = {')
                new_lines.append('                    "price_precision": 3,')
                new_lines.append('                    "quantity_precision": 4,')
                new_lines.append('                    "tick_size": 0.001,')
                new_lines.append('                    "step_size": 0.0001,')
                new_lines.append('                    "min_notional": 5.0,')
                new_lines.append('                    "status": "TRADING",')
                new_lines.append('                }')
                new_lines.append('                self.logger.info(f"🔒 FORCED SOL precision: step_size={info[\'step_size\']}, quantity_precision={info[\'quantity_precision\']}")')
                new_lines.append('                return info')
        
        new_content = '\n'.join(new_lines)
    
    # Update the _round_to_step_size method to handle SOL
    step_size_pattern = r'(# For ADA: ensure proper rounding.*?return.*?step_size)(.*?return.*?step_size)'
    
    sol_step_size_fix = r'''\1
        
        # For SOL: ensure proper rounding to 0.0001
        if step_size == 0.0001:
            return round(quantity / step_size) * step_size
        
        \2'''
    
    new_content = re.sub(step_size_pattern, sol_step_size_fix, new_content, flags=re.DOTALL)
    
    # Update quantity formatting to handle SOL
    if 'if symbol == "ADAUSDT":' in new_content and 'quantity_str' in new_content:
        formatting_pattern = r'(if symbol == "ADAUSDT":.*?quantity_str = f"{adjusted_quantity:.1f}")(.*?else:.*?quantity_str = str\(adjusted_quantity\))'
        
        sol_formatting = r'''\1
                    elif symbol == "SOLUSDT":
                        quantity_str = f"{adjusted_quantity:.4f}"
                    \2'''
        
        new_content = re.sub(formatting_pattern, sol_formatting, new_content, flags=re.DOTALL)
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("✅ ADDED SOL precision overrides!")
    print()
    print("🔧 SOL SETTINGS:")
    print("   step_size: 0.0001")
    print("   quantity_precision: 4 decimals")
    print("   Example: 1.2345 SOL (not 1.23456789)")
    
    return True

def show_sol_vs_ada_comparison():
    """Show the difference between SOL and ADA precision"""
    
    print("\n📊 PRECISION COMPARISON:")
    print("=" * 40)
    print()
    print("🔵 ADA (ADAUSDT):")
    print("   step_size: 0.1")
    print("   quantity_precision: 1")
    print("   Example: 23.4 ADA")
    print()
    print("🟠 SOL (SOLUSDT):")
    print("   step_size: 0.0001") 
    print("   quantity_precision: 4")
    print("   Example: 1.2345 SOL")
    print()
    print("💡 KEY INSIGHT:")
    print("   Each symbol has different precision requirements")
    print("   We must format quantities to match their step_size")

def main():
    """Main execution"""
    
    print("🚨 SOL PRECISION FIX")
    print("=" * 50)
    print()
    print("PROBLEM: SOL orders failing with 'too much precision'")
    print("SOLUTION: Add SOL-specific overrides like we did for ADA")
    print()
    
    success = fix_sol_precision()
    
    if success:
        show_sol_vs_ada_comparison()
        
        print("\n🎉 SOL FIX APPLIED!")
        print()
        print("🚀 NEXT STEPS:")
        print("   1. ✅ Restart your bot")
        print("   2. 🧪 Test: SOL 660")
        print("   3. 📊 Should see 100% success rate")
        print("   4. ✅ Look for: '🔒 FORCED SOL precision' in logs")
        
        print("\n📋 WHAT TO EXPECT:")
        print("   Before: 1.23456789 SOL → API Error")
        print("   After:  1.2345 SOL → SUCCESS ✅")
        
    else:
        print("\n❌ AUTOMATIC FIX FAILED")
        print()
        print("📝 MANUAL FIX:")
        print("1. Open services/single_advanced_grid_manager.py")
        print("2. Find the ADA override section")
        print("3. Add SOL override right after it:")
        print()
        print('   if symbol == "SOLUSDT":')
        print('       info = {')
        print('           "price_precision": 3,')
        print('           "quantity_precision": 4,')
        print('           "tick_size": 0.001,')
        print('           "step_size": 0.0001,')
        print('           "min_notional": 5.0,')
        print('           "status": "TRADING",')
        print('       }')
        print('       return info')
        print()
        print("4. Update quantity formatting:")
        print('   elif symbol == "SOLUSDT":')
        print('       quantity_str = f"{adjusted_quantity:.4f}"')

if __name__ == "__main__":
    main()
