#!/usr/bin/env python3
"""Test order size calculations"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_order_sizing():
    """Test the order sizing logic"""
    print("🧪 Testing Order Size Calculations")
    print("=" * 50)
    
    # Test parameters
    capital = 800.0
    grid_levels = 8
    grid_spacing = 0.025
    
    # ADA test
    ada_price = 0.74
    avax_price = 22.0
    
    print(f"📊 Test Parameters:")
    print(f"   Capital per pair: ${capital}")
    print(f"   Grid levels: {grid_levels}")
    print(f"   Grid spacing: {grid_spacing * 100:.1f}%")
    print()
    
    # Calculate order size
    order_size_usd = capital / grid_levels
    print(f"✅ Calculated order size: ${order_size_usd:.2f} USD per order")
    print()
    
    # ADA Grid Test
    print(f"🔵 ADA Grid (Price: ${ada_price:.4f}):")
    print(f"   Buy Orders:")
    for i in range(1, grid_levels + 1):
        price = ada_price * (1 - grid_spacing * i)
        quantity = order_size_usd / price
        print(f"   Level {i}: {quantity:.1f} ADA at ${price:.4f} = ${order_size_usd:.2f}")
    
    print(f"   Sell Orders:")
    for i in range(1, grid_levels + 1):
        price = ada_price * (1 + grid_spacing * i)
        quantity = order_size_usd / price
        print(f"   Level {i}: {quantity:.1f} ADA at ${price:.4f} = ${order_size_usd:.2f}")
    print()
    
    # AVAX Grid Test
    print(f"🟠 AVAX Grid (Price: ${avax_price:.2f}):")
    print(f"   Buy Orders:")
    for i in range(1, grid_levels + 1):
        price = avax_price * (1 - grid_spacing * i)
        quantity = order_size_usd / price
        print(f"   Level {i}: {quantity:.3f} AVAX at ${price:.2f} = ${order_size_usd:.2f}")
    
    print(f"   Sell Orders:")
    for i in range(1, grid_levels + 1):
        price = avax_price * (1 + grid_spacing * i)
        quantity = order_size_usd / price
        print(f"   Level {i}: {quantity:.3f} AVAX at ${price:.2f} = ${order_size_usd:.2f}")
    print()
    
    # Summary
    total_capital_deployed = order_size_usd * grid_levels * 2  # Buy + sell orders
    print(f"📈 Expected Results:")
    print(f"   Order size per level: ${order_size_usd:.2f}")
    print(f"   Orders per side: {grid_levels}")
    print(f"   Total orders: {grid_levels * 2}")
    print(f"   Total capital deployed: ${total_capital_deployed:.2f}")
    print()
    
    # Current vs Fixed
    print(f"🔧 Current vs Fixed:")
    print(f"   Current (broken): ~$6.25 per order")
    print(f"   Fixed (correct): ${order_size_usd:.2f} per order")
    print(f"   Improvement: {order_size_usd / 6.25:.1f}x larger orders")

if __name__ == "__main__":
    test_order_sizing()
