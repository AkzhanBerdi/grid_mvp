#!/usr/bin/env python3
"""Integration test for dual trial system"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_dual_trial_system():
    """Test the complete dual trial system"""
    
    print("🧪 TESTING DUAL TRIAL SYSTEM")
    print("=" * 40)
    
    try:
        # Test 1: User model
        from models.user import User, SubscriptionStatus, BotStatus
        
        user = User(telegram_id=999999997, username="test_integration", first_name="Test")
        print("✅ User creation")
        
        # Test demo trial
        success = user.start_demo_trial()
        assert success, "Demo trial start should succeed"
        assert user.subscription_status == SubscriptionStatus.DEMO_TRIAL, "Should be in demo trial"
        assert user.is_demo_trial_active(), "Demo trial should be active"
        print("✅ Demo trial functionality")
        
        # Test real trial upgrade
        success = user.upgrade_to_real_trial("test_real_api", "test_real_secret")
        assert success, "Real trial upgrade should succeed"
        assert user.subscription_status == SubscriptionStatus.REAL_TRIAL, "Should be in real trial"
        assert user.is_real_trial_active(), "Real trial should be active"
        assert not user.is_demo_trial_active(), "Demo trial should no longer be active"
        print("✅ Real trial upgrade")
        
        # Test 2: Database integration
        from repositories.user_repository import UserRepository
        
        user_repo = UserRepository()
        
        # Test saving and retrieving user
        saved_user = user_repo.create_user(
            telegram_id=999999996,
            username="test_db",
            first_name="Test DB"
        )
        
        retrieved_user = user_repo.get_user(999999996)
        assert retrieved_user is not None, "User should be retrievable"
        print("✅ Database integration")
        
        # Test 3: Trial expiry logic
        # Create user with expired trial
        expired_user = User(telegram_id=999999995)
        expired_user.subscription_status = SubscriptionStatus.DEMO_TRIAL
        expired_user.demo_trial_started = datetime.now() - timedelta(days=8)
        expired_user.demo_trial_expires = datetime.now() - timedelta(days=1)
        expired_user.bot_status = BotStatus.ACTIVE
        
        assert expired_user.is_trial_expired(), "Trial should be expired"
        assert expired_user.needs_trial_stop(), "Bot should need stopping"
        print("✅ Trial expiry logic")
        
        # Test 4: Conversion tracker integration
        from analytics.conversion_tracker import ConversionTracker
        
        tracker = ConversionTracker()
        tracker.track_event(999999994, "demo_trial_started")
        tracker.track_event(999999994, "upgraded_to_real_trial")
        print("✅ Conversion tracker integration")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Dual trial system is ready for deployment")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dual_trial_system()
    sys.exit(0 if success else 1)
