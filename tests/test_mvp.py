# tests/test_mvp.py
"""Basic tests for MVP functionality"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta

from analytics.conversion_tracker import ConversionTracker
from models.user import SubscriptionStatus, User
from repositories.user_repository import UserRepository


class TestMVPCore(unittest.TestCase):
    """Test core MVP functionality"""

    def setUp(self):
        """Set up test database"""
        self.test_db = tempfile.mktemp()
        self.user_repo = UserRepository(self.test_db)
        self.conversion_tracker = ConversionTracker(self.test_db)

        # Initialize test database
        from database.db_setup import DatabaseSetup

        db_setup = DatabaseSetup(self.test_db)
        db_setup.initialize()

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.unlink(self.test_db)

    def test_user_creation(self):
        """Test user creation and retrieval"""
        # Create user
        user = self.user_repo.create_user(
            telegram_id=123456, username="testuser", first_name="Test"
        )

        self.assertEqual(user.telegram_id, 123456)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.subscription_status, SubscriptionStatus.NONE)

        # Retrieve user
        retrieved_user = self.user_repo.get_user(123456)
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.telegram_id, 123456)

    def test_trial_activation(self):
        """Test trial activation"""
        # Create user
        user = self.user_repo.create_user(123456, "testuser", "Test")

        # Start trial
        trial_end = datetime.now() + timedelta(days=7)
        user.subscription_status = SubscriptionStatus.TRIAL
        user.trial_expires = trial_end

        self.user_repo.update_user(user)

        # Verify trial is active
        updated_user = self.user_repo.get_user(123456)
        self.assertTrue(updated_user.is_subscription_active())

    def test_conversion_tracking(self):
        """Test conversion tracking"""
        user_id = 123456

        # Track events
        self.conversion_tracker.track_event(user_id, "bot_start")
        self.conversion_tracker.track_event(user_id, "user_registered")
        self.conversion_tracker.track_event(user_id, "trial_started")

        # Get metrics
        metrics = self.conversion_tracker.get_conversion_metrics()

        self.assertEqual(metrics.get("started", 0), 1)
        self.assertEqual(metrics.get("registered", 0), 1)
        self.assertEqual(metrics.get("trial", 0), 1)

    def test_bot_configuration(self):
        """Test bot configuration validation"""
        # Create user with full setup
        user = User(
            telegram_id=123456,
            subscription_status=SubscriptionStatus.TRIAL,
            trial_expires=datetime.now() + timedelta(days=7),
            binance_api_key="test_api_key_12345",
            binance_secret_key="test_secret_key_12345",
            total_capital=1000.0,
            risk_level="moderate",
            trading_pairs=["ADA", "AVAX"],
        )

        # Test can_start_bot
        self.assertTrue(user.can_start_bot())

        # Test without API keys
        user.binance_api_key = None
        self.assertFalse(user.can_start_bot())


if __name__ == "__main__":
    unittest.main()
