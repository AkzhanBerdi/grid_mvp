import logging
from typing import Dict


class HighRiskPortfolioManager:
    """Manages aggressive multi-pair portfolio for $2200 capital"""

    def __init__(self, total_capital: float = 2200.0):
        self.total_capital = total_capital
        self.logger = logging.getLogger(__name__)

        # Aggressive portfolio allocation
        self.portfolio_allocation = {
            "AVAXUSDT": {"allocation": 0.35, "capital": 770.0, "risk_level": "high"},
            "ADAUSDT": {
                "allocation": 0.30,
                "capital": 660.0,
                "risk_level": "moderate-high",
            },
            "ETHUSDT": {"allocation": 0.25, "capital": 550.0, "risk_level": "moderate"},
            "BTCUSDT": {
                "allocation": 0.10,
                "capital": 220.0,
                "risk_level": "low-moderate",
            },
        }

    def get_optimized_grid_parameters(self, symbol: str) -> Dict:
        """Get symbol-specific aggressive grid parameters"""
        base_params = {
            "AVAXUSDT": {
                "base_order_size": 45.0,
                "enhanced_order_size": 85.0,
                "base_grid_spacing": 0.025,  # 2.5%
                "enhanced_grid_spacing": 0.020,  # 2.0%
                "grid_levels": 12,
                "volatility_threshold": 1.50,  # 150% before pause
            },
            "ADAUSDT": {
                "base_order_size": 40.0,
                "enhanced_order_size": 75.0,
                "base_grid_spacing": 0.030,  # 3.0%
                "enhanced_grid_spacing": 0.025,  # 2.5%
                "grid_levels": 10,
                "volatility_threshold": 1.30,  # 130%
            },
            "ETHUSDT": {
                "base_order_size": 35.0,
                "enhanced_order_size": 65.0,
                "base_grid_spacing": 0.035,  # 3.5%
                "enhanced_grid_spacing": 0.030,  # 3.0%
                "grid_levels": 8,
                "volatility_threshold": 1.20,  # 120%
            },
            "BTCUSDT": {
                "base_order_size": 25.0,
                "enhanced_order_size": 40.0,
                "base_grid_spacing": 0.040,  # 4.0%
                "enhanced_grid_spacing": 0.035,  # 3.5%
                "grid_levels": 6,
                "volatility_threshold": 1.00,  # 100%
            },
        }
        return base_params.get(symbol, base_params["ADAUSDT"])
