# services/market_analysis.py
"""Fixed Market Analysis Service with Better Error Handling"""

import logging
import time
from datetime import datetime
from typing import Dict, Optional

import numpy as np
from binance.client import Client


class MarketCondition:
    """Market condition classification"""

    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"


class MarketAnalysisService:
    """Fixed market analysis service with robust error handling"""

    def __init__(self, binance_client: Client):
        self.binance_client = binance_client
        self.logger = logging.getLogger(__name__)

        # Cache for market data
        self.price_cache = {}
        self.analysis_cache = {}
        self.cache_timeout = 300  # 5 minutes

        # Fear & Greed Index (if available)
        self.fear_greed_cache = None
        self.fear_greed_timestamp = 0

        # Market thresholds
        self.BULLISH_THRESHOLD = 0.7
        self.BEARISH_THRESHOLD = 0.3

    async def get_market_condition(self, symbol: str) -> Dict:
        """Get market condition with robust fallback handling"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{int(time.time() // self.cache_timeout)}"
            if cache_key in self.analysis_cache:
                return self.analysis_cache[cache_key]

            self.logger.info(f"🔍 Analyzing market condition for {symbol}")

            # Get basic price data (most reliable)
            price_data = await self._get_price_data_safe(symbol)

            # Get technical indicators with fallbacks
            rsi = await self._calculate_rsi_safe(symbol)
            volatility = await self._calculate_volatility_safe(symbol)
            volume_profile = await self._analyze_volume_safe(symbol)

            # Skip Fear & Greed for now to avoid external API issues
            fear_greed = None

            # Combine all indicators
            market_score = self._calculate_market_score_safe(
                price_data, rsi, volatility, volume_profile, fear_greed
            )

            # Determine condition
            if market_score >= self.BULLISH_THRESHOLD:
                condition = MarketCondition.BULLISH
            elif market_score <= self.BEARISH_THRESHOLD:
                condition = MarketCondition.BEARISH
            else:
                condition = MarketCondition.NEUTRAL

            result = {
                "symbol": symbol,
                "condition": condition,
                "score": market_score,
                "confidence": self._calculate_confidence(market_score),
                "indicators": {
                    "rsi": rsi,
                    "volatility": volatility,
                    "volume_ratio": volume_profile.get("ratio", 1.0),
                    "price_trend": price_data.get("trend", 0.0),
                    "fear_greed": fear_greed,
                },
                "timestamp": datetime.now().isoformat(),
            }

            # Cache the result
            self.analysis_cache[cache_key] = result

            self.logger.info(
                f"📊 Market analysis for {symbol}: {condition} (score: {market_score:.2f})"
            )
            return result

        except Exception as e:
            self.logger.error(f"❌ Market analysis failed for {symbol}: {e}")
            # Return safe neutral condition
            return self._get_fallback_condition(symbol)

    def _get_fallback_condition(self, symbol: str) -> Dict:
        """Return safe fallback market condition"""
        return {
            "symbol": symbol,
            "condition": MarketCondition.NEUTRAL,
            "score": 0.5,
            "confidence": 0.0,
            "indicators": {
                "rsi": 50.0,
                "volatility": 0.25,
                "volume_ratio": 1.0,
                "price_trend": 0.0,
                "fear_greed": None,
            },
            "timestamp": datetime.now().isoformat(),
            "fallback": True,
            "error": "Market analysis unavailable, using neutral condition",
        }

    async def _get_price_data_safe(self, symbol: str) -> Dict:
        """Get price data with error handling"""
        try:
            # Get 24h price data
            ticker = self.binance_client.get_ticker(symbol=symbol)
            current_price = float(ticker["lastPrice"])
            price_change_24h = float(ticker["priceChangePercent"])

            # Try to get historical data for trend analysis
            try:
                klines = self.binance_client.get_historical_klines(
                    symbol, Client.KLINE_INTERVAL_1HOUR, "24 hours ago UTC"
                )

                if klines and len(klines) >= 12:
                    prices = [float(kline[4]) for kline in klines]  # Close prices

                    # Calculate trend
                    recent_avg = np.mean(prices[-12:])  # Last 12 hours
                    older_avg = np.mean(prices[-24:-12])  # Previous 12 hours
                    trend = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
                else:
                    trend = price_change_24h / 100

            except Exception as e:
                self.logger.warning(f"Historical data unavailable for {symbol}: {e}")
                trend = price_change_24h / 100

            return {
                "current_price": current_price,
                "price_change_24h": price_change_24h,
                "trend": trend,
                "valid": True,
            }

        except Exception as e:
            self.logger.error(f"❌ Price data error for {symbol}: {e}")
            return {
                "current_price": 0,
                "price_change_24h": 0,
                "trend": 0,
                "valid": False,
            }

    async def _calculate_rsi_safe(self, symbol: str, period: int = 14) -> float:
        """Calculate RSI with error handling"""
        try:
            # Get historical data for RSI calculation
            klines = self.binance_client.get_historical_klines(
                symbol, Client.KLINE_INTERVAL_1HOUR, f"{period * 2} hours ago UTC"
            )

            if not klines or len(klines) < period:
                self.logger.warning(
                    f"Insufficient data for RSI calculation: {len(klines) if klines else 0} klines"
                )
                return 50.0  # Neutral RSI

            closes = [float(kline[4]) for kline in klines]

            if len(closes) < 2:
                return 50.0

            # Calculate price changes
            deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

            # Separate gains and losses
            gains = [delta if delta > 0 else 0 for delta in deltas]
            losses = [-delta if delta < 0 else 0 for delta in deltas]

            if len(gains) < period or len(losses) < period:
                return 50.0

            # Calculate average gains and losses
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])

            # Calculate RSI
            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # Validate RSI range
            rsi = max(0, min(100, rsi))

            return float(rsi)

        except Exception as e:
            self.logger.warning(f"❌ RSI calculation error for {symbol}: {e}")
            return 50.0  # Neutral RSI on error

    async def _calculate_volatility_safe(self, symbol: str) -> float:
        """Calculate volatility with error handling"""
        try:
            # Get 24h klines
            klines = self.binance_client.get_historical_klines(
                symbol, Client.KLINE_INTERVAL_1HOUR, "24 hours ago UTC"
            )

            if not klines or len(klines) < 2:
                self.logger.warning(
                    f"Insufficient data for volatility calculation: {len(klines) if klines else 0} klines"
                )
                return 0.25  # Default moderate volatility

            # Calculate hourly returns
            closes = [float(kline[4]) for kline in klines]

            if len(closes) < 2:
                return 0.25

            returns = []
            for i in range(1, len(closes)):
                if closes[i - 1] > 0:
                    ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                    returns.append(ret)

            if len(returns) == 0:
                return 0.25

            # Calculate standard deviation (volatility)
            volatility = np.std(returns) * np.sqrt(24)  # Annualized

            # Cap volatility at reasonable bounds
            volatility = max(0.0, min(2.0, volatility))

            return float(volatility)

        except Exception as e:
            self.logger.warning(f"❌ Volatility calculation error for {symbol}: {e}")
            return 0.25  # Default moderate volatility

    async def _analyze_volume_safe(self, symbol: str) -> Dict:
        """Analyze volume with error handling"""
        try:
            # Get 24h volume data
            ticker = self.binance_client.get_ticker(symbol=symbol)
            current_volume = float(ticker["volume"])

            # Try to get historical volume for comparison
            try:
                klines = self.binance_client.get_historical_klines(
                    symbol, Client.KLINE_INTERVAL_1HOUR, "48 hours ago UTC"
                )

                if klines and len(klines) >= 24:
                    # Calculate volume ratio (current 24h vs previous 24h)
                    recent_volumes = [float(kline[5]) for kline in klines[-24:]]
                    older_volumes = [float(kline[5]) for kline in klines[-48:-24]]

                    recent_avg = (
                        np.mean(recent_volumes) if recent_volumes else current_volume
                    )
                    older_avg = (
                        np.mean(older_volumes) if older_volumes else current_volume
                    )

                    volume_ratio = recent_avg / older_avg if older_avg > 0 else 1.0
                else:
                    volume_ratio = 1.0  # Default neutral ratio

            except Exception as e:
                self.logger.warning(
                    f"Historical volume data unavailable for {symbol}: {e}"
                )
                volume_ratio = 1.0

            # Determine volume trend
            if volume_ratio > 1.5:
                trend = "increasing"
            elif volume_ratio < 0.7:
                trend = "decreasing"
            else:
                trend = "stable"

            # Cap volume ratio at reasonable bounds
            volume_ratio = max(0.1, min(5.0, volume_ratio))

            return {
                "current_volume": current_volume,
                "ratio": volume_ratio,
                "trend": trend,
            }

        except Exception as e:
            self.logger.warning(f"❌ Volume analysis error for {symbol}: {e}")
            return {"current_volume": 0, "ratio": 1.0, "trend": "stable"}

    def _calculate_market_score_safe(
        self,
        price_data: Dict,
        rsi: float,
        volatility: float,
        volume_profile: Dict,
        fear_greed: Optional[int],
    ) -> float:
        """Calculate market score with safe fallbacks"""
        try:
            scores = []

            # Price trend score (0-1)
            trend = price_data.get("trend", 0)
            if trend > 0.05:  # Strong bullish
                trend_score = 0.8
            elif trend > 0.02:  # Mild bullish
                trend_score = 0.6
            elif trend < -0.05:  # Strong bearish
                trend_score = 0.2
            elif trend < -0.02:  # Mild bearish
                trend_score = 0.4
            else:  # Neutral
                trend_score = 0.5

            scores.append(("trend", trend_score, 0.3))

            # RSI score (0-1)
            rsi = max(0, min(100, rsi))  # Ensure valid range
            if rsi > 70:  # Overbought
                rsi_score = 0.2
            elif rsi > 60:  # Bullish
                rsi_score = 0.7
            elif rsi < 30:  # Oversold
                rsi_score = 0.8
            elif rsi < 40:  # Bearish
                rsi_score = 0.3
            else:  # Neutral
                rsi_score = 0.5

            scores.append(("rsi", rsi_score, 0.25))

            # Volume score (0-1)
            volume_ratio = volume_profile.get("ratio", 1.0)
            volume_ratio = max(0.1, min(5.0, volume_ratio))  # Cap at reasonable bounds

            if volume_ratio > 1.5:  # High volume
                volume_score = 0.7
            elif volume_ratio > 1.2:  # Moderate volume
                volume_score = 0.6
            elif volume_ratio < 0.8:  # Low volume
                volume_score = 0.4
            else:  # Normal volume
                volume_score = 0.5

            scores.append(("volume", volume_score, 0.2))

            # Volatility score (0-1)
            volatility = max(0.0, min(2.0, volatility))  # Cap volatility

            if volatility > 0.5:  # High volatility
                volatility_score = 0.3  # Risky
            elif volatility > 0.3:  # Moderate volatility
                volatility_score = 0.6
            elif volatility < 0.1:  # Low volatility
                volatility_score = 0.4
            else:  # Normal volatility
                volatility_score = 0.5

            scores.append(("volatility", volatility_score, 0.15))

            # Fear & Greed score (0-1) - if available
            if fear_greed is not None:
                fear_greed = max(0, min(100, fear_greed))  # Ensure valid range

                if fear_greed > 75:  # Extreme greed
                    fg_score = 0.2
                elif fear_greed > 55:  # Greed
                    fg_score = 0.6
                elif fear_greed < 25:  # Extreme fear
                    fg_score = 0.8
                elif fear_greed < 45:  # Fear
                    fg_score = 0.7
                else:  # Neutral
                    fg_score = 0.5

                scores.append(("fear_greed", fg_score, 0.1))

            # Calculate weighted average
            if scores:
                total_weight = sum(weight for _, _, weight in scores)
                weighted_score = (
                    sum(score * weight for _, score, weight in scores) / total_weight
                )
            else:
                weighted_score = 0.5  # Default neutral

            # Ensure score is in valid range
            final_score = max(0.0, min(1.0, weighted_score))

            return final_score

        except Exception as e:
            self.logger.error(f"❌ Market score calculation error: {e}")
            return 0.5  # Default neutral score

    def _calculate_confidence(self, score: float) -> float:
        """Calculate confidence level based on deviation from neutral"""
        try:
            score = max(0.0, min(1.0, score))  # Ensure valid range
            deviation = abs(score - 0.5)
            confidence = deviation * 2  # Scale 0-1
            return min(1.0, confidence)
        except:
            return 0.0

    def get_recommended_grid_config(
        self, market_condition: Dict, base_capital: float
    ) -> Dict:
        """Get recommended grid configuration with safe defaults"""
        try:
            condition = market_condition.get("condition", MarketCondition.NEUTRAL)
            score = market_condition.get("score", 0.5)
            confidence = market_condition.get("confidence", 0.0)

            # Base configuration with safe defaults
            config = {
                "base_grid_levels": 6,  # Reduced for better NOTIONAL compliance
                "base_grid_spacing": 0.025,
                "base_order_size": max(
                    15.0, base_capital / 12
                ),  # Ensure minimum $15 per order
                "enhanced_multiplier": 1.0,
                "risk_level": "moderate",
            }

            # Adjust based on market condition
            if condition == MarketCondition.BULLISH and confidence > 0.6:
                # Bullish: Tighter grids, larger orders
                config.update(
                    {
                        "enhanced_multiplier": 1.5 + (score - 0.7) * 1.5,  # 1.5x-2x
                        "base_grid_spacing": 0.02,  # Tighter spacing
                        "base_grid_levels": 8,  # More levels
                        "risk_level": "aggressive",
                    }
                )

            elif condition == MarketCondition.BEARISH and confidence > 0.6:
                # Bearish: Wider grids, strategic positioning
                config.update(
                    {
                        "enhanced_multiplier": 1.3 + (0.3 - score) * 1.0,  # 1.3x-1.6x
                        "base_grid_spacing": 0.03,  # Wider spacing
                        "base_grid_levels": 4,  # Fewer levels
                        "risk_level": "conservative",
                    }
                )

            # Ensure minimum order sizes
            enhanced_order_size = (
                config["base_order_size"] * config["enhanced_multiplier"]
            )

            # Check if total capital can support the configuration
            total_base_orders = config["base_grid_levels"] * 2
            total_enhanced_orders = config["base_grid_levels"] * 2

            total_base_capital = config["base_order_size"] * total_base_orders
            total_enhanced_capital = enhanced_order_size * total_enhanced_orders

            # If total exceeds available capital, scale down
            if total_base_capital > base_capital:
                config["base_order_size"] = base_capital / total_base_orders
                config["enhanced_multiplier"] = 1.0  # Reset multiplier

            config["enhanced_order_size"] = (
                config["base_order_size"] * config["enhanced_multiplier"]
            )

            return config

        except Exception as e:
            self.logger.error(f"❌ Grid config recommendation error: {e}")
            # Return safe fallback configuration
            return {
                "base_grid_levels": 6,
                "base_grid_spacing": 0.025,
                "base_order_size": max(15.0, base_capital / 12),
                "enhanced_multiplier": 1.0,
                "enhanced_order_size": max(15.0, base_capital / 12),
                "risk_level": "moderate",
            }
