import logging
from typing import Dict, Tuple


class SmartDecisionEngine:
    """Smart hierarchical decision engine - integrated into GridManager"""

    def __init__(self, client_id: int, fifo_service):
        self.client_id = client_id
        self.fifo_service = fifo_service
        self.logger = logging.getLogger(__name__)

        # Base configuration per symbol
        self.symbol_targets = {
            "ADAUSDT": {"base_size": 25.0, "base_spacing": 0.04, "daily_target": 2.0},
            "ETHUSDT": {"base_size": 50.0, "base_spacing": 0.035, "daily_target": 5.0},
            "SOLUSDT": {"base_size": 40.0, "base_spacing": 0.045, "daily_target": 4.0},
        }

        self.logger.info("🧠 Smart Decision Engine activated for passive income")

    async def get_smart_order_size(
        self, symbol: str, total_capital: float, binance_client
    ) -> float:
        """Master order sizing with hierarchical intelligence"""
        try:
            config = self.symbol_targets.get(symbol, {"base_size": 30.0})
            base_size = config["base_size"]

            # LEVEL 1: Risk Protection (40% weight)
            risk_factor = self._calculate_risk_factor()

            # LEVEL 2: Performance Growth (30% weight)
            performance_factor = self._calculate_performance_factor()

            # LEVEL 3: Market Adaptation (20% weight)
            market_factor = await self._calculate_market_factor(symbol, binance_client)

            # LEVEL 4: Consistency Bonus (10% weight)
            consistency_factor = 1.0  # Start neutral, grows with success

            # Hierarchical combination
            smart_factor = (
                risk_factor * 0.4
                + performance_factor * 0.3
                + market_factor * 0.2
                + consistency_factor * 0.1
            )

            smart_size = base_size * smart_factor

            # Safety bounds
            min_size = 12.0
            max_size = total_capital * 0.15
            final_size = max(min_size, min(smart_size, max_size))

            # Smart logging
            self.logger.info(f"🧠 Smart sizing for {symbol}:")
            self.logger.info(f"   💰 ${base_size} → ${final_size:.2f}")
            self.logger.info(
                f"   🛡️ Risk: {risk_factor:.2f}x, 📈 Performance: {performance_factor:.2f}x"
            )
            self.logger.info(
                f"   🌊 Market: {market_factor:.2f}x, Combined: {smart_factor:.2f}x"
            )

            return final_size

        except Exception as e:
            self.logger.error(f"❌ Smart sizing error: {e}")
            return config["base_size"]

    def _calculate_risk_factor(self) -> float:
        """Level 1: Risk protection factor"""
        try:
            performance = self._get_performance_metrics()
            recent_24h = performance.get("recent_24h_profit", 0.0)
            total_profit = performance.get("total_profit", 0.0)
            win_rate = performance.get("win_rate", 50.0)

            risk_factor = 1.0

            # Recent losses reduce risk appetite
            if recent_24h < -20.0:
                risk_factor *= 0.7
                self.logger.info(f"   🛡️ Risk protection: Recent loss ${recent_24h:.2f}")

            # Poor win rate increases caution
            if win_rate < 40.0:
                risk_factor *= 0.8

            # Good performance allows more risk
            if total_profit > 100.0 and win_rate > 60.0:
                risk_factor *= 1.1

            return max(0.5, min(1.5, risk_factor))

        except Exception:
            return 1.0

    def _calculate_performance_factor(self) -> float:
        """Level 2: Performance growth factor"""
        try:
            performance = self._get_performance_metrics()
            total_profit = performance.get("total_profit", 0.0)
            total_trades = performance.get("total_trades", 0)
            win_rate = performance.get("win_rate", 50.0)

            performance_factor = 1.0

            if total_trades >= 20:
                if total_profit > 50.0 and win_rate > 60.0:
                    performance_factor *= 1.15
                    self.logger.info(
                        f"   📈 Performance bonus: ${total_profit:.2f}, {win_rate:.1f}%"
                    )
                elif total_profit < -25.0:
                    performance_factor *= 0.85
            elif total_trades < 10:
                performance_factor *= 0.9  # Conservative start

            return max(0.8, min(1.2, performance_factor))

        except Exception:
            return 1.0

    async def _calculate_market_factor(self, symbol: str, binance_client) -> float:
        """Level 3: Market adaptation factor"""
        try:
            ticker = binance_client.get_ticker(symbol=symbol)
            high_24h = float(ticker["highPrice"])
            low_24h = float(ticker["lowPrice"])
            current_price = float(ticker["lastPrice"])

            volatility = (high_24h - low_24h) / current_price
            market_factor = 1.0

            if volatility > 0.6:  # High volatility
                market_factor *= 0.8
                self.logger.info(f"   🌊 Market: High volatility {volatility:.2f}")
            elif volatility < 0.25:  # Low volatility
                market_factor *= 1.05

            return max(0.7, min(1.1, market_factor))

        except Exception:
            return 1.0

    def should_smart_reset(
        self, symbol: str, current_price: float, center_price: float, grid_config
    ) -> Tuple[bool, str]:
        """Smart reset decision with multiple triggers"""
        try:
            # TRIGGER 1: Adaptive price threshold
            price_deviation = abs(current_price - center_price) / center_price
            adaptive_threshold = self._get_adaptive_threshold(symbol)

            if price_deviation >= adaptive_threshold:
                return (
                    True,
                    f"Price deviation {price_deviation:.1%} exceeds adaptive threshold {adaptive_threshold:.1%}",
                )

            # TRIGGER 2: Fill ratio (fixes your business logic issue)
            if hasattr(grid_config, "buy_levels") and hasattr(
                grid_config, "sell_levels"
            ):
                filled_buys = len(
                    [l for l in grid_config.buy_levels if l.get("filled", False)]
                )
                total_buys = len(grid_config.buy_levels)
                buy_fill_ratio = filled_buys / total_buys if total_buys > 0 else 0

                filled_sells = len(
                    [l for l in grid_config.sell_levels if l.get("filled", False)]
                )
                total_sells = len(grid_config.sell_levels)
                sell_fill_ratio = filled_sells / total_sells if total_sells > 0 else 0

                # Reset when grid becomes one-sided (BUSINESS LOGIC FIX)
                if buy_fill_ratio >= 0.8:
                    return (
                        True,
                        f"Grid one-sided: {buy_fill_ratio:.1%} buy orders filled",
                    )

                if buy_fill_ratio >= 0.6 and sell_fill_ratio <= 0.2:
                    return (
                        True,
                        f"Grid becoming buy-heavy: {buy_fill_ratio:.1%} vs {sell_fill_ratio:.1%}",
                    )

            return False, f"Reset conditions normal (deviation: {price_deviation:.1%})"

        except Exception as e:
            return False, f"Reset check error: {e}"

    def _get_adaptive_threshold(self, symbol: str) -> float:
        """Adaptive threshold based on conditions"""
        try:
            base_threshold = 0.08  # 8% base
            performance = self._get_performance_metrics()

            # Good performance = allow wider range before reset
            if performance.get("win_rate", 50) > 65:
                return base_threshold * 1.2  # 9.6%
            elif performance.get("total_profit", 0) < -50:
                return base_threshold * 0.8  # 6.4%

            return base_threshold

        except Exception:
            return 0.08

    def _get_performance_metrics(self) -> Dict:
        """Get performance from FIFO service"""
        try:
            if hasattr(self.fifo_service, "calculate_fifo_profit_with_cost_basis"):
                return self.fifo_service.calculate_fifo_profit_with_cost_basis(
                    self.client_id
                )
            return {
                "total_profit": 0.0,
                "total_trades": 0,
                "win_rate": 50.0,
                "recent_24h_profit": 0.0,
            }
        except:
            return {
                "total_profit": 0.0,
                "total_trades": 0,
                "win_rate": 50.0,
                "recent_24h_profit": 0.0,
            }
