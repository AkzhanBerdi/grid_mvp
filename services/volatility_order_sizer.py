"""
Advanced Feature 2: Volatility-Based Order Sizing
=================================================

This implements intelligent order sizing that automatically adjusts to market volatility:
- Reduces order sizes during high volatility (risk protection)
- Increases order sizes during low volatility (opportunity capture)
- Calculates real-time volatility from multiple indicators
- Integrates with Compound Interest Manager for optimal sizing
- Provides dynamic grid spacing based on market conditions

Key Benefits:
- Automatic risk adjustment during market stress
- Better profit capture during stable periods
- Reduces losses during volatile market conditions
- Complements compound interest system perfectly
"""

import logging
import math
import time
from datetime import datetime
from typing import Dict, List

import numpy as np
import requests

from config import Config


class VolatilityCalculator:
    """
    Multi-method volatility calculation system

    Combines multiple volatility measures for robust market assessment:
    - Price volatility (standard deviation of returns)
    - Volume volatility (changes in trading volume)
    - Momentum volatility (rate of price change acceleration)
    - Market structure volatility (bid-ask spread analysis)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.price_cache = {}  # Cache for price data
        self.volatility_cache = {}  # Cache for calculated volatility
        self.cache_timeout = 300  # 5-minute cache

    async def calculate_comprehensive_volatility(self, symbol: str) -> Dict:
        """
        Calculate comprehensive volatility metrics for a symbol

        Returns dict with:
        - overall_volatility: Combined volatility score (0-1 scale)
        - price_volatility: Price-based volatility
        - volume_volatility: Volume-based volatility
        - momentum_volatility: Momentum-based volatility
        - volatility_regime: Low/Medium/High classification
        """
        try:
            # Check cache first
            cache_key = f"vol_{symbol}_{int(time.time() // self.cache_timeout)}"
            if cache_key in self.volatility_cache:
                return self.volatility_cache[cache_key]

            # Get price data for volatility calculation
            price_data = await self._get_price_data(symbol)

            if not price_data or len(price_data) < 20:
                # Insufficient data, return neutral volatility
                return self._get_neutral_volatility()

            # Calculate different volatility components
            price_vol = self._calculate_price_volatility(price_data)
            volume_vol = self._calculate_volume_volatility(price_data)
            momentum_vol = self._calculate_momentum_volatility(price_data)

            # Combine volatilities with weights
            overall_volatility = (
                price_vol * 0.5  # Price volatility most important
                + volume_vol * 0.3  # Volume volatility secondary
                + momentum_vol * 0.2  # Momentum volatility tertiary
            )

            # Classify volatility regime
            volatility_regime = self._classify_volatility_regime(overall_volatility)

            result = {
                "overall_volatility": overall_volatility,
                "price_volatility": price_vol,
                "volume_volatility": volume_vol,
                "momentum_volatility": momentum_vol,
                "volatility_regime": volatility_regime,
                "timestamp": datetime.now(),
                "symbol": symbol,
            }

            # Cache the result
            self.volatility_cache[cache_key] = result

            self.logger.debug(
                f"📊 {symbol} volatility: {overall_volatility:.3f} ({volatility_regime})"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Volatility calculation error for {symbol}: {e}")
            return self._get_neutral_volatility()

    async def _get_price_data(self, symbol: str) -> List[Dict]:
        """Get recent price data for volatility calculation"""
        try:
            # Use Binance API to get recent klines
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": "1h",  # 1-hour candles
                "limit": 100,  # Last 100 hours
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            klines = response.json()

            price_data = []
            for kline in klines:
                price_data.append(
                    {
                        "timestamp": int(kline[0]),
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5]),
                    }
                )

            return price_data

        except Exception as e:
            self.logger.error(f"❌ Error getting price data for {symbol}: {e}")
            return []

    def _calculate_price_volatility(self, price_data: List[Dict]) -> float:
        """Calculate price volatility using returns standard deviation"""
        try:
            if len(price_data) < 10:
                return 0.25  # Default medium volatility

            # Calculate hourly returns
            returns = []
            for i in range(1, len(price_data)):
                prev_close = price_data[i - 1]["close"]
                curr_close = price_data[i]["close"]

                if prev_close > 0:
                    hourly_return = (curr_close - prev_close) / prev_close
                    returns.append(hourly_return)

            if not returns:
                return 0.25

            # Calculate standard deviation of returns
            returns_array = np.array(returns)
            volatility = np.std(returns_array)

            # Annualize the volatility (hourly to yearly)
            # 24 hours * 365 days = 8760 hours per year
            annualized_volatility = volatility * math.sqrt(8760)

            # Scale to 0-1 range (typical crypto volatility is 0.5-3.0)
            scaled_volatility = min(1.0, annualized_volatility / 2.0)

            return scaled_volatility

        except Exception as e:
            self.logger.error(f"❌ Price volatility calculation error: {e}")
            return 0.25

    def _calculate_volume_volatility(self, price_data: List[Dict]) -> float:
        """Calculate volume volatility"""
        try:
            if len(price_data) < 10:
                return 0.25

            volumes = [candle["volume"] for candle in price_data]

            if not volumes or all(v == 0 for v in volumes):
                return 0.25

            # Calculate volume changes
            volume_changes = []
            for i in range(1, len(volumes)):
                if volumes[i - 1] > 0:
                    change = abs(volumes[i] - volumes[i - 1]) / volumes[i - 1]
                    volume_changes.append(change)

            if not volume_changes:
                return 0.25

            # Volume volatility is the standard deviation of volume changes
            volume_volatility = np.std(volume_changes)

            # Scale to 0-1 range
            scaled_volume_volatility = min(1.0, volume_volatility * 2)

            return scaled_volume_volatility

        except Exception as e:
            self.logger.error(f"❌ Volume volatility calculation error: {e}")
            return 0.25

    def _calculate_momentum_volatility(self, price_data: List[Dict]) -> float:
        """Calculate momentum volatility (rate of change acceleration)"""
        try:
            if len(price_data) < 20:
                return 0.25

            prices = [candle["close"] for candle in price_data]

            # Calculate momentum (rate of change)
            momentum = []
            for i in range(10, len(prices)):
                # 10-period momentum
                if prices[i - 10] > 0:
                    mom = (prices[i] - prices[i - 10]) / prices[i - 10]
                    momentum.append(mom)

            if len(momentum) < 10:
                return 0.25

            # Momentum volatility is the standard deviation of momentum
            momentum_volatility = np.std(momentum)

            # Scale to 0-1 range
            scaled_momentum_volatility = min(1.0, momentum_volatility * 5)

            return scaled_momentum_volatility

        except Exception as e:
            self.logger.error(f"❌ Momentum volatility calculation error: {e}")
            return 0.25

    def _classify_volatility_regime(self, overall_volatility: float) -> str:
        """Classify volatility into regimes"""
        if overall_volatility < 0.3:
            return "low"
        elif overall_volatility < 0.7:
            return "medium"
        else:
            return "high"

    def _get_neutral_volatility(self) -> Dict:
        """Return neutral volatility when calculation fails"""
        return {
            "overall_volatility": 0.25,
            "price_volatility": 0.25,
            "volume_volatility": 0.25,
            "momentum_volatility": 0.25,
            "volatility_regime": "medium",
            "timestamp": datetime.now(),
            "symbol": "unknown",
        }


class VolatilityOrderSizer:
    """
    Intelligent order sizing based on market volatility

    Automatically adjusts order sizes and grid parameters based on:
    - Current market volatility
    - Historical volatility patterns
    - Risk management constraints
    - Integration with compound interest system
    """

    def __init__(self):
        self.volatility_calculator = VolatilityCalculator()
        self.logger = logging.getLogger(__name__)

        # Volatility adjustment parameters
        self.low_volatility_multiplier = 1.3  # 30% larger orders in calm markets
        self.medium_volatility_multiplier = 1.0  # Normal orders
        self.high_volatility_multiplier = 0.6  # 40% smaller orders in volatile markets

        # Grid spacing adjustments
        self.low_volatility_spacing_factor = 0.8  # Tighter grids (20% less spacing)
        self.medium_volatility_spacing_factor = 1.0  # Normal spacing
        self.high_volatility_spacing_factor = 1.5  # Wider grids (50% more spacing)

        # Safety constraints
        self.max_volatility_adjustment = 2.0  # Never more than 2x adjustment
        self.min_volatility_adjustment = 0.3  # Never less than 30% of base

        self.logger.info("🌊 Volatility-based Order Sizer initialized")

    async def get_volatility_adjusted_order_size(
        self, symbol: str, base_size: float
    ) -> float:
        """
        Calculate volatility-adjusted order size

        Process:
        1. Get current market volatility
        2. Determine appropriate multiplier
        3. Apply safety constraints
        4. Return adjusted order size
        """
        try:
            # Get volatility metrics
            volatility_data = (
                await self.volatility_calculator.calculate_comprehensive_volatility(
                    symbol
                )
            )

            overall_volatility = volatility_data["overall_volatility"]
            volatility_regime = volatility_data["volatility_regime"]

            # Determine multiplier based on volatility regime
            if volatility_regime == "low":
                multiplier = self.low_volatility_multiplier
                reason = "calm market - increased size"
            elif volatility_regime == "high":
                multiplier = self.high_volatility_multiplier
                reason = "volatile market - reduced size"
            else:
                multiplier = self.medium_volatility_multiplier
                reason = "normal market - standard size"

            # Fine-tune multiplier based on exact volatility value
            if volatility_regime == "medium":
                # Linear interpolation within medium range (0.3 to 0.7)
                volatility_factor = (overall_volatility - 0.3) / (0.7 - 0.3)
                multiplier = 1.2 - (volatility_factor * 0.4)  # 1.2 to 0.8 range

            # Apply safety constraints
            safe_multiplier = max(
                self.min_volatility_adjustment,
                min(self.max_volatility_adjustment, multiplier),
            )

            # Calculate final order size
            adjusted_size = base_size * safe_multiplier

            self.logger.info(
                f"🌊 {symbol} volatility adjustment: {overall_volatility:.3f} → "
                f"{safe_multiplier:.2f}x ({reason})"
            )

            return adjusted_size

        except Exception as e:
            self.logger.error(f"❌ Volatility order size adjustment error: {e}")
            return base_size  # Return unchanged on error

    async def get_volatility_adjusted_spacing(
        self, symbol: str, base_spacing: float
    ) -> float:
        """
        Calculate volatility-adjusted grid spacing

        Logic:
        - Low volatility: Tighter grids to capture smaller movements
        - High volatility: Wider grids to avoid excessive triggering
        """
        try:
            volatility_data = (
                await self.volatility_calculator.calculate_comprehensive_volatility(
                    symbol
                )
            )
            volatility_regime = volatility_data["volatility_regime"]

            # Determine spacing factor
            if volatility_regime == "low":
                spacing_factor = self.low_volatility_spacing_factor
                reason = "tight grids for calm market"
            elif volatility_regime == "high":
                spacing_factor = self.high_volatility_spacing_factor
                reason = "wide grids for volatile market"
            else:
                spacing_factor = self.medium_volatility_spacing_factor
                reason = "standard grids for normal market"

            # Calculate adjusted spacing
            adjusted_spacing = base_spacing * spacing_factor

            # Ensure reasonable bounds
            min_spacing = 0.01  # 1% minimum
            max_spacing = 0.08  # 8% maximum
            final_spacing = max(min_spacing, min(max_spacing, adjusted_spacing))

            self.logger.info(
                f"📏 {symbol} spacing adjustment: {base_spacing:.3f} → "
                f"{final_spacing:.3f} ({reason})"
            )

            return final_spacing

        except Exception as e:
            self.logger.error(f"❌ Volatility spacing adjustment error: {e}")
            return base_spacing

    async def get_risk_adjusted_levels(self, symbol: str, base_levels: int) -> int:
        """
        Adjust number of grid levels based on volatility

        Logic:
        - High volatility: Fewer levels to reduce exposure
        - Low volatility: More levels to capture opportunities
        """
        try:
            volatility_data = (
                await self.volatility_calculator.calculate_comprehensive_volatility(
                    symbol
                )
            )
            volatility_regime = volatility_data["volatility_regime"]

            if volatility_regime == "low":
                # More levels in calm markets
                adjustment_factor = 1.2
                reason = "more levels for stable market"
            elif volatility_regime == "high":
                # Fewer levels in volatile markets
                adjustment_factor = 0.8
                reason = "fewer levels for volatile market"
            else:
                adjustment_factor = 1.0
                reason = "standard levels for normal market"

            adjusted_levels = int(base_levels * adjustment_factor)

            # Ensure reasonable bounds
            min_levels = 3  # Minimum 3 levels
            max_levels = 12  # Maximum 12 levels
            final_levels = max(min_levels, min(max_levels, adjusted_levels))

            if final_levels != base_levels:
                self.logger.info(
                    f"📊 {symbol} levels adjustment: {base_levels} → "
                    f"{final_levels} ({reason})"
                )

            return final_levels

        except Exception as e:
            self.logger.error(f"❌ Risk level adjustment error: {e}")
            return base_levels

    async def get_volatility_dashboard_data(self, symbols: List[str]) -> Dict:
        """Get volatility data for dashboard display"""
        try:
            dashboard_data = {}

            for symbol in symbols:
                volatility_data = (
                    await self.volatility_calculator.calculate_comprehensive_volatility(
                        symbol
                    )
                )

                dashboard_data[symbol] = {
                    "volatility": volatility_data["overall_volatility"],
                    "regime": volatility_data["volatility_regime"],
                    "order_size_multiplier": await self._get_order_size_multiplier(
                        symbol
                    ),
                    "grid_spacing_factor": await self._get_spacing_factor(symbol),
                    "risk_level": await self._get_risk_level(
                        volatility_data["overall_volatility"]
                    ),
                }

            return dashboard_data

        except Exception as e:
            self.logger.error(f"❌ Dashboard data error: {e}")
            return {}

    async def _get_order_size_multiplier(self, symbol: str) -> float:
        """Get the current order size multiplier for a symbol"""
        volatility_data = (
            await self.volatility_calculator.calculate_comprehensive_volatility(symbol)
        )
        volatility_regime = volatility_data["volatility_regime"]

        multiplier_map = {
            "low": self.low_volatility_multiplier,
            "medium": self.medium_volatility_multiplier,
            "high": self.high_volatility_multiplier,
        }

        return multiplier_map.get(volatility_regime, 1.0)

    async def _get_spacing_factor(self, symbol: str) -> float:
        """Get the current spacing factor for a symbol"""
        volatility_data = (
            await self.volatility_calculator.calculate_comprehensive_volatility(symbol)
        )
        volatility_regime = volatility_data["volatility_regime"]

        factor_map = {
            "low": self.low_volatility_spacing_factor,
            "medium": self.medium_volatility_spacing_factor,
            "high": self.high_volatility_spacing_factor,
        }

        return factor_map.get(volatility_regime, 1.0)

    def _get_risk_level(self, overall_volatility: float) -> str:
        """Convert volatility to risk level description"""
        if overall_volatility < 0.2:
            return "Very Low Risk"
        elif overall_volatility < 0.4:
            return "Low Risk"
        elif overall_volatility < 0.6:
            return "Moderate Risk"
        elif overall_volatility < 0.8:
            return "High Risk"
        else:
            return "Very High Risk"


# =============================================================================
# INTEGRATION WITH COMPOUND INTEREST MANAGER
# =============================================================================


class VolatilityCompoundIntegration:
    """
    Integration service to combine Volatility Order Sizer with Compound Interest Manager

    This creates a sophisticated order sizing system that considers:
    - Compound interest growth (from profits)
    - Market volatility conditions (from current market state)
    - Risk management (safety constraints)
    """

    def __init__(self, compound_manager, volatility_sizer: VolatilityOrderSizer):
        self.compound_manager = compound_manager
        self.volatility_sizer = volatility_sizer
        self.logger = logging.getLogger(__name__)

    async def get_optimized_order_size(
        self, client_id: int, symbol: str, base_capital: float
    ) -> float:
        """
        Get fully optimized order size considering both compound and volatility factors

        Process:
        1. Get compound-adjusted order size (based on profits)
        2. Apply volatility adjustment (based on market conditions)
        3. Ensure final size meets all safety constraints
        """
        try:
            # Step 1: Get compound-adjusted order size
            compound_size = await self.compound_manager.get_current_order_size(
                client_id, symbol, base_capital
            )

            # Step 2: Apply volatility adjustment
            final_size = await self.volatility_sizer.get_volatility_adjusted_order_size(
                symbol, compound_size
            )

            # Step 3: Log the optimization process
            compound_multiplier = (
                await self.compound_manager._calculate_compound_multiplier(client_id)
            )
            volatility_data = await self.volatility_sizer.volatility_calculator.calculate_comprehensive_volatility(
                symbol
            )
            volatility_multiplier = (
                await self.volatility_sizer._get_order_size_multiplier(symbol)
            )

            total_multiplier = (final_size / base_capital) if base_capital > 0 else 1.0

            self.logger.info(
                f"🎯 {symbol} optimized sizing for client {client_id}:\n"
                f"   Base: ${base_capital:.2f}\n"
                f"   Compound: {compound_multiplier:.2f}x → ${compound_size:.2f}\n"
                f"   Volatility: {volatility_multiplier:.2f}x ({volatility_data['volatility_regime']})\n"
                f"   Final: {total_multiplier:.2f}x → ${final_size:.2f}"
            )

            return final_size

        except Exception as e:
            self.logger.error(f"❌ Optimized order size calculation error: {e}")
            return base_capital * 0.1  # Safe fallback

    async def get_optimized_grid_config(
        self, client_id: int, symbol: str, base_capital: float
    ) -> Dict:
        """
        Get complete optimized grid configuration

        Returns all parameters needed for grid setup:
        - order_size: Optimized order size
        - grid_spacing: Volatility-adjusted spacing
        - grid_levels: Risk-adjusted level count
        - allocation: Performance-based allocation
        """
        try:
            # Get optimized order size
            order_size = await self.get_optimized_order_size(
                client_id, symbol, base_capital
            )

            # Get volatility-adjusted spacing
            base_spacing = (
                Config.BASE_GRID_SPACING
                if hasattr(Config, "BASE_GRID_SPACING")
                else 0.025
            )
            grid_spacing = await self.volatility_sizer.get_volatility_adjusted_spacing(
                symbol, base_spacing
            )

            # Get risk-adjusted levels
            base_levels = (
                Config.DEFAULT_GRID_LEVELS
                if hasattr(Config, "DEFAULT_GRID_LEVELS")
                else 8
            )
            grid_levels = await self.volatility_sizer.get_risk_adjusted_levels(
                symbol, base_levels
            )

            # Get performance-based allocation
            allocation = await self.compound_manager.get_grid_allocation(
                client_id, base_capital
            )

            # Get volatility context
            volatility_data = await self.volatility_sizer.volatility_calculator.calculate_comprehensive_volatility(
                symbol
            )

            config = {
                "order_size": order_size,
                "grid_spacing": grid_spacing,
                "grid_levels": grid_levels,
                "allocation": allocation,
                "volatility_context": {
                    "regime": volatility_data["volatility_regime"],
                    "score": volatility_data["overall_volatility"],
                    "adjustments_applied": {
                        "order_size_factor": await self.volatility_sizer._get_order_size_multiplier(
                            symbol
                        ),
                        "spacing_factor": await self.volatility_sizer._get_spacing_factor(
                            symbol
                        ),
                    },
                },
                "optimization_summary": f"Compound + Volatility optimized for {volatility_data['volatility_regime']} market",
            }

            return config

        except Exception as e:
            self.logger.error(f"❌ Grid configuration optimization error: {e}")
            return self._get_fallback_config(base_capital)

    def _get_fallback_config(self, base_capital: float) -> Dict:
        """Safe fallback configuration if optimization fails"""
        return {
            "order_size": base_capital * 0.1,
            "grid_spacing": 0.025,
            "grid_levels": 8,
            "allocation": {
                "base_allocation": 0.4,
                "enhanced_allocation": 0.6,
                "base_capital": base_capital * 0.4,
                "enhanced_capital": base_capital * 0.6,
            },
            "volatility_context": {"regime": "unknown"},
            "optimization_summary": "Fallback configuration due to optimization error",
        }
