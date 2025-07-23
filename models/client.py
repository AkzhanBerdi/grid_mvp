# models/client.py - FIXED VERSION
"""Fixed Client model with proper database schema compatibility"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class ClientStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class GridStatus(Enum):
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class Client:
    """FIXED Client model - matches database schema exactly"""

    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    status: ClientStatus = ClientStatus.ACTIVE
    grid_status: GridStatus = GridStatus.INACTIVE
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Trading Configuration
    total_capital: float = 0.0
    risk_level: str = "moderate"
    trading_pairs: List[str] = field(default_factory=lambda: ["ADA", "AVAX"])

    # API Credentials (encrypted in database)
    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None

    # Grid Settings - FIXED: Added order_size parameter
    grid_spacing: float = 0.025  # 2.5%
    grid_levels: int = 8
    order_size: float = 50.0  # USD per order - THIS WAS MISSING!

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def is_active(self) -> bool:
        """Check if client is active"""
        return self.status == ClientStatus.ACTIVE

    def can_start_grid(self) -> bool:
        """Check if client can start grid trading"""
        return self.is_active() and self.binance_api_key and self.binance_secret_key

    def get_order_size_per_pair(self) -> float:
        """Calculate order size per trading pair"""
        if not self.trading_pairs:
            return self.order_size

        # Distribute capital across pairs
        return min(
            self.order_size,
            self.total_capital / (len(self.trading_pairs) * self.grid_levels),
        )
