# utils/base_handler.py
"""
Enhanced Base Client Handler with User Registry Integration
==========================================================

Extends your existing BaseClientHandler with user registration and admin functionality
while maintaining all existing functionality and structure.
"""

import logging
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from repositories.client_repository import ClientRepository
from services.grid_orchestrator import GridOrchestrator
from services.user_registry import AdminService, UserRegistryService


class BaseClientHandler:
    """Enhanced base handler with user registry and shared functionality"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client_repo = ClientRepository()
        self.grid_orchestrator = GridOrchestrator()
        self.client_states = {}

        # NEW: Add user registry services
        self.user_registry = UserRegistryService()
        self.admin_service = AdminService()

        self.logger.info(
            f"🎯 Enhanced base_handler.py using GridOrchestrator instance ID: {id(self.grid_orchestrator)}"
        )

    # =====================================
    # NEW: USER REGISTRY METHODS
    # =====================================

    async def handle_start_with_registration(self, update, context):
        """Enhanced /start command with user registration"""
        user = update.effective_user

        # Track user activity
        await self.user_registry.log_user_activity(
            user.id,
            "start_command",
            {"username": user.username, "first_name": user.first_name},
        )

        # Check if user exists and get registration info
        client_info = self.user_registry.get_client_registration_info(user.id)

        if client_info:
            await self._handle_existing_user_registration(update, client_info)
        else:
            await self._handle_new_user_registration(update, user)

    async def _handle_existing_user_registration(self, update, client_info: dict):
        """Handle existing user based on registration status"""
        status = client_info["registration_status"]
        first_name = client_info["first_name"]

        if status == "approved":
            # User is approved, show normal dashboard
            client = self.client_repo.get_client(client_info["telegram_id"])
            if client:
                await self.show_dashboard(update, client)
            else:
                # Edge case: approved in registry but not in client_repo
                await self._sync_registry_to_client_repo(update, client_info)

        elif status == "pending":
            await self._show_pending_approval_message(update, first_name)
        elif status == "rejected":
            await self._show_rejected_message(update, client_info)
        elif status == "suspended":
            await self._show_suspended_message(update, first_name)
        elif status == "banned":
            await self._show_banned_message(update)

    async def _handle_new_user_registration(self, update, user):
        """Handle new user registration"""
        registration_result = await self.user_registry.register_user(user)

        if not registration_result["success"]:
            await update.message.reply_text(registration_result["message"])
            return

        status = registration_result["status"]
        client_info = registration_result["client"]

        if status == "approved":
            # User auto-approved, sync to client_repo and show welcome
            await self._sync_registry_to_client_repo(update, client_info, is_new=True)
        elif status == "pending":
            await self._show_pending_approval_message(update, client_info["first_name"])
        else:
            await update.message.reply_text(registration_result["message"])

    async def _sync_registry_to_client_repo(
        self, update, client_info: dict, is_new: bool = False
    ):
        """Sync user registry data to your existing client repository"""
        try:
            # Check if client exists in your client_repo
            existing_client = self.client_repo.get_client(client_info["telegram_id"])

            if not existing_client:
                # Create new client in your existing system
                client = self.client_repo.create_client(
                    telegram_id=client_info["telegram_id"],
                    username=client_info["username"],
                    first_name=client_info["first_name"],
                )
            else:
                client = existing_client

            if is_new:
                await self._show_welcome_message(update, client)
            else:
                await self.show_dashboard(update, client)

        except Exception as e:
            self.logger.error(f"Error syncing registry to client_repo: {e}")
            await update.message.reply_text(
                "❌ System error during registration. Please try again later."
            )

    async def _show_welcome_message(self, update, client):
        """Show welcome message to newly approved users"""
        keyboard = [
            [InlineKeyboardButton("🔑 Setup API Keys", callback_data="setup_api")],
            [InlineKeyboardButton("📊 View Dashboard", callback_data="home")],
            [InlineKeyboardButton("❓ Help & Guide", callback_data="show_help")],
        ]

        welcome_text = f"""🎉 **Welcome to GridTrader Pro, {client.first_name}!**

Your account has been created and activated successfully.

**Your Details:**
🆔 Client ID: `{client.telegram_id}`
💰 Initial Capital: ${client.total_capital:,.2f}

**Next Steps:**
1. 🔑 Setup your Binance API keys
2. 💰 Configure your trading capital
3. 🎯 Choose your trading pairs
4. 🚀 Start grid trading

Click a button below to get started!"""

        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _show_pending_approval_message(self, update, first_name: str):
        """Show pending approval message"""
        pending_text = f"""⏳ **Registration Submitted**

Thank you for registering, {first_name}!

**Status:** Pending Admin Approval

**What happens next:**
• An administrator will review your application
• You'll receive a notification when approved
• Setup instructions will be provided

**Estimated Review Time:** 24-48 hours

Please be patient while we process your registration."""

        await update.message.reply_text(pending_text, parse_mode="Markdown")

    async def _show_rejected_message(self, update, client_info: dict):
        """Show rejection message"""
        reason = client_info.get("registration_notes", "Not specified")

        rejected_text = f"""❌ **Registration Not Approved**

Your registration was not approved.

**Reason:** {reason}

Contact the administrator for more information or to appeal this decision."""

        await update.message.reply_text(rejected_text, parse_mode="Markdown")

    async def _show_suspended_message(self, update, first_name: str):
        """Show suspension message"""
        suspended_text = f"""⚠️ **Account Suspended**

Hello {first_name}, your account is temporarily suspended.

Please contact the administrator for assistance and to resolve any issues."""

        await update.message.reply_text(suspended_text, parse_mode="Markdown")

    async def _show_banned_message(self, update):
        """Show banned message"""
        banned_text = """🚫 **Access Denied**

Your account has been permanently banned from this service."""

        await update.message.reply_text(banned_text, parse_mode="Markdown")

    # =====================================
    # NEW: ADMIN FUNCTIONALITY
    # =====================================

    async def handle_admin_command(self, update, context):
        """Handle /admin command"""
        user_id = update.effective_user.id

        if not self.admin_service.is_admin(user_id):
            await update.message.reply_text(
                "❌ Access denied. Admin privileges required."
            )
            return

        await self._show_admin_panel(update)

    async def _show_admin_panel(self, update):
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

        admin_text = f"""🛡️ **Admin Control Panel**

**User Statistics:**
✅ Approved: {stats.get("approved_users", 0)}
⏳ Pending: {stats.get("pending_users", 0)}
❌ Rejected: {stats.get("rejected_users", 0)}
🚫 Suspended: {stats.get("suspended_users", 0)}

**Activity:**
📈 Recent (7 days): {stats.get("recent_registrations", 0)} new users
⚡ Active Traders: {stats.get("active_traders", 0)}

**Pending Approvals:** {len(pending_users)}

Choose an admin action:"""

        if hasattr(update, "message") and update.message:
            await update.message.reply_text(
                admin_text, reply_markup=reply_markup, parse_mode="Markdown"
            )
        else:
            await update.edit_message_text(
                admin_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

    async def handle_admin_callbacks(self, query, client_id: int, action: str) -> bool:
        """Handle admin callback queries"""
        if not self.admin_service.is_admin(client_id):
            await query.answer("❌ Access denied")
            return False

        if action == "admin_pending":
            await self._show_pending_users(query)
            return True
        elif action == "admin_stats":
            await self._show_detailed_stats(query)
            return True
        elif action == "admin_settings":
            await self._show_admin_settings(query)
            return True
        elif action == "admin_refresh":
            await self._show_admin_panel(query)
            return True
        elif action.startswith("approve_"):
            user_to_approve = int(action.split("_")[1])
            await self._approve_user_callback(query, user_to_approve)
            return True
        elif action.startswith("reject_"):
            user_to_reject = int(action.split("_")[1])
            await self._reject_user_callback(query, user_to_reject)
            return True

        return False

    async def _show_pending_users(self, query):
        """Show pending users for approval - FIXED VERSION"""
        pending_users = self.admin_service.get_pending_users()

        if not pending_users:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 Back to Admin Panel", callback_data="admin_refresh"
                    )
                ]
            ]

            await query.edit_message_text(
                "✅ No pending users to review.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Build message WITHOUT complex Markdown formatting
        message = "👥 PENDING USER APPROVALS\n\n"

        for i, user in enumerate(pending_users[:5], 1):  # Limit to 5 users
            telegram_id = user.get("telegram_id", "Unknown")
            username = user.get("username", "No username")
            first_name = user.get("first_name", "Unknown")
            reg_date = user.get("registration_date", "Unknown")[:10]  # Just date part

            # Simple text formatting without complex Markdown
            message += f"{i}. User: {first_name}\n"
            message += f"   ID: {telegram_id}\n"
            message += f"   Username: @{username}\n"
            message += f"   Registered: {reg_date}\n\n"

        # Simple keyboard with approve/reject buttons
        keyboard = []

        for user in pending_users[:3]:  # Limit to 3 users to avoid message limits
            telegram_id = user.get("telegram_id")
            first_name = user.get("first_name", "User")[:10]  # Truncate name

            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"✅ {first_name}", callback_data=f"approve_{telegram_id}"
                    ),
                    InlineKeyboardButton(
                        f"❌ {first_name}", callback_data=f"reject_{telegram_id}"
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

        try:
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=None,  # No Markdown parsing to avoid errors
            )
        except Exception:
            # Fallback to even simpler message
            simple_message = (
                f"Pending users: {len(pending_users)}\nUse /admin to manage users."
            )

            await query.edit_message_text(
                simple_message,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔙 Admin Panel", callback_data="admin_refresh"
                            )
                        ]
                    ]
                ),
                parse_mode=None,
            )

    async def _approve_user_callback(self, query, user_id: int):
        """Handle user approval"""
        admin_id = query.from_user.id
        success = await self.admin_service.approve_user(
            admin_id, user_id, "Approved via Telegram"
        )

        if success:
            await query.answer(f"✅ User {user_id} approved successfully!")
            # Refresh the pending users list
            await self._show_pending_users(query)
        else:
            await query.answer(f"❌ Failed to approve user {user_id}")

    async def _reject_user_callback(self, query, user_id: int):
        """Handle user rejection"""
        admin_id = query.from_user.id
        success = await self.admin_service.reject_user(
            admin_id, user_id, "Rejected via Telegram"
        )

        if success:
            await query.answer(f"❌ User {user_id} rejected")
            # Refresh the pending users list
            await self._show_pending_users(query)
        else:
            await query.answer(f"❌ Failed to reject user {user_id}")

    async def _show_detailed_stats(self, query):
        """Show detailed user statistics"""
        stats = self.admin_service.get_user_statistics()

        stats_text = f"""📊 **Detailed User Statistics**

**Registration Status:**
✅ Approved Users: {stats.get("approved_users", 0)}
⏳ Pending Users: {stats.get("pending_users", 0)}
❌ Rejected Users: {stats.get("rejected_users", 0)}
⚠️ Suspended Users: {stats.get("suspended_users", 0)}
🚫 Banned Users: {stats.get("banned_users", 0)}

**Activity Metrics:**
📈 Recent Registrations (7 days): {stats.get("recent_registrations", 0)}
⚡ Active Traders: {stats.get("active_traders", 0)}
👥 Total Users: {sum([stats.get(k, 0) for k in ["approved_users", "pending_users", "rejected_users", "suspended_users", "banned_users"]])}

**System Health:** {"🟢 Good" if stats.get("pending_users", 0) < 5 else "🟡 Needs Attention"}"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 Back to Admin Panel", callback_data="admin_refresh"
                )
            ]
        ]

        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _show_admin_settings(self, query):
        """Show admin settings"""
        settings_text = """⚙️ **Admin Settings**

**Current Configuration:**
🔓 Auto Approve: Enabled
👥 Max Users: 50
📝 Registration: Open

**Available Actions:**
• View pending users
• Approve/reject registrations
• View user statistics
• Monitor system health

Contact system administrator to modify settings."""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 Back to Admin Panel", callback_data="admin_refresh"
                )
            ]
        ]

        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # =====================================
    # ENHANCED COMMON CALLBACK HANDLING
    # =====================================

    async def handle_common_callbacks(self, query, client_id: int, action: str) -> bool:
        """Enhanced common callback handler with admin support"""

        # First check if it's an admin callback
        if action.startswith(("admin_", "approve_", "reject_")):
            return await self.handle_admin_callbacks(query, client_id, action)

        # Then handle regular callbacks (your existing logic)
        handlers = {
            "setup_api": self.setup_api_keys,
            "show_settings": self.show_settings,
            "stop_all_grids": self.stop_all_grids,
            "set_capital": self.set_capital,
            "cancel_input": self.cancel_input,
            "show_dashboard": self.go_home,
            "home": self.go_home,
            "show_help": self.show_help,  # NEW: Add help handler
        }

        handler = handlers.get(action)
        if handler:
            await handler(query, client_id)
            return True
        return False

    # =====================================
    # ENHANCED USER ACCESS CONTROL
    # =====================================

    def _check_user_access(self, client_id: int) -> tuple[bool, str]:
        """Check if user has access and return status"""
        client_info = self.user_registry.get_client_registration_info(client_id)

        if not client_info:
            return False, "not_registered"

        status = client_info["registration_status"]

        if status == "approved":
            return True, "approved"
        elif status == "pending":
            return False, "pending"
        elif status == "rejected":
            return False, "rejected"
        elif status == "suspended":
            return False, "suspended"
        elif status == "banned":
            return False, "banned"
        else:
            return False, "unknown"

    async def _handle_access_denied(
        self, update, status: str, client_info: dict = None
    ):
        """Handle access denied scenarios"""
        if status == "pending":
            await update.message.reply_text(
                "⏳ Your registration is still pending admin approval."
            )
        elif status == "rejected":
            reason = (
                client_info.get("registration_notes", "Not specified")
                if client_info
                else "Not specified"
            )
            await update.message.reply_text(f"❌ Access denied. Reason: {reason}")
        elif status == "suspended":
            await update.message.reply_text(
                "⚠️ Your account is temporarily suspended. Contact administrator."
            )
        elif status == "banned":
            await update.message.reply_text(
                "🚫 Your account has been permanently banned."
            )
        else:
            await update.message.reply_text(
                "❌ Access denied. Please contact administrator."
            )

    # =====================================
    # NEW: HELP SYSTEM
    # =====================================

    async def show_help(self, query, client_id: int):
        """Show help information"""
        help_text = """❓ **GridTrader Pro Help**

**Available Commands:**
/start - Main dashboard
/admin - Admin panel (admins only)

**Quick Trading Commands:**
• `ADA 1000` - Start ADA grid with $1000
• `ETH 2000` - Start ETH grid with $2000
• `SOL 1500` - Start SOL grid with $1500

**Getting Started:**
1. Setup your Binance API keys
2. Configure your trading capital
3. Start grid trading
4. Monitor your profits!

**Button Navigation:**
Use the buttons in messages to navigate easily.

**Support:**
Contact @admin for technical support."""

        keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="home")]]

        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # =====================================
    # EXISTING METHODS (keeping all your current functionality)
    # =====================================

    # All your existing methods remain exactly the same:
    # - handle_common_messages
    # - _handle_api_key_input
    # - _handle_secret_input
    # - _handle_capital_input
    # - setup_api_keys
    # - show_settings
    # - set_capital
    # - stop_all_grids
    # - cancel_input
    # - go_home
    # - show_dashboard
    # - _is_trading_command

    async def handle_common_messages(self, update, context, text: str) -> bool:
        """Handle common message patterns. Returns True if handled."""
        client_id = update.effective_user.id

        if client_id not in self.client_states:
            return False

        state = self.client_states[client_id]
        step = state.get("step")

        if step == "waiting_api_key":
            return await self._handle_api_key_input(update, client_id, text, state)
        elif step == "waiting_secret":
            return await self._handle_secret_input(update, client_id, text, state)
        elif step == "waiting_capital":
            return await self._handle_capital_input(update, client_id, text)

        return False

    def _is_trading_command(self, text: str) -> bool:
        """Check if text is a trading command (ETH 1000, ADA 500, etc.)"""
        try:
            parts = text.strip().upper().split()
            if len(parts) == 2:
                symbol, amount = parts[0], float(parts[1])
                return symbol in ["ADA", "AVAX", "BTC", "ETH", "SOL"] and amount > 0
        except (ValueError, IndexError):
            pass
        return False

    # INPUT HANDLERS (keeping your existing logic)
    async def _handle_api_key_input(
        self, update, client_id: int, text: str, state: dict
    ) -> bool:
        """Handle API key input"""
        api_key = text.strip()
        if len(api_key) < 20:
            await update.message.reply_text(
                "❌ Invalid API key format. Please try again."
            )
            return True

        state["api_key"] = api_key
        state["step"] = "waiting_secret"

        await update.message.reply_text(
            "🔐 **Step 2:** Send your Binance Secret Key\n\n⚠️ Make sure this chat is private!"
        )
        return True

    # Fix for utils/base_handler.py
    # Replace your _handle_secret_input method with this:

    async def _handle_secret_input(
        self, update, client_id: int, text: str, state: dict
    ) -> bool:
        """Handle secret key input - FIXED VERSION"""
        secret_key = text.strip()
        if len(secret_key) < 20:
            await update.message.reply_text(
                "❌ Invalid secret key format. Please try again."
            )
            return True

        try:
            # Get the API key from state
            api_key = state.get("api_key", "").strip()

            if not api_key:
                await update.message.reply_text(
                    "❌ API key missing. Please restart setup."
                )
                del self.client_states[client_id]
                return True

            # Get client from database
            client = self.client_repo.get_client(client_id)
            if not client:
                await update.message.reply_text(
                    "❌ Client not found. Please try /start again."
                )
                del self.client_states[client_id]
                return True

            # CRITICAL FIX: Use correct field names
            client.binance_api_key = api_key  # ✅ FIXED
            client.binance_secret_key = secret_key  # ✅ FIXED

            # Save to database
            success = self.client_repo.update_client(client)

            if success:
                # Clear state
                del self.client_states[client_id]

                await update.message.reply_text(
                    "✅ **API Keys Saved Successfully!**\n\n"
                    "🔒 Your keys are encrypted and secure.\n"
                    "Ready to start trading!"
                )

                await self.show_dashboard(update, client)
            else:
                await update.message.reply_text(
                    "❌ Error saving API keys to database. Please try again."
                )
                del self.client_states[client_id]

        except Exception as e:
            self.logger.error(f"Error saving API keys: {e}")
            await update.message.reply_text(
                "❌ Error saving API keys. Please try again."
            )
            # Clean up state
            if client_id in self.client_states:
                del self.client_states[client_id]

        return True

    async def _handle_capital_input(self, update, client_id: int, text: str) -> bool:
        """Handle capital input"""
        try:
            capital = float(text.strip().replace(",", ""))
            if capital < 100:
                await update.message.reply_text("💰 Minimum capital: $100")
                return True

            client = self.client_repo.get_client(client_id)
            client.total_capital = capital
            self.client_repo.update_client(client)

            # Clear state
            del self.client_states[client_id]

            await update.message.reply_text(
                f"✅ **Capital Set: ${capital:,.2f}**\n\nReady to start grid trading!"
            )

            await self.show_dashboard(update, client)

        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a number.")

        return True

    # UI METHODS (keeping your existing implementations)
    async def setup_api_keys(self, query, client_id: int):
        """Start API key setup process"""
        self.client_states[client_id] = {"step": "waiting_api_key"}

        message = """🔐 **Binance API Setup**

**Step 1:** Send your Binance API Key

**How to get your API keys:**
1. Go to Binance.com → Profile → API Management
2. Create new API key with these permissions:
   ✅ Enable Spot Trading
   ❌ DO NOT enable withdrawals
3. Copy and send your API Key below

**Security:** Your keys are encrypted and used only for trading."""

        keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="home")]]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def show_settings(self, query, client_id: int):
        """Show account settings"""
        client = self.client_repo.get_client(client_id)

        has_api_keys = bool(client.binance_api_key and client.binance_secret_key)
        api_status = "✅ Connected" if has_api_keys else "❌ Not Set"
        capital_status = (
            f"${client.total_capital:,.2f}"
            if client.total_capital > 0
            else "❌ Not Set"
        )

        message = f"""⚙️ **Account Settings**

**API Connection:** {api_status}
**Trading Capital:** {capital_status}
**Risk Level:** {client.risk_level.title()}

**Account Status:** {"✅ Ready" if client.can_start_grid() else "❌ Setup Required"}"""

        keyboard = []
        if not has_api_keys:
            keyboard.append(
                [InlineKeyboardButton("🔐 Setup API Keys", callback_data="setup_api")]
            )
        if client.total_capital <= 0:
            keyboard.append(
                [InlineKeyboardButton("💰 Set Capital", callback_data="set_capital")]
            )
        keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="home")])

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def set_capital(self, query, client_id: int):
        """Start capital setting process"""
        self.client_states[client_id] = {"step": "waiting_capital"}

        message = """💰 **Set Trading Capital**

Enter your total trading capital in USD.

**Examples:**
• `1000` = $1,000
• `5000` = $5,000
• `10000` = $10,000

**Minimum:** $100
**Recommended:** Start with $500-1000 for best results"""

        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_input")]]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def stop_all_grids(self, query, client_id: int):
        """Stop all active grids"""
        await query.edit_message_text("🔄 **Stopping all grids...**")

        result = await self.grid_orchestrator.stop_all_client_grids(client_id)

        if result["success"]:
            grids_stopped = result.get("total_stopped", 0)
            message = f"""🛑 **All Grids Stopped**

✅ Successfully stopped {grids_stopped} grid(s)
✅ All orders cancelled
✅ Positions secured

Your account is now in safe mode."""
        else:
            message = f"""❌ **Error Stopping Grids**

Some grids may still be active.
Error: {result.get("error", "Unknown error")}

Please check manually or contact support."""

        keyboard = [[InlineKeyboardButton("🏠 Home", callback_data="home")]]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def cancel_input(self, query, client_id: int):
        """Cancel any input state and return home"""
        self.client_states.pop(client_id, None)
        await self.go_home(query, client_id)

    async def go_home(self, query, client_id: int):
        """Return to home dashboard"""
        try:
            client = self.client_repo.get_client(client_id)

            has_api_keys = bool(client.binance_api_key and client.binance_secret_key)
            setup_status = (
                "✅ Ready"
                if (has_api_keys and client.total_capital > 0)
                else "⚙️ Setup Required"
            )

            message = f"""🏠 **GridTrader Pro Home**

**Status:** {setup_status}
**Capital:** ${client.total_capital:,.2f}

**Quick Commands:**
`ETH 1000` • `SOL 800` • `ADA 600`"""

            keyboard = [
                [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
                [
                    InlineKeyboardButton(
                        "📈 Performance", callback_data="show_performance"
                    )
                ],
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error going home: {e}")
            await query.edit_message_text("🏠 Home\n\nUse: `ETH 1000` or `ADA 800`")

    async def show_dashboard(
        self, update, client, extra_buttons: Optional[List] = None
    ):
        """Show main dashboard - enhanced with registration check"""
        try:
            # Check user access first
            has_access, access_status = self._check_user_access(client.telegram_id)

            if not has_access:
                client_info = self.user_registry.get_client_registration_info(
                    client.telegram_id
                )
                await self._handle_access_denied(update, access_status, client_info)
                return

            # Get grid status safely
            grid_status = {}
            try:
                grid_status = await self.grid_orchestrator.get_client_grid_status(
                    client.telegram_id
                )
            except Exception as e:
                self.logger.warning(f"Grid status error: {e}")

            # Build basic dashboard
            has_api_keys = bool(client.binance_api_key and client.binance_secret_key)
            api_status = "✅ Connected" if has_api_keys else "❌ Not Set"

            active_grids = grid_status.get("active_grids", {})
            active_info = (
                f"\n🤖 Active Grids: {len(active_grids)}"
                if active_grids
                else "\n💤 No active grids"
            )

            message = f"""📊 **GridTrader Pro Dashboard**

**Account Status:**
🔐 API Keys: {api_status}
💰 Capital: ${client.total_capital:,.2f}{active_info}

**Quick Trading:** Type `ADA 1000` or `ETH 500`"""

            keyboard = [
                [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
                [
                    InlineKeyboardButton(
                        "📈 Performance", callback_data="show_performance"
                    )
                ],
            ]

            if extra_buttons:
                keyboard.extend(extra_buttons)

            # Send _handle_api_input
            if hasattr(update, "message") and update.message:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                )
            else:
                await update.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                )

        except Exception as e:
            self.logger.error(f"Error showing dashboard: {e}")
            # Simple fallback
            fallback_msg = (
                "📊 **Dashboard**\n\nUse quick commands: `ADA 1000` or `ETH 500`"
            )
            try:
                if hasattr(update, "message") and update.message:
                    await update.message.reply_text(fallback_msg)
                else:
                    await update.edit_message_text(fallback_msg)
            except:
                pass
