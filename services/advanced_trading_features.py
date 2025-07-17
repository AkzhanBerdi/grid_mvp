# services/advanced_trading_features.py
"""
Advanced Trading Features Implementation
Replaces temporary placeholders with full OOP implementations
"""

from datetime import datetime
from typing import Dict, List, Tuple
import logging
import time

from binance.client import Client
import numpy as np
import pytz

from config import Config
from repositories.trade_repository import TradeRepository


class CompoundInterestManager:
    """
    Automatically grows order sizes from profits using compound strategy
    Integrates with FIFO profit tracking for accurate profit calculation
    """

    def __init__(self, client_id: int, base_order_size: float = 50.0):
        self.client_id = client_id
        self.base_order_size = base_order_size
        self.logger = logging.getLogger(__name__)

        # Compound settings
        self.profit_reinvestment_rate = 0.30  # Reinvest 30% of profits
        self.max_order_size_multiplier = 3.0  # Safety cap at 3x
        self.compound_threshold = 25.0  # Start compounding after $25 profit
        self.reset_on_loss_threshold = -50.0  # Reset multiplier if losses exceed $50

        # State tracking
        self.current_multiplier = 1.0
        self.total_compounded_profit = 0.0
        self.last_profit_check = 0.0
        self.compound_history = []

        self.logger.info(f"💰 CompoundManager initialized for client {client_id}")
        self.logger.info(f"   Base order size: ${base_order_size}")
        self.logger.info(
            f"   Reinvestment rate: {self.profit_reinvestment_rate * 100}%"
        )
        self.logger.info(f"   Max multiplier: {self.max_order_size_multiplier}x")

    async def update_from_fifo_profit(self, fifo_profit: float) -> bool:
        """
        Update compound multiplier based on FIFO profit calculation
        Returns True if multiplier changed significantly
        """
        try:
            profit_change = fifo_profit - self.last_profit_check

            # Only update if profit changed significantly
            if abs(profit_change) < 1.0:
                return False

            old_multiplier = self.current_multiplier

            # Calculate new multiplier based on total FIFO profit
            if fifo_profit >= self.compound_threshold:
                # Progressive compounding: higher profits = higher multiplier
                profit_factor = fifo_profit / self.compound_threshold
                new_multiplier = 1.0 + (profit_factor * self.profit_reinvestment_rate)

                # Apply safety cap
                self.current_multiplier = min(
                    new_multiplier, self.max_order_size_multiplier
                )

                # Track compounded profit
                self.total_compounded_profit = (
                    fifo_profit * self.profit_reinvestment_rate
                )

                self.logger.info(
                    f"📈 Compound update: ${fifo_profit:.2f} profit → {self.current_multiplier:.2f}x multiplier"
                )

            elif fifo_profit <= self.reset_on_loss_threshold:
                # Reset multiplier on significant losses
                self.current_multiplier = 1.0
                self.total_compounded_profit = 0.0

                self.logger.warning(
                    f"🔄 Compound reset: ${fifo_profit:.2f} loss → 1.0x multiplier"
                )

            else:
                # Gradual reduction for small losses
                if fifo_profit < 0 and self.current_multiplier > 1.0:
                    reduction_factor = max(
                        0.95, 1.0 + (fifo_profit / self.compound_threshold)
                    )
                    self.current_multiplier = max(
                        1.0, self.current_multiplier * reduction_factor
                    )

            # Record history if changed significantly
            if abs(self.current_multiplier - old_multiplier) > 0.05:
                self.compound_history.append(
                    {
                        "timestamp": datetime.now(),
                        "profit": fifo_profit,
                        "old_multiplier": old_multiplier,
                        "new_multiplier": self.current_multiplier,
                        "profit_change": profit_change,
                    }
                )

                # Keep history manageable
                if len(self.compound_history) > 50:
                    self.compound_history = self.compound_history[-25:]

            self.last_profit_check = fifo_profit
            return abs(self.current_multiplier - old_multiplier) > 0.05

        except Exception as e:
            self.logger.error(f"❌ Compound update error: {e}")
            return False

    def get_current_order_size(self) -> float:
        """Get dynamically adjusted order size"""
        adjusted_size = self.base_order_size * self.current_multiplier

        # Ensure minimum notional compliance
        return max(adjusted_size, 15.0)  # Minimum $15 for Binance NOTIONAL

    def get_compound_status(self) -> Dict:
        """Get comprehensive compound status"""
        return {
            "client_id": self.client_id,
            "base_order_size": self.base_order_size,
            "current_multiplier": round(self.current_multiplier, 3),
            "current_order_size": round(self.get_current_order_size(), 2),
            "total_compounded_profit": round(self.total_compounded_profit, 2),
            "profit_reinvestment_rate": self.profit_reinvestment_rate,
            "compound_threshold": self.compound_threshold,
            "max_multiplier": self.max_order_size_multiplier,
            "compound_active": self.current_multiplier > 1.05,
            "recent_changes": len(self.compound_history[-5:]),
            "status": self._get_compound_status_text(),
        }

    def _get_compound_status_text(self) -> str:
        """Get human-readable compound status"""
        if self.current_multiplier >= 2.5:
            return "🚀 High Performance"
        elif self.current_multiplier >= 1.5:
            return "📈 Growing Strong"
        elif self.current_multiplier >= 1.1:
            return "💰 Compounding"
        else:
            return "⚪ Building Foundation"


class IntelligentMarketTimer:
    """
    Adjusts trading frequency and order placement based on market sessions
    Optimizes for volume and volatility patterns
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Market session definitions (UTC)
        self.market_sessions = {
            "asia": {"start": 0, "end": 8, "intensity": 1.2},
            "london": {"start": 8, "end": 16, "intensity": 1.0},
            "newyork": {"start": 13, "end": 21, "intensity": 1.3},
            "overlap_london_ny": {"start": 13, "end": 16, "intensity": 1.5},
            "quiet": {"start": 21, "end": 24, "intensity": 0.7},
        }

        # Weekend adjustments
        self.weekend_multiplier = 0.6

        self.logger.info("⏰ IntelligentMarketTimer initialized")

    def get_current_trading_intensity(self) -> float:
        """
        Calculate current trading intensity based on time and market conditions
        Returns multiplier: 1.0 = normal, >1.0 = increased activity, <1.0 = reduced
        """
        try:
            now_utc = datetime.now(pytz.UTC)
            current_hour = now_utc.hour
            current_weekday = now_utc.weekday()  # 0 = Monday, 6 = Sunday

            # Weekend adjustment
            is_weekend = current_weekday >= 5  # Saturday = 5, Sunday = 6
            base_intensity = self.weekend_multiplier if is_weekend else 1.0

            # Find current session
            session_intensity = 1.0
            current_session = "unknown"

            # Check overlap periods first (highest priority)
            if 13 <= current_hour <= 16 and not is_weekend:
                session_intensity = self.market_sessions["overlap_london_ny"][
                    "intensity"
                ]
                current_session = "London-NY Overlap"

            else:
                # Check individual sessions
                for session_name, session_data in self.market_sessions.items():
                    if session_name == "overlap_london_ny":
                        continue

                    start_hour = session_data["start"]
                    end_hour = session_data["end"]

                    if start_hour <= current_hour < end_hour:
                        session_intensity = session_data["intensity"]
                        current_session = session_name.title()
                        break

            # Handle wrap-around for quiet hours (21-24 and 0-8)
            if current_hour >= 21 or current_hour < 8:
                if current_hour >= 21:
                    session_intensity = self.market_sessions["quiet"]["intensity"]
                    current_session = "Quiet Hours"
                else:
                    session_intensity = self.market_sessions["asia"]["intensity"]
                    current_session = "Asia"

            final_intensity = base_intensity * session_intensity

            self.logger.debug(
                f"⏰ Market timing: {current_session} session, intensity: {final_intensity:.2f}"
            )

            return final_intensity

        except Exception as e:
            self.logger.error(f"❌ Market timing error: {e}")
            return 1.0  # Default neutral intensity

    def get_optimal_check_interval(self, base_interval: float = 30.0) -> float:
        """
        Get optimal check interval based on market activity
        Higher activity = shorter intervals for more responsive trading
        """
        intensity = self.get_current_trading_intensity()

        # Inverse relationship: higher intensity = shorter intervals
        optimal_interval = base_interval / intensity

        # Ensure reasonable bounds (10 seconds to 2 minutes)
        optimal_interval = max(10.0, min(120.0, optimal_interval))

        return optimal_interval

    def should_place_orders_now(self) -> bool:
        """
        Determine if it's a good time to place new orders
        Considers market activity and volatility expectations
        """
        intensity = self.get_current_trading_intensity()

        # Higher threshold during low activity periods
        return intensity >= 0.8

    def get_session_info(self) -> Dict:
        """Get current market session information"""
        now_utc = datetime.now(pytz.UTC)
        current_hour = now_utc.hour
        is_weekend = now_utc.weekday() >= 5

        return {
            "current_utc_hour": current_hour,
            "is_weekend": is_weekend,
            "trading_intensity": self.get_current_trading_intensity(),
            "optimal_check_interval": self.get_optimal_check_interval(),
            "should_place_orders": self.should_place_orders_now(),
            "session_recommendation": self._get_session_recommendation(),
        }

    def _get_session_recommendation(self) -> str:
        """Get trading recommendation for current session"""
        intensity = self.get_current_trading_intensity()

        if intensity >= 1.4:
            return "🔥 Peak Activity - Aggressive Trading"
        elif intensity >= 1.1:
            return "📈 High Activity - Normal Trading"
        elif intensity >= 0.9:
            return "⚖️ Moderate Activity - Steady Trading"
        elif intensity >= 0.7:
            return "🌙 Low Activity - Conservative Trading"
        else:
            return "💤 Minimal Activity - Maintenance Mode"


class VolatilityBasedRiskManager:
    """
    Advanced risk management based on real-time volatility analysis
    Dynamically adjusts order sizes and grid spacing
    """

    def __init__(self, binance_client: Client, symbol: str):
        self.binance_client = binance_client
        self.symbol = symbol
        self.logger = logging.getLogger(__name__)

        # Volatility settings
        self.volatility_lookback_hours = 24
        self.volatility_cache = {}
        self.cache_ttl = 300  # 5 minutes

        # Risk parameters
        self.low_volatility_threshold = 0.15  # 15% daily volatility
        self.high_volatility_threshold = 0.35  # 35% daily volatility
        self.extreme_volatility_threshold = 0.50  # 50% daily volatility

        # Risk multipliers
        self.risk_multipliers = {
            "low": {
                "order_size": 1.2,
                "grid_spacing": 0.8,
            },  # Larger orders, tighter grids
            "moderate": {"order_size": 1.0, "grid_spacing": 1.0},  # Normal settings
            "high": {
                "order_size": 0.7,
                "grid_spacing": 1.3,
            },  # Smaller orders, wider grids
            "extreme": {"order_size": 0.5, "grid_spacing": 1.6},  # Very conservative
        }

        self.logger.info(f"🛡️ VolatilityRiskManager initialized for {symbol}")

    async def calculate_current_volatility(self) -> float:
        """
        Calculate current volatility using multiple methods
        Returns annualized volatility as a decimal (0.20 = 20%)
        """
        try:
            cache_key = f"{self.symbol}_volatility"
            now = time.time()

            # Check cache
            if cache_key in self.volatility_cache:
                cached_data = self.volatility_cache[cache_key]
                if now - cached_data["timestamp"] < self.cache_ttl:
                    return cached_data["volatility"]

            # Get kline data for volatility calculation
            klines = self.binance_client.get_historical_klines(
                self.symbol,
                Client.KLINE_INTERVAL_1HOUR,
                f"{self.volatility_lookback_hours} hours ago UTC",
            )

            if len(klines) < 12:  # Need at least 12 hours of data
                self.logger.warning(
                    f"Insufficient data for volatility calculation: {len(klines)} klines"
                )
                return 0.25  # Default moderate volatility

            # Calculate hourly returns
            closes = [float(kline[4]) for kline in klines]
            returns = []

            for i in range(1, len(closes)):
                if closes[i - 1] > 0:
                    hourly_return = (closes[i] - closes[i - 1]) / closes[i - 1]
                    returns.append(hourly_return)

            if len(returns) < 10:
                return 0.25  # Default if insufficient returns

            # Calculate standard deviation and annualize
            returns_array = np.array(returns)
            hourly_volatility = np.std(returns_array)

            # Annualize: hourly → daily → yearly
            daily_volatility = hourly_volatility * np.sqrt(24)
            annualized_volatility = daily_volatility * np.sqrt(365)

            # Apply bounds checking
            volatility = max(0.05, min(1.0, annualized_volatility))

            # Cache result
            self.volatility_cache[cache_key] = {
                "volatility": volatility,
                "timestamp": now,
            }

            self.logger.debug(
                f"📊 {self.symbol} volatility: {volatility:.3f} ({volatility * 100:.1f}%)"
            )

            return volatility

        except Exception as e:
            self.logger.error(f"❌ Volatility calculation error for {self.symbol}: {e}")
            return 0.25  # Safe default

    def classify_volatility_regime(self, volatility: float) -> str:
        """Classify current volatility regime"""
        if volatility >= self.extreme_volatility_threshold:
            return "extreme"
        elif volatility >= self.high_volatility_threshold:
            return "high"
        elif volatility <= self.low_volatility_threshold:
            return "low"
        else:
            return "moderate"

    async def get_risk_adjusted_parameters(
        self, base_order_size: float, base_grid_spacing: float
    ) -> Dict:
        """
        Get risk-adjusted trading parameters based on current volatility
        """
        try:
            current_volatility = await self.calculate_current_volatility()
            regime = self.classify_volatility_regime(current_volatility)
            multipliers = self.risk_multipliers[regime]

            adjusted_order_size = base_order_size * multipliers["order_size"]
            adjusted_grid_spacing = base_grid_spacing * multipliers["grid_spacing"]

            # Ensure minimum order size for Binance
            adjusted_order_size = max(adjusted_order_size, 15.0)

            # Ensure reasonable grid spacing bounds
            adjusted_grid_spacing = max(0.01, min(0.08, adjusted_grid_spacing))

            risk_score = self._calculate_risk_score(current_volatility, regime)

            result = {
                "volatility": current_volatility,
                "regime": regime,
                "risk_score": risk_score,
                "original_order_size": base_order_size,
                "adjusted_order_size": round(adjusted_order_size, 2),
                "original_grid_spacing": base_grid_spacing,
                "adjusted_grid_spacing": round(adjusted_grid_spacing, 4),
                "order_size_multiplier": multipliers["order_size"],
                "grid_spacing_multiplier": multipliers["grid_spacing"],
                "recommendation": self._get_risk_recommendation(regime, risk_score),
            }

            self.logger.info(f"🛡️ Risk adjustment for {self.symbol}:")
            self.logger.info(f"   Volatility: {current_volatility:.3f} ({regime})")
            self.logger.info(
                f"   Order size: ${base_order_size:.2f} → ${adjusted_order_size:.2f}"
            )
            self.logger.info(
                f"   Grid spacing: {base_grid_spacing:.3f} → {adjusted_grid_spacing:.3f}"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Risk adjustment error: {e}")
            return {
                "volatility": 0.25,
                "regime": "moderate",
                "risk_score": 0.5,
                "adjusted_order_size": base_order_size,
                "adjusted_grid_spacing": base_grid_spacing,
                "recommendation": "Using default parameters due to error",
            }

    def _calculate_risk_score(self, volatility: float, regime: str) -> float:
        """Calculate overall risk score (0-1, higher = riskier)"""
        # Base score from volatility
        volatility_score = min(1.0, volatility / 0.5)  # Normalize to 50% volatility

        # Regime adjustment
        regime_multipliers = {"low": 0.3, "moderate": 0.5, "high": 0.8, "extreme": 1.0}

        regime_factor = regime_multipliers.get(regime, 0.5)
        risk_score = (volatility_score * 0.7) + (regime_factor * 0.3)

        return min(1.0, risk_score)

    def _get_risk_recommendation(self, regime: str, risk_score: float) -> str:
        """Get human-readable risk recommendation"""
        if regime == "extreme":
            return "🚨 Extreme volatility - Minimal position sizes recommended"
        elif regime == "high":
            return "⚠️ High volatility - Reduced risk exposure"
        elif regime == "low":
            return "✅ Low volatility - Safe to increase position sizes"
        else:
            return "📊 Moderate volatility - Standard risk management"

    async def should_pause_trading(self) -> Tuple[bool, str]:
        """
        Determine if trading should be paused due to extreme conditions
        Returns (should_pause, reason)
        """
        try:
            volatility = await self.calculate_current_volatility()

            # Pause if volatility is extremely high
            if volatility >= 0.6:  # 60% annualized volatility
                return True, f"Extreme volatility detected: {volatility * 100:.1f}%"

            # Additional checks could be added here:
            # - Price gaps
            # - Volume spikes
            # - Market manipulation indicators

            return False, "Normal trading conditions"

        except Exception as e:
            self.logger.error(f"❌ Error checking pause conditions: {e}")
            return False, "Unable to assess conditions"


class SmartGridAutoReset:
    """
    Intelligent grid reset system that adapts to market movements
    Automatically repositions grids when price moves significantly
    """

    def __init__(self, symbol: str, client_id: int):
        self.symbol = symbol
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        # Reset parameters
        self.price_deviation_threshold = 0.15  # 15% price movement triggers reset
        self.min_reset_interval = 3600  # 1 hour minimum between resets
        self.max_resets_per_day = 5  # Maximum resets in 24 hours

        # State tracking
        self.last_reset_time = 0
        self.center_price = 0.0
        self.reset_history = []
        self.pending_reset = False

        self.logger.info(f"🔄 SmartGridAutoReset initialized for {symbol}")

    def should_reset_grid(
        self, current_price: float, grid_center_price: float
    ) -> Tuple[bool, str]:
        """
        Determine if grid should be reset based on multiple criteria
        Returns (should_reset, reason)
        """
        try:
            if grid_center_price <= 0:
                return False, "Invalid center price"

            # Calculate price deviation
            price_deviation = abs(current_price - grid_center_price) / grid_center_price

            # Check time constraint
            time_since_last_reset = time.time() - self.last_reset_time
            can_reset_time = time_since_last_reset >= self.min_reset_interval

            # Check daily reset limit
            daily_resets = self._count_recent_resets(24 * 3600)  # 24 hours
            can_reset_frequency = daily_resets < self.max_resets_per_day

            # Adaptive threshold based on recent volatility
            adaptive_threshold = self._calculate_adaptive_threshold()

            self.logger.debug(f"🔄 Reset check for {self.symbol}:")
            self.logger.debug(
                f"   Price deviation: {price_deviation:.3f} (threshold: {adaptive_threshold:.3f})"
            )
            self.logger.debug(
                f"   Time since reset: {time_since_last_reset:.0f}s (min: {self.min_reset_interval})"
            )
            self.logger.debug(
                f"   Daily resets: {daily_resets}/{self.max_resets_per_day}"
            )

            # Decision logic
            if price_deviation >= adaptive_threshold:
                if not can_reset_time:
                    time_remaining = self.min_reset_interval - time_since_last_reset
                    return (
                        False,
                        f"Reset cooling down ({time_remaining:.0f}s remaining)",
                    )

                if not can_reset_frequency:
                    return (
                        False,
                        f"Daily reset limit reached ({daily_resets}/{self.max_resets_per_day})",
                    )

                return (
                    True,
                    f"Price moved {price_deviation:.1%} from center (threshold: {adaptive_threshold:.1%})",
                )

            return (
                False,
                f"Price deviation {price_deviation:.1%} below threshold {adaptive_threshold:.1%}",
            )

        except Exception as e:
            self.logger.error(f"❌ Reset check error: {e}")
            return False, f"Error in reset logic: {e}"

    def _calculate_adaptive_threshold(self) -> float:
        """
        Calculate adaptive reset threshold based on recent market conditions
        More volatile markets get higher thresholds to reduce reset frequency
        """
        base_threshold = self.price_deviation_threshold

        # Analyze recent reset frequency to adapt threshold
        recent_resets = self._count_recent_resets(3600 * 6)  # 6 hours

        if recent_resets >= 3:
            # Too many resets - increase threshold
            adaptive_factor = 1.5
        elif recent_resets == 0 and time.time() - self.last_reset_time > 3600 * 12:
            # No resets for a while - could be less sensitive
            adaptive_factor = 0.8
        else:
            # Normal conditions
            adaptive_factor = 1.0

        return base_threshold * adaptive_factor

    def _count_recent_resets(self, time_window_seconds: int) -> int:
        """Count resets within the specified time window"""
        current_time = time.time()
        cutoff_time = current_time - time_window_seconds

        return len(
            [reset for reset in self.reset_history if reset["timestamp"] >= cutoff_time]
        )

    async def execute_smart_reset(
        self, new_center_price: float, grid_config, reason: str
    ) -> Dict:
        """
        Execute intelligent grid reset with comprehensive logging
        """
        try:
            reset_start_time = time.time()
            old_center = (
                grid_config.center_price if hasattr(grid_config, "center_price") else 0
            )

            self.logger.info(f"🔄 Executing smart reset for {self.symbol}:")
            self.logger.info(f"   Reason: {reason}")
            self.logger.info(f"   Old center: ${old_center:.4f}")
            self.logger.info(f"   New center: ${new_center_price:.4f}")
            self.logger.info(
                f"   Price change: {((new_center_price - old_center) / old_center * 100):.2f}%"
                if old_center > 0
                else "   Initial setup"
            )

            # Record reset in history
            reset_record = {
                "timestamp": reset_start_time,
                "old_center_price": old_center,
                "new_center_price": new_center_price,
                "reason": reason,
                "client_id": self.client_id,
            }

            self.reset_history.append(reset_record)

            # Keep history manageable (last 50 resets)
            if len(self.reset_history) > 50:
                self.reset_history = self.reset_history[-25:]

            # Update state
            self.last_reset_time = reset_start_time
            self.center_price = new_center_price

            # Reset grid levels (this would integrate with your grid config)
            if hasattr(grid_config, "calculate_grid_levels"):
                grid_config.calculate_grid_levels(new_center_price)

            reset_duration = time.time() - reset_start_time

            result = {
                "success": True,
                "symbol": self.symbol,
                "old_center_price": old_center,
                "new_center_price": new_center_price,
                "price_change_percent": (
                    (new_center_price - old_center) / old_center * 100
                )
                if old_center > 0
                else 0,
                "reason": reason,
                "reset_duration": reset_duration,
                "reset_count_today": self._count_recent_resets(24 * 3600),
                "next_reset_available_in": self.min_reset_interval,
            }

            self.logger.info(f"✅ Smart reset completed in {reset_duration:.2f}s")

            return result

        except Exception as e:
            self.logger.error(f"❌ Smart reset error: {e}")
            return {"success": False, "error": str(e), "symbol": self.symbol}

    def get_reset_status(self) -> Dict:
        """Get comprehensive reset status and statistics"""
        current_time = time.time()
        time_since_last_reset = current_time - self.last_reset_time

        return {
            "symbol": self.symbol,
            "last_reset_time": datetime.fromtimestamp(self.last_reset_time).isoformat()
            if self.last_reset_time > 0
            else None,
            "time_since_last_reset_seconds": time_since_last_reset,
            "time_until_next_reset_available": max(
                0, self.min_reset_interval - time_since_last_reset
            ),
            "can_reset_now": time_since_last_reset >= self.min_reset_interval,
            "current_center_price": self.center_price,
            "adaptive_threshold": self._calculate_adaptive_threshold(),
            "resets_today": self._count_recent_resets(24 * 3600),
            "resets_this_week": self._count_recent_resets(7 * 24 * 3600),
            "total_resets": len(self.reset_history),
            "reset_frequency_analysis": self._analyze_reset_frequency(),
        }

    def _analyze_reset_frequency(self) -> Dict:
        """Analyze reset patterns for optimization"""
        if len(self.reset_history) < 2:
            return {"status": "insufficient_data"}

        # Calculate average time between resets
        time_deltas = []
        for i in range(1, len(self.reset_history)):
            delta = (
                self.reset_history[i]["timestamp"]
                - self.reset_history[i - 1]["timestamp"]
            )
            time_deltas.append(delta)

        if time_deltas:
            avg_time_between_resets = sum(time_deltas) / len(time_deltas)

            if avg_time_between_resets < 1800:  # 30 minutes
                frequency_assessment = "too_frequent"
                recommendation = "Consider increasing reset threshold"
            elif avg_time_between_resets > 24 * 3600:  # 24 hours
                frequency_assessment = "infrequent"
                recommendation = "Reset system working well or market is stable"
            else:
                frequency_assessment = "optimal"
                recommendation = "Reset frequency appears balanced"
        else:
            avg_time_between_resets = 0
            frequency_assessment = "unknown"
            recommendation = "Need more data"

        return {
            "average_time_between_resets": avg_time_between_resets,
            "frequency_assessment": frequency_assessment,
            "recommendation": recommendation,
            "total_resets_analyzed": len(time_deltas),
        }


class PrecisionOrderHandler:
    """
    Eliminates LOT_SIZE and NOTIONAL errors with symbol-specific precision handling
    Integrates with Binance exchange info for dynamic precision rules
    """

    def __init__(self, binance_client: Client):
        self.binance_client = binance_client
        self.logger = logging.getLogger(__name__)

        # Cache for exchange info
        self.exchange_info_cache = {}
        self.cache_ttl = 3600  # 1 hour cache

        # Symbol-specific overrides for known issues
        self.symbol_overrides = {
            "ADAUSDT": {
                "quantity_precision": 0,  # Whole numbers only
                "min_quantity": 10,
                "step_size": 1.0,
            },
            "AVAXUSDT": {
                "quantity_precision": 3,  # 3 decimal places
                "min_quantity": 0.1,
                "step_size": 0.001,
            },
        }

        self.logger.info("🎯 PrecisionOrderHandler initialized")

    async def get_symbol_precision_rules(self, symbol: str) -> Dict:
        """
        Get comprehensive precision rules for a symbol
        Uses cache and fallbacks for reliability
        """
        try:
            cache_key = f"{symbol}_precision"
            current_time = time.time()

            # Check cache first
            if cache_key in self.exchange_info_cache:
                cached_data = self.exchange_info_cache[cache_key]
                if current_time - cached_data["timestamp"] < self.cache_ttl:
                    return cached_data["rules"]

            # Get fresh exchange info
            exchange_info = self.binance_client.get_exchange_info()
            symbol_info = next(
                (s for s in exchange_info["symbols"] if s["symbol"] == symbol), None
            )

            if not symbol_info:
                self.logger.warning(f"Symbol {symbol} not found in exchange info")
                return self._get_fallback_rules(symbol)

            # Extract filters
            filters = {f["filterType"]: f for f in symbol_info["filters"]}

            # Build precision rules
            rules = {
                "symbol": symbol,
                "status": symbol_info.get("status", "UNKNOWN"),
                "base_asset": symbol_info.get("baseAsset"),
                "quote_asset": symbol_info.get("quoteAsset"),
                "price_precision": int(symbol_info.get("quotePrecision", 8)),
                "quantity_precision": int(symbol_info.get("baseAssetPrecision", 8)),
                # LOT_SIZE filter
                "min_quantity": float(filters.get("LOT_SIZE", {}).get("minQty", 0.001)),
                "max_quantity": float(
                    filters.get("LOT_SIZE", {}).get("maxQty", 1000000)
                ),
                "step_size": float(filters.get("LOT_SIZE", {}).get("stepSize", 0.001)),
                # PRICE_FILTER
                "min_price": float(
                    filters.get("PRICE_FILTER", {}).get("minPrice", 0.01)
                ),
                "max_price": float(
                    filters.get("PRICE_FILTER", {}).get("maxPrice", 1000000)
                ),
                "tick_size": float(
                    filters.get("PRICE_FILTER", {}).get("tickSize", 0.01)
                ),
                # MIN_NOTIONAL
                "min_notional": float(
                    filters.get("MIN_NOTIONAL", {}).get("minNotional", 10.0)
                ),
                # PERCENT_PRICE (if exists)
                "percent_price_up": float(
                    filters.get("PERCENT_PRICE", {}).get("multiplierUp", 5.0)
                ),
                "percent_price_down": float(
                    filters.get("PERCENT_PRICE", {}).get("multiplierDown", 0.2)
                ),
            }

            # Apply symbol-specific overrides
            if symbol in self.symbol_overrides:
                overrides = self.symbol_overrides[symbol]
                rules.update(overrides)
                self.logger.debug(f"Applied overrides for {symbol}: {overrides}")

            # Cache the rules
            self.exchange_info_cache[cache_key] = {
                "rules": rules,
                "timestamp": current_time,
            }

            self.logger.debug(f"📋 Precision rules for {symbol}: {rules}")
            return rules

        except Exception as e:
            self.logger.error(f"❌ Error getting precision rules for {symbol}: {e}")
            return self._get_fallback_rules(symbol)

    def _get_fallback_rules(self, symbol: str) -> Dict:
        """Get safe fallback rules when exchange info fails"""
        # Use symbol overrides if available
        if symbol in self.symbol_overrides:
            base_rules = self.symbol_overrides[symbol].copy()
        else:
            base_rules = {
                "quantity_precision": 3,
                "min_quantity": 0.001,
                "step_size": 0.001,
            }

        # Add standard fallback values
        fallback = {
            "symbol": symbol,
            "status": "UNKNOWN",
            "price_precision": 4,
            "min_price": 0.01,
            "tick_size": 0.01,
            "min_notional": 10.0,
            "max_quantity": 1000000,
            "max_price": 1000000,
            "percent_price_up": 5.0,
            "percent_price_down": 0.2,
            "fallback": True,
            **base_rules,
        }

        self.logger.warning(f"Using fallback rules for {symbol}")
        return fallback

    async def format_precision_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> Dict:
        """
        Format order with perfect precision compliance
        Returns formatted order parameters or error details
        """
        try:
            rules = await self.get_symbol_precision_rules(symbol)

            # Format price
            tick_size = rules["tick_size"]
            formatted_price = round(price / tick_size) * tick_size
            formatted_price = max(
                rules["min_price"], min(rules["max_price"], formatted_price)
            )

            # Format quantity
            step_size = rules["step_size"]
            formatted_quantity = round(quantity / step_size) * step_size
            formatted_quantity = max(
                rules["min_quantity"], min(rules["max_quantity"], formatted_quantity)
            )

            # Calculate notional value
            notional_value = formatted_quantity * formatted_price

            # Validate minimum notional
            if notional_value < rules["min_notional"]:
                # Adjust quantity to meet minimum notional
                required_quantity = (
                    rules["min_notional"] * 1.01
                ) / formatted_price  # 1% buffer
                formatted_quantity = round(required_quantity / step_size) * step_size
                formatted_quantity = max(rules["min_quantity"], formatted_quantity)
                notional_value = formatted_quantity * formatted_price

            # Final validation
            validation_errors = []

            if formatted_quantity < rules["min_quantity"]:
                validation_errors.append(
                    f"Quantity {formatted_quantity} below minimum {rules['min_quantity']}"
                )

            if formatted_quantity > rules["max_quantity"]:
                validation_errors.append(
                    f"Quantity {formatted_quantity} above maximum {rules['max_quantity']}"
                )

            if formatted_price < rules["min_price"]:
                validation_errors.append(
                    f"Price {formatted_price} below minimum {rules['min_price']}"
                )

            if formatted_price > rules["max_price"]:
                validation_errors.append(
                    f"Price {formatted_price} above maximum {rules['max_price']}"
                )

            if notional_value < rules["min_notional"]:
                validation_errors.append(
                    f"Notional {notional_value:.2f} below minimum {rules['min_notional']}"
                )

            # Format output strings with proper precision
            price_str = f"{formatted_price:.{rules['price_precision']}f}".rstrip(
                "0"
            ).rstrip(".")
            quantity_str = (
                f"{formatted_quantity:.{rules['quantity_precision']}f}".rstrip(
                    "0"
                ).rstrip(".")
            )

            result = {
                "success": len(validation_errors) == 0,
                "symbol": symbol,
                "side": side,
                "original_quantity": quantity,
                "original_price": price,
                "formatted_quantity": formatted_quantity,
                "formatted_price": formatted_price,
                "quantity_str": quantity_str,
                "price_str": price_str,
                "notional_value": notional_value,
                "validation_errors": validation_errors,
                "precision_rules_applied": {
                    "quantity_precision": rules["quantity_precision"],
                    "price_precision": rules["price_precision"],
                    "step_size": rules["step_size"],
                    "tick_size": rules["tick_size"],
                    "min_notional": rules["min_notional"],
                },
            }

            if result["success"]:
                self.logger.debug(
                    f"✅ Formatted {side} order for {symbol}: {quantity_str} @ {price_str} = ${notional_value:.2f}"
                )
            else:
                self.logger.error(
                    f"❌ Order formatting failed for {symbol}: {validation_errors}"
                )

            return result

        except Exception as e:
            self.logger.error(f"❌ Precision formatting error: {e}")
            return {"success": False, "error": str(e), "symbol": symbol, "side": side}

    async def execute_precision_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> Dict:
        """
        Execute order with precision formatting and comprehensive error handling
        """
        try:
            # Format the order
            formatted_order = await self.format_precision_order(
                symbol, side, quantity, price
            )

            if not formatted_order["success"]:
                return {
                    "success": False,
                    "error": "Order formatting failed",
                    "details": formatted_order["validation_errors"],
                }

            # Execute the order
            if side.upper() == "BUY":
                order = self.binance_client.order_limit_buy(
                    symbol=symbol,
                    quantity=formatted_order["quantity_str"],
                    price=formatted_order["price_str"],
                    recvWindow=60000,
                )
            else:
                order = self.binance_client.order_limit_sell(
                    symbol=symbol,
                    quantity=formatted_order["quantity_str"],
                    price=formatted_order["price_str"],
                    recvWindow=60000,
                )

            # Parse response
            if order and order.get("status") in ["NEW", "PARTIALLY_FILLED"]:
                result = {
                    "success": True,
                    "order_id": order["orderId"],
                    "symbol": symbol,
                    "side": side,
                    "quantity": float(order["origQty"]),
                    "price": float(order["price"]),
                    "status": order["status"],
                    "client_order_id": order.get("clientOrderId"),
                    "transact_time": order.get("transactTime"),
                    "formatted_params": formatted_order,
                }

                self.logger.info(
                    f"✅ Precision order executed: {symbol} {side} {result['quantity']} @ {result['price']}"
                )
                return result

            else:
                return {
                    "success": False,
                    "error": "Order execution failed",
                    "order_response": order,
                }

        except Exception as e:
            self.logger.error(f"❌ Precision order execution error: {e}")
            return {"success": False, "error": str(e), "symbol": symbol, "side": side}


class AdvancedPerformanceMonitor:
    """
    Comprehensive performance monitoring and reporting system
    Integrates with FIFO calculations and provides actionable insights
    """

    def __init__(self, client_id: int, db_path: str = None):
        self.client_id = client_id
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)

        # Performance tracking
        self.performance_history = []
        self.alert_thresholds = {
            "loss_threshold": -100.0,  # Alert if losses exceed $100
            "win_rate_threshold": 30.0,  # Alert if win rate drops below 30%
            "volume_spike_threshold": 10.0,  # Alert if volume spikes 10x
            "drawdown_threshold": 0.15,  # Alert if drawdown exceeds 15%
        }

        self.trade_repo = TradeRepository(db_path)

        self.logger.info(
            f"📊 AdvancedPerformanceMonitor initialized for client {client_id}"
        )

    async def generate_comprehensive_report(self, days: int = 30) -> Dict:
        """
        Generate detailed performance report with actionable insights
        """
        try:
            self.logger.info(
                f"📊 Generating {days}-day performance report for client {self.client_id}"
            )

            # Get basic trade statistics
            basic_stats = self.trade_repo.get_client_trade_stats(self.client_id)
            daily_performance = self.trade_repo.get_daily_performance(
                self.client_id, days
            )
            symbol_performance = self.trade_repo.get_symbol_performance(self.client_id)

            # Calculate advanced metrics
            advanced_metrics = await self._calculate_advanced_metrics(
                basic_stats, daily_performance
            )
            risk_metrics = await self._calculate_risk_metrics(daily_performance)
            efficiency_metrics = await self._calculate_efficiency_metrics(
                basic_stats, symbol_performance
            )

            # Generate insights and recommendations
            insights = await self._generate_performance_insights(
                basic_stats, advanced_metrics, risk_metrics
            )
            recommendations = await self._generate_recommendations(
                basic_stats, advanced_metrics, risk_metrics
            )

            # Performance alerts
            alerts = await self._check_performance_alerts(basic_stats, advanced_metrics)

            # Comprehensive report
            report = {
                "client_id": self.client_id,
                "report_period_days": days,
                "generated_at": datetime.now().isoformat(),
                # Core statistics
                "basic_statistics": basic_stats,
                "daily_performance": daily_performance[-14:],  # Last 14 days
                "symbol_breakdown": symbol_performance,
                # Advanced analytics
                "advanced_metrics": advanced_metrics,
                "risk_metrics": risk_metrics,
                "efficiency_metrics": efficiency_metrics,
                # Insights and recommendations
                "performance_insights": insights,
                "recommendations": recommendations,
                "alerts": alerts,
                # Summary scores
                "overall_score": self._calculate_overall_score(
                    basic_stats, advanced_metrics, risk_metrics
                ),
                "performance_grade": self._assign_performance_grade(
                    basic_stats, advanced_metrics
                ),
            }

            # Store in performance history
            self.performance_history.append(
                {"timestamp": time.time(), "report": report}
            )

            # Keep history manageable
            if len(self.performance_history) > 30:
                self.performance_history = self.performance_history[-15:]

            self.logger.info(
                f"✅ Performance report generated: Grade {report['performance_grade']}, Score {report['overall_score']:.1f}"
            )

            return report

        except Exception as e:
            self.logger.error(f"❌ Error generating performance report: {e}")
            return {
                "error": str(e),
                "client_id": self.client_id,
                "generated_at": datetime.now().isoformat(),
            }

    async def _calculate_advanced_metrics(
        self, basic_stats: Dict, daily_performance: List[Dict]
    ) -> Dict:
        """Calculate advanced performance metrics"""
        try:
            if not daily_performance:
                return self._empty_advanced_metrics()

            # Extract daily PnL values
            daily_pnls = [day.get("pnl", 0) for day in daily_performance]

            # Profit/Loss analysis
            positive_days = [pnl for pnl in daily_pnls if pnl > 0]
            negative_days = [pnl for pnl in daily_pnls if pnl < 0]

            # Calculate Sharpe-like ratio (simplified)
            avg_daily_return = np.mean(daily_pnls) if daily_pnls else 0
            daily_volatility = np.std(daily_pnls) if len(daily_pnls) > 1 else 0
            sharpe_ratio = (
                (avg_daily_return / daily_volatility) if daily_volatility > 0 else 0
            )

            # Maximum drawdown calculation
            cumulative_pnl = np.cumsum(daily_pnls)
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = cumulative_pnl - running_max
            max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0

            # Profit factor
            gross_profit = sum(positive_days) if positive_days else 0
            gross_loss = abs(sum(negative_days)) if negative_days else 0
            profit_factor = (
                gross_profit / gross_loss
                if gross_loss > 0
                else float("inf")
                if gross_profit > 0
                else 0
            )

            # Consistency metrics
            win_days = len(positive_days)
            total_days = len(daily_pnls)
            daily_win_rate = (win_days / total_days * 100) if total_days > 0 else 0

            # Recovery time analysis
            recovery_periods = self._calculate_recovery_periods(daily_pnls)

            return {
                "total_trading_days": total_days,
                "profitable_days": win_days,
                "losing_days": len(negative_days),
                "daily_win_rate": round(daily_win_rate, 2),
                "average_daily_return": round(avg_daily_return, 2),
                "daily_volatility": round(daily_volatility, 2),
                "sharpe_ratio": round(sharpe_ratio, 3),
                "max_drawdown": round(max_drawdown, 2),
                "max_drawdown_percent": round(
                    (max_drawdown / max(cumulative_pnl)) * 100, 2
                )
                if max(cumulative_pnl) > 0
                else 0,
                "profit_factor": round(profit_factor, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_loss": round(gross_loss, 2),
                "best_day": round(max(daily_pnls), 2) if daily_pnls else 0,
                "worst_day": round(min(daily_pnls), 2) if daily_pnls else 0,
                "average_win": round(np.mean(positive_days), 2) if positive_days else 0,
                "average_loss": round(np.mean(negative_days), 2)
                if negative_days
                else 0,
                "recovery_analysis": recovery_periods,
            }

        except Exception as e:
            self.logger.error(f"❌ Error calculating advanced metrics: {e}")
            return self._empty_advanced_metrics()

    def _empty_advanced_metrics(self) -> Dict:
        """Return empty advanced metrics structure"""
        return {
            "total_trading_days": 0,
            "profitable_days": 0,
            "losing_days": 0,
            "daily_win_rate": 0,
            "average_daily_return": 0,
            "daily_volatility": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "max_drawdown_percent": 0,
            "profit_factor": 0,
            "gross_profit": 0,
            "gross_loss": 0,
            "best_day": 0,
            "worst_day": 0,
            "average_win": 0,
            "average_loss": 0,
            "recovery_analysis": {"average_recovery_days": 0, "longest_recovery": 0},
        }

    def _calculate_recovery_periods(self, daily_pnls: List[float]) -> Dict:
        """Calculate how long it takes to recover from losses"""
        if not daily_pnls:
            return {"average_recovery_days": 0, "longest_recovery": 0}

        cumulative = np.cumsum(daily_pnls)
        recovery_periods = []
        in_drawdown = False
        drawdown_start = 0

        for i, cum_pnl in enumerate(cumulative):
            if i == 0:
                peak = cum_pnl
                continue

            if cum_pnl > peak:
                if in_drawdown:
                    # Recovery completed
                    recovery_periods.append(i - drawdown_start)
                    in_drawdown = False
                peak = cum_pnl
            elif cum_pnl < peak and not in_drawdown:
                # Start of drawdown
                in_drawdown = True
                drawdown_start = i

        if recovery_periods:
            return {
                "average_recovery_days": round(np.mean(recovery_periods), 1),
                "longest_recovery": max(recovery_periods),
                "total_recovery_events": len(recovery_periods),
            }
        else:
            return {
                "average_recovery_days": 0,
                "longest_recovery": 0,
                "total_recovery_events": 0,
            }

    async def _calculate_risk_metrics(self, daily_performance: List[Dict]) -> Dict:
        """Calculate comprehensive risk metrics"""
        # Implementation for risk calculations
        # VaR, Expected Shortfall, Beta, etc.
        return {
            "value_at_risk_95": 0,
            "expected_shortfall": 0,
            "volatility_score": "moderate",
            "risk_adjusted_return": 0,
        }

    async def _calculate_efficiency_metrics(
        self, basic_stats: Dict, symbol_performance: Dict
    ) -> Dict:
        """Calculate trading efficiency metrics"""
        # Implementation for efficiency calculations
        return {
            "trades_per_day": 0,
            "profit_per_trade": 0,
            "symbol_efficiency": symbol_performance,
        }

    async def _generate_performance_insights(
        self, basic_stats: Dict, advanced_metrics: Dict, risk_metrics: Dict
    ) -> List[str]:
        """Generate actionable performance insights"""
        insights = []

        # Profitability insights
        total_profit = basic_stats.get("total_profit", 0)
        if total_profit > 100:
            insights.append(
                f"💰 Strong profitability: ${total_profit:.2f} total profit demonstrates effective grid trading"
            )
        elif total_profit > 0:
            insights.append(
                f"📈 Positive performance: ${total_profit:.2f} profit shows strategy is working"
            )
        else:
            insights.append(
                f"⚠️ Performance concern: ${total_profit:.2f} indicates strategy adjustment needed"
            )

        # Win rate insights
        win_rate = basic_stats.get("win_rate", 0)
        if win_rate > 70:
            insights.append(
                f"🎯 Excellent win rate: {win_rate:.1f}% shows consistent profitable trades"
            )
        elif win_rate > 50:
            insights.append(
                f"✅ Good win rate: {win_rate:.1f}% indicates solid trade selection"
            )
        else:
            insights.append(
                f"📊 Win rate opportunity: {win_rate:.1f}% suggests reviewing grid spacing"
            )

        # Risk insights
        max_drawdown = advanced_metrics.get("max_drawdown", 0)
        if abs(max_drawdown) > 50:
            insights.append(
                f"🚨 Risk alert: ${abs(max_drawdown):.2f} maximum drawdown requires attention"
            )

        return insights

    async def _generate_recommendations(
        self, basic_stats: Dict, advanced_metrics: Dict, risk_metrics: Dict
    ) -> List[str]:
        """Generate specific improvement recommendations"""
        recommendations = []

        # Add specific recommendations based on performance
        if basic_stats.get("win_rate", 0) < 50:
            recommendations.append(
                "📊 Consider widening grid spacing to increase win rate"
            )

        if advanced_metrics.get("profit_factor", 0) < 1.5:
            recommendations.append(
                "💡 Review order sizing strategy to improve profit factor"
            )

        return recommendations

    async def _check_performance_alerts(
        self, basic_stats: Dict, advanced_metrics: Dict
    ) -> List[Dict]:
        """Check for performance alerts and warnings"""
        alerts = []

        # Loss threshold alert
        total_profit = basic_stats.get("total_profit", 0)
        if total_profit < self.alert_thresholds["loss_threshold"]:
            alerts.append(
                {
                    "level": "critical",
                    "type": "loss_threshold",
                    "message": f"Total loss ${abs(total_profit):.2f} exceeds threshold ${abs(self.alert_thresholds['loss_threshold']):.2f}",
                    "action_required": True,
                }
            )

        # Win rate alert
        win_rate = basic_stats.get("win_rate", 0)
        if win_rate < self.alert_thresholds["win_rate_threshold"]:
            alerts.append(
                {
                    "level": "warning",
                    "type": "low_win_rate",
                    "message": f"Win rate {win_rate:.1f}% below threshold {self.alert_thresholds['win_rate_threshold']:.1f}%",
                    "action_required": False,
                }
            )

        return alerts

    def _calculate_overall_score(
        self, basic_stats: Dict, advanced_metrics: Dict, risk_metrics: Dict
    ) -> float:
        """Calculate overall performance score (0-100)"""
        # Weighted scoring system
        profit_score = min(100, max(0, (basic_stats.get("total_profit", 0) + 100) / 2))
        win_rate_score = basic_stats.get("win_rate", 0)
        consistency_score = advanced_metrics.get("daily_win_rate", 0)

        # Weighted average
        overall_score = (
            (profit_score * 0.4) + (win_rate_score * 0.3) + (consistency_score * 0.3)
        )
        return round(overall_score, 1)

    def _assign_performance_grade(
        self, basic_stats: Dict, advanced_metrics: Dict
    ) -> str:
        """Assign letter grade based on performance"""
        score = self._calculate_overall_score(basic_stats, advanced_metrics, {})

        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C+"
        elif score >= 40:
            return "C"
        else:
            return "D"
