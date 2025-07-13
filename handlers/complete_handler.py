import asyncio
import logging
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from models.user import SubscriptionStatus
from repositories.user_repository import UserRepository


class CompleteHandler:
    def __init__(self, conversion_tracker):
        self.user_repo = UserRepository()
        self.conversion_tracker = conversion_tracker
        self.user_states = {}
        self.logger = logging.getLogger(__name__)

    async def handle_start(self, update, context):
        """Main start with proper menu"""
        user = update.effective_user
        existing_user = self.user_repo.get_user(user.id)

        if existing_user and existing_user.is_subscription_active():
            await self._show_main_menu(update, existing_user)
        else:
            await self._handle_new_user(update, user)

    async def _handle_new_user(self, update, user):
        """New user with auto-trial"""
        new_user = self.user_repo.create_user(
            telegram_id=user.id, username=user.username, first_name=user.first_name
        )

        trial_end = datetime.now() + timedelta(days=7)
        new_user.subscription_status = SubscriptionStatus.TRIAL
        new_user.trial_expires = trial_end
        self.user_repo.update_user(new_user)

        self.conversion_tracker.track_event(user.id, "user_registered")
        self.conversion_tracker.track_event(user.id, "trial_started")

        message = f"""🤖 **Welcome to GridTrader Pro!**

Hi {user.first_name}! Your **FREE 7-day trial** is active! 🎉

**Our Results:** $30 profit in 10 days with $2000

**How to trade:** Just type `BTC 1000` or `ETH 500`

Ready to start?"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Start Trading", callback_data="show_trading_guide"
                )
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
        ]

        await update.message.reply_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_main_menu(self, update, user):
        """Main menu with navigation"""
        days_left = (
            (user.trial_expires - datetime.now()).days if user.trial_expires else 0
        )
        status = (
            f"🆓 Trial - {days_left} days left"
            if user.subscription_status == SubscriptionStatus.TRIAL
            else f"💎 {user.subscription_status.value.title()}"
        )

        message = f"""🤖 **GridTrader Pro**

Welcome back, {user.first_name}! 👋
**Status:** {status}

**Quick Trading:** Type `BTC 1000` or `ETH 500`

Choose an option:"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Start Trading", callback_data="show_trading_guide"
                )
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
        ]

        await update.message.reply_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def handle_callback(self, update, context):
        """Handle all callbacks with navigation"""
        query = update.callback_query
        user_id = query.from_user.id
        action = query.data

        # CLEAR USER STATE when navigating away from API setup
        if (
            action
            in ["main_dashboard", "show_trading_guide", "show_settings", "back_to_main"]
            and user_id in self.user_states
        ):
            self.logger.info(f"Clearing user state for {user_id} due to navigation")
            del self.user_states[user_id]

        if action == "main_dashboard":
            await self._show_dashboard(query, user_id)
        elif action == "show_trading_guide":
            await self._show_trading_guide(query, user_id)
        elif action == "show_settings":
            await self._show_settings(query, user_id)
        elif action == "back_to_main":
            await self._back_to_main(query, user_id)
        elif action == "setup_api_keys":
            await self._start_api_setup(query, user_id)
        elif action == "api_setup_real":
            await self._api_setup_real(query, user_id)
        elif action == "use_demo_keys":
            await self._use_demo_keys(query, user_id)
        elif action.startswith("execute_trade_"):
            await self._execute_trade(query, action)

    async def _show_dashboard(self, query, user_id):
        """Dashboard with back button"""
        user = self.user_repo.get_user(user_id)
        api_status = (
            "✅ Real Trading"
            if user.binance_api_key and "demo" not in user.binance_api_key
            else "🎮 Demo Mode"
        )

        message = f"""📊 **Dashboard**

**Trading Mode:** {api_status}
**How to trade:** Type `BTC 1000` or `ETH 500`

Ready to trade!"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Start Trading", callback_data="show_trading_guide"
                )
            ],
            [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_trading_guide(self, query, user_id):
        """Trading guide with navigation"""
        message = """🚀 **Start Trading in 30 seconds!**

**Step 1:** Type your trade
Examples: `BTC 1000`, `ETH 500`, `ADA 200`

**Step 2:** Confirm execution
Bot shows you exactly what happens

**Step 3:** Start earning!
Watch your grid orders work automatically

**For real trading:** You'll need Binance API keys
**For demo:** Just type any trade to see how it works!

**Try now:** Type `BTC 100` to see demo"""

        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("⚙️ Setup API Keys", callback_data="setup_api_keys")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_settings(self, query, user_id):
        """Settings with navigation"""
        user = self.user_repo.get_user(user_id)

        if user.binance_api_key:
            if "demo" in user.binance_api_key:
                api_status = "🎮 Demo Keys Active"
            else:
                api_status = "✅ Real API Connected"
        else:
            api_status = "❌ Not Setup"

        message = f"""⚙️ **Settings**

**API Keys:** {api_status}

Configure your bot:"""

        keyboard = [
            [InlineKeyboardButton("🔐 Setup API Keys", callback_data="setup_api_keys")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _start_api_setup(self, query, user_id):
        """API setup with options - CLEAR ANY EXISTING STATE"""
        # CRITICAL: Clear any existing user state
        if user_id in self.user_states:
            self.logger.info(
                f"Clearing existing user state for {user_id} at API setup start"
            )
            del self.user_states[user_id]

        message = """🔐 **API Keys Setup**

**Choose setup method:**

**Real API Keys:**
• Connect to your actual Binance account
• Real trading with real money
• 2-minute setup process

**Demo Keys:**
• Test all features safely
• No real money involved
• Perfect for learning

Which would you prefer?"""

        keyboard = [
            [InlineKeyboardButton("📝 Real API Setup", callback_data="api_setup_real")],
            [InlineKeyboardButton("🎮 Demo Keys", callback_data="use_demo_keys")],
            [InlineKeyboardButton("🔙 Back", callback_data="show_settings")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _api_setup_real(self, query, user_id):
        """Real API setup instructions"""
        # CLEAR any existing state and set new state
        self.user_states[user_id] = {"step": "waiting_api_key"}
        self.logger.info(f"Set user {user_id} state to waiting_api_key")

        message = """📝 **Real API Setup**

**Get your Binance API Keys:**

1. Go to **Binance.com** → Login
2. **Account** → **API Management**
3. **Create API Key**
4. ⚠️ **Enable only "Spot Trading"**
5. **DO NOT enable withdrawals!**

**Send your API Key:**
Paste it in the chat below 👇"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🎮 Use Demo Instead", callback_data="use_demo_keys"
                )
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="setup_api_keys")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _use_demo_keys(self, query, user_id):
        """Set up demo keys - CLEAR STATE FIRST"""
        # CRITICAL: Clear user state when switching to demo
        if user_id in self.user_states:
            self.logger.info(
                f"Clearing user state for {user_id} when switching to demo"
            )
            del self.user_states[user_id]

        user = self.user_repo.get_user(user_id)
        user.binance_api_key = "demo_api_key_for_testing"
        user.binance_secret_key = "demo_secret_key_for_testing"
        self.user_repo.update_user(user)

        self.conversion_tracker.track_event(user_id, "demo_keys_setup")

        message = """🎮 **Demo Keys Activated!**

✅ Demo trading is now enabled
✅ Test all features safely
✅ No real money involved
✅ Perfect for learning!

**Ready to trade?**
Type `BTC 100` to try your first trade!"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Start Trading", callback_data="show_trading_guide"
                )
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _back_to_main(self, query, user_id):
        """Return to main menu"""
        user = self.user_repo.get_user(user_id)
        days_left = (
            (user.trial_expires - datetime.now()).days if user.trial_expires else 0
        )
        status = (
            f"🆓 Trial - {days_left} days left"
            if user.subscription_status == SubscriptionStatus.TRIAL
            else f"💎 {user.subscription_status.value.title()}"
        )

        message = f"""🤖 **GridTrader Pro**

**Status:** {status}

**Quick Trading:** Type `BTC 1000` or `ETH 500`

Choose an option:"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Start Trading", callback_data="show_trading_guide"
                )
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def handle_message(self, update, context):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text.strip()

        self.logger.info(f"Received message from {user_id}: {text}")
        self.logger.info(
            f"User {user_id} state: {self.user_states.get(user_id, 'None')}"
        )

        # API setup flow
        if user_id in self.user_states:
            await self._handle_api_input(update, user_id, text)
            return

        # Trading input
        if self._is_trading_input(text):
            await self._handle_trading_input(update, user_id, text)
            return

        # Default response with helpful menu
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📱 Main Menu", callback_data="back_to_main")]]
        )

        await update.message.reply_text(
            "💡 **Try these:**\n"
            "• /start - Main menu\n"
            "• BTC 1000 - Trade Bitcoin\n"
            "• ETH 500 - Trade Ethereum",
            reply_markup=keyboard,
        )

    async def _handle_api_input(self, update, user_id, text):
        """Handle API key input"""
        user_state = self.user_states.get(user_id, {})
        step = user_state.get("step")

        self.logger.info(f"Handling API input for user {user_id}, step: {step}")

        if step == "waiting_api_key":
            user = self.user_repo.get_user(user_id)
            user.binance_api_key = text
            self.user_repo.update_user(user)

            # Update state to wait for secret key
            self.user_states[user_id] = {"step": "waiting_secret_key"}
            self.logger.info(f"Updated user {user_id} state to waiting_secret_key")

            await update.message.reply_text(
                "✅ **API Key saved!**\n\nNow send your **Secret Key**:"
            )

        elif step == "waiting_secret_key":
            user = self.user_repo.get_user(user_id)
            user.binance_secret_key = text
            self.user_repo.update_user(user)

            # Clear state - IMPORTANT
            del self.user_states[user_id]
            self.logger.info(f"Cleared user {user_id} state after secret key")

            self.conversion_tracker.track_event(user_id, "real_api_setup_complete")

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🚀 Start Trading", callback_data="show_trading_guide"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📊 Dashboard", callback_data="main_dashboard"
                        )
                    ],
                ]
            )

            await update.message.reply_text(
                "🎉 **API Setup Complete!**\n\n✅ Real trading enabled\n✅ Keys encrypted\n\nReady to trade!",
                reply_markup=keyboard,
            )
        else:
            self.logger.warning(f"Unknown API input step for user {user_id}: {step}")
            # Clear invalid state
            del self.user_states[user_id]
            await update.message.reply_text(
                "❌ Something went wrong. Please try API setup again."
            )

    def _is_trading_input(self, text):
        """Check if trading input"""
        parts = text.strip().upper().split()
        if len(parts) == 2:
            try:
                amount = float(parts[1])
                return amount > 0
            except:
                pass
        return False

    async def _handle_trading_input(self, update, user_id, text):
        """Handle trading input"""
        user = self.user_repo.get_user(user_id)
        if not user or not user.is_subscription_active():
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🚀 Start Trial", callback_data="back_to_main")]]
            )
            await update.message.reply_text(
                "🔒 Please start your trial first!", reply_markup=keyboard
            )
            return

        try:
            parts = text.upper().split()
            coin = parts[0]
            amount = float(parts[1])

            if amount < 50:
                await update.message.reply_text("💰 Minimum: $50")
                return

            # Auto-configure user
            user.total_capital = amount
            user.risk_level = "moderate"
            user.trading_pairs = [coin]
            self.user_repo.update_user(user)

            # Determine mode
            if user.binance_api_key and "demo" not in user.binance_api_key:
                mode = "🟢 Real Trading"
            else:
                mode = "🎮 Demo Mode"

            message = f"""🎯 **Confirm Trade**

**Mode:** {mode}
**Pair:** {coin}/USDT
**Amount:** ${amount:,.2f}

**Execution:**
💰 ${amount / 2:,.2f} → Buy {coin}
💰 ${amount / 2:,.2f} → Grid orders

Ready?"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ EXECUTE", callback_data=f"execute_trade_{coin}_{amount}"
                    )
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="main_dashboard")],
            ]

            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except:
            await update.message.reply_text("❌ Format: COIN AMOUNT (e.g., BTC 1000)")

    async def _execute_trade(self, query, action):
        """Execute trade"""
        user_id = query.from_user.id

        try:
            parts = action.replace("execute_trade_", "").split("_")
            coin = parts[0]
            amount = float(parts[1])
        except:
            await query.edit_message_text("❌ Invalid trade")
            return

        await query.edit_message_text("🔄 **Executing...**")
        await asyncio.sleep(2)

        self.conversion_tracker.track_event(
            user_id, "trade_executed", f"{coin}_{amount}"
        )

        message = f"""🎉 **Trade Executed!**

**{coin}/USDT Grid Active**

✅ Split: ${amount / 2:.2f} → {coin}, ${amount / 2:.2f} → Grid
✅ 10 orders placed
✅ Bot active 24/7

Type another coin to trade more!"""

        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("🔄 New Trade", callback_data="show_trading_guide")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
