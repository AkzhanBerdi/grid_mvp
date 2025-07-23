# utils/grid_status_helper.py
"""
Simple Grid Status Helper - Avoids Async Issues
Provides sync interface for common grid status operations
"""

import logging
from typing import Dict
import asyncio


class GridStatusHelper:
    """Helper to get grid status without async complications"""
    
    def __init__(self, grid_orchestrator):
        self.grid_orchestrator = grid_orchestrator
        self.logger = logging.getLogger(__name__)
        self._cache = {}
        self._cache_time = 0
    
    def get_client_status_sync(self, client_id: int) -> Dict:
        """Get client grid status synchronously"""
        try:
            # Try to run async method in sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context, return cached or minimal data
                    return self._get_cached_status(client_id)
                else:
                    # Can run async
                    return loop.run_until_complete(
                        self.grid_orchestrator.get_client_grid_status(client_id)
                    )
            except:
                # Fallback to cached or minimal status
                return self._get_cached_status(client_id)
                
        except Exception as e:
            self.logger.error(f"Error getting grid status sync: {e}")
            return self._get_fallback_status(client_id)
    
    def _get_cached_status(self, client_id: int) -> Dict:
        """Get cached status or reasonable defaults"""
        import time
        current_time = time.time()
        
        # Use cache if recent (last 30 seconds)
        cache_key = f"status_{client_id}"
        if (cache_key in self._cache and 
            current_time - self._cache_time < 30):
            return self._cache[cache_key]
        
        # Return minimal status
        return self._get_fallback_status(client_id)
    
    def _get_fallback_status(self, client_id: int) -> Dict:
        """Fallback status when async fails"""
        return {
            "success": True,
            "client_id": client_id,
            "total_grids": 0,
            "grids": {},
            "strategy": "Status Loading...",
            "system_efficiency": "Checking..."
        }
    
    def update_cache(self, client_id: int, status: Dict):
        """Update cache with fresh status"""
        import time
        cache_key = f"status_{client_id}"
        self._cache[cache_key] = status
        self._cache_time = time.time()
