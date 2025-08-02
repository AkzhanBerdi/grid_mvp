# emergency_inventory_debug.py
"""
Emergency diagnostic script to identify and fix corrupted inventory objects
Run this to check the state of your inventory system
"""

import logging
from services.inventory_manager import AssetInventory

def emergency_inventory_repair(grid_orchestrator, client_id: int = 485825055):
    """
    🚨 EMERGENCY REPAIR: Check and fix corrupted inventory objects
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 EMERGENCY INVENTORY DIAGNOSIS STARTING...")
        
        # Get the manager
        if client_id not in grid_orchestrator.advanced_managers:
            logger.error(f"❌ No manager found for client {client_id}")
            return
            
        manager = grid_orchestrator.advanced_managers[client_id]
        
        if not hasattr(manager, 'inventory_manager'):
            logger.error("❌ No inventory manager found")
            return
            
        inventory_manager = manager.inventory_manager
        
        logger.info(f"✅ Found inventory manager: {type(inventory_manager)}")
        logger.info(f"   Has inventories: {hasattr(inventory_manager, 'inventories')}")
        
        if not hasattr(inventory_manager, 'inventories'):
            logger.error("❌ No inventories dict found")
            return
            
        # Check each inventory object
        corrupted_symbols = []
        healthy_symbols = []
        
        for symbol, inventory in inventory_manager.inventories.items():
            logger.info(f"\n🔍 Checking {symbol}:")
            logger.info(f"   Type: {type(inventory)}")
            logger.info(f"   Type name: {type(inventory).__name__}")
            
            if isinstance(inventory, dict):
                logger.error(f"   ❌ CORRUPTED: {symbol} is a dict instead of AssetInventory")
                logger.error(f"   Dict contents: {inventory}")
                corrupted_symbols.append(symbol)
            elif hasattr(inventory, 'usdt_balance'):
                logger.info(f"   ✅ HEALTHY: {symbol} is proper AssetInventory")
                logger.info(f"   USDT: ${inventory.usdt_balance:.2f}")
                logger.info(f"   Asset: {inventory.asset_balance:.4f}")
                healthy_symbols.append(symbol)
            else:
                logger.error(f"   ❌ UNKNOWN: {symbol} is unknown type")
                corrupted_symbols.append(symbol)
        
        # Report summary
        logger.info(f"\n📊 DIAGNOSIS SUMMARY:")
        logger.info(f"   Healthy symbols: {len(healthy_symbols)} - {healthy_symbols}")
        logger.info(f"   Corrupted symbols: {len(corrupted_symbols)} - {corrupted_symbols}")
        
        # Attempt repair
        if corrupted_symbols:
            logger.info(f"\n🔧 ATTEMPTING REPAIR...")
            
            for symbol in corrupted_symbols:
                try:
                    corrupted_data = inventory_manager.inventories[symbol]
                    logger.info(f"   Repairing {symbol}...")
                    
                    # Extract data from corrupted dict
                    if isinstance(corrupted_data, dict):
                        usdt_balance = corrupted_data.get('usdt_balance', 0.0)
                        asset_balance = corrupted_data.get('asset_balance', 0.0)
                        reserved_usdt = corrupted_data.get('reserved_usdt', 0.0)
                        reserved_asset = corrupted_data.get('reserved_asset', 0.0)
                    else:
                        # Fallback values
                        usdt_balance = 400.0  # Default for SOL
                        asset_balance = 2.5
                        reserved_usdt = 0.0
                        reserved_asset = 0.0
                    
                    # Calculate missing values
                    total_allocation = usdt_balance + (asset_balance * 160.0)  # Estimate
                    
                    # Grid spacing
                    grid_spacing = 0.030 if symbol == "SOLUSDT" else 0.025
                    
                    # Create proper AssetInventory object
                    inventory_manager.inventories[symbol] = AssetInventory(
                        symbol=symbol,
                        total_allocation=total_allocation,
                        usdt_balance=usdt_balance,
                        asset_balance=asset_balance,
                        reserved_usdt=reserved_usdt,
                        reserved_asset=reserved_asset,
                        grid_spacing=grid_spacing,
                        order_size_base=total_allocation / 10,
                        grid_levels=10
                    )
                    
                    logger.info(f"   ✅ Repaired {symbol} as AssetInventory")
                    logger.info(f"      USDT: ${usdt_balance:.2f}")
                    logger.info(f"      Asset: {asset_balance:.4f}")
                    
                except Exception as repair_error:
                    logger.error(f"   ❌ Failed to repair {symbol}: {repair_error}")
        
        # Final verification
        logger.info(f"\n🔍 POST-REPAIR VERIFICATION:")
        all_healthy = True
        for symbol, inventory in inventory_manager.inventories.items():
            is_healthy = hasattr(inventory, 'usdt_balance') and isinstance(inventory, AssetInventory)
            status = "✅ HEALTHY" if is_healthy else "❌ STILL CORRUPTED"
            logger.info(f"   {symbol}: {status}")
            if not is_healthy:
                all_healthy = False
        
        if all_healthy:
            logger.info("🎉 ALL INVENTORY OBJECTS ARE NOW HEALTHY!")
        else:
            logger.error("❌ Some objects are still corrupted - manual intervention needed")
            
        return all_healthy
        
    except Exception as e:
        logger.error(f"❌ Emergency repair failed: {e}")
        return False


# Quick access function for your main code
def quick_fix_inventory(grid_orchestrator):
    """Quick one-liner to fix inventory issues"""
    return emergency_inventory_repair(grid_orchestrator)


# Example usage:
# from emergency_inventory_debug import quick_fix_inventory
# success = quick_fix_inventory(your_grid_orchestrator)
