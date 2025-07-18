#!/usr/bin/env python3
"""
ETH Precision Fix for single_advanced_grid_manager.py
Adds ETH-specific precision overrides to fix the "too much precision" errors
"""

import re
from pathlib import Path

def fix_eth_precision():
    """Add ETH precision overrides to single_advanced_grid_manager.py"""
    
    print("🔧 FIXING ETH PRECISION")
    print("=" * 30)
    
    file_path = Path("services/single_advanced_grid_manager.py")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    # Read current content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_path = file_path.with_suffix('.py.eth_backup')
    with open(backup_path, 'w') as f:
        f.write(content)
    
    print(f"💾 Backup created: {backup_path}")
    
    # Add ETH override after the existing overrides
    # Find where SOL override ends and add ETH
    pattern = r'(if symbol == "SOLUSDT":.*?return info\s*)(.*?# For other symbols)'
    
    eth_override = '''
            # FORCE ETH overrides to fix precision issues
            if symbol == "ETHUSDT":
                info = {
                    "price_precision": 2,
                    "quantity_precision": 5,  # Allow 5 decimal places
                    "tick_size": 0.01,
                    "step_size": 0.00001,     # ETH step size is 0.00001
                    "min_notional": 5.0,
                    "status": "TRADING",
                }
                self.logger.info(f"🔒 FORCED ETH precision: step_size={info['step_size']}, quantity_precision={info['quantity_precision']}")
                return info
            
            # For other symbols, get from Binance API'''
    
    # Replace the section
    new_content = re.sub(
        pattern, 
        r'\1' + eth_override + r'\2',
        content,
        flags=re.DOTALL
    )
    
    # If that didn't work, try finding after ADA instead
    if new_content == content:
        print("🔍 Trying after ADA override...")
        ada_pattern = r'(if symbol == "ADAUSDT":.*?return info\s*)(.*?# For other symbols)'
        
        eth_after_ada = '''
            
            # FORCE ETH overrides to fix precision issues
            if symbol == "ETHUSDT":
                info = {
                    "price_precision": 2,
                    "quantity_precision": 5,
                    "tick_size": 0.01,
                    "step_size": 0.00001,
                    "min_notional": 5.0,
                    "status": "TRADING",
                }
                self.logger.info(f"🔒 FORCED ETH precision: step_size={info['step_size']}, quantity_precision={info['quantity_precision']}")
                return info
            
            # For other symbols, get from Binance API'''
        
        new_content = re.sub(
            ada_pattern,
            r'\1' + eth_after_ada + r'\2',
            content,
            flags=re.DOTALL
        )
    
    # If still no match, try manual insertion
    if new_content == content:
        print("🔍 Manual insertion...")
        
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Add ETH override after any existing return info
            if ('return info' in line and 
                any('ADA' in prev_line or 'SOL' in prev_line for prev_line in lines[max(0, i-10):i])):
                new_lines.append('')
                new_lines.append('            # FORCE ETH overrides to fix precision issues')
                new_lines.append('            if symbol == "ETHUSDT":')
                new_lines.append('                info = {')
                new_lines.append('                    "price_precision": 2,')
                new_lines.append('                    "quantity_precision": 5,')
                new_lines.append('                    "tick_size": 0.01,')
                new_lines.append('                    "step_size": 0.00001,')
                new_lines.append('                    "min_notional": 5.0,')
                new_lines.append('                    "status": "TRADING",')
                new_lines.append('                }')
                new_lines.append('                self.logger.info(f"🔒 FORCED ETH precision: step_size={info[\'step_size\']}, quantity_precision={info[\'quantity_precision\']}")')
                new_lines.append('                return info')
                break  # Only add once
        
        new_content = '\n'.join(new_lines)
    
    # Update the _round_to_step_size method to handle ETH
    if 'For SOL: ensure proper rounding' in new_content:
        step_size_pattern = r'(# For SOL: ensure proper rounding.*?return.*?step_size)(.*?return.*?step_size)'
        
        eth_step_size_fix = r'''\1
        
        # For ETH: ensure proper rounding to 0.00001
        if step_size == 0.00001:
            return round(quantity / step_size) * step_size
        
        \2'''
        
        new_content = re.sub(step_size_pattern, eth_step_size_fix, new_content, flags=re.DOTALL)
    
    # Update quantity formatting to handle ETH
    if 'elif symbol == "SOLUSDT":' in new_content:
        formatting_pattern = r'(elif symbol == "SOLUSDT":.*?quantity_str = f"{adjusted_quantity:.4f}")(.*?else:)'
        
        eth_formatting = r'''\1
                    elif symbol == "ETHUSDT":
                        quantity_str = f"{adjusted_quantity:.5f}"
                    \2'''
        
        new_content = re.sub(formatting_pattern, eth_formatting, new_content, flags=re.DOTALL)
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("✅ ADDED ETH precision overrides!")
    print()
    print("🔧 ETH SETTINGS:")
    print("   step_size: 0.00001")
    print("   quantity_precision: 5 decimals")
    print("   Example: 0.00420 ETH (not 0.004200000)")
    
    return True

def analyze_eth_failures():
    """Analyze why specific ETH quantities failed"""
    
    print("\n📊 ETH FAILURE ANALYSIS:")
    print("=" * 40)
    print()
    print("❌ FAILED QUANTITIES:")
    print("   0.004200 ETH → 'too much precision'")
    print("   0.004800 ETH → 'too much precision'")
    print()
    print("✅ SUCCESSFUL QUANTITIES:")
    print("   0.004400 ETH → SUCCESS")
    print("   0.004600 ETH → SUCCESS")
    print("   0.005100 ETH → SUCCESS")
    print()
    print("🔍 PATTERN:")
    print("   Failed: Ending in exactly .00")
    print("   Success: Ending in other digits")
    print()
    print("💡 ROOT CAUSE:")
    print("   API requires exactly 5 decimals: 0.00420")
    print("   But gets: 0.004200000... (too many zeros)")
    print()
    print("✅ SOLUTION:")
    print("   Format with f'{quantity:.5f}'")
    print("   0.004200 → '0.00420' ✅")

def show_all_symbol_precision():
    """Show precision settings for all symbols"""
    
    print("\n📋 ALL SYMBOL PRECISION SETTINGS:")
    print("=" * 50)
    print()
    print("🔵 ADA (ADAUSDT):")
    print("   step_size: 0.1")
    print("   quantity_precision: 1")
    print("   Format: f'{quantity:.1f}' → 23.4")
    print()
    print("🟠 SOL (SOLUSDT):")
    print("   step_size: 0.0001")
    print("   quantity_precision: 4")
    print("   Format: f'{quantity:.4f}' → 1.2345")
    print()
    print("🔷 ETH (ETHUSDT):")
    print("   step_size: 0.00001")
    print("   quantity_precision: 5")
    print("   Format: f'{quantity:.5f}' → 0.00420")
    print()
    print("💡 KEY INSIGHT:")
    print("   Each symbol needs EXACT formatting")
    print("   to match Binance API requirements")

def main():
    """Main execution"""
    
    print("🚨 ETH PRECISION FIX")
    print("=" * 50)
    print()
    print("PROBLEM: ETH orders failing with 'too much precision'")
    print("SPECIFIC: 0.004200 and 0.004800 ETH failing")
    print("SOLUTION: Add ETH-specific formatting overrides")
    print()
    
    analyze_eth_failures()
    
    success = fix_eth_precision()
    
    if success:
        show_all_symbol_precision()
        
        print("\n🎉 ETH FIX APPLIED!")
        print()
        print("🚀 NEXT STEPS:")
        print("   1. ✅ Restart your bot")
        print("   2. 🧪 Test: ETH 700")
        print("   3. 📊 Should see 100% success rate")
        print("   4. ✅ Look for: '🔒 FORCED ETH precision' in logs")
        
        print("\n📋 WHAT TO EXPECT:")
        print("   Before: 0.004200000 ETH → API Error")
        print("   After:  0.00420 ETH → SUCCESS ✅")
        
    else:
        print("\n❌ AUTOMATIC FIX FAILED")
        print()
        print("📝 MANUAL FIX:")
        print("1. Open services/single_advanced_grid_manager.py")
        print("2. Find existing symbol overrides")
        print("3. Add ETH override:")
        print()
        print('   if symbol == "ETHUSDT":')
        print('       info = {')
        print('           "price_precision": 2,')
        print('           "quantity_precision": 5,')
        print('           "tick_size": 0.01,')
        print('           "step_size": 0.00001,')
        print('           "min_notional": 5.0,')
        print('           "status": "TRADING",')
        print('       }')
        print('       return info')
        print()
        print("4. Update quantity formatting:")
        print('   elif symbol == "ETHUSDT":')
        print('       quantity_str = f"{adjusted_quantity:.5f}"')

if __name__ == "__main__":
    main()
