"""User model with all database fields - FIXED"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class SubscriptionStatus(Enum):
    NONE = "none"
    TRIAL = "trial"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class BotStatus(Enum):
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class User:
    """User model - FIXED to handle all database fields"""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.NONE
    bot_status: BotStatus = BotStatus.INACTIVE
    trial_started: Optional[datetime] = None
    trial_expires: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None  # ADDED - this was missing
    
    # Trading Configuration
    total_capital: float = 0.0
    risk_level: str = "moderate"
    trading_pairs: List[str] = field(default_factory=lambda: ["ADA"])
    
    # API Credentials
    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def is_subscription_active(self) -> bool:
        """Check if user has active subscription"""
        if self.subscription_status == SubscriptionStatus.TRIAL:
            return self.trial_expires and datetime.now() < self.trial_expires
        return self.subscription_status in [
            SubscriptionStatus.STARTER,
            SubscriptionStatus.PRO, 
            SubscriptionStatus.ENTERPRISE
        ]
    
    def can_start_bot(self) -> bool:
        """Check if user can start trading bot"""
        return (
            self.is_subscription_active() and
            self.binance_api_key and
            self.binance_secret_key and
            self.total_capital > 0
        )
