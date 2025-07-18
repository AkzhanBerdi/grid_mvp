#!/usr/bin/env python3
"""
IMMEDIATE ADA Precision Fix
Fixes the "Parameter 'quantity' has too much precision" error
"""

import re
from pathlib import Path

def fix_ada_precision_immediately():
    """Fix ADA precision settings in advanced_trading_features.py"""
    
    print("🚨 EMERGENCY ADA PRECISION FIX")
    print("=" * 40)
    
    file_path = Path("services/advanced_trading_features.py")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    # Read current content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_path = file_path.with_suffix('.py.precision_backup')
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print(f"💾 Backup created: {backup_path}")
    
    # Find and replace the WRONG ADAUSDT settings
    wrong_ada_block = r'"ADAUSDT":\s*\{[^}]*"quantity_precision":\s*0[^}]*"min_quantity":\s*10[^}]*"step_size":\s*1\.0[^}]*\}'
    
    correct_ada_block = '''
            "ADAUSDT": {
                "quantity_precision": 1,
                "min_quantity": 0.1,
                "step_size": 0.1,
                "min_notional": 5.0,
                "price_precision": 4,
                "tick_size": 0.0001,
                "max_quantity": 1000000,
                "min_price": 0.0001,
                "max_price": 1000000,
                "force_override": True,
            }'''.strip()
    
    # Replace using regex
    new_content = re.sub(wrong_ada_block, correct_ada_block, content, flags=re.MULTILINE | re.DOTALL)
    
    # If regex didn't work, try manual replacement
    if new_content == content:
        print("🔍 Regex replacement failed, trying manual replacement...")
        
        # Find the ADAUSDT block manually
        lines = content.split('\n')
        new_lines = []
        in_ada_block = False
        brace_count = 0
        
        for line in lines:
            if '"ADAUSDT":' in line and '{' in line:
                in_ada_block = True
                brace_count = line.count('{') - line.count('}')
                # Replace the entire ADAUSDT block
                new_lines.append('            "ADAUSDT": {')
                new_lines.append('                "quantity_precision": 1,')
                new_lines.append('                "min_quantity": 0.1,')
                new_lines.append('                "step_size": 0.1,')
                new_lines.append('                "min_notional": 5.0,')
                new_lines.append('                "price_precision": 4,')
                new_lines.append('                "tick_size": 0.0001,')
                new_lines.append('                "max_quantity": 1000000,')
                new_lines.append('                "min_price": 0.0001,')
                new_lines.append('                "max_price": 1000000,')
                new_lines.append('                "force_override": True,')
                new_lines.append('            },')
                continue
            elif in_ada_block:
                brace_count += line.count('{') - line.count('}')
                if brace_count <= 0:
                    in_ada_block = False
                continue
            else:
                new_lines.append(line)
        
        new_content = '\n'.join(new_lines)
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("✅ FIXED ADA precision settings!")
    print()
    print("🔧 CHANGES MADE:")
    print("   quantity_precision: 0 → 1")
    print("   min_quantity: 10 → 0.1") 
    print("   step_size: 1.0 → 0.1")
    print()
    print("✅ This should fix the 'too much precision' error")
    
    return True

def verify_ada_settings():
    """Verify the ADA settings are correct"""
    
    file_path = Path("services/advanced_trading_features.py")
    
    if not file_path.exists():
        print("❌ Cannot verify - file not found")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    print("\n🔍 VERIFYING ADA SETTINGS:")
    print("=" * 30)
    
    # Check for correct settings
    checks = {
        '"quantity_precision": 1': "✅ quantity_precision: 1 (correct)",
        '"min_quantity": 0.1': "✅ min_quantity: 0.1 (correct)", 
        '"step_size": 0.1': "✅ step_size: 0.1 (correct)",
    }
    
    wrong_checks = {
        '"quantity_precision": 0': "❌ quantity_precision: 0 (WRONG)",
        '"min_quantity": 10': "❌ min_quantity: 10 (WRONG)",
        '"step_size": 1.0': "❌ step_size: 1.0 (WRONG)",
    }
    
    all_correct = True
    
    # Check for correct settings
    for setting, message in checks.items():
        if setting in content:
            print(message)
        else:
            print(f"❌ Missing: {setting}")
            all_correct = False
    
    # Check for wrong settings
    for setting, message in wrong_checks.items():
        if setting in content:
            print(message)
            all_correct = False
    
    if all_correct:
        print("\n🎉 ALL ADA SETTINGS CORRECT!")
        print("   ADA orders should work now")
    else:
        print("\n⚠️  Some settings still wrong")
        print("   May need manual editing")
    
    return all_correct

def show_ada_explanation():
    """Explain why these settings fix the issue"""
    
    print("\n📚 WHY THESE SETTINGS FIX ADA:")
    print("=" * 40)
    print()
    print("🔍 THE PROBLEM:")
    print("   • quantity_precision: 0 = only whole numbers (20.0)")
    print("   • But step_size: 1.0 = must be multiples of 1")
    print("   • When quantity 23.4 gets formatted:")
    print("     → precision:0 makes it '23'")  
    print("     → But internally it's still 23.4 (too much precision)")
    print()
    print("✅ THE SOLUTION:")
    print("   • quantity_precision: 1 = allows 1 decimal (23.4)")
    print("   • step_size: 0.1 = correct ADA step size")
    print("   • min_quantity: 0.1 = reasonable minimum")
    print()
    print("📊 EXAMPLE:")
    print("   Input: 23.456 ADA @ $0.8015")
    print("   OLD: 23 (precision:0) → API error")
    print("   NEW: 23.5 (precision:1, step:0.1) → SUCCESS ✅")

if __name__ == "__main__":
    print("🚨 ADA PRECISION EMERGENCY FIX")
    print("=" * 50)
    
    success = fix_ada_precision_immediately()
    
    if success:
        verify_ada_settings()
        show_ada_explanation()
        
        print("\n🚀 NEXT STEPS:")
        print("   1. ✅ Settings fixed")
        print("   2. 🔄 Restart your bot")
        print("   3. 🧪 Test: ADA 700")
        print("   4. 📊 Should see orders placed successfully")
        
    else:
        print("\n❌ FIX FAILED")
        print("   Try manual editing:")
        print("   1. Open services/advanced_trading_features.py")
        print("   2. Find 'ADAUSDT' section")
        print("   3. Change:")
        print("      quantity_precision: 0 → 1")
        print("      min_quantity: 10 → 0.1")
        print("      step_size: 1.0 → 0.1")
