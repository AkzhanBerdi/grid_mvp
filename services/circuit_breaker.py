# services/circuit_braker.py
import logging
from typing import Tuple


class PortfolioCircuitBreaker:
    """Emergency stop system for high-risk trading"""

    def __init__(self, client_id: int):
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        # Circuit breaker levels
        self.circuit_breaker_levels = {
            "level_1": 0.07,  # 7% portfolio drawdown - warning
            "level_2": 0.15,  # 15% portfolio drawdown - reduce positions
            "level_3": 0.25,  # 25% portfolio drawdown - emergency stop
        }

        self.recovery_threshold = 0.05  # 5% gain to resume
        self.emergency_stop_active = False

    async def check_portfolio_drawdown(
        self, current_value: float, initial_value: float
    ) -> Tuple[bool, str, int]:
        """Check if circuit breakers should trigger"""
        try:
            drawdown = (initial_value - current_value) / initial_value

            if drawdown >= self.circuit_breaker_levels["level_3"]:
                self.emergency_stop_active = True
                return True, f"🚨 EMERGENCY STOP: {drawdown:.1%} drawdown", 3

            elif drawdown >= self.circuit_breaker_levels["level_2"]:
                return True, f"⚠️ Level 2 Alert: {drawdown:.1%} drawdown", 2

            elif drawdown >= self.circuit_breaker_levels["level_1"]:
                return True, f"📊 Level 1 Warning: {drawdown:.1%} drawdown", 1

            return False, "Portfolio healthy", 0

        except Exception as e:
            self.logger.error(f"Circuit breaker check failed: {e}")
            return True, "Circuit breaker malfunction - stopping for safety", 3
