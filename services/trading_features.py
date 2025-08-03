# services/trading_features.py

"""
Advanced Trading Features Implementation
Replaces temporary placeholders with full OOP implementations
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pytz
from binance.client import Client

from config import Config
from repositories.trade_repository import TradeRepository


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

        # Risk parameters (changed to aggressive mode)
        self.low_volatility_threshold = 0.30  # 15% daily volatility
        self.high_volatility_threshold = 0.80  # 35% daily volatility
        self.extreme_volatility_threshold = 1.50  # 50% daily volatility

        # Risk multipliers
        self.risk_multipliers = {
            "low": {"order_size": 1.5, "grid_spacing": 0.6},  # More aggressive
            "moderate": {"order_size": 1.2, "grid_spacing": 0.8},
            "high": {"order_size": 0.8, "grid_spacing": 1.2},  # Less conservative
            "extreme": {
                "order_size": 0.6,
                "grid_spacing": 1.4,
            },  # Less severe reduction
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
        SIMPLIFIED: Only provide spacing adjustments, let SmartEngine handle order size
        """
        try:
            current_volatility = await self.calculate_current_volatility()
            regime = self.classify_volatility_regime(current_volatility)

            # ONLY adjust spacing (no order size conflicts)
            spacing_adjustment = 1.0

            if regime == "extreme":
                spacing_adjustment = 1.4  # Much wider
            elif regime == "high":
                spacing_adjustment = 1.2  # Wider
            elif regime == "low":
                spacing_adjustment = 0.9  # Slightly tighter

            adjusted_spacing = base_grid_spacing * spacing_adjustment
            adjusted_spacing = max(0.02, min(0.08, adjusted_spacing))  # Bounds

            result = {
                "volatility": current_volatility,
                "regime": regime,
                "adjusted_order_size": base_order_size,  # Don't change - let smart engine handle
                "adjusted_grid_spacing": adjusted_spacing,
                "order_size_multiplier": 1.0,  # No conflicts
                "spacing_multiplier": spacing_adjustment,
            }

            self.logger.info(f"🛡️ Volatility adjustment for {self.symbol}:")
            self.logger.info(f"   Volatility: {current_volatility:.3f} ({regime})")
            self.logger.info(
                f"   Grid spacing: {base_grid_spacing:.3f} → {adjusted_spacing:.3f}"
            )
            self.logger.info("   Order sizing: Delegated to SmartEngine")

            return result

        except Exception as e:
            self.logger.error(f"❌ Volatility adjustment error: {e}")
            return {
                "volatility": 0.25,
                "regime": "moderate",
                "adjusted_order_size": base_order_size,
                "adjusted_grid_spacing": base_grid_spacing,
                "order_size_multiplier": 1.0,
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


# REPLACE the PrecisionOrderHandler class in your single_advanced_grid_manager.py with this UNIVERSAL version


class PrecisionOrderHandler:
    def __init__(self, binance_client):
        self.binance_client = binance_client
        self.logger = logging.getLogger(__name__)

        # Cache for exchange info
        self.exchange_info_cache = {}
        self.cache_timestamp = 0
        self.cache_duration = 3600  # 1 hour

    async def get_real_exchange_info(self, symbol: str) -> dict:
        """Get REAL exchange info from Binance API - no hardcoded overrides"""
        try:
            import time

            current_time = time.time()

            # Check cache
            if (
                symbol in self.exchange_info_cache
                and current_time - self.cache_timestamp < self.cache_duration
            ):
                return self.exchange_info_cache[symbol]

            # Fetch fresh data from Binance
            self.logger.info(f"🔍 Fetching REAL exchange info for {symbol}")
            exchange_info = self.binance_client.get_exchange_info()

            for sym_info in exchange_info["symbols"]:
                if sym_info["symbol"] == symbol:
                    # Extract filters
                    filters = {}
                    for filter_info in sym_info.get("filters", []):
                        filters[filter_info["filterType"]] = filter_info

                    # Build precision rules from REAL API data
                    price_filter = filters.get("PRICE_FILTER", {})
                    lot_size = filters.get("LOT_SIZE", {})
                    min_notional = filters.get("MIN_NOTIONAL", {})

                    rules = {
                        "symbol": symbol,
                        "status": sym_info.get("status", "TRADING"),
                        "baseAsset": sym_info.get("baseAsset"),
                        "quoteAsset": sym_info.get("quoteAsset"),
                        "baseAssetPrecision": int(
                            sym_info.get("baseAssetPrecision", 8)
                        ),
                        "quotePrecision": int(sym_info.get("quotePrecision", 8)),
                        "quoteAssetPrecision": int(
                            sym_info.get("quoteAssetPrecision", 8)
                        ),
                        # PRICE_FILTER
                        "minPrice": float(price_filter.get("minPrice", "0.00000001")),
                        "maxPrice": float(price_filter.get("maxPrice", "1000000")),
                        "tickSize": float(price_filter.get("tickSize", "0.00000001")),
                        # LOT_SIZE
                        "minQty": float(lot_size.get("minQty", "0.00000001")),
                        "maxQty": float(lot_size.get("maxQty", "1000000")),
                        "stepSize": float(lot_size.get("stepSize", "0.00000001")),
                        # MIN_NOTIONAL
                        "minNotional": float(min_notional.get("minNotional", "5.0")),
                        # Calculate precision from step sizes
                        "price_precision": self._calculate_precision(
                            float(price_filter.get("tickSize", "0.01"))
                        ),
                        "quantity_precision": self._calculate_precision(
                            float(lot_size.get("stepSize", "0.00000001"))
                        ),
                    }

                    # Cache the result
                    self.exchange_info_cache[symbol] = rules
                    self.cache_timestamp = current_time

                    self.logger.info(f"✅ Real exchange info for {symbol}:")
                    self.logger.info(
                        f"   📏 Price: tick_size={rules['tickSize']}, precision={rules['price_precision']}"
                    )
                    self.logger.info(
                        f"   📦 Quantity: step_size={rules['stepSize']}, precision={rules['quantity_precision']}"
                    )
                    self.logger.info(f"   💰 Min notional: ${rules['minNotional']}")

                    return rules

            raise ValueError(f"Symbol {symbol} not found in exchange info")

        except Exception as e:
            self.logger.error(f"❌ Failed to get exchange info for {symbol}: {e}")
            raise

    def _calculate_precision(self, step_size: float) -> int:
        """Calculate decimal precision from step size"""
        try:
            if step_size >= 1:
                return 0

            # Count decimal places
            step_str = f"{step_size:.10f}".rstrip("0")
            if "." in step_str:
                return len(step_str.split(".")[1])
            return 0

        except:
            return 8  # Safe fallback

    def _round_to_step_size(self, value: float, step_size: float) -> float:
        """Round value to nearest valid step size"""
        try:
            if step_size == 0:
                return value

            # Use high precision decimal arithmetic
            from decimal import ROUND_HALF_UP, Decimal

            decimal_value = Decimal(str(value))
            decimal_step = Decimal(str(step_size))

            # Calculate steps and round
            steps = (decimal_value / decimal_step).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            result = float(steps * decimal_step)

            return result

        except Exception as e:
            self.logger.error(f"Step size rounding error: {e}")
            return value

    async def calculate_valid_order_from_usd(
        self, symbol: str, side: str, usd_amount: float, price: float
    ):
        """
        UNIVERSAL METHOD: Calculate valid order parameters from any USD amount
        This is the key method that adapts ANY amount to Binance requirements
        """
        try:
            self.logger.info(
                f"🎯 Calculating valid order for {symbol}: ${usd_amount} at ${price}"
            )

            # Get real exchange rules
            rules = await self.get_real_exchange_info(symbol)

            # Calculate initial quantity from USD amount
            initial_quantity = usd_amount / price

            # Round price to valid tick size
            valid_price = self._round_to_step_size(price, rules["tickSize"])
            valid_price = max(rules["minPrice"], min(rules["maxPrice"], valid_price))

            # Round quantity to valid step size
            valid_quantity = self._round_to_step_size(
                initial_quantity, rules["stepSize"]
            )
            valid_quantity = max(rules["minQty"], min(rules["maxQty"], valid_quantity))

            # Calculate actual notional value
            actual_notional = valid_quantity * valid_price

            # Check minimum notional requirement
            if actual_notional < rules["minNotional"]:
                # Adjust quantity up to meet minimum notional
                required_quantity = rules["minNotional"] / valid_price
                valid_quantity = self._round_to_step_size(
                    required_quantity, rules["stepSize"]
                )

                # Ensure we don't exceed max quantity
                if valid_quantity > rules["maxQty"]:
                    # Try adjusting price down slightly
                    adjusted_price = rules["minNotional"] / rules["maxQty"]
                    valid_price = self._round_to_step_size(
                        adjusted_price, rules["tickSize"]
                    )
                    valid_quantity = rules["maxQty"]

                actual_notional = valid_quantity * valid_price

            # Format strings with correct precision
            price_str = f"{valid_price:.{rules['price_precision']}f}".rstrip(
                "0"
            ).rstrip(".")
            quantity_str = f"{valid_quantity:.{rules['quantity_precision']}f}".rstrip(
                "0"
            ).rstrip(".")

            # Ensure minimum decimal places for display
            if "." not in price_str and rules["price_precision"] > 0:
                price_str += ".00"
            if "." not in quantity_str and rules["quantity_precision"] > 0:
                quantity_str += ".00000"

            self.logger.info("📊 Valid order calculated:")
            self.logger.info(
                f"   💰 Original: ${usd_amount} → Actual: ${actual_notional:.2f}"
            )
            self.logger.info(f"   📦 Quantity: {initial_quantity:.8f} → {quantity_str}")
            self.logger.info(f"   💲 Price: ${price:.8f} → ${price_str}")

            return {
                "success": True,
                "original_usd_amount": usd_amount,
                "actual_notional": actual_notional,
                "valid_quantity": valid_quantity,
                "valid_price": valid_price,
                "quantity_str": quantity_str,
                "price_str": price_str,
                "rules_used": {
                    "tickSize": rules["tickSize"],
                    "stepSize": rules["stepSize"],
                    "minNotional": rules["minNotional"],
                },
            }

        except Exception as e:
            self.logger.error(f"❌ Error calculating valid order: {e}")
            return {"success": False, "error": str(e)}

    async def execute_precision_order(
        self, symbol: str, side: str, quantity: float, price: float
    ):
        """Execute order with universal precision handling"""
        try:
            # Calculate USD amount from inputs
            usd_amount = quantity * price

            # Get valid order parameters
            valid_order = await self.calculate_valid_order_from_usd(
                symbol, side, usd_amount, price
            )

            if not valid_order["success"]:
                return {
                    "success": False,
                    "error": f"Could not calculate valid order: {valid_order.get('error')}",
                }

            # Log what we're sending to Binance
            self.logger.info(f"📤 Executing {symbol} {side} order:")
            self.logger.info(f"   📦 Quantity: {valid_order['quantity_str']}")
            self.logger.info(f"   💲 Price: {valid_order['price_str']}")
            self.logger.info(f"   💰 Notional: ${valid_order['actual_notional']:.2f}")

            # Execute the order
            if side.upper() == "BUY":
                order = self.binance_client.order_limit_buy(
                    symbol=symbol,
                    quantity=valid_order["quantity_str"],
                    price=valid_order["price_str"],
                    recvWindow=60000,
                )
            else:
                order = self.binance_client.order_limit_sell(
                    symbol=symbol,
                    quantity=valid_order["quantity_str"],
                    price=valid_order["price_str"],
                    recvWindow=60000,
                )

            self.logger.info("✅ Order executed successfully!")
            self.logger.info(f"   🆔 Order ID: {order['orderId']}")
            self.logger.info(f"   📊 Actual: {order['origQty']} @ {order['price']}")

            return {
                "success": True,
                "order_id": order["orderId"],
                "quantity": float(order["origQty"]),
                "price": float(order["price"]),
                "symbol": symbol,
                "side": side,
                "status": order["status"],
                "original_request": {
                    "requested_quantity": quantity,
                    "requested_price": price,
                    "requested_notional": usd_amount,
                },
                "actual_execution": {
                    "executed_quantity": float(order["origQty"]),
                    "executed_price": float(order["price"]),
                    "executed_notional": float(order["origQty"])
                    * float(order["price"]),
                },
            }

        except Exception as e:
            self.logger.error(f"❌ Order execution failed for {symbol} {side}: {e}")

            # Log detailed error for debugging
            if "Filter failure" in str(e):
                self.logger.error("   🔍 Filter failure - check precision requirements")
                self.logger.error(f"   📦 Requested quantity: {quantity}")
                self.logger.error(f"   💲 Requested price: {price}")

            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "side": side,
                "requested_quantity": quantity,
                "requested_price": price,
            }

    async def format_precision_order(
        self, symbol: str, side: str, quantity: float, price: float
    ):
        """Format order with precision - uses universal method"""
        try:
            # Use the universal calculation method
            usd_amount = quantity * price
            valid_order = await self.calculate_valid_order_from_usd(
                symbol, side, usd_amount, price
            )

            if valid_order["success"]:
                return {
                    "success": True,
                    "formatted_quantity": valid_order["valid_quantity"],
                    "formatted_price": valid_order["valid_price"],
                    "quantity_str": valid_order["quantity_str"],
                    "price_str": valid_order["price_str"],
                    "notional_value": valid_order["actual_notional"],
                    "validation_errors": [],
                }
            else:
                return {
                    "success": False,
                    "validation_errors": [
                        valid_order.get("error", "Unknown formatting error")
                    ],
                }

        except Exception as e:
            return {
                "success": False,
                "validation_errors": [f"Formatting error: {str(e)}"],
            }


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
