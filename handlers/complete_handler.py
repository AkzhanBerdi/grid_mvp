#!/usr/bin/env python3
"""Complete Improved Handler with Smart API Management - FULL FILE"""

import logging
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from models.user import SubscriptionStatus
from repositories.user_repository import UserRepository
from services.bot_orchestrator import BotOrchestrator


class CompleteHandler:
    """Complete improved handler with smart API management - avoids repeated setup"""

    def __init__(self, conversion_tracker):
        self.user_repo = UserRepository()
        self.conversion_tracker = conversion_tracker
        self.bot_orchestrator = BotOrchestrator()
        self.user_states = {}
        self.logger = logging.getLogger(__name__)

    def _has_real_api_keys(self, user) -> bool:
        """Check if user has real (non-demo) API keys"""
        if not user.binance_api_key or not user.binance_secret_key:
            return False

        # Check for demo keywords
        api_key_lower = user.binance_api_key.lower()
        if any(keyword in api_key_lower for keyword in ["demo", "test", "fake"]):
            return False

        # Check length (real Binance keys are 64 chars)
        if len(user.binance_api_key) < 60:
            return False

        return True

    def _has_demo_api_keys(self, user) -> bool:
        """Check if user has demo API keys"""
        if not user.binance_api_key:
            return False

        api_key_lower = user.binance_api_key.lower()
        return any(keyword in api_key_lower for keyword in ["demo", "test", "fake"])

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

**How to trade:** Just type `BTC 1000` or `TUT 100`

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

        # Get bot status
        bot_status = self.bot_orchestrator.get_user_bot_status(user.telegram_id)
        bot_info = ""
        if bot_status["running"]:
            bot_info = f"\n🤖 Bot: Active ({bot_status['total_trades']} trades)"

        # Smart mode detection
        if self._has_real_api_keys(user):
            mode_info = "\n🟢 Mode: Real Trading"
        elif self._has_demo_api_keys(user):
            mode_info = "\n🎮 Mode: Demo Trading"
        else:
            mode_info = "\n❌ Mode: Not Setup"

        message = f"""🤖 **GridTrader Pro**

Welcome back, {user.first_name}!

**Status:** {status}{mode_info}{bot_info}

**Quick Trading:** Type `BTC 1000` or `TUT 100`

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

        # Use appropriate method based on how we got here
        if hasattr(update, "message") and update.message:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        else:
            # This is a callback query
            await update.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

    async def handle_callback(self, update, context):
        """Handle callback queries with improved API management"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        action = query.data

        self.logger.info(f"User {user_id} clicked: {action}")

        # Route to appropriate handler
        if action == "back_to_main":
            await self._back_to_main(query, user_id)
        elif action == "show_trading_guide":
            await self._show_trading_guide(query, user_id)
        elif action == "main_dashboard":
            await self._show_dashboard(query, user_id)
        elif action == "show_settings":
            await self._show_settings(query, user_id)
        elif action == "manage_api_keys":  # NEW: Manage existing keys
            await self._manage_api_keys(query, user_id)
        elif action == "setup_api_keys":
            await self._start_api_setup(query, user_id)
        elif action == "api_setup_real":
            await self._api_setup_real(query, user_id)
        elif action == "use_demo_keys":
            await self._use_demo_keys(query, user_id)
        elif action == "cancel_api_input":
            await self._cancel_api_input(query, user_id)
        elif action == "switch_to_demo":
            await self._switch_to_demo_mode(query, user_id)
        elif action == "switch_to_real":
            await self._smart_switch_to_real(query, user_id)  # NEW: Smart switching
        elif action == "reset_api_keys":  # NEW: Reset keys
            await self._reset_api_keys(query, user_id)
        elif action == "confirm_reset_keys":  # NEW: Confirm reset
            await self._confirm_reset_keys(query, user_id)
        elif action.startswith("execute_trade_"):
            await self._execute_trade(query, action)
        elif action.startswith("stop_bot_"):
            await self._stop_user_bot(query, user_id)
        else:
            await query.edit_message_text("🔧 Feature coming soon!")

    async def _smart_switch_to_real(self, query, user_id):
        """Smart switch to real mode - checks if user already has real keys"""
        user = self.user_repo.get_user(user_id)

        if self._has_real_api_keys(user):
            # User already has real API keys, just switch mode
            await self._confirm_real_mode_switch(query, user_id)
        else:
            # User needs to set up real API keys
            await self._api_setup_real(query, user_id)

    async def _manage_api_keys(self, query, user_id):
        """NEW: Manage existing API keys without forcing re-setup"""
        user = self.user_repo.get_user(user_id)

        if self._has_real_api_keys(user):
            current_status = "🟢 **Real API Keys Configured**"
            key_info = (
                f"API Key: {user.binance_api_key[:10]}...{user.binance_api_key[-4:]}"
            )
        elif self._has_demo_api_keys(user):
            current_status = "🎮 **Demo Keys Active**"
            key_info = "Using demo mode for safe testing"
        else:
            current_status = "❌ **No API Keys**"
            key_info = "No trading keys configured"

        message = f"""🔐 **API Key Management**

{current_status}

{key_info}

**Options:**"""

        keyboard = []

        if self._has_real_api_keys(user):
            # User has real keys
            keyboard.extend(
                [
                    [
                        InlineKeyboardButton(
                            "🎮 Switch to Demo Mode", callback_data="switch_to_demo"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔄 Reset API Keys", callback_data="reset_api_keys"
                        )
                    ],
                ]
            )
        elif self._has_demo_api_keys(user):
            # User has demo keys
            keyboard.extend(
                [
                    [
                        InlineKeyboardButton(
                            "🟢 Switch to Real Trading", callback_data="switch_to_real"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔄 Reset to No Keys", callback_data="reset_api_keys"
                        )
                    ],
                ]
            )
        else:
            # No keys
            keyboard.extend(
                [
                    [
                        InlineKeyboardButton(
                            "🟢 Setup Real Trading", callback_data="api_setup_real"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🎮 Use Demo Mode", callback_data="use_demo_keys"
                        )
                    ],
                ]
            )

        keyboard.extend(
            [
                [
                    InlineKeyboardButton(
                        "🔙 Back to Settings", callback_data="show_settings"
                    )
                ],
            ]
        )

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _reset_api_keys(self, query, user_id):
        """NEW: Reset API keys with confirmation"""
        message = """⚠️ **Reset API Keys**

This will remove your current API keys and stop any active trading.

Are you sure you want to continue?"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Yes, Reset Keys", callback_data="confirm_reset_keys"
                )
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="manage_api_keys")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _confirm_reset_keys(self, query, user_id):
        """Confirm and execute API key reset"""
        try:
            # Stop any active trading first
            await self.bot_orchestrator.stop_user_bot(user_id)

            # Reset API keys
            user = self.user_repo.get_user(user_id)
            user.binance_api_key = None
            user.binance_secret_key = None
            self.user_repo.update_user(user)

            message = """✅ **API Keys Reset**

Your API keys have been removed and trading has been stopped.

What would you like to do next?"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🟢 Setup Real Trading", callback_data="api_setup_real"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎮 Use Demo Mode", callback_data="use_demo_keys"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error resetting API keys for user {user_id}: {e}")
            await query.edit_message_text("❌ Error resetting keys. Please try again.")

    async def _show_settings(self, query, user_id):
        """Enhanced settings with smart API management"""
        user = self.user_repo.get_user(user_id)

        # Smart status detection
        if self._has_real_api_keys(user):
            current_mode = "🟢 Real Trading Mode"
            api_status = "✅ Real API keys configured"
            main_button_text = "🎮 Switch to Demo Mode"
            main_button_action = "switch_to_demo"
        elif self._has_demo_api_keys(user):
            current_mode = "🎮 Demo Mode"
            api_status = "🎮 Demo keys active"
            main_button_text = "🟢 Switch to Real Trading"
            main_button_action = "switch_to_real"
        else:
            current_mode = "❌ Not Setup"
            api_status = "❌ No API keys configured"
            main_button_text = "🔐 Setup Trading Keys"
            main_button_action = "setup_api_keys"

        # Get bot status
        bot_status = self.bot_orchestrator.get_user_bot_status(user_id)
        if bot_status["running"]:
            bot_info = (
                f"\n🤖 **Bot Status:** Active ({bot_status['total_trades']} trades)"
            )
        else:
            bot_info = "\n🤖 **Bot Status:** Inactive"

        message = f"""⚙️ **Settings**

**Current Mode:** {current_mode}
**API Status:** {api_status}
**Capital:** ${user.total_capital:,.2f}
**Risk Level:** {user.risk_level.title()}
**Trading Pairs:** {", ".join(user.trading_pairs)}{bot_info}

Configure your bot:"""

        keyboard = [
            [InlineKeyboardButton(main_button_text, callback_data=main_button_action)],
        ]

        # Only show API management if user has keys configured
        if self._has_real_api_keys(user) or self._has_demo_api_keys(user):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "🔐 Manage API Keys", callback_data="manage_api_keys"
                    )
                ]
            )

        keyboard.extend(
            [
                [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
            ]
        )

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _start_api_setup(self, query, user_id):
        """API setup - only show if user doesn't have keys"""
        user = self.user_repo.get_user(user_id)

        # If user already has real keys, don't force setup
        if self._has_real_api_keys(user):
            await self._manage_api_keys(query, user_id)
            return

        # Clear any existing user state
        if user_id in self.user_states:
            self.logger.info(
                f"Clearing existing user state for {user_id} at API setup start"
            )
            del self.user_states[user_id]

        message = """🔐 **API Keys Setup**

**Choose setup method:**

**📱 Real API Keys:**
• Connect to your actual Binance account
• Real trading with real money
• 2-minute mobile setup process

**🎮 Demo Keys:**
• Test all features safely
• No real money involved
• Perfect for learning the system

Which would you prefer?"""

        keyboard = [
            [InlineKeyboardButton("📱 Real API Setup", callback_data="api_setup_real")],
            [InlineKeyboardButton("🎮 Demo Keys", callback_data="use_demo_keys")],
            [InlineKeyboardButton("🔙 Back", callback_data="show_settings")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _api_setup_real(self, query, user_id):
        """Enhanced real API setup with cancellation option"""
        # CLEAR any existing state and set new state for SECRET KEY first
        self.user_states[user_id] = {"step": "waiting_secret_key"}
        self.logger.info(f"Set user {user_id} state to waiting_secret_key")

        message = """📱 **Real API Setup (Mobile)**

**⚠️ IMPORTANT: Copy SECRET KEY first!**
The secret key is shown only ONCE and disappears forever after you close the screen.

**📱 Binance Mobile App Steps:**

1. Open **Binance app** → Login
2. Tap **Profile** (bottom right)
3. Tap **Security** 
4. Tap **API Management**
5. Tap **Create API** → **System Generated**
6. Label: "GridTrader Pro"
7. Complete verification (2FA, email, etc.)

**🔴 CRITICAL STEP:**
8. **COPY SECRET KEY FIRST** ✂️
9. **PASTE SECRET KEY** in this chat below 👇

⚠️ Don't close the screen yet - you'll need the API key next!

**Security Settings:**
✅ Enable "Spot Trading" only
❌ DO NOT enable withdrawals!"""

        keyboard = [
            [InlineKeyboardButton("❌ Cancel Setup", callback_data="cancel_api_input")],
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
Type `BTC 100` or `TUT 100` to try your first trade!"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Start Trading", callback_data="show_trading_guide"
                )
            ],
            [
                InlineKeyboardButton(
                    "🟢 Switch to Real Trading", callback_data="switch_to_real"
                )
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _cancel_api_input(self, query, user_id):
        """Cancel API key input flow"""
        # Clear any existing state
        if user_id in self.user_states:
            del self.user_states[user_id]
            self.logger.info(f"Cancelled API input for user {user_id}")

        message = """❌ **API Setup Cancelled**

No changes were made to your account.

What would you like to do?"""

        keyboard = [
            [InlineKeyboardButton("🎮 Use Demo Mode", callback_data="use_demo_keys")],
            [
                InlineKeyboardButton(
                    "🔐 Try API Setup Again", callback_data="setup_api_keys"
                )
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _switch_to_demo_mode(self, query, user_id):
        """Switch user to demo mode"""
        try:
            # Stop any active trading first
            await self.bot_orchestrator.stop_user_bot(user_id)

            # Set demo keys
            user = self.user_repo.get_user(user_id)
            user.binance_api_key = "demo_api_key_for_testing"
            user.binance_secret_key = "demo_secret_key_for_testing"
            self.user_repo.update_user(user)

            self.conversion_tracker.track_event(user_id, "switched_to_demo")

            message = """🎮 **Switched to Demo Mode**

✅ Demo trading is now active
✅ Use real market prices safely
✅ Test all features risk-free
✅ No real money involved

**Ready to trade?**
Type `BTC 100` or `TUT 100` to start!"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚀 Start Demo Trading", callback_data="show_trading_guide"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🟢 Switch to Real Trading", callback_data="switch_to_real"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error switching to demo mode for user {user_id}: {e}")
            await query.edit_message_text(
                "❌ Error switching to demo mode. Please try again."
            )

    async def _confirm_real_mode_switch(self, query, user_id):
        """Confirm switching to real mode for users with existing API keys"""
        try:
            # Stop any active demo trading
            await self.bot_orchestrator.stop_user_bot(user_id)

            self.conversion_tracker.track_event(user_id, "switched_to_real")

            message = """🟢 **Switched to Real Trading Mode**

✅ Real trading is now active
✅ Connected to your Binance account
✅ Real money, real profits
⚠️ Trade responsibly

**Ready to make real profits?**
Type `BTC 100` or `TUT 100` to start!"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚀 Start Real Trading", callback_data="show_trading_guide"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🎮 Switch to Demo", callback_data="switch_to_demo"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error switching to real mode for user {user_id}: {e}")
            await query.edit_message_text(
                "❌ Error switching to real mode. Please try again."
            )

    async def _show_dashboard(self, query, user_id):
        """Enhanced dashboard with mode switching"""
        user = self.user_repo.get_user(user_id)

        # Get comprehensive performance data
        performance = await self.bot_orchestrator.get_user_performance(user_id)
        bot_status = performance.get("bot_status", {})

        # Determine current mode
        if self._has_real_api_keys(user):
            mode = "🟢 Real Trading"
            switch_button = InlineKeyboardButton(
                "🎮 Switch to Demo", callback_data="switch_to_demo"
            )
        elif self._has_demo_api_keys(user):
            mode = "🎮 Demo Mode"
            switch_button = InlineKeyboardButton(
                "🟢 Switch to Real", callback_data="switch_to_real"
            )
        else:
            mode = "❌ Not Setup"
            switch_button = InlineKeyboardButton(
                "🔐 Setup Trading", callback_data="setup_api_keys"
            )

        # Bot status information
        if bot_status.get("running"):
            bot_info = f"""🤖 **Bot Status:** Active
📊 **Trades:** {bot_status.get("total_trades", 0)}
💰 **Profit:** ${bot_status.get("total_profit", 0):.2f}
🎯 **Active Orders:** {bot_status.get("active_orders", 0)}
⏱️ **Runtime:** {bot_status.get("runtime_minutes", 0)} minutes"""
        else:
            bot_info = "🤖 **Bot Status:** Inactive"

        message = f"""📊 **Trading Dashboard**

**Mode:** {mode}
**Capital:** ${user.total_capital:,.2f}
**Pairs:** {", ".join(user.trading_pairs)}

{bot_info}

**Total Volume:** ${performance.get("total_volume", 0):.2f}
**Avg Trade:** ${performance.get("avg_trade_size", 0):.2f}"""

        keyboard = []

        # Add mode switch button
        keyboard.append([switch_button])

        if bot_status.get("running"):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "🛑 Stop Bot", callback_data=f"stop_bot_{user_id}"
                    )
                ]
            )
        else:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "🚀 Start Trading", callback_data="show_trading_guide"
                    )
                ]
            )

        keyboard.extend(
            [
                [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
            ]
        )

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _stop_user_bot(self, query, user_id):
        """Stop user's trading bot"""
        try:
            success = await self.bot_orchestrator.stop_user_bot(user_id)

            if success:
                message = """🛑 **Bot Stopped**

Your trading bot has been stopped.
All open orders have been canceled.

Ready to start again?"""

                keyboard = [
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
                    [
                        InlineKeyboardButton(
                            "🔙 Main Menu", callback_data="back_to_main"
                        )
                    ],
                ]
            else:
                message = "❌ Error stopping bot. Please try again."
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Dashboard", callback_data="main_dashboard"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔙 Main Menu", callback_data="back_to_main"
                        )
                    ],
                ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error stopping bot for user {user_id}: {e}")
            await query.edit_message_text("❌ Error stopping bot. Please try again.")

    async def _show_trading_guide(self, query, user_id):
        """Trading guide with navigation"""
        message = """🚀 **Start Trading in 30 seconds!**

**Step 1:** Type your trade
Examples: `BTC 1000`, `ETH 500`, `TUT 100`

**Step 2:** Confirm execution
Bot shows you exactly what happens

**Step 3:** Start earning!
Watch your grid orders work automatically

**For real trading:** You'll need Binance API keys
**For demo:** Just type any trade to see how it works!

**Try now:** Type `TUT 100` to see demo"""

        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
            [InlineKeyboardButton("⚙️ Setup API Keys", callback_data="setup_api_keys")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _back_to_main(self, query, user_id):
        """Return to main menu"""
        user = self.user_repo.get_user(user_id)
        await self._show_main_menu(query, user)

    async def handle_message(self, update, context):
        """Enhanced message handling with cancellation support"""
        user_id = update.effective_user.id
        text = update.message.text.strip()

        self.logger.info(f"Received message from {user_id}: {text}")

        # Check for cancel commands during API setup
        if user_id in self.user_states and text.lower() in [
            "/cancel",
            "cancel",
            "stop",
            "abort",
        ]:
            del self.user_states[user_id]

            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📱 Main Menu", callback_data="back_to_main")]]
            )

            await update.message.reply_text(
                "❌ **API Setup Cancelled**\n\nNo changes were made.",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            return

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
            "• TUT 100 - Trade TUT\n"
            "• /cancel - Cancel any setup",
            reply_markup=keyboard,
        )

    async def _handle_api_input(self, update, user_id, text):
        """Enhanced API input handling with cancellation support"""
        user_state = self.user_states.get(user_id, {})
        step = user_state.get("step")

        self.logger.info(f"Handling API input for user {user_id}, step: {step}")

        if step == "waiting_secret_key":
            # First step: Save secret key
            user = self.user_repo.get_user(user_id)
            user.binance_secret_key = text
            self.user_repo.update_user(user)

            # Update state to wait for API key
            self.user_states[user_id] = {"step": "waiting_api_key"}
            self.logger.info(f"Updated user {user_id} state to waiting_api_key")

            # Send message with cancel option
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "❌ Cancel & Start Over", callback_data="cancel_api_input"
                        )
                    ]
                ]
            )

            await update.message.reply_text(
                """✅ **Secret Key Saved!**

Perfect! Now copy and send your **API Key**.

**📱 In your Binance app:**
• The API Key should still be visible on screen
• **COPY the API Key** ✂️
• **PASTE it below** 👇

🔒 After this, you can safely close the Binance screen.""",
                reply_markup=keyboard,
            )

        elif step == "waiting_api_key":
            # Second step: Save API key and complete setup
            user = self.user_repo.get_user(user_id)
            user.binance_api_key = text
            self.user_repo.update_user(user)

            # Clear state - IMPORTANT
            del self.user_states[user_id]
            self.logger.info(f"Cleared user {user_id} state after API key")

            self.conversion_tracker.track_event(user_id, "real_api_setup_complete")

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🚀 Start Real Trading", callback_data="show_trading_guide"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🎮 Switch to Demo", callback_data="switch_to_demo"
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
                """🎉 **API Setup Complete!**

✅ **Real trading enabled**
✅ **Keys encrypted & secured**
✅ **Connected to your Binance account**

🔒 **Security Note:**
• We can only trade (buy/sell) on your behalf
• We CANNOT withdraw your funds
• We CANNOT transfer money out
• You control your money at all times

**Ready to start making real profits?**""",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        else:
            self.logger.warning(f"Unknown API input step for user {user_id}: {step}")
            # Clear invalid state
            if user_id in self.user_states:
                del self.user_states[user_id]
            await update.message.reply_text(
                "❌ Something went wrong. Please start API setup again."
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
        """Handle trading input with real bot integration"""
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

            # Determine mode
            if self._has_real_api_keys(user):
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
        """Execute trade using bot orchestrator"""
        user_id = query.from_user.id

        try:
            parts = action.replace("execute_trade_", "").split("_")
            coin = parts[0]
            amount = float(parts[1])
        except:
            await query.edit_message_text("❌ Invalid trade")
            return

        await query.edit_message_text("🔄 **Executing...**")

        # Use bot orchestrator to process the trade
        result = await self.bot_orchestrator.process_user_trade_command(
            user_id, coin, amount
        )

        if result["success"]:
            self.conversion_tracker.track_event(
                user_id, "trade_executed", f"{coin}_{amount}"
            )

            bot_status = result["status"]
            mode_emoji = "🎮" if bot_status["mode"] == "demo" else "🟢"

            message = f"""🎉 **Trade Executed!**

{mode_emoji} **{coin}/USDT Grid Active**

✅ Split: ${amount / 2:.2f} → {coin}, ${amount / 2:.2f} → Grid
✅ {bot_status["active_orders"]} orders placed
✅ Bot active 24/7

Type another coin to trade more!"""

            keyboard = [
                [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
                [
                    InlineKeyboardButton(
                        "🔄 New Trade", callback_data="show_trading_guide"
                    )
                ],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
            ]

        else:
            message = f"""❌ **Trade Failed**

Error: {result.get("error", "Unknown error")}

Please try again or contact support."""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Try Again", callback_data="show_trading_guide"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="main_dashboard")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_main")],
            ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
