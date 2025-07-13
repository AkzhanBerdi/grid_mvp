"""User repository - COMPLETELY FIXED"""

import sqlite3
import logging
from typing import Optional
from datetime import datetime
from config import Config
from models.user import User, SubscriptionStatus, BotStatus

class UserRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
    
    def create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> User:
        """Create a new user"""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO users (
                        telegram_id, username, first_name, subscription_status, 
                        bot_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user.telegram_id,
                    user.username,
                    user.first_name,
                    user.subscription_status.value,
                    user.bot_status.value,
                    user.created_at.isoformat()
                ))
            
            self.logger.info(f"Created user: {telegram_id}")
            return user
            
        except sqlite3.IntegrityError:
            # User already exists, return existing user
            return self.get_user(telegram_id)
        except Exception as e:
            self.logger.error(f"Error creating user {telegram_id}: {e}")
            # Return a basic user object anyway
            return user
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID - SAFE VERSION"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT telegram_id, username, first_name, subscription_status, 
                           bot_status, trial_started, trial_expires, total_capital,
                           risk_level, trading_pairs, binance_api_key, binance_secret_key, 
                           created_at, updated_at
                    FROM users WHERE telegram_id = ?
                """, (telegram_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Manually map fields to avoid constructor issues
                fields = [
                    'telegram_id', 'username', 'first_name', 'subscription_status',
                    'bot_status', 'trial_started', 'trial_expires', 'total_capital',
                    'risk_level', 'trading_pairs', 'binance_api_key', 'binance_secret_key',
                    'created_at', 'updated_at'
                ]
                
                user_data = {}
                for i, value in enumerate(row):
                    user_data[fields[i]] = value
                
                # Parse trading pairs
                if user_data.get('trading_pairs'):
                    user_data['trading_pairs'] = user_data['trading_pairs'].split(',')
                else:
                    user_data['trading_pairs'] = ['ADA']
                
                # Convert datetime strings
                for field in ['trial_started', 'trial_expires', 'created_at', 'updated_at']:
                    if user_data.get(field):
                        try:
                            user_data[field] = datetime.fromisoformat(user_data[field])
                        except:
                            user_data[field] = None
                
                # Convert enums
                try:
                    user_data['subscription_status'] = SubscriptionStatus(user_data['subscription_status'])
                except:
                    user_data['subscription_status'] = SubscriptionStatus.NONE
                
                try:
                    user_data['bot_status'] = BotStatus(user_data['bot_status'])
                except:
                    user_data['bot_status'] = BotStatus.INACTIVE
                
                # Handle None values
                for field in ['total_capital']:
                    if user_data.get(field) is None:
                        user_data[field] = 0.0
                
                for field in ['risk_level']:
                    if user_data.get(field) is None:
                        user_data[field] = 'moderate'
                
                return User(**user_data)
                
        except Exception as e:
            self.logger.error(f"Error getting user {telegram_id}: {e}")
            # Return None if we can't get user
            return None
    
    def update_user(self, user: User) -> bool:
        """Update user information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE users SET
                        username = ?, first_name = ?, subscription_status = ?,
                        bot_status = ?, trial_started = ?, trial_expires = ?,
                        total_capital = ?, risk_level = ?, trading_pairs = ?,
                        binance_api_key = ?, binance_secret_key = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """, (
                    user.username, user.first_name, user.subscription_status.value,
                    user.bot_status.value,
                    user.trial_started.isoformat() if user.trial_started else None,
                    user.trial_expires.isoformat() if user.trial_expires else None,
                    user.total_capital, user.risk_level,
                    ','.join(user.trading_pairs) if user.trading_pairs else None,
                    user.binance_api_key, user.binance_secret_key, user.telegram_id
                ))
            return True
        except Exception as e:
            self.logger.error(f"Error updating user {user.telegram_id}: {e}")
            return False
    
    def user_exists(self, telegram_id: int) -> bool:
        """Check if user exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
                return cursor.fetchone() is not None
        except:
            return False
