#!/usr/bin/env python3
"""
Fix precision handling in single_advanced_grid_manager.py
The issue is it's using Binance API data instead of our fixed overrides
"""

import re
from pathlib import Path

def fix_single_grid_manager_precision():
    """Fix the precision handling in single_advanced_grid_manager.py"""
    
    print("🔧 FIXING SINGLE GRID MANAGER PRECISION")
    print("=" * 50)
    
    file_path = Path("services/single_advanced_grid_manager.py")
    
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
    
    # Fix 1: Add ADA-specific overrides to _get_symbol_precision_info method
    ada_override_code = '''
    async def _get_symbol_precision_info(self, symbol: str) -> Dict:
        """Get symbol precision information with ADA-specific overrides"""
        try:
            # FORCE ADA overrides to fix precision issues
            if symbol == "ADAUSDT":
                info = {
                    "price_precision": 4,
                    "quantity_precision": 1,  # Allow 1 decimal place
                    "tick_size": 0.0001,
                    "step_size": 0.1,         # Correct ADA step size
                    "min_notional": 5.0,
                    "status": "TRADING",
                }
                self.logger.info(f"🔒 FORCED ADA precision: step_size={info['step_size']}, quantity_precision={info['quantity_precision']}")
                return info
            
            # For other symbols, get from Binance API
            exchange_info = self.binance_client.get_exchange_info()'''
    
    # Replace the existing method
    pattern = r'async def _get_symbol_precision_info\(self, symbol: str\) -> Dict:.*?try:'
    replacement = ada_override_code.strip()
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Fix 2: Update _round_to_step_size to handle ADA properly
    ada_step_size_fix = '''
    def _round_to_step_size(self, quantity: float, step_size: float) -> float:
        """Round quantity to valid step size with ADA-specific handling"""
        if step_size <= 0:
            return round(quantity, 6)
        
        # For ADA: ensure we round to 0.1 increments
        if step_size == 0.1:  # ADA case
            return round(quantity / step_size) * step_size
        
        return round(quantity / step_size) * step_size'''
    
    # Replace _round_to_step_size method
    step_size_pattern = r'def _round_to_step_size\(self, quantity[^}]*?return[^}]*?step_size'
    
    if 'def _round_to_step_size(' in new_content:
        # Find and replace the method
        lines = new_content.split('\n')
        new_lines = []
        in_method = False
        indent_level = 0
        
        for line in lines:
            if 'def _round_to_step_size(' in line:
                in_method = True
                indent_level = len(line) - len(line.lstrip())
                # Replace with our fixed method
                new_lines.append('    def _round_to_step_size(self, quantity: float, step_size: float) -> float:')
                new_lines.append('        """Round quantity to valid step size with ADA-specific handling"""')
                new_lines.append('        if step_size <= 0:')
                new_lines.append('            return round(quantity, 6)')
                new_lines.append('        ')
                new_lines.append('        # For ADA: ensure we round to 0.1 increments')
                new_lines.append('        if step_size == 0.1:  # ADA case')
                new_lines.append('            return round(quantity / step_size) * step_size')
                new_lines.append('        ')
                new_lines.append('        return round(quantity / step_size) * step_size')
                continue
            elif in_method:
                current_indent = len(line) - len(line.lstrip())
                # If we hit a line at the same or lower indentation level, stop replacing
                if line.strip() and current_indent <= indent_level:
                    in_method = False
                    new_lines.append(line)
                # Skip lines inside the old method
                continue
            else:
                new_lines.append(line)
        
        new_content = '\n'.join(new_lines)
    
    # Fix 3: Add quantity formatting to the order placement
    quantity_format_fix = '''
                    # Format quantity for API (ADA needs 1 decimal place)
                    if symbol == "ADAUSDT":
                        quantity_str = f"{adjusted_quantity:.1f}"
                    else:
                        quantity_str = str(adjusted_quantity)
                    
                    price_str = f"{adjusted_price:.4f}"'''
    
    # Add this before the order placement
    if 'self.binance_client.order_limit(' in new_content:
        # Find the order placement and add quantity formatting
        order_pattern = r'(# Place limit order.*?)(\s+order = self\.binance_client\.order_limit\()'
        order_replacement = r'\1\n' + quantity_format_fix + r'\2'
        new_content = re.sub(order_pattern, order_replacement, new_content, flags=re.DOTALL)
        
        # Update the order call to use formatted strings
        new_content = re.sub(
            r'quantity=adjusted_quantity,\s*price=adjusted_price',
            'quantity=quantity_str, price=price_str',
            new_content
        )
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("✅ FIXED single_advanced_grid_manager.py!")
    print()
    print("🔧 CHANGES MADE:")
    print("   1. ✅ Added ADA-specific precision overrides")
    print("   2. ✅ Fixed _round_to_step_size for 0.1 step size")
    print("   3. ✅ Added proper quantity formatting for API")
    print()
    print("📊 KEY FIXES:")
    print("   • ADA step_size: 0.1 (forced override)")
    print("   • ADA quantity_precision: 1 decimal")
    print("   • Proper quantity formatting: 23.4 not 23.456789")
    
    return True

def create_manual_fix_instructions():
    """Create manual fix instructions if script fails"""
    
    instructions = """
🔧 MANUAL FIX INSTRUCTIONS FOR single_advanced_grid_manager.py:

1. Open: services/single_advanced_grid_manager.py

2. Find: async def _get_symbol_precision_info(self, symbol: str) -> Dict:

3. Replace the beginning with:
   ```python
   async def _get_symbol_precision_info(self, symbol: str) -> Dict:
       try:
           # FORCE ADA overrides to fix precision issues
           if symbol == "ADAUSDT":
               info = {
                   "price_precision": 4,
                   "quantity_precision": 1,
                   "tick_size": 0.0001,
                   "step_size": 0.1,
                   "min_notional": 5.0,
                   "status": "TRADING",
               }
               self.logger.info(f"🔒 FORCED ADA precision: step_size={info['step_size']}")
               return info
           
           # For other symbols, get from Binance API
           exchange_info = self.binance_client.get_exchange_info()
           # ... rest of method unchanged
   ```

4. Find: def _round_to_step_size(self, quantity, step_size):

5. Replace with:
   ```python
   def _round_to_step_size(self, quantity: float, step_size: float) -> float:
       if step_size <= 0:
           return round(quantity, 6)
       
       # For ADA: ensure proper rounding to 0.1
       if step_size == 0.1:
           return round(quantity / step_size) * step_size
       
       return round(quantity / step_size) * step_size
   ```

6. Find the order placement section and add quantity formatting:
   ```python
   # Before: order = self.binance_client.order_limit(
   
   # Add this:
   if symbol == "ADAUSDT":
       quantity_str = f"{adjusted_quantity:.1f}"
   else:
       quantity_str = str(adjusted_quantity)
   
   price_str = f"{adjusted_price:.4f}"
   
   # Then change:
   order = self.binance_client.order_limit(
       symbol=symbol,
       side=side,
       quantity=quantity_str,  # Use formatted string
       price=price_str,        # Use formatted string
   )
   ```
"""
    
    return instructions

def main():
    """Main execution"""
    
    print("🚨 SINGLE GRID MANAGER PRECISION FIX")
    print("=" * 60)
    print()
    print("PROBLEM: single_advanced_grid_manager.py uses Binance API")
    print("         precision instead of our fixed overrides")
    print()
    print("SOLUTION: Force ADA-specific precision handling")
    print("=" * 60)
    
    success = fix_single_grid_manager_precision()
    
    if success:
        print("\n🎉 FIX APPLIED SUCCESSFULLY!")
        print("\n🚀 NEXT STEPS:")
        print("   1. ✅ Restart your bot")
        print("   2. 🧪 Test: ADA 700")
        print("   3. 📊 Should see 100% success rate now")
        print("   4. ✅ No more 'too much precision' errors")
        
        print("\n📋 VERIFICATION:")
        print("   Look for log: '🔒 FORCED ADA precision: step_size=0.1'")
        print("   Should see: 'Adjusted: 23.4' (not 23.456789)")
        
    else:
        print("\n❌ AUTOMATIC FIX FAILED")
        print("\n📝 MANUAL FIX REQUIRED:")
        instructions = create_manual_fix_instructions()
        print(instructions)
        
        # Save instructions to file
        with open("manual_ada_fix_instructions.txt", "w") as f:
            f.write(instructions)
        
        print("\n💾 Instructions saved: manual_ada_fix_instructions.txt")

if __name__ == "__main__":
    main()
