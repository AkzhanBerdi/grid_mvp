#!/usr/bin/env python3
"""
Test Order Replacement - Works with Running Service
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

async def test_with_running_service():
    """Test order replacement with your running service"""
    
    # Get your client ID
    client_id = 485825055
    
    # Get the grid orchestrator
    orchestrator = GridOrchestrator()
    
    print("🔍 Checking active managers...")
    print(f"Available managers: {list(orchestrator.advanced_managers.keys())}")
    
    # If no managers, try to create one
    if client_id not in orchestrator.advanced_managers:
        print(f"⚠️ No manager found for client {client_id}")
        print("Creating manager...")
        
        try:
            success = await orchestrator.create_advanced_manager(client_id)
            if not success:
                print("❌ Failed to create manager")
                print("Make sure you have:")
                print("1. API keys set up in database")
                print("2. Client record exists")
                return
        except Exception as e:
            print(f"❌ Manager creation failed: {e}")
            return
    
    # Now test
    manager = orchestrator.advanced_managers[client_id]
    print(f"✅ Got manager for client {client_id}")
    
    # Get active grids
    all_grids = manager.get_all_active_grids()
    print(f"📊 Active grids: {list(all_grids.get('grids', {}).keys())}")
    
    if not all_grids.get("grids"):
        print("❌ No active grids found")
        print("Start a grid first using the Telegram bot:")
        print("Example: Send 'ADA 660' to your bot")
        return
        
    # Test each active grid
    for symbol in all_grids["grids"].keys():
        print(f"\n🎯 Testing {symbol}:")
        
        try:
            grid_config = manager.active_grids[symbol]
            
            # Print current status
            buy_orders = [l for l in grid_config.buy_levels if l.get("order_id") and not l.get("filled")]
            sell_orders = [l for l in grid_config.sell_levels if l.get("order_id") and not l.get("filled")]
            
            print(f"  📉 Active buy orders: {len(buy_orders)}")
            print(f"  📈 Active sell orders: {len(sell_orders)}")
            
            # Test order monitoring (safe - just checks status)
            print(f"  🔍 Testing order monitoring...")
            await manager.trading_engine.check_and_replace_filled_orders(symbol, grid_config)
            print(f"  ✅ Monitoring test completed")
            
            # If you want to simulate a fill, uncomment this:
            # await simulate_order_fill(manager, symbol, grid_config)
            
        except Exception as e:
            print(f"  ❌ Error testing {symbol}: {e}")

async def simulate_order_fill(manager, symbol, grid_config):
    """Simulate an order fill for testing"""
    print(f"  🧪 Simulating order fill for {symbol}")
    
    # Find first unfilled buy order
    test_level = None
    for level in grid_config.buy_levels:
        if level.get("order_id") and not level.get("filled"):
            test_level = level
            break
            
    if not test_level:
        print("  ⚠️ No unfilled buy orders to simulate")
        return
        
    # Create fake filled order
    fake_order = {
        "orderId": test_level["order_id"],
        "side": "BUY", 
        "executedQty": str(test_level["quantity"]),
        "price": str(test_level["price"]),
        "status": "FILLED"
    }
    
    print(f"  📋 Simulating: {fake_order['side']} {fake_order['executedQty']} @ {fake_order['price']}")
    
    try:
        # Test the fill handler
        await manager.trading_engine._handle_filled_order(
            symbol=symbol,
            level=test_level,
            order=fake_order,
            grid_config=grid_config
        )
        print(f"  ✅ Simulation completed - check logs for replacement order")
        
    except Exception as e:
        print(f"  ❌ Simulation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_running_service())
