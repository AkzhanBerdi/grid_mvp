# models/bot_config.py
"""Bot configuration model"""

from typing import Dict, List

from dataclasses import asdict, dataclass

from config import Config


@dataclass
class BotConfig:
    """Trading bot configuration"""

    user_id: int
    trading_pairs: List[str]
    risk_level: str
    total_capital: float
    api_key: str
    secret_key: str

    def get_pair_config(self, pair: str) -> Dict:
        """Get configuration for specific trading pair"""
        base_config = Config.DEFAULT_TRADING_PAIRS.get(pair, {})
        risk_config = Config.RISK_LEVELS.get(
            self.risk_level, Config.RISK_LEVELS["moderate"]
        )

        # Calculate order size per pair
        order_size = self.total_capital / (
            len(self.trading_pairs) * risk_config["grid_levels"]
        )

        return {
            **base_config,
            **risk_config,
            "order_size": max(order_size, base_config.get("min_order_size", 10.0)),
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
