# utils/time_sync.py
"""
Clean Time Sync Implementation
Replaces all complex sync methods with simple, reliable approach
"""

import logging
import time

import requests


class BinanceTimeSync:
    """
    Clean, reliable Time Sync for Binance API
    Set once at startup - no complex ongoing sync needed
    """

    def __init__(self, binance_client):
        self.client = binance_client
        self.logger = logging.getLogger(__name__)
        self.offset_set = False

        # Set timestamp offset once
        self.sync_time()

    def sync_time(self) -> bool:
        """
        One-time timestamp synchronization
        Much simpler than complex ongoing sync approaches
        """
        try:
            # Determine API base URL
            base_url = (
                "https://testnet.binance.vision"
                if getattr(self.client, "testnet", False)
                else "https://api.binance.com"
            )

            # Get server time
            response = requests.get(f"{base_url}/api/v3/time", timeout=10)
            server_time = response.json()["serverTime"]
            local_time = int(time.time() * 1000)

            # Set client offset - this handles all future requests automatically
            self.client.timestamp_offset = server_time - local_time
            self.offset_set = True

            self.logger.info(
                f"🔄 Time sync complete: offset {self.client.timestamp_offset}ms"
            )
            return True

        except Exception as e:
            self.logger.warning(f"Time sync failed: {e}")
            # Conservative fallback - 5 seconds behind server
            self.client.timestamp_offset = -5000
            self.offset_set = True
            return False

    def is_synced(self) -> bool:
        """Check if time sync has been set"""
        return self.offset_set
