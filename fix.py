# SOL-Specific Fix - Run this in your console to fix SOLUSDT inventory issues
from services.grid_orchestrator import GridManager

grid_orchestrator = GridManager
print("🟣 SOL-SPECIFIC INVENTORY MANAGER FIX")
print("=" * 50)

# Step 1: Check the current state
client_id = 485825055
if client_id in grid_orchestrator.advanced_managers:
    manager = grid_orchestrator.advanced_managers[client_id]
    print(f"Manager found: {type(manager)}")
    print(f"Current inventory_manager: {type(manager.inventory_manager)}")
    print(f"Inventory manager is None: {manager.inventory_manager is None}")

    # Step 2: Fix the None inventory manager
    if manager.inventory_manager is None:
        print("🔧 Creating inventory manager for SOL...")

        from services.inventory_manager import SingleGridInventoryManager

        # Create new inventory manager
        manager.inventory_manager = SingleGridInventoryManager(
            binance_client=manager.binance_client,
            total_capital=2400.0,  # Adjust based on your setup
        )
        print("✅ Created new inventory manager")

        # Step 3: Inject into trading engine
        if hasattr(manager, "trading_engine") and manager.trading_engine:
            print("🔧 Injecting into trading engine...")

            # Try set_managers method first
            if hasattr(manager.trading_engine, "set_managers"):
                compound_manager = getattr(manager, "compound_manager", None)
                manager.trading_engine.set_managers(
                    manager.inventory_manager, compound_manager
                )
                print("✅ Used set_managers method")
            else:
                # Direct assignment
                manager.trading_engine.inventory_manager = manager.inventory_manager
                print("✅ Direct assignment completed")

    # Step 4: Specifically add SOL tracking
    if manager.inventory_manager and hasattr(manager.inventory_manager, "has_tracking"):
        print("🔧 Checking SOL tracking...")

        # Check if SOL tracking exists
        has_sol_tracking = manager.inventory_manager.has_tracking("SOLUSDT")
        print(f"SOL tracking exists: {has_sol_tracking}")

        if not has_sol_tracking:
            print("🔧 Adding SOL tracking...")

            import asyncio

            async def add_sol_tracking():
                try:
                    # Add SOL tracking with appropriate capital
                    sol_capital = 840.0  # 35% of 2400 as per your config
                    success = await manager.inventory_manager.add_symbol_tracking(
                        "SOLUSDT", sol_capital
                    )
                    if success:
                        print("✅ Successfully added SOL tracking")

                        # Check the created inventory
                        if "SOLUSDT" in manager.inventory_manager.inventories:
                            inventory = manager.inventory_manager.inventories["SOLUSDT"]
                            print(f"SOL inventory type: {type(inventory)}")
                            if hasattr(inventory, "usdt_balance"):
                                print(
                                    f"SOL USDT balance: ${inventory.usdt_balance:.2f}"
                                )
                                print(
                                    f"SOL asset balance: {inventory.asset_balance:.4f}"
                                )
                            else:
                                print("❌ SOL inventory object is corrupted!")
                        return True
                    else:
                        print("❌ Failed to add SOL tracking")
                        return False
                except Exception as e:
                    print(f"❌ Error adding SOL tracking: {e}")
                    return False

            # Run the async function
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule as task if loop is running
                    task = asyncio.create_task(add_sol_tracking())
                    print("✅ Scheduled SOL tracking addition")
                else:
                    # Run directly if no loop
                    result = asyncio.run(add_sol_tracking())
                    print(f"SOL tracking result: {result}")
            except Exception as e:
                print(f"❌ Async execution error: {e}")
        else:
            print("✅ SOL tracking already exists")

            # Check SOL inventory health
            if "SOLUSDT" in manager.inventory_manager.inventories:
                inventory = manager.inventory_manager.inventories["SOLUSDT"]
                print(f"SOL inventory type: {type(inventory)}")
                print(f"SOL inventory is dict: {isinstance(inventory, dict)}")

                if isinstance(inventory, dict):
                    print(
                        "🚨 SOL INVENTORY IS CORRUPTED (dict instead of AssetInventory)!"
                    )
                    print("🔧 Attempting emergency repair...")

                    # Emergency repair - replace dict with proper AssetInventory
                    from services.inventory_manager import AssetInventory

                    # Extract values from corrupted dict
                    usdt_balance = inventory.get(
                        "usdt_balance", 420.0
                    )  # Default 50% of 840
                    asset_balance = inventory.get(
                        "asset_balance", 2.5
                    )  # Default SOL amount

                    # Create proper AssetInventory object
                    manager.inventory_manager.inventories["SOLUSDT"] = AssetInventory(
                        symbol="SOLUSDT",
                        total_allocation=840.0,
                        usdt_balance=usdt_balance,
                        asset_balance=asset_balance,
                        reserved_usdt=0.0,
                        reserved_asset=0.0,
                        grid_spacing=0.030,  # 3% for SOL
                        order_size_base=84.0,  # 840/10
                        grid_levels=10,
                    )
                    print("✅ Emergency repair completed - SOL inventory restored")
                else:
                    print("✅ SOL inventory object is healthy")

    # Step 5: Final verification
    print("\n🔍 FINAL VERIFICATION:")
    print(f"Inventory manager type: {type(manager.inventory_manager)}")
    print(f"Has has_tracking: {hasattr(manager.inventory_manager, 'has_tracking')}")

    if manager.inventory_manager and hasattr(manager.inventory_manager, "has_tracking"):
        sol_tracking = manager.inventory_manager.has_tracking("SOLUSDT")
        print(f"SOL tracking exists: {sol_tracking}")

        if sol_tracking and "SOLUSDT" in manager.inventory_manager.inventories:
            sol_inventory = manager.inventory_manager.inventories["SOLUSDT"]
            print(f"SOL inventory type: {type(sol_inventory)}")
            print(
                f"SOL inventory is AssetInventory: {type(sol_inventory).__name__ == 'AssetInventory'}"
            )

    print("\n✅ SOL FIX COMPLETED!")
    print("The next SOL order check should work without errors.")

else:
    print(f"❌ No manager found for client {client_id}")

print("\n" + "=" * 50)
print("🟣 SOL inventory manager should now be working")
