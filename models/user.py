"""Enhanced User model with dual trial system"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

class SubscriptionStatus(Enum):
    NONE = "none"
    DEMO_TRIAL = "demo_trial"  # NEW: 7 days demo
    REAL_TRIAL = "real_trial"  # NEW: 7 days real trading
    TRIAL = "trial"  # Legacy - for backwards compatibility
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class BotStatus(Enum):
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"
    TRIAL_EXPIRED = "trial_expired"  # NEW: Auto-stopped due to trial expiry

@dataclass
class User:
    """Enhanced User model with dual trial system"""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.NONE
    bot_status: BotStatus = BotStatus.INACTIVE
    
    # Enhanced trial system
    demo_trial_started: Optional[datetime] = None
    demo_trial_expires: Optional[datetime] = None
    real_trial_started: Optional[datetime] = None
    real_trial_expires: Optional[datetime] = None
    
    # Legacy fields (for backwards compatibility)
    trial_started: Optional[datetime] = None
    trial_expires: Optional[datetime] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
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
    
    def start_demo_trial(self) -> bool:
        """Start 7-day demo trial"""
        if self.subscription_status != SubscriptionStatus.NONE:
            return False  # Already has some subscription
        
        now = datetime.now()
        self.subscription_status = SubscriptionStatus.DEMO_TRIAL
        self.demo_trial_started = now
        self.demo_trial_expires = now + timedelta(days=7)
        
        # Set demo API keys
        self.binance_api_key = "demo_api_key_for_testing"
        self.binance_secret_key = "demo_secret_key_for_testing"
        
        return True
    
    def upgrade_to_real_trial(self, real_api_key: str, real_secret_key: str) -> bool:
        """Upgrade from demo trial to real trial with fresh 7 days"""
        if self.subscription_status != SubscriptionStatus.DEMO_TRIAL:
            return False  # Must be in demo trial to upgrade
        
        now = datetime.now()
        self.subscription_status = SubscriptionStatus.REAL_TRIAL
        self.real_trial_started = now
        self.real_trial_expires = now + timedelta(days=7)
        
        # Set real API keys
        self.binance_api_key = real_api_key
        self.binance_secret_key = real_secret_key
        
        return True
    
    def is_demo_trial_active(self) -> bool:
        """Check if demo trial is active"""
        if self.subscription_status != SubscriptionStatus.DEMO_TRIAL:
            return False
        return self.demo_trial_expires and datetime.now() < self.demo_trial_expires
    
    def is_real_trial_active(self) -> bool:
        """Check if real trial is active"""
        if self.subscription_status != SubscriptionStatus.REAL_TRIAL:
            return False
        return self.real_trial_expires and datetime.now() < self.real_trial_expires
    
    def is_subscription_active(self) -> bool:
        """Check if user has any active subscription"""
        if self.subscription_status in [SubscriptionStatus.STARTER, SubscriptionStatus.PRO, SubscriptionStatus.ENTERPRISE]:
            return True
        
        # Legacy trial support
        if self.subscription_status == SubscriptionStatus.TRIAL:
            return self.trial_expires and datetime.now() < self.trial_expires
        
        return self.is_demo_trial_active() or self.is_real_trial_active()
    
    def is_trial_expired(self) -> bool:
        """Check if any trial has expired"""
        now = datetime.now()
        
        if self.subscription_status == SubscriptionStatus.DEMO_TRIAL:
            return self.demo_trial_expires and now >= self.demo_trial_expires
        
        if self.subscription_status == SubscriptionStatus.REAL_TRIAL:
            return self.real_trial_expires and now >= self.real_trial_expires
        
        # Legacy trial support
        if self.subscription_status == SubscriptionStatus.TRIAL:
            return self.trial_expires and now >= self.trial_expires
        
        return False
    
    def get_trial_days_left(self) -> int:
        """Get days left in current trial"""
        now = datetime.now()
        
        if self.subscription_status == SubscriptionStatus.DEMO_TRIAL and self.demo_trial_expires:
            delta = self.demo_trial_expires - now
            return max(0, delta.days)
        
        if self.subscription_status == SubscriptionStatus.REAL_TRIAL and self.real_trial_expires:
            delta = self.real_trial_expires - now
            return max(0, delta.days)
        
        # Legacy trial support
        if self.subscription_status == SubscriptionStatus.TRIAL and self.trial_expires:
            delta = self.trial_expires - now
            return max(0, delta.days)
        
        return 0
    
    def get_trial_status_message(self) -> str:
        """Get user-friendly trial status message"""
        days_left = self.get_trial_days_left()
        
        if self.subscription_status == SubscriptionStatus.DEMO_TRIAL:
            if days_left > 0:
                return f"🎮 Demo Trial - {days_left} days left"
            else:
                return "🎮 Demo Trial Expired"
        
        if self.subscription_status == SubscriptionStatus.REAL_TRIAL:
            if days_left > 0:
                return f"🟢 Real Trial - {days_left} days left"
            else:
                return "🟢 Real Trial Expired"
        
        # Legacy trial support
        if self.subscription_status == SubscriptionStatus.TRIAL:
            if days_left > 0:
                return f"🆓 Trial - {days_left} days left"
            else:
                return "🆓 Trial Expired"
        
        if self.subscription_status in [SubscriptionStatus.STARTER, SubscriptionStatus.PRO, SubscriptionStatus.ENTERPRISE]:
            return f"💎 {self.subscription_status.value.title()}"
        
        return "❌ No Active Subscription"
    
    def can_upgrade_to_real_trial(self) -> bool:
        """Check if user can upgrade from demo to real trial"""
        return (
            self.subscription_status == SubscriptionStatus.DEMO_TRIAL and
            self.is_demo_trial_active()
        )
    
    def can_start_bot(self) -> bool:
        """Check if user can start trading bot"""
        if not self.is_subscription_active():
            return False
        
        # Must have API keys and capital
        if not self.binance_api_key or not self.binance_secret_key or self.total_capital <= 0:
            return False
        
        return True
    
    def needs_trial_stop(self) -> bool:
        """Check if bot should be auto-stopped due to trial expiry"""
        return (
            self.is_trial_expired() and 
            self.bot_status in [BotStatus.ACTIVE, BotStatus.STARTING]
        )
