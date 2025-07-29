# test_monitoring.py
#!/usr/bin/env python3

import asyncio
from services.grid_orchestrator import GridOrchestrator

async def test_order_monitoring():
    """Test order monitoring system"""
    
    client_id = 485825055  # Your client ID
    orchestrator = GridOrchestrator()
    manager = orchestrator.advanced_managers[client_id]
    
    # Get active grids
    all_grids = manager.get_all_active_grids()
    
    for symbol in all_grids["grids"].keys():
        print(f"\n🔍 Monitoring {symbol}:")
        grid_config = manager.active_grids[symbol]
        
        # Check current order status
        try:
            await manager.trading_engine.check_and_replace_filled_orders(
                symbol, grid_config
            )
            print(f"✅ Monitoring check completed for {symbol}")
            
        except Exception as e:
            print(f"❌ Monitoring error for {symbol}: {e}")
            
        # Print current grid status
        buy_active = sum(1 for level in grid_config.buy_levels 
                        if level.get("order_id") and not level.get("filled"))
        sell_active = sum(1 for level in grid_config.sell_levels 
                         if level.get("order_id") and not level.get("filled"))
        
        print(f"📊 Active orders: {buy_active} buy, {sell_active} sell")

if __name__ == "__main__":
    asyncio.run(test_order_monitoring())
