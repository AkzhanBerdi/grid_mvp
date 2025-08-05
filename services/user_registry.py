# services/user_registry.py
"""
Complete Telegram User Registry System
Handles user registration, admin approval, and access control
"""

import logging
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import Config
from services.telegram_notifier import TelegramNotifier


class ClientRegistrationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    BANNED = "banned"


class UserRegistryService:
    """Complete user registration and management system"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        self.notifier = TelegramNotifier()

        # Settings
        self.auto_approve = Config.get_setting("AUTO_APPROVE_USERS", True)
        self.max_users = Config.get_setting("MAX_USERS", 50)
        self.registration_open = Config.get_setting("REGISTRATION_OPEN", True)

        # Initialize with graceful handling
        self._initialize_registry_tables()

    def _initialize_registry_tables(self):
        """Initialize registry tables with graceful error handling"""
        try:
            # Check if database file exists and has basic structure
            if not self._database_ready():
                self.logger.debug(
                    "Database not ready yet, skipping registry table initialization"
                )
                return

            self._ensure_tables()
            self.logger.info("✅ User registry tables initialized")

        except Exception as e:
            # Log as debug during initialization, not error
            self.logger.debug(f"Registry tables initialization deferred: {e}")

    def _database_ready(self) -> bool:
        """Check if the main database structure exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Check if the main clients table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='clients'
                """)
                return cursor.fetchone() is not None
        except Exception:
            return False

    def _ensure_tables(self):
        """Ensure required tables exist - only called when database is ready"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check and add registration columns to clients table
                self._add_registration_columns_if_missing(conn)

                # Create admin permissions table
                self._create_admin_permissions_table(conn)

                # Create user activity table
                self._create_user_activity_table(conn)

                # Add default admin if configured
                self._add_default_admin(conn)

                conn.commit()

        except Exception as e:
            self.logger.error(f"❌ Error setting up registry tables: {e}")
            raise

    def _add_registration_columns_if_missing(self, conn):
        """Add registration columns to clients table if they don't exist"""
        cursor = conn.cursor()

        # Get existing columns
        cursor.execute("PRAGMA table_info(clients)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Add missing columns
        columns_to_add = [
            ("registration_status", "TEXT DEFAULT 'approved'"),
            ("registration_date", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
            ("approved_by", "INTEGER"),
            ("registration_notes", "TEXT"),
        ]

        for column_name, column_def in columns_to_add:
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE clients ADD COLUMN {column_name} {column_def}"
                )
                self.logger.debug(f"Added column {column_name} to clients table")

    def _create_admin_permissions_table(self, conn):
        """Create admin permissions table"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_permissions (
                telegram_id INTEGER PRIMARY KEY,
                permission_level TEXT DEFAULT 'admin',
                granted_by INTEGER,
                granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (granted_by) REFERENCES admin_permissions (telegram_id)
            )
        """)

    def _create_user_activity_table(self, conn):
        """Create user activity table with indexes"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                activity_data TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (telegram_id)
            )
        """)

        # Create indexes
        indexes = [
            ("idx_user_activity_client_id", "user_activity(client_id)"),
            ("idx_user_activity_type", "user_activity(activity_type)"),
            ("idx_user_activity_timestamp", "user_activity(timestamp)"),
        ]

        for index_name, index_def in indexes:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}")

    def _add_default_admin(self, conn):
        """Add default admin if configured"""
        if hasattr(Config, "ADMIN_TELEGRAM_ID") and Config.ADMIN_TELEGRAM_ID:
            conn.execute(
                """
                INSERT OR IGNORE INTO admin_permissions (telegram_id, permission_level)
                VALUES (?, 'admin')
            """,
                (Config.ADMIN_TELEGRAM_ID,),
            )

    def ensure_registry_ready(self):
        """Public method to ensure registry is ready - can be called after main DB setup"""
        if not hasattr(self, "_registry_initialized"):
            self._initialize_registry_tables()
            self._registry_initialized = True

    def complete_initialization(self):
        """Complete the initialization after main database is ready"""
        if self._database_ready():
            try:
                self._ensure_tables()
                self.logger.info("✅ User registry initialization completed")
            except Exception as e:
                self.logger.error(f"❌ Failed to complete registry initialization: {e}")
        else:
            self.logger.warning(
                "⚠️ Main database not ready, registry initialization skipped"
            )

    async def register_user(self, user_data) -> Dict:
        """Register a new user"""
        try:
            # Ensure registry is ready before registering users
            self.ensure_registry_ready()

            telegram_id = user_data.id
            username = user_data.username or f"user_{telegram_id}"
            first_name = user_data.first_name or "Unknown"

            # Check if registration is open
            if not self.registration_open:
                return {
                    "success": False,
                    "status": "registration_closed",
                    "message": "🚫 Registration is currently closed. Contact the administrator for access.",
                }

            # Check if user already exists
            if self.client_exists(telegram_id):
                existing_client = self.get_client_registration_info(telegram_id)
                return {
                    "success": True,
                    "status": "already_exists",
                    "client": existing_client,
                    "message": f"Welcome back, {first_name}!",
                }

            # Check user limit
            current_user_count = self.get_user_count()
            if current_user_count >= self.max_users:
                return {
                    "success": False,
                    "status": "user_limit_reached",
                    "message": f"🚫 Maximum users ({self.max_users}) reached. Contact administrator.",
                }

            # Determine registration status
            if telegram_id == Config.ADMIN_TELEGRAM_ID:
                registration_status = "approved"  # Auto-approve admin
            else:
                registration_status = "approved" if self.auto_approve else "pending"

            # Create the client - simplified registration
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO clients (
                        telegram_id, username, first_name, status, grid_status,
                        registration_status, registration_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        telegram_id,
                        username,
                        first_name,
                        "active",
                        "inactive",
                        registration_status,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()

            # Log registration activity
            await self.log_user_activity(
                telegram_id,
                "registration",
                {"auto_approved": self.auto_approve, "username": username},
            )

            client_info = self.get_client_registration_info(telegram_id)

            if self.auto_approve:
                # Send welcome message
                await self.send_welcome_notification(client_info)
                self.logger.info(f"✅ Auto-approved user: {username} ({telegram_id})")

                return {
                    "success": True,
                    "status": "approved",
                    "client": client_info,
                    "message": f"🎉 Welcome to GridTrader Pro, {first_name}!",
                }
            else:
                # Send pending notification and notify admins
                await self.send_pending_notification(client_info)
                await self.notify_admins_new_user(client_info)
                self.logger.info(f"⏳ Pending approval: {username} ({telegram_id})")

                return {
                    "success": True,
                    "status": "pending",
                    "client": client_info,
                    "message": f"⏳ Registration submitted, {first_name}. Awaiting admin approval.",
                }

        except Exception as e:
            self.logger.error(f"❌ User registration failed for {telegram_id}: {e}")
            return {
                "success": False,
                "status": "error",
                "message": "❌ Registration failed. Please try again later.",
            }

    def client_exists(self, telegram_id: int) -> bool:
        """Check if client exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM clients WHERE telegram_id = ?", (telegram_id,)
                )
                return cursor.fetchone() is not None
        except:
            return False

    def get_client_registration_info(self, telegram_id: int) -> Optional[Dict]:
        """Get client registration information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT telegram_id, username, first_name, status, grid_status,
                           registration_status, registration_date, approved_by,
                           registration_notes
                    FROM clients WHERE telegram_id = ?
                """,
                    (telegram_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                return {
                    "telegram_id": row[0],
                    "username": row[1],
                    "first_name": row[2],
                    "status": row[3],
                    "grid_status": row[4],
                    "registration_status": row[5],
                    "registration_date": row[6],
                    "approved_by": row[7],
                    "registration_notes": row[8],
                    # Remove total_capital from registration info - it's a trading setting
                }

        except Exception as e:
            self.logger.error(f"❌ Error getting client info: {e}")
            return None

    def get_user_count(self) -> int:
        """Get current user count"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM clients")
                return cursor.fetchone()[0]
        except:
            return 0

    async def log_user_activity(
        self, client_id: int, activity_type: str, activity_data: Dict = None
    ):
        """Log user activity"""
        try:
            import json

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO user_activity (client_id, activity_type, activity_data)
                    VALUES (?, ?, ?)
                """,
                    (
                        client_id,
                        activity_type,
                        json.dumps(activity_data) if activity_data else None,
                    ),
                )
                conn.commit()

        except Exception as e:
            self.logger.error(f"❌ Error logging activity: {e}")

    async def send_welcome_notification(self, client_info: Dict):
        """Send welcome message to approved user"""
        if not self.notifier.enabled:
            return

        message = f"""🎉 *Welcome to GridTrader Pro!*

Your account has been activated successfully.

👤 *User:* {client_info["first_name"]}
🆔 *Client ID:* `{client_info["telegram_id"]}`
📅 *Registered:* {client_info["registration_date"][:10]}

*Next Steps:*
🔑 Setup your Binance API keys
💰 Configure your trading capital
🚀 Start grid trading

Type /start to begin!"""

        # Note: Would need to send to the user's chat, not admin chat
        # This is a placeholder - you'd need the user's chat_id
        pass

    async def send_pending_notification(self, client_info: Dict):
        """Send pending approval message to user"""
        # Similar to welcome but for pending users
        pass

    async def notify_admins_new_user(self, client_info: Dict):
        """Notify admins of new user registration"""
        if not self.notifier.enabled:
            return

        message = f"""👤 *New User Registration*

🆔 *Telegram ID:* `{client_info["telegram_id"]}`
👤 *Name:* {client_info["first_name"]}
🏷️ *Username:* @{client_info["username"] or "None"}
📅 *Registered:* {client_info["registration_date"][:16]}

*Action Required:*
Use /admin to approve or reject this user."""

        await self.notifier.send_message(message)


class AdminService:
    """Admin management and approval system"""

    def __init__(self, registry: UserRegistryService = None):
        self.registry = registry or UserRegistryService()
        self.db_path = self.registry.db_path
        self.logger = logging.getLogger(__name__)
        self.notifier = TelegramNotifier()

    def is_admin(self, telegram_id: int) -> bool:
        """Check if user is admin"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT permission_level FROM admin_permissions WHERE telegram_id = ?",
                    (telegram_id,),
                )
                result = cursor.fetchone()
                return result is not None
        except:
            # Fallback to config admin
            return telegram_id == getattr(Config, "ADMIN_TELEGRAM_ID", 0)

    async def approve_user(
        self, admin_id: int, user_id: int, notes: str = None
    ) -> bool:
        """Approve a pending user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if user exists and is pending
                cursor = conn.execute(
                    "SELECT registration_status FROM clients WHERE telegram_id = ?",
                    (user_id,),
                )
                result = cursor.fetchone()

                if not result:
                    self.logger.warning(f"User {user_id} not found for approval")
                    return False

                if result[0] != "pending":
                    self.logger.warning(
                        f"User {user_id} not in pending status: {result[0]}"
                    )
                    return False

                # Update user status
                conn.execute(
                    """
                    UPDATE clients 
                    SET registration_status = 'approved',
                        approved_by = ?,
                        registration_notes = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """,
                    (admin_id, notes, user_id),
                )
                conn.commit()

            # Log admin action
            await self.registry.log_user_activity(
                admin_id, "admin_approval", {"approved_user": user_id, "notes": notes}
            )

            # Get user info for notification
            client_info = self.registry.get_client_registration_info(user_id)
            if client_info:
                await self.registry.send_welcome_notification(client_info)

            self.logger.info(f"✅ Admin {admin_id} approved user {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error approving user {user_id}: {e}")
            return False

    async def reject_user(
        self, admin_id: int, user_id: int, reason: str = None
    ) -> bool:
        """Reject a pending user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE clients 
                    SET registration_status = 'rejected',
                        approved_by = ?,
                        registration_notes = ?
                    WHERE telegram_id = ? AND registration_status = 'pending'
                """,
                    (admin_id, reason, user_id),
                )
                conn.commit()

            # Log admin action
            await self.registry.log_user_activity(
                admin_id,
                "admin_rejection",
                {"rejected_user": user_id, "reason": reason},
            )

            self.logger.info(f"❌ Admin {admin_id} rejected user {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error rejecting user {user_id}: {e}")
            return False

    def get_pending_users(self) -> List[Dict]:
        """Get all users pending approval"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT telegram_id, username, first_name, registration_date
                    FROM clients 
                    WHERE registration_status = 'pending'
                    ORDER BY registration_date ASC
                """)

                return [
                    {
                        "telegram_id": row[0],
                        "username": row[1],
                        "first_name": row[2],
                        "registration_date": row[3],
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            self.logger.error(f"❌ Error getting pending users: {e}")
            return []

    def get_user_statistics(self) -> Dict:
        """Get user registration statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # Total users by status
                cursor = conn.execute("""
                    SELECT registration_status, COUNT(*) 
                    FROM clients 
                    GROUP BY registration_status
                """)

                for status, count in cursor.fetchall():
                    stats[f"{status}_users"] = count

                # Recent registrations (last 7 days)
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM clients 
                    WHERE registration_date >= datetime('now', '-7 days')
                """)
                stats["recent_registrations"] = cursor.fetchone()[0]

                # Active traders (have API keys)
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM clients 
                    WHERE binance_api_key IS NOT NULL 
                    AND registration_status = 'approved'
                """)
                stats["active_traders"] = cursor.fetchone()[0]

                return stats

        except Exception as e:
            self.logger.error(f"❌ Error getting user statistics: {e}")
            return {}


class RegistrationHandler:
    """Telegram handler for user registration"""

    def __init__(self):
        self.registry = UserRegistryService()
        self.admin_service = AdminService(self.registry)
        self.logger = logging.getLogger(__name__)

    async def handle_start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Enhanced /start command with registration"""
        user = update.effective_user

        # Log user activity
        await self.registry.log_user_activity(
            user.id,
            "start_command",
            {"username": user.username, "first_name": user.first_name},
        )

        # Check if user exists
        client_info = self.registry.get_client_registration_info(user.id)

        if client_info:
            await self.handle_existing_user(update, client_info)
        else:
            await self.handle_new_user(update, user)

    async def handle_existing_user(self, update: Update, client_info: Dict):
        """Handle existing user based on their registration status"""
        status = client_info["registration_status"]
        first_name = client_info["first_name"]

        if status == "approved":
            await self.show_main_dashboard(update, client_info)
        elif status == "pending":
            await update.message.reply_text(
                f"⏳ Hello {first_name}!\n\n"
                "Your registration is still pending admin approval.\n"
                "You'll be notified once your account is activated."
            )
        elif status == "rejected":
            await update.message.reply_text(
                f"❌ Hello {first_name}!\n\n"
                "Your registration was not approved.\n"
                f"Reason: {client_info.get('registration_notes', 'Not specified')}\n\n"
                "Contact the administrator for more information."
            )
        elif status == "suspended":
            await update.message.reply_text(
                f"⚠️ Hello {first_name}!\n\n"
                "Your account is temporarily suspended.\n"
                "Contact the administrator for assistance."
            )
        elif status == "banned":
            await update.message.reply_text(
                "🚫 Access denied.\n\nYour account has been permanently banned."
            )

    async def handle_new_user(self, update: Update, user):
        """Handle new user registration"""
        registration_result = await self.registry.register_user(user)

        if not registration_result["success"]:
            await update.message.reply_text(registration_result["message"])
            return

        status = registration_result["status"]
        client_info = registration_result["client"]

        if status == "approved":
            await self.send_welcome_message(update, client_info)
        elif status == "pending":
            await self.send_pending_message(update, client_info)
        else:
            await update.message.reply_text(registration_result["message"])

    async def send_welcome_message(self, update: Update, client_info: Dict):
        """Send welcome message to new approved user"""
        keyboard = [
            [InlineKeyboardButton("🔑 Setup API Keys", callback_data="setup_api")],
            [InlineKeyboardButton("📊 View Dashboard", callback_data="dashboard")],
            [InlineKeyboardButton("❓ Help & Guide", callback_data="help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = f"""🎉 *Welcome to GridTrader Pro, {client_info["first_name"]}!*

Your account has been created and activated successfully.

*Your Details:*
🆔 Client ID: `{client_info["telegram_id"]}`
📅 Registered: {client_info["registration_date"][:10]}
✅ Status: Approved

*Next Steps:*
1. 🔑 Setup your Binance API keys
2. 💰 Configure your trading capital  
3. 🎯 Choose your trading pairs
4. 🚀 Start grid trading

Click a button below to get started!"""

        await update.message.reply_text(
            welcome_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def send_pending_message(self, update: Update, client_info: Dict):
        """Send pending approval message"""
        pending_text = f"""⏳ *Registration Submitted*

Thank you for registering, {client_info["first_name"]}!

*Your Details:*
🆔 Application ID: `{client_info["telegram_id"]}`
📅 Submitted: {client_info["registration_date"][:16]}
📋 Status: Pending Admin Approval

*What happens next:*
• An administrator will review your application
• You'll receive a notification when approved
• Setup instructions will be provided

*Estimated Review Time:* 24-48 hours

Please be patient while we process your registration."""

        await update.message.reply_text(pending_text, parse_mode="Markdown")

    async def show_main_dashboard(self, update: Update, client_info: Dict):
        """Show main dashboard for approved users"""
        # Get actual client data for API keys only
        from repositories.client_repository import ClientRepository

        client_repo = ClientRepository()
        client = client_repo.get_client(client_info["telegram_id"])

        # Only check API keys - capital is set when starting trading
        has_api_keys = bool(client and client.binance_api_key)
        grid_status = client.grid_status if client else "inactive"

        # Create dynamic keyboard based on user state
        keyboard = []

        if not has_api_keys:
            keyboard.append(
                [InlineKeyboardButton("🔑 Setup API Keys", callback_data="setup_api")]
            )
        else:
            # Once API keys are set, user can start trading (capital set during trading setup)
            if grid_status == "inactive":
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🚀 Start Trading", callback_data="start_grid"
                        )
                    ]
                )
            else:
                keyboard.append(
                    [InlineKeyboardButton("⏹️ Stop Trading", callback_data="stop_grid")]
                )

        keyboard.extend(
            [
                [
                    InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
                    InlineKeyboardButton("💰 Profit Report", callback_data="profit"),
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                    InlineKeyboardButton("❓ Help", callback_data="help"),
                ],
            ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Simplified status display
        api_status = "✅ Connected" if has_api_keys else "❌ Not Setup"
        grid_status_emoji = "🟢 Active" if grid_status == "active" else "🔴 Inactive"

        dashboard_text = f"""🤖 *GridTrader Pro Dashboard*

👤 *User:* {client_info["first_name"]}
🆔 *Client ID:* `{client_info["telegram_id"]}`

*Account Status:*
🔑 API Keys: {api_status}
⚡ Grid Trading: {grid_status_emoji}

{"✅ Ready to trade!" if has_api_keys else "🔧 Setup your API keys to start trading"}

Choose an option below:"""

        await update.message.reply_text(
            dashboard_text, reply_markup=reply_markup, parse_mode="Markdown"
        )


class AdminHandler:
    """Telegram handler for admin commands"""

    def __init__(self):
        self.admin_service = AdminService()
        self.registry = UserRegistryService()
        self.logger = logging.getLogger(__name__)

    async def handle_admin_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /admin command"""
        user_id = update.effective_user.id

        if not self.admin_service.is_admin(user_id):
            await update.message.reply_text(
                "❌ Access denied. Admin privileges required."
            )
            return

        # Show admin panel
        await self.show_admin_panel(update)

    async def show_admin_panel(self, update: Update):
        """Show admin control panel"""
        # Get statistics
        stats = self.admin_service.get_user_statistics()
        pending_users = self.admin_service.get_pending_users()

        keyboard = [
            [
                InlineKeyboardButton("👥 Pending Users", callback_data="admin_pending"),
                InlineKeyboardButton("📊 User Stats", callback_data="admin_stats"),
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        admin_text = f"""🛡️ *Admin Control Panel*

*User Statistics:*
✅ Approved: {stats.get("approved_users", 0)}
⏳ Pending: {stats.get("pending_users", 0)}
❌ Rejected: {stats.get("rejected_users", 0)}
🚫 Suspended: {stats.get("suspended_users", 0)}
🔴 Banned: {stats.get("banned_users", 0)}

*Activity:*
📈 Recent (7 days): {stats.get("recent_registrations", 0)} new users
⚡ Active Traders: {stats.get("active_traders", 0)}

*Pending Approvals:* {len(pending_users)}

Choose an admin action:"""

        await update.message.reply_text(
            admin_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def handle_admin_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle admin callback queries"""
        query = update.callback_query
        user_id = update.effective_user.id

        if not self.admin_service.is_admin(user_id):
            await query.answer("❌ Access denied")
            return

        data = query.data

        if data == "admin_pending":
            await self.show_pending_users(query)
        elif data == "admin_stats":
            await self.show_detailed_stats(query)
        elif data == "admin_settings":
            await self.show_admin_settings(query)
        elif data == "admin_refresh":
            await self.show_admin_panel(query)
        elif data.startswith("approve_"):
            user_to_approve = int(data.split("_")[1])
            await self.approve_user_callback(query, user_to_approve)
        elif data.startswith("reject_"):
            user_to_reject = int(data.split("_")[1])
            await self.reject_user_callback(query, user_to_reject)

    async def show_pending_users(self, query):
        """Show pending users for approval"""
        pending_users = self.admin_service.get_pending_users()

        if not pending_users:
            await query.edit_message_text("✅ No pending users to review.")
            return

        text = "👥 *Pending User Approvals:*\n\n"
        keyboard = []

        for user in pending_users[:10]:  # Limit to 10 users per page
            user_info = (
                f"👤 {user['first_name']} (@{user['username'] or 'no_username'})\n"
            )
            user_info += f"🆔 `{user['telegram_id']}`\n"
            user_info += f"📅 {user['registration_date'][:10]}\n\n"
            text += user_info

            # Add approve/reject buttons
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"✅ Approve {user['first_name']}",
                        callback_data=f"approve_{user['telegram_id']}",
                    ),
                    InlineKeyboardButton(
                        f"❌ Reject {user['first_name']}",
                        callback_data=f"reject_{user['telegram_id']}",
                    ),
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "🔙 Back to Admin Panel", callback_data="admin_refresh"
                )
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def show_detailed_stats(self, query):
        """Show detailed user statistics"""
        stats = self.admin_service.get_user_statistics()

        stats_text = f"""📊 *Detailed User Statistics*

*Registration Status:*
✅ Approved: {stats.get("approved_users", 0)}
⏳ Pending: {stats.get("pending_users", 0)}
❌ Rejected: {stats.get("rejected_users", 0)}
⚠️ Suspended: {stats.get("suspended_users", 0)}
🚫 Banned: {stats.get("banned_users", 0)}

*Activity Metrics:*
📈 Recent (7 days): {stats.get("recent_registrations", 0)} new registrations
⚡ Active Traders: {stats.get("active_traders", 0)} users with API keys
💰 Total Users: {sum(v for k, v in stats.items() if k.endswith("_users"))}

*System Health:*
🟢 Registration: {"Open" if self.registry.registration_open else "Closed"}
👥 User Limit: {self.registry.get_user_count()}/{self.registry.max_users}
🤖 Auto Approve: {"Enabled" if self.registry.auto_approve else "Disabled"}"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 Back to Admin Panel", callback_data="admin_refresh"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            stats_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def show_admin_settings(self, query):
        """Show admin settings panel"""
        settings_text = f"""⚙️ *Admin Settings*

*Current Configuration:*
🔓 Registration Open: {"Yes" if self.registry.registration_open else "No"}
🤖 Auto Approve: {"Enabled" if self.registry.auto_approve else "Disabled"}
👥 Max Users: {self.registry.max_users}
🔔 Notifications: {"Enabled" if self.registry.notifier.enabled else "Disabled"}

*Quick Actions:*
Use these commands to modify settings:
• `/admin_toggle_registration` - Toggle registration
• `/admin_toggle_auto_approve` - Toggle auto approval
• `/admin_set_max_users <number>` - Set user limit

*Note:* Settings changes require bot restart to take full effect."""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 Back to Admin Panel", callback_data="admin_refresh"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            settings_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def approve_user_callback(self, query, user_id: int):
        """Handle user approval"""
        admin_id = query.from_user.id
        success = await self.admin_service.approve_user(
            admin_id, user_id, "Approved via Telegram"
        )

        if success:
            await query.answer(f"✅ User {user_id} approved successfully!")
            # Refresh the pending users list
            await self.show_pending_users(query)
        else:
            await query.answer(f"❌ Failed to approve user {user_id}")

    async def reject_user_callback(self, query, user_id: int):
        """Handle user rejection"""
        admin_id = query.from_user.id
        success = await self.admin_service.reject_user(
            admin_id, user_id, "Rejected via Telegram"
        )

        if success:
            await query.answer(f"❌ User {user_id} rejected")
            # Refresh the pending users list
            await self.show_pending_users(query)
        else:
            await query.answer(f"❌ Failed to reject user {user_id}")


# Integration with your existing handlers
class EnhancedClientHandler:
    """Enhanced client handler with registration integration"""

    def __init__(self):
        self.registration_handler = RegistrationHandler()
        self.admin_handler = AdminHandler()
        self.logger = logging.getLogger(__name__)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced start command with registration"""
        await self.registration_handler.handle_start_command(update, context)

    async def handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin commands"""
        await self.admin_handler.handle_admin_command(update, context)

    async def handle_callback_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle callback queries with registration support"""
        query = update.callback_query
        data = query.data

        # Check if it's an admin callback
        if (
            data.startswith("admin_")
            or data.startswith("approve_")
            or data.startswith("reject_")
        ):
            await self.admin_handler.handle_admin_callback(update, context)
        else:
            # Handle regular user callbacks
            await self.handle_user_callback(update, context)

    async def handle_user_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle regular user callback queries"""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data

        # Check user registration status
        registry = UserRegistryService()
        client_info = registry.get_client_registration_info(user_id)

        if not client_info or client_info["registration_status"] != "approved":
            await query.answer("❌ Access denied. Account not approved.")
            return

        # Handle approved user callbacks
        if data == "dashboard":
            await self.show_user_dashboard(query, client_info)
        elif data == "setup_api":
            await self.show_api_setup(query, client_info)
        elif data == "profit":
            await self.show_profit_report(query, client_info)
        elif data == "settings":
            await self.show_user_settings(query, client_info)
        elif data == "help":
            await self.show_help(query, client_info)
        else:
            await query.answer("🔧 Feature coming soon!")

    async def show_user_dashboard(self, query, client_info: Dict):
        """Show user dashboard"""
        # Get actual client data for trading info
        from repositories.client_repository import ClientRepository

        client_repo = ClientRepository()
        client = client_repo.get_client(client_info["telegram_id"])

        # Get real trading data
        capital = client.total_capital if client else 0.0
        capital_display = f"${capital:,.2f}" if capital > 0 else "❌ Not Set"
        grid_status = client.grid_status if client else "inactive"

        dashboard_text = f"""📊 *Trading Dashboard*

👤 User: {client_info["first_name"]}
💰 Capital: {capital_display}
⚡ Grid Status: {grid_status.title()}

🔧 Use the buttons below to manage your trading"""

        keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            dashboard_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def show_api_setup(self, query, client_info: Dict):
        """Show API setup instructions"""
        setup_text = """🔑 *Binance API Setup*

To start trading, you need to setup your Binance API keys:

*Steps:*
1. Login to Binance.com
2. Go to API Management
3. Create a new API key
4. Enable only "Spot Trading" permissions
5. Use /setapi command to add your keys

*Security:*
• Your keys are encrypted in our database
• Only spot trading permissions needed
• We never store your withdrawal permissions

Type: `/setapi YOUR_API_KEY YOUR_SECRET_KEY`"""

        await query.edit_message_text(setup_text, parse_mode="Markdown")

    async def show_profit_report(self, query, client_info: Dict):
        """Show profit report"""
        # Get actual client data for profit calculations
        from repositories.client_repository import ClientRepository

        client_repo = ClientRepository()
        client = client_repo.get_client(client_info["telegram_id"])

        if not client or not client.binance_api_key:
            profit_text = f"""💰 *Profit Report*

👤 User: {client_info["first_name"]}

⚠️ **Setup Required**
Please setup your API keys and trading capital first.

📊 Profit tracking will begin once you start trading."""
        else:
            profit_text = f"""💰 *Profit Report*

👤 User: {client_info["first_name"]}
💰 Capital: ${client.total_capital:,.2f}

📊 Total Profit: Available after first trades
📈 Recent Performance: Tracking will begin soon
💹 Best Performing Pair: Data pending

*Note: Detailed analytics coming soon*"""

        keyboard = [[InlineKeyboardButton("🔙 Back to Main", callback_data="home")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            profit_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def show_user_settings(self, query, client_info: Dict):
        """Show user settings"""
        # Get actual client data for settings
        from repositories.client_repository import ClientRepository

        client_repo = ClientRepository()
        client = client_repo.get_client(client_info["telegram_id"])

        capital = client.total_capital if client else 0.0
        risk_level = client.risk_level if client else "moderate"

        settings_text = f"""⚙️ *User Settings*

👤 User: {client_info["first_name"]}
💰 Capital: ${capital:,.2f}
🎯 Risk Level: {risk_level.title()}

🔧 Use /settings to modify trading parameters"""

        await query.edit_message_text(settings_text, parse_mode="Markdown")

    async def show_help(self, query, client_info: Dict):
        """Show help information"""
        help_text = """❓ *GridTrader Pro Help*

*Available Commands:*
/start - Main dashboard
/profit - View profit report
/status - Check grid status
/setapi - Setup API keys
/help - Show this help

*Getting Started:*
1. Setup your Binance API keys
2. Configure your trading capital
3. Start grid trading
4. Monitor your profits!

*Support:*
Contact the administrator for technical support."""

        await query.edit_message_text(help_text, parse_mode="Markdown")


# Configuration extension for user registry
class RegistryConfig:
    """Configuration settings for user registry"""

    # Registration settings
    AUTO_APPROVE_USERS = True  # Set to False to require admin approval
    MAX_USERS = 50  # Maximum number of users allowed
    REGISTRATION_OPEN = True  # Whether new registrations are accepted

    # Admin settings
    ADMIN_TELEGRAM_ID = None  # Set your Telegram ID
    ADMIN_NOTIFICATIONS = True  # Send notifications to admin

    # Security settings
    REQUIRE_USERNAME = False  # Require users to have a Telegram username
    MIN_ACCOUNT_AGE_DAYS = 0  # Minimum Telegram account age in days

    @classmethod
    def get_setting(cls, key: str, default=None):
        """Get configuration setting with fallback"""
        return getattr(cls, key, default)


if __name__ == "__main__":
    """Test the user registry system"""
    import asyncio

    async def test_registry():
        """Test user registry functionality"""
        print("🧪 Testing User Registry System...")

        # Initialize registry
        registry = UserRegistryService()
        admin_service = AdminService()

        # Test user registration (mock user)
        class MockUser:
            def __init__(self, user_id, username, first_name):
                self.id = user_id
                self.username = username
                self.first_name = first_name

        test_user = MockUser(123456789, "testuser", "Test User")

        # Test registration
        result = await registry.register_user(test_user)
        print(f"✅ Registration result: {result['status']}")

        # Test admin functions
        if admin_service.is_admin(123456789):  # Replace with your admin ID
            pending_users = admin_service.get_pending_users()
            print(f"📋 Pending users: {len(pending_users)}")

            stats = admin_service.get_user_statistics()
            print(f"📊 User stats: {stats}")

        print("🎉 User Registry System Ready!")
        print("\nNext steps:")
        print("1. Set your ADMIN_TELEGRAM_ID in config")
        print("2. Update your main.py to use EnhancedClientHandler")
        print("3. Test registration flow")

    try:
        asyncio.run(test_registry())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Check database permissions and configuration")
