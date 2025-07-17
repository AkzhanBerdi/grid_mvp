# Enhanced Grid Orchestrator (create this file: services/enhanced_grid_orchestrator.py)
"""
Enhanced Grid Orchestrator that uses Advanced Features
Only loaded when ADVANCED_FEATURES=true
"""

import logging
from typing import Dict

from services.enhanced_dual_scale_manager import EnhancedDualScaleGridManager
from services.grid_orchestrator import GridOrchestrator as BaseGridOrchestrator


class EnhancedGridOrchestrator(BaseGridOrchestrator):
    """
    Enhanced Grid Orchestrator with Advanced Features
    Inherits all functionality from base orchestrator
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Override with enhanced managers
        self.adaptive_managers = {}  # Will hold EnhancedDualScaleGridManager instances

        self.logger.info(
            "🚀 Enhanced Grid Orchestrator initialized with Advanced Features"
        )

    async def start_client_grid(
        self, client_id: int, symbol: str, capital: float
    ) -> Dict:
        """Enhanced grid startup with advanced features"""
        try:
            self.logger.info(
                f"🚀 Starting ENHANCED grid for client {client_id}: {symbol} with ${capital:,.2f}"
            )

            # Ensure API connection
            if client_id not in self.binance_clients:
                api_test = await self.test_client_api(client_id)
                if not api_test["success"]:
                    return {
                        "success": False,
                        "error": "Failed to connect to Binance API",
                    }

            # Initialize ENHANCED adaptive grid manager
            if client_id not in self.adaptive_managers:
                self.adaptive_managers[client_id] = EnhancedDualScaleGridManager(
                    self.binance_clients[client_id], client_id
                )
                self.logger.info(f"✅ Enhanced manager created for client {client_id}")

            # Start ENHANCED dual-scale grid
            manager = self.adaptive_managers[client_id]
            result = await manager.start_enhanced_dual_scale_grid(symbol, capital)

            if result["success"]:
                # Update client status
                from models.client import GridStatus

                client = self.client_repo.get_client(client_id)
                client.grid_status = GridStatus.ACTIVE
                self.client_repo.update_client(client)

                # Enhanced logging
                self.logger.info(f"🎉 ENHANCED grid started for client {client_id}:")
                self.logger.info(
                    f"   💰 Compound Management: {result.get('enhanced_features', {}).get('compound_management', {}).get('status', 'Active')}"
                )
                self.logger.info(
                    f"   🛡️ Volatility Regime: {result.get('enhanced_features', {}).get('volatility_management', {}).get('regime', 'Moderate')}"
                )
                self.logger.info(
                    f"   ⏰ Market Session: {result.get('enhanced_features', {}).get('market_timing', {}).get('session', 'Normal')}"
                )

            return result

        except Exception as e:
            self.logger.error(
                f"❌ Enhanced grid startup error for client {client_id}: {e}"
            )
            return {"success": False, "error": str(e)}

    def get_all_active_grids(self) -> Dict:
        """Get all active enhanced grids"""
        all_grids = {}

        for client_id, manager in self.adaptive_managers.items():
            try:
                if hasattr(manager, "get_all_enhanced_grids_status"):
                    grids_status = manager.get_all_enhanced_grids_status()
                    if grids_status and grids_status.get("grids"):
                        all_grids[client_id] = {
                            "client_id": client_id,
                            "grids": grids_status["grids"],
                            "trading_mode": "Enhanced Dual-Scale with Advanced Features",
                            "enhanced_features": grids_status.get(
                                "global_summary", {}
                            ).get("enhanced_features_enabled", {}),
                        }
            except Exception as e:
                self.logger.error(
                    f"❌ Failed to get enhanced grids for client {client_id}: {e}"
                )

        return all_grids


# DEPLOYMENT INSTRUCTIONS
"""
🚀 SAFE DEPLOYMENT STEPS:

1. ADD ENVIRONMENT VARIABLE SUPPORT:
   Add the code above to your existing main.py

2. CREATE ENHANCED GRID ORCHESTRATOR:
   Create services/enhanced_grid_orchestrator.py with the code above

3. TEST IN PRODUCTION (SAFE):
   # Start with standard mode (current functionality)
   python main.py
   
4. ENABLE ADVANCED FEATURES:
   # Enable advanced features
   export ADVANCED_FEATURES=true
   python main.py
   
5. MONITOR STARTUP LOGS:
   Look for:
   🚀 ADVANCED FEATURES ENABLED - Enhanced Grid Orchestrator loaded
   💰 Compound Interest Management: ACTIVE
   ⏰ Intelligent Market Timing: ACTIVE
   etc.

6. ROLLBACK IF NEEDED:
   # Disable advanced features instantly
   export ADVANCED_FEATURES=false
   # or just restart without the environment variable

✅ ZERO DOWNTIME DEPLOYMENT
✅ INSTANT ROLLBACK CAPABILITY  
✅ PRODUCTION SAFETY
✅ GRADUAL FEATURE ACTIVATION
"""
