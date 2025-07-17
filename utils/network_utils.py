# utils/network_utils.py
"""
Simplified Network Utilities
Consolidates error handling and retry logic
"""

import asyncio
import logging
from typing import Any, Callable


class NetworkUtils:
    """
    Simplified network operations and error handling
    Replaces complex NetworkRecoveryService for most use cases
    """

    @staticmethod
    def is_retryable_error(error: Exception) -> bool:
        """
        Clean error classification
        Based on actual error patterns from your logs
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Retryable network errors (from your July 16 logs)
        retryable_patterns = [
            "name or service not known",  # DNS failure
            "connection error",
            "timeout",
            "network is unreachable",
            "connection refused",
            "connection reset",
            "httpsconnectionpool",
            "read timed out",
            "max retries exceeded",
        ]

        # Check patterns
        for pattern in retryable_patterns:
            if pattern in error_str or pattern in error_type:
                return True

        # Don't retry these
        non_retryable = [
            "invalid api",
            "signature",
            "permission",
            "unauthorized",
            "rate limit",
            "banned",
            "lot_size",
            "insufficient_balance",
        ]

        for pattern in non_retryable:
            if pattern in error_str:
                return False

        return False  # Conservative default

    @staticmethod
    async def safe_request(
        func: Callable, *args, max_retries: int = 3, base_delay: float = 1.0, **kwargs
    ) -> Any:
        """
        Unified retry logic for network operations
        Exponential backoff with jitter
        """
        logger = logging.getLogger(__name__)

        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                is_last_attempt = attempt == max_retries - 1

                if not NetworkUtils.is_retryable_error(e) or is_last_attempt:
                    logger.error(f"Network request failed (attempt {attempt + 1}): {e}")
                    raise

                # Exponential backoff with jitter
                delay = (
                    base_delay * (2**attempt) * (0.5 + 0.5 * hash(str(e)) % 100 / 100)
                )
                logger.warning(
                    f"Retryable error (attempt {attempt + 1}): {e}. Retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        raise Exception("Should not reach here")  # Safety net

    @staticmethod
    def log_network_event(event_type: str, details: str):
        """Simple network event logging"""
        logger = logging.getLogger("network")
        timestamp = asyncio.get_event_loop().time()
        logger.info(f"[{timestamp:.3f}] {event_type}: {details}")

    # Time Synchronization Functions (consolidated from time_sync.py)
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
