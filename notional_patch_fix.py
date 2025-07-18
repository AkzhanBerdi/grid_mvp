#!/usr/bin/env python3
"""
NOTIONAL Fix Patch for Single Advanced Grid Manager
Patches the existing code to prevent NOTIONAL filter failures
"""

# Add this method to your SingleAdvancedGridManager class

def _fix_notional_compliance(self, symbol: str, quantity: float, price: float, symbol_info: dict) -> dict:
    """
    Fix order parameters to ensure NOTIONAL compliance
    This method prevents the recurring NOTIONAL filter failures
    """
    
    min_notional = symbol_info.get("min_notional", 5.0)
    step_size = symbol_info.get("step_size", 0.1)
    tick_size = symbol_info.get("tick_size", 0.0001)
    min_quantity = symbol_info.get("min_quantity", 0.1)
    
    # Round price to tick size first
    adjusted_price = round(price / tick_size) * tick_size
    
    # Round quantity to step size
    adjusted_quantity = round(quantity / step_size) * step_size
    
    # Calculate notional value
    notional_value = adjusted_quantity * adjusted_price
    
    self.logger.info(f"🔍 NOTIONAL CHECK for {symbol}:")
    self.logger.info(f"   Original: {quantity:.6f} @ ${price:.6f} = ${quantity * price:.2f}")
    self.logger.info(f"   Adjusted: {adjusted_quantity:.1f} @ ${adjusted_price:.4f} = ${notional_value:.2f}")
    self.logger.info(f"   Min notional required: ${min_notional}")
    
    # If notional is too low, fix it
    if notional_value < min_notional:
        self.logger.warning(f"⚠️ Notional ${notional_value:.2f} below minimum ${min_notional}")
        
        # Calculate required quantity for minimum notional (with 10% buffer)
        required_quantity = (min_notional * 1.1) / adjusted_price
        
        # Round UP to next step size to ensure we exceed minimum
        steps_needed = required_quantity / step_size
        steps_rounded = int(steps_needed) + (1 if steps_needed % 1 > 0 else 0)
        adjusted_quantity = steps_rounded * step_size
        
        # Ensure we don't go below absolute minimum
        if adjusted_quantity < min_quantity:
            adjusted_quantity = min_quantity
        
        # Recalculate notional
        notional_value = adjusted_quantity * adjusted_price
        
        self.logger.info(f"✅ FIXED: {adjusted_quantity:.1f} @ ${adjusted_price:.4f} = ${notional_value:.2f}")
    
    # Final validation
    if notional_value < min_notional:
        self.logger.error(f"❌ Still below minimum after fix: ${notional_value:.2f} < ${min_notional}")
        return {
            "success": False,
            "error": f"Cannot meet minimum notional of ${min_notional}",
            "quantity": adjusted_quantity,
            "price": adjusted_price,
            "notional": notional_value
        }
    
    return {
        "success": True,
        "quantity": adjusted_quantity,
        "price": adjusted_price,
        "notional": notional_value,
        "quantity_str": f"{adjusted_quantity:.1f}",
        "price_str": f"{adjusted_price:.4f}"
    }

# Replace the existing _execute_precision_order method with this fixed version
async def _execute_precision_order_fixed(self, symbol: str, side: str, quantity: float, price: float) -> dict:
    """
    FIXED VERSION: Execute precision order with proper NOTIONAL compliance
    """
    try:
        self.logger.info(f"🎯 EXECUTING PRECISION ORDER: {symbol} {side} {quantity} @ {price}")
        
        # Get symbol info
        symbol_info = await self._get_symbol_precision_info(symbol)
        
        # Apply NOTIONAL compliance fix
        fix_result = self._fix_notional_compliance(symbol, quantity, price, symbol_info)
        
        if not fix_result["success"]:
            self.logger.error(f"❌ NOTIONAL compliance failed: {fix_result['error']}")
            return fix_result
        
        adjusted_quantity = fix_result["quantity"]
        adjusted_price = fix_result["price"]
        quantity_str = fix_result["quantity_str"]
        price_str = fix_result["price_str"]
        
        self.logger.info(f"🔒 USING FORCED OVERRIDE for {symbol}")
        self.logger.info(f"📤 SENDING TO BINANCE: {symbol} {side}")
        self.logger.info(f"   Quantity: '{quantity_str}'")
        self.logger.info(f"   Price: '{price_str}'")
        self.logger.info(f"   Notional: ${fix_result['notional']:.2f}")
        
        # Execute the order with fixed parameters
        if side.upper() == "BUY":
            order = self.binance_client.order_limit_buy(
                symbol=symbol,
                quantity=quantity_str,
                price=price_str
            )
        else:  # SELL
            order = self.binance_client.order_limit_sell(
                symbol=symbol,
                quantity=quantity_str,
                price=price_str
            )
        
        self.logger.info(f"✅ SUCCESS: {symbol} {side} {adjusted_quantity} @ {adjusted_price}")
        
        return {
            "success": True,
            "order_id": order["orderId"],
            "price": float(order["price"]),
            "quantity": float(order["origQty"]),
            "notional": float(order["origQty"]) * float(order["price"]),
        }
        
    except Exception as e:
        error_msg = str(e)
        self.logger.error(f"❌ Precision order execution error: {error_msg}")
        
        # Check if it's a NOTIONAL error and log additional debug info
        if "NOTIONAL" in error_msg:
            self.logger.error(f"🚨 NOTIONAL ERROR DETAILS:")
            self.logger.error(f"   Original params: {quantity} @ {price}")
            self.logger.error(f"   Symbol info: {symbol_info}")
            self.logger.error(f"   This should have been prevented by the fix!")
        
        return {"success": False, "error": error_msg}

# QUICK PATCH: Add this to your existing code
def patch_existing_grid_manager():
    """
    Quick patch to apply to existing SingleAdvancedGridManager
    Add this to your imports and call it before starting grids
    """
    
    # For ADA specifically, update the minimum order calculations
    ADA_SAFE_MINIMUMS = {
        "ADAUSDT": {
            "min_order_size_usd": 6.0,    # Ensure at least $6 per order
            "step_size": 0.1,             # ADA step size is 0.1
            "tick_size": 0.0001,          # ADA tick size is 0.0001
            "min_notional": 5.0,          # Binance minimum
            "safety_buffer": 1.2          # 20% safety buffer
        }
    }
    
    return ADA_SAFE_MINIMUMS

# Emergency fix for current code - replace the order size calculation
def calculate_safe_ada_order_size(total_capital: float, num_levels: int = 10) -> float:
    """
    Calculate safe ADA order size that won't fail NOTIONAL
    """
    
    # Base calculation
    base_order_size = total_capital / num_levels
    
    # ADA minimum to avoid NOTIONAL failures
    ada_minimum = 6.0  # $6 minimum per order
    
    # Use the larger of calculated or minimum
    safe_order_size = max(base_order_size, ada_minimum)
    
    print(f"💰 ADA Order Size Calculation:")
    print(f"   Total Capital: ${total_capital}")
    print(f"   Levels: {num_levels}")
    print(f"   Base Size: ${base_order_size:.2f}")
    print(f"   Safe Size: ${safe_order_size:.2f}")
    
    return safe_order_size

# Diagnostic function to check current ADA setup
def diagnose_current_ada_setup(client_id: int):
    """
    Diagnose current ADA grid setup to identify NOTIONAL issues
    Run this before starting ADA grids
    """
    
    print(f"🔍 DIAGNOSING ADA SETUP FOR CLIENT {client_id}")
    print("="*60)
    
    try:
        # Import your existing classes
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from repositories.client_repository import ClientRepository
        from services.grid_orchestrator import GridOrchestrator
        
        # Get client info
        client_repo = ClientRepository()
        client = client_repo.get_client(client_id)
        
        if not client:
            print(f"❌ Client {client_id} not found")
            return
        
        print(f"👤 Client: {client.first_name}")
        print(f"💰 Total Capital: ${client.total_capital}")
        print(f"📊 Order Size Setting: ${client.order_size}")
        
        # Calculate what the grid would use
        ada_capital = 700.0  # From your command "ADA 700"
        grid_levels = 10     # From logs
        
        base_order_size = ada_capital / grid_levels
        print(f"\n📈 CURRENT ADA GRID CALCULATION:")
        print(f"   ADA Capital: ${ada_capital}")
        print(f"   Grid Levels: {grid_levels}")
        print(f"   Order Size: ${base_order_size:.2f}")
        
        # Check if this would cause NOTIONAL issues
        min_notional = 5.0
        ada_price_example = 0.8289  # From your logs
        
        min_quantity_needed = min_notional / ada_price_example
        actual_quantity = base_order_size / ada_price_example
        
        print(f"\n🔍 NOTIONAL ANALYSIS:")
        print(f"   ADA Price: ${ada_price_example}")
        print(f"   Min Quantity Needed: {min_quantity_needed:.1f} ADA")
        print(f"   Actual Quantity: {actual_quantity:.1f} ADA")
        
        if actual_quantity < min_quantity_needed:
            print(f"   ❌ PROBLEM: Quantity too low for NOTIONAL!")
            safe_order_size = calculate_safe_ada_order_size(ada_capital, grid_levels)
            print(f"   ✅ SOLUTION: Use ${safe_order_size:.2f} per order")
        else:
            print(f"   ✅ Should be safe")
            
        # Show the exact failure from logs
        print(f"\n📋 FAILURE FROM YOUR LOGS:")
        print(f"   Failed: 20.21 ADA @ $0.7966 = $16.09")
        print(f"   But API got: 2 ADA @ $0.7966 = $1.59 < $5.00 minimum")
        print(f"   Issue: Quantity got rounded/truncated incorrectly")
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")

if __name__ == "__main__":
    # Test the diagnostic
    diagnose_current_ada_setup(485825055)  # Your client ID from logs
