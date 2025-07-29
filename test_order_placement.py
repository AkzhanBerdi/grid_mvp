# test_order_replacement.py
#!/usr/bin/env python3
"""
Test Order Replacement by Simulating Fills
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.grid_orchestrator import GridOrchestrator
from config import Config

logging.basicConfig(level=logging.INFO)

async def test_order_replacement():
    """Test order replacement by simulating fills"""
    
    # Get your client ID (replace with your actual Telegram ID)
    client_id = 485825055  # Your client ID from the logs
    
    # Get the grid orchestrator
    orchestrator = GridOrchestrator()
    
    # Get your grid manager
    if client_id not in orchestrator.advanced_managers:
        print(f"❌ No active manager for client {client_id}")
        return
        
    manager = orchestrator.advanced_managers[client_id]
    
    # Get active grids
    all_grids = manager.get_all_active_grids()
    if not all_grids.get("grids"):
        print("❌ No active grids found")
        return
        
    # Pick the first active grid
    symbol = list(all_grids["grids"].keys())[0]
    grid_config = manager.active_grids[symbol]
    
    print(f"🎯 Testing order replacement for {symbol}")
    print(f"📊 Grid has {len(grid_config.buy_levels)} buy levels, {len(grid_config.sell_levels)} sell levels")
    
    # Find the first unfilled buy level
    test_level = None
    for level in grid_config.buy_levels:
        if not level.get("filled", False) and level.get("order_id"):
            test_level = level
            break
            
    if not test_level:
        print("❌ No unfilled buy orders with order_id found")
        return
        
    print(f"🔍 Found test level: {test_level}")
    
    # Simulate the order fill
    fake_order = {
        "orderId": test_level["order_id"],
        "side": "BUY",
        "executedQty": str(test_level["quantity"]),
        "price": str(test_level["price"]),
        "status": "FILLED"
    }
    
    print(f"🧪 Simulating order fill: {fake_order}")
    
    # Call the fill handler directly
    try:
        await manager.trading_engine._handle_filled_order(
            symbol=symbol,
            level=test_level,
            order=fake_order,
            grid_config=grid_config
        )
        
        print("✅ Order replacement test completed!")
        print("Check logs for:")
        print("  - FIFO recording messages")
        print("  - Inventory updates") 
        print("  - Replacement order creation")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_order_replacement())
