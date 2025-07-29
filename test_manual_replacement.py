# test_manual_replacement.py
#!/usr/bin/env python3

import asyncio
from services.grid_orchestrator import GridOrchestrator

async def test_manual_cancellation():
    """Test by manually canceling an order"""
    
    client_id = 485825055  # Your client ID
    orchestrator = GridOrchestrator()
    manager = orchestrator.advanced_managers[client_id]
    
    # Get active grids
    all_grids = manager.get_all_active_grids()
    symbol = list(all_grids["grids"].keys())[0]
    grid_config = manager.active_grids[symbol]
    
    # Find an active order
    for level in grid_config.buy_levels:
        if level.get("order_id") and not level.get("filled"):
            order_id = level["order_id"]
            
            print(f"🎯 Canceling order {order_id} for testing")
            
            try:
                # Cancel the order on Binance
                binance_client = manager.binance_client
                result = binance_client.cancel_order(symbol=symbol, orderId=order_id)
                
                print(f"✅ Order canceled: {result}")
                
                # Mark as filled for testing
                level["filled"] = True
                level["order_id"] = None
                
                # Trigger replacement manually
                await manager.trading_engine._create_replacement_order(
                    symbol, level, "BUY", grid_config
                )
                
                print("✅ Replacement order test completed")
                break
                
            except Exception as e:
                print(f"❌ Cancellation test failed: {e}")
                
if __name__ == "__main__":
    asyncio.run(test_manual_cancellation())
