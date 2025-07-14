# handlers/client_handler.py
"""Complete Client Handler for GridTrader Pro"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from repositories.client_repository import ClientRepository
from utils.validators import Validators


class ClientHandler:
    """Complete handler for paying clients"""

    def __init__(self, grid_orchestrator):
        self.client_repo = ClientRepository()
        self.grid_orchestrator = grid_orchestrator
        self.client_states = {}  # Track client input states
        self.logger = logging.getLogger(__name__)

    async def handle_start(self, update, context):
        """Handle /start command"""
        user = update.effective_user
        client = self.client_repo.get_client(user.id)

        if client and client.is_active():
            await self._show_client_dashboard(update, client)
        else:
            await self._handle_new_client(update, user)

    async def _handle_new_client(self, update, user):
        """Handle new client registration"""
        client = self.client_repo.create_client(
            telegram_id=user.id, username=user.username, first_name=user.first_name
        )

        message = f"""🤖 **Welcome to GridTrader Pro**

Hi {user.first_name}! Welcome to professional grid trading.

**What you get:**
✅ Real-time grid trading on Binance
✅ ADA & AVAX pairs (more coming soon)
✅ Automated profit generation
✅ Professional risk management

**To start trading:**
1. Set up your Binance API keys
2. Configure your trading capital
3. Start earning profits!

Ready to begin?"""

        keyboard = [
            [InlineKeyboardButton("🔐 Setup API Keys", callback_data="setup_api")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
        ]

        await update.message.reply_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_client_dashboard(self, update, client):
        """Show client dashboard"""
        # Get grid status
        grid_status = self.grid_orchestrator.get_client_grid_status(client.telegram_id)

        # API setup status
        api_status = "✅ Connected" if client.binance_api_key else "❌ Not Setup"

        # Active grids info
        if grid_status and grid_status.get("active_grids"):
            active_info = f"\n🤖 Active Grids: {len(grid_status['active_grids'])}"
            total_trades = sum(
                g.get("total_trades", 0) for g in grid_status["active_grids"].values()
            )
            total_profit = sum(
                g.get("total_profit", 0) for g in grid_status["active_grids"].values()
            )
            active_info += f"\n📊 Total Trades: {total_trades}"
            active_info += f"\n💰 Total Profit: ${total_profit:.2f}"
        else:
            active_info = "\n🤖 No active grids"

        message = f"""📊 **GridTrader Pro Dashboard**

Welcome back, {client.first_name}!

**Account Status:**
🔐 API Keys: {api_status}
💰 Capital: ${client.total_capital:,.2f}
⚙️ Pairs: {", ".join(client.trading_pairs)}
📈 Risk Level: {client.risk_level.title()}{active_info}

**Quick Trading:** Type `ADA 1000` or `AVAX 500`"""

        keyboard = []

        if client.can_start_grid():
            if grid_status and grid_status.get("active_grids"):
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🛑 Stop Trading", callback_data="stop_all_grids"
                        )
                    ]
                )
            else:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🚀 Start Trading", callback_data="start_trading"
                        )
                    ]
                )

        keyboard.extend(
            [
                [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
                [
                    InlineKeyboardButton(
                        "📈 Performance", callback_data="show_performance"
                    )
                ],
            ]
        )

        # Use appropriate method based on context
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

    async def handle_callback(self, update, context):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()

        client_id = query.from_user.id
        action = query.data

        self.logger.info(f"Client {client_id} action: {action}")

        # Route to appropriate handler
        if action == "setup_api":
            await self._setup_api_keys(query, client_id)
        elif action == "show_dashboard":
            await self._back_to_dashboard(query, client_id)
        elif action == "show_settings":
            await self._show_settings(query, client_id)
        elif action == "show_performance":
            await self._show_performance(query, client_id)
        elif action == "start_trading":
            await self._start_trading(query, client_id)
        elif action == "stop_all_grids":
            await self._stop_all_grids(query, client_id)
        elif action == "cancel_input":
            await self._cancel_input(query, client_id)
        elif action == "set_capital":
            await self._set_capital(query, client_id)
        elif action == "confirm_start_trading":  # ADD THIS
            await self._confirm_start_trading(query, client_id)
        elif action.startswith("execute_trade_"):
            await self._execute_trade(query, action)
        else:
            await query.edit_message_text(f"🔧 Feature: {action} - Coming soon!")

    # ADD THIS NEW METHOD
    async def _confirm_start_trading(self, query, client_id):
        """Confirm and start trading for all configured pairs"""
        await query.edit_message_text("🔄 **Starting Grid Trading...**")

        try:
            client = self.client_repo.get_client(client_id)
            if not client or not client.can_start_grid():
                await query.edit_message_text(
                    "❌ **Cannot Start Trading**\n\n"
                    "Please ensure your API keys and capital are configured."
                )
                return

            results = []
            successful_grids = 0

            # Start grids for each trading pair
            for pair in client.trading_pairs:
                # Calculate capital per pair
                capital_per_pair = client.total_capital / len(client.trading_pairs)

                self.logger.info(
                    f"Starting grid for {pair} with ${capital_per_pair:.2f}"
                )

                result = await self.grid_orchestrator.start_client_grid(
                    client_id, pair, capital_per_pair
                )

                results.append(
                    {"pair": pair, "success": result["success"], "result": result}
                )

                if result["success"]:
                    successful_grids += 1

            # Format response based on results
            if successful_grids == len(client.trading_pairs):
                # All grids started successfully
                grid_info = []
                total_orders = 0

                for res in results:
                    if res["success"]:
                        status = res["result"]["status"]
                        orders = status.get("total_orders", 0)
                        total_orders += orders
                        grid_info.append(f"✅ {res['pair']}: {orders} orders")

                message = f"""🎉 **Grid Trading Started!**

✅ **All grids active for {client.first_name}!**

**Grids Summary:**
{chr(10).join(grid_info)}

📊 **Total Orders:** {total_orders}
💰 **Total Capital:** ${client.total_capital:,.2f}
🤖 **Status:** Active 24/7

Your grids will automatically trade when prices move!"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Dashboard", callback_data="show_dashboard"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📈 Performance", callback_data="show_performance"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🛑 Stop All Grids", callback_data="stop_all_grids"
                        )
                    ],
                ]

            elif successful_grids > 0:
                # Some grids started
                success_pairs = [res["pair"] for res in results if res["success"]]
                failed_pairs = [res["pair"] for res in results if not res["success"]]

                message = f"""⚠️ **Partial Grid Start**

✅ **Started:** {", ".join(success_pairs)}
❌ **Failed:** {", ".join(failed_pairs)}

Check your API permissions and account balance."""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Dashboard", callback_data="show_dashboard"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔄 Retry Failed", callback_data="start_trading"
                        )
                    ],
                ]

            else:
                # No grids started
                error_messages = [
                    res["result"].get("error", "Unknown error")
                    for res in results
                    if not res["success"]
                ]
                first_error = error_messages[0] if error_messages else "Unknown error"

                message = f"""❌ **Grid Start Failed**

Error: {first_error}

Please check:
• API key permissions (Spot Trading enabled)
• Account balance (sufficient USDT)
• Network connection"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔄 Try Again", callback_data="start_trading"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⚙️ Check Settings", callback_data="show_settings"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📊 Dashboard", callback_data="show_dashboard"
                        )
                    ],
                ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(
                f"Error in confirm_start_trading for client {client_id}: {e}"
            )

            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_trading")],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]

            await query.edit_message_text(
                "❌ **System Error**\n\n"
                "An error occurred while starting trading.\n"
                "Please try again or contact support.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

    async def _setup_api_keys(self, query, client_id):
        """Setup API keys flow"""
        # Clear any existing state
        if client_id in self.client_states:
            del self.client_states[client_id]

        # Set state for API key input
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

        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_input")],
            [InlineKeyboardButton("🔙 Back", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_settings(self, query, client_id):
        """Show client settings"""
        client = self.client_repo.get_client(client_id)

        message = f"""⚙️ **Trading Settings**

**Current Configuration:**
💰 Capital: ${client.total_capital:,.2f}
📈 Risk Level: {client.risk_level.title()}
🎯 Grid Spacing: {client.grid_spacing * 100:.1f}%
📊 Grid Levels: {client.grid_levels}
💵 Order Size: ${client.order_size:.2f}
🔄 Trading Pairs: {", ".join(client.trading_pairs)}

**API Status:**
🔐 API Key: {"✅ Set" if client.binance_api_key else "❌ Not Set"}

Configure your bot:"""

        keyboard = [
            [InlineKeyboardButton("🔐 Update API Keys", callback_data="setup_api")],
            [InlineKeyboardButton("💰 Set Capital", callback_data="set_capital")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_performance(self, query, client_id):
        """Show trading performance"""
        performance = await self.grid_orchestrator.get_client_performance(client_id)

        message = f"""📈 **Trading Performance**

**Overall Statistics:**
📊 Total Trades: {performance.get("total_trades", 0)}
💰 Total Profit: ${performance.get("total_profit", 0):.2f}
📈 Win Rate: {performance.get("win_rate", 0):.1f}%
💵 Total Volume: ${performance.get("total_volume", 0):,.2f}

**Active Grids:**
🤖 Running: {len(performance.get("active_grids", {}))}/2 pairs

**Recent Activity:**
{self._format_recent_trades(performance.get("recent_trades", []))}"""

        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    def _format_recent_trades(self, trades):
        """Format recent trades for display"""
        if not trades:
            return "No recent trades"

        formatted = []
        for trade in trades[:5]:  # Show last 5 trades
            symbol = trade.get("symbol", "UNKNOWN")
            side = trade.get("side", "UNKNOWN")
            profit = trade.get("profit", 0)
            emoji = "🟢" if side == "SELL" else "🔵"
            formatted.append(f"{emoji} {symbol} {side} (+${profit:.2f})")

        return "\n".join(formatted)

    async def _start_trading(self, query, client_id):
        """Start grid trading for client"""
        client = self.client_repo.get_client(client_id)

        if not client.can_start_grid():
            await query.edit_message_text(
                "❌ Cannot start trading. Please ensure:\n"
                "• API keys are configured\n"
                "• Capital is set\n"
                "• Account is active"
            )
            return

        message = f"""🚀 **Start Grid Trading**

Ready to start automated grid trading with:

💰 **Capital:** ${client.total_capital:,.2f}
🎯 **Pairs:** {", ".join(client.trading_pairs)}
📊 **Strategy:** Grid spacing {client.grid_spacing * 100:.1f}%
💵 **Order Size:** ${client.order_size:.2f} per order

**This will:**
• Create grid orders for each pair
• Trade automatically 24/7
• Generate profits from market volatility

Ready to begin?"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ START TRADING", callback_data="confirm_start_trading"
                )
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _set_capital(self, query, client_id):
        """Start capital setting process"""
        # Clear any existing state
        if client_id in self.client_states:
            del self.client_states[client_id]

        # Set state for capital input
        self.client_states[client_id] = {"step": "waiting_capital"}

        message = """💰 **Set Trading Capital**

Please enter the amount you want to use for grid trading.

**Examples:**
• `1000` - $1,000
• `$2500` - $2,500
• `500` - $500

**Requirements:**
• Minimum: $100
• Recommended: $400+ for optimal grid spacing

**Security:** This amount stays in your Binance account. We never handle your funds directly."""

        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_input")],
            [InlineKeyboardButton("🔙 Back", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _cancel_input(self, query, client_id):
        """Cancel any ongoing input"""
        if client_id in self.client_states:
            del self.client_states[client_id]

        await query.edit_message_text(
            "❌ **Input Cancelled**\n\nReturning to dashboard...",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")]]
            ),
        )

    async def _back_to_dashboard(self, query, client_id):
        """Return to dashboard"""
        client = self.client_repo.get_client(client_id)
        await self._show_client_dashboard(query, client)

    async def _stop_all_grids(self, query, client_id):
        """Stop all active grids for client"""
        await query.edit_message_text("🔄 **Stopping all grids...**")

        result = await self.grid_orchestrator.stop_all_client_grids(client_id)

        if result["success"]:
            message = f"""🛑 **All Grids Stopped**

✅ All trading grids have been stopped
✅ {result["orders_cancelled"]} orders cancelled
✅ Positions secured

Your account is now in safe mode."""

        else:
            message = f"""❌ **Error Stopping Grids**

Some grids may still be active.
Error: {result.get("error", "Unknown error")}

Please check manually or contact support."""

        keyboard = [
            [InlineKeyboardButton("🚀 Start Trading", callback_data="start_trading")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def handle_message(self, update, context):
        """Handle text messages"""
        client_id = update.effective_user.id
        text = update.message.text.strip()

        self.logger.info(f"Message from client {client_id}: {text}")

        # Handle API setup flow
        if client_id in self.client_states:
            await self._handle_api_input(update, client_id, text)
            return

        # Handle trading commands
        if self._is_trading_command(text):
            await self._handle_trading_command(update, client_id, text)
            return

        # Default response
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")]]
        )

        await update.message.reply_text(
            "💡 **Quick Commands:**\n"
            "• /start - Main dashboard\n"
            "• ADA 1000 - Trade ADA with $1000\n"
            "• AVAX 500 - Trade AVAX with $500",
            reply_markup=keyboard,
        )

    async def _handle_api_input(self, update, client_id, text):
        """Handle API key input with better error handling"""
        client_state = self.client_states.get(client_id, {})
        step = client_state.get("step")

        self.logger.info(f"Handling API input for client {client_id}, step: {step}")

        if step == "waiting_api_key":
            # Validate API key format
            is_valid, error = Validators.validate_api_key(text)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ {error}\nPlease send a valid API key."
                )
                return

            try:
                # Store temporarily in state
                self.client_states[client_id] = {
                    "step": "waiting_secret_key",
                    "temp_api_key": text,
                }

                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_input")]]
                )

                await update.message.reply_text(
                    "✅ **API Key received!**\n\n"
                    "**Step 2:** Now send your Secret Key\n\n"
                    "🔒 Your keys will be encrypted and secured after both are provided.",
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )

            except Exception as e:
                self.logger.error(f"Error saving API key for client {client_id}: {e}")
                await update.message.reply_text(
                    "❌ Error saving API key. Please try again."
                )

        elif step == "waiting_secret_key":
            # Validate secret key format
            is_valid, error = Validators.validate_api_key(text)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ {error}\nPlease send a valid secret key."
                )
                return

            try:
                # Get both keys
                temp_api_key = client_state.get("temp_api_key")
                secret_key = text

                if not temp_api_key:
                    await update.message.reply_text(
                        "❌ **Setup Error**\n\nAPI key was lost. Please start setup again."
                    )
                    return

                # Save both keys to database (encrypted)
                client = self.client_repo.get_client(client_id)
                client.binance_api_key = temp_api_key
                client.binance_secret_key = secret_key

                update_success = self.client_repo.update_client(client)

                if not update_success:
                    await update.message.reply_text(
                        "❌ **Failed to save API keys**\n\n"
                        "Please try the setup process again."
                    )
                    return

                # Clear state
                del self.client_states[client_id]

                # Test API connection
                self.logger.info(f"Testing API connection for client {client_id}")

                try:
                    connection_test = await self.grid_orchestrator.test_client_api(
                        client_id
                    )

                    if connection_test.get("success", False):
                        keyboard = InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "💰 Set Capital", callback_data="set_capital"
                                    )
                                ],
                                [
                                    InlineKeyboardButton(
                                        "📊 Dashboard", callback_data="show_dashboard"
                                    )
                                ],
                            ]
                        )

                        await update.message.reply_text(
                            "🎉 **API Setup Complete!**\n\n"
                            "✅ Keys saved and encrypted\n"
                            "✅ Connection successful\n"
                            "✅ Ready for trading\n\n"
                            "**Next Step:** Set your trading capital",
                            reply_markup=keyboard,
                            parse_mode="Markdown",
                        )
                    else:
                        error_msg = connection_test.get(
                            "error", "Unknown connection error"
                        )

                        keyboard = InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "🔄 Try Again", callback_data="setup_api"
                                    )
                                ],
                                [
                                    InlineKeyboardButton(
                                        "📊 Dashboard", callback_data="show_dashboard"
                                    )
                                ],
                            ]
                        )

                        await update.message.reply_text(
                            f"⚠️ **API Keys Saved, Connection Issue**\n\n"
                            f"✅ Your keys are saved securely\n"
                            f"❌ Connection test failed: {error_msg}\n\n"
                            f"Please check your API key permissions:\n"
                            f"• Spot Trading must be enabled\n"
                            f"• IP restrictions (if any) must allow your server\n"
                            f"• Keys must be active",
                            reply_markup=keyboard,
                            parse_mode="Markdown",
                        )

                except Exception as api_test_error:
                    self.logger.error(
                        f"API test error for client {client_id}: {api_test_error}"
                    )

                    keyboard = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "💰 Set Capital Anyway", callback_data="set_capital"
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "🔄 Retry Setup", callback_data="setup_api"
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "📊 Dashboard", callback_data="show_dashboard"
                                )
                            ],
                        ]
                    )

                    await update.message.reply_text(
                        "✅ **API Keys Saved Successfully**\n\n"
                        "⚠️ Connection test encountered an error, but your keys are saved.\n\n"
                        "You can proceed to set your capital and the system will test "
                        "the connection when you start trading.",
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                    )

            except Exception as e:
                self.logger.error(
                    f"Error in secret key processing for client {client_id}: {e}"
                )
                if client_id in self.client_states:
                    del self.client_states[client_id]

                await update.message.reply_text(
                    "❌ **Setup Error**\n\n"
                    "There was an error saving your API keys. Please try the setup process again."
                )

        elif step == "waiting_capital":
            # Handle capital input
            is_valid, amount, error = Validators.validate_capital_amount(text)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ {error}\nPlease enter a valid amount (minimum $100)."
                )
                return

            # Save capital
            client = self.client_repo.get_client(client_id)
            client.total_capital = amount
            client.order_size = min(
                50.0, amount / (len(client.trading_pairs) * client.grid_levels)
            )
            self.client_repo.update_client(client)

            # Clear state
            del self.client_states[client_id]

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🚀 Start Trading", callback_data="start_trading"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📊 Dashboard", callback_data="show_dashboard"
                        )
                    ],
                ]
            )

            await update.message.reply_text(
                f"✅ **Capital Set: ${amount:,.2f}**\n\n"
                f"💵 Order size per trade: ${client.order_size:.2f}\n"
                f"📊 Grid levels: {client.grid_levels} per pair\n"
                f"🎯 Trading pairs: {', '.join(client.trading_pairs)}\n\n"
                f"Ready to start automated trading!",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        else:
            # Unknown step, clear state
            if client_id in self.client_states:
                del self.client_states[client_id]
            await update.message.reply_text("❌ Setup error. Please start again.")

    def _is_trading_command(self, text):
        """Check if text is a trading command"""
        parts = text.strip().upper().split()
        if len(parts) == 2:
            try:
                symbol = parts[0]
                amount = float(parts[1])
                return symbol in ["ADA", "AVAX", "BTC", "ETH"] and amount > 0
            except:
                pass
        return False

    async def _handle_trading_command(self, update, client_id, text):
        """Handle trading command like 'ADA 1000'"""
        client = self.client_repo.get_client(client_id)

        if not client or not client.is_active():
            await update.message.reply_text(
                "❌ Please complete your account setup first."
            )
            return

        if not client.can_start_grid():
            await update.message.reply_text(
                "❌ Please set up your API keys and capital first."
            )
            return

        try:
            parts = text.upper().split()
            symbol = parts[0]
            amount = float(parts[1])

            if amount < 100:
                await update.message.reply_text("💰 Minimum trading amount: $100")
                return

            if symbol not in ["ADA", "AVAX"]:
                await update.message.reply_text(
                    f"❌ {symbol} not supported yet. Available: ADA, AVAX"
                )
                return

            message = f"""🎯 **Confirm Grid Trading**

**Symbol:** {symbol}/USDT
**Capital:** ${amount:,.2f}
**Strategy:** Grid trading with {client.grid_spacing * 100:.1f}% spacing

**Execution Plan:**
• Create {client.grid_levels} buy orders below market
• Create {client.grid_levels} sell orders above market
• Order size: ${min(client.order_size, amount / client.grid_levels):.2f} each
• Automatic profit capture on every price move

Ready to execute?"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ EXECUTE", callback_data=f"execute_trade_{symbol}_{amount}"
                    )
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="show_dashboard")],
            ]

            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error handling trading command: {e}")
            await update.message.reply_text(
                "❌ Invalid format. Use: SYMBOL AMOUNT (e.g., ADA 1000)"
            )

    async def _execute_trade(self, query, action):
        """Execute trading command"""
        client_id = query.from_user.id

        try:
            parts = action.replace("execute_trade_", "").split("_")
            symbol = parts[0]
            amount = float(parts[1])
        except:
            await query.edit_message_text("❌ Invalid trade parameters")
            return

        await query.edit_message_text("🔄 **Executing Grid Setup...**")

        # Execute through grid orchestrator
        result = await self.grid_orchestrator.start_client_grid(
            client_id, symbol, amount
        )

        if result["success"]:
            status = result["status"]

            message = f"""🎉 **Grid Trading Started!**

✅ **{symbol}/USDT Grid Active**

📊 **Setup Complete:**
• {status["buy_levels"]} buy orders placed
• {status["sell_levels"]} sell orders placed
• Total orders: {status["total_orders"]}
• Grid center: ${status["center_price"]:.4f}

🤖 **Bot Status:** Active 24/7
💰 **Ready to capture profits!**

Your grid will automatically trade when prices move."""

            keyboard = [
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
                [
                    InlineKeyboardButton(
                        "📈 Performance", callback_data="show_performance"
                    )
                ],
            ]

        else:
            message = f"""❌ **Grid Setup Failed**

Error: {result.get("error", "Unknown error")}

Please check your account and try again."""

            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_trading")],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
