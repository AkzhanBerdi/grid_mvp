# test_config.py
"""Test configuration matching actual project structure"""

import os
from pathlib import Path

class TestConfig:
    """Test-specific configuration"""
    
    # Use in-memory database for tests
    DATABASE_PATH = ":memory:"
    
    # Test environment settings
    ENVIRONMENT = "test"
    TELEGRAM_BOT_TOKEN = "test_token_123"
    ADMIN_TELEGRAM_ID = 123456789
    ENCRYPTION_KEY = "test-encryption-key-32-characters"
    
    # Trading settings for tests
    DEFAULT_TRADING_PAIRS = ["ADA", "AVAX"]
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "test_logs/test.log"
    
    @classmethod
    def setup_test_environment(cls):
        """Setup test environment"""
        # Create test logs directory
        Path("test_logs").mkdir(exist_ok=True)
        
        # Override main config for testing
        import config
        config.Config.DATABASE_PATH = cls.DATABASE_PATH
        config.Config.ENVIRONMENT = cls.ENVIRONMENT
        config.Config.ENCRYPTION_KEY = cls.ENCRYPTION_KEY
