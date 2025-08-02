from services.usdt_initializer import InventoryDiagnostic

# Create diagnostic instance
diagnostic = InventoryDiagnostic()

# Get your manager
client_id = 485825055  # Your client ID
manager = your_grid_orchestrator.advanced_managers[client_id]
inventory_manager = manager.inventory_manager

# Run detailed diagnosis
detailed_diagnosis = diagnostic.diagnose_inventory_health(inventory_manager)

# Print detailed results
print("🔍 DETAILED INVENTORY DIAGNOSIS:")
print(f"Manager Type: {detailed_diagnosis['manager_type']}")
print(f"Overall Health: {detailed_diagnosis['overall_health']}")
print(f"Symbol Count: {detailed_diagnosis.get('symbol_count', 0)}")

for symbol, info in detailed_diagnosis.get('symbols', {}).items():
    print(f"\n{symbol}:")
    print(f"  Status: {info['status']}")
    print(f"  Type: {info['type']}")
    print(f"  Is AssetInventory: {info['is_asset_inventory']}")
    if info['status'] == 'healthy':
        print(f"  USDT Balance: ${info.get('usdt_balance', 0):.2f}")
        print(f"  Asset Balance: {info.get('asset_balance', 0):.4f}")
