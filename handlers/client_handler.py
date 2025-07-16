# Updated handlers/smart_client_handler.py
# Fix the "Coming soon" buttons by implementing the actual functionality


from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.base_handler import BaseClientHandler


class ClientHandler(BaseClientHandler):
    """Enhanced client handler with smart adaptive trading - FIXED BUTTONS"""

    def __init__(self):
        super().__init__()  # Inherit all base functionality

        # Initialize FIFO service for dashboard integration
        try:
            from services.fifo_service import FIFOService

            self.fifo_service = FIFOService()
        except ImportError:
            self.logger.warning("FIFO service not available")
            self.fifo_service = None

    async def handle_start(self, update, context):
        """Handle /start command with smart trading introduction"""
        user = update.effective_user
        client = self.client_repo.get_client(user.id)

        if client and client.is_active():
            await self._show_smart_dashboard(update, client)
        else:
            await self._handle_new_smart_client(update, user)

    async def _show_smart_dashboard(self, update, client):
        """Smart dashboard with FIFO metrics integration"""
        try:
            # Get grid status (without await - it's not async)
            grid_status = self.grid_orchestrator.get_client_grid_status(
                client.telegram_id
            )

            # Check API keys
            has_api_keys = bool(client.binance_api_key and client.binance_secret_key)
            api_status = "✅ Connected" if has_api_keys else "❌ Not Set"

            # Get FIFO metrics if available - FOR THIS SPECIFIC USER
            fifo_metrics = ""
            if hasattr(self, "fifo_service") and self.fifo_service:
                try:
                    # IMPORTANT: Use client.telegram_id to get metrics for THIS user only
                    self.logger.info(
                        f"Getting FIFO metrics for user {client.telegram_id}"
                    )
                    display_metrics = self.fifo_service.get_display_metrics(
                        client.telegram_id
                    )
                    performance = self.fifo_service.calculate_fifo_performance(
                        client.telegram_id
                    )

                    # Log what we got for debugging
                    self.logger.info(
                        f"FIFO metrics for user {client.telegram_id}: {display_metrics}"
                    )

                    fifo_metrics = f"""
💰 **FIFO Profit Tracking:**
{display_metrics["total_profit_display"]}
Win Rate: {display_metrics["win_rate_display"]}
Efficiency: {display_metrics["efficiency_display"]}
Volume: {display_metrics["volume_display"]}
Trades: {performance.get("total_trades", 0)}"""
                except Exception as e:
                    self.logger.error(
                        f"Error getting FIFO metrics for user {client.telegram_id}: {e}"
                    )
                    fifo_metrics = "\n💰 **Profit:** Calculating..."
            else:
                self.logger.warning("FIFO service not available")
                fifo_metrics = "\n💰 **FIFO service not available**"

            # Active grids info
            active_info = ""
            if grid_status and grid_status.get("active_grids"):
                active_grids = grid_status["active_grids"]
                active_info = f"\n🤖 Active Grids: {len(active_grids)}"
                for symbol, grid_info in active_grids.items():
                    status = grid_info.get("status", "Unknown")
                    active_info += f"\n   {symbol}: {status}"
            else:
                active_info = "\n💤 No active grids"

            message = f"""📊 **GridTrader Pro Smart Dashboard**

**Account Status:**
🔐 API Keys: {api_status}
💰 Capital: ${client.total_capital:,.2f}
⚙️ Pairs: {", ".join(client.trading_pairs) if client.trading_pairs else "Not Set"}
📈 Risk Level: {client.risk_level.title()}{active_info}{fifo_metrics}

**Quick Trading:** Type `ADA 1000` or `AVAX 500`"""

            # Build keyboard - same as BaseClientHandler but with FIFO-enhanced display
            keyboard = []

            # Add trading controls
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

            # Add standard buttons
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

            # Send message
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
            self.logger.error(f"Error showing smart dashboard: {e}")
            # Fallback to base dashboard if FIFO integration fails
            await self.show_base_dashboard(update, client, extra_buttons=None)

    async def handle_callback(self, update, context):
        """Handle callback queries - FIXED to remove placeholder responses"""
        query = update.callback_query
        await query.answer()

        client_id = query.from_user.id
        action = query.data

        self.logger.info(f"Smart client {client_id} action: {action}")

        # Try common handlers first (from BaseClientHandler)
        if await self.handle_common_callbacks(query, client_id, action):
            return

        # Smart-specific actions - IMPLEMENTED
        if action == "show_performance":
            await self._show_performance(query, client_id)
        elif action == "start_trading":
            await self._start_trading(query, client_id)
        elif action.startswith("execute_trade_"):
            await self._execute_trade(query, action)
        else:
            # REMOVED: No more "Coming soon" messages
            await query.edit_message_text(
                "❌ **Unknown Action**\n\nPlease use the dashboard buttons.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📊 Dashboard", callback_data="show_dashboard"
                            )
                        ]
                    ]
                ),
            )

    async def _show_performance(self, query, client_id):
        """Show actual performance data - IMPLEMENTED"""
        try:
            client = self.client_repo.get_client(client_id)

            # Get FIFO performance if service is available
            if hasattr(self, "fifo_service") and self.fifo_service:
                performance = self.fifo_service.calculate_fifo_performance(client_id)
                display_metrics = self.fifo_service.get_display_metrics(client_id)

                message = f"""📈 **Smart Trading Performance**

💰 **Profit Analysis:**
{display_metrics["total_profit_display"]}
Recent 24h: {display_metrics["recent_profit_display"]}

📊 **Trading Statistics:**
Total Volume: {display_metrics["volume_display"]}
Win Rate: {display_metrics["win_rate_display"]}
Efficiency: {display_metrics["efficiency_display"]}
Active Grids: {display_metrics["active_grids_display"]}

🎯 **Performance Summary:**
{display_metrics["performance_summary"]}

🔄 **Compound System:**
Current Multiplier: {display_metrics["multiplier_display"]}
Status: {"🟢 ACTIVE" if performance.get("current_multiplier", 1.0) > 1.0 else "⚪ INACTIVE"}"""

            else:
                # Fallback performance display
                message = f"""📈 **Smart Trading Performance**

💰 **Account Overview:**
Capital: ${client.total_capital:,.2f}
Risk Level: {client.risk_level.title()}
Trading Pairs: {", ".join(client.trading_pairs)}

🤖 **Grid Status:**
Status: {"✅ Ready" if client.can_start_grid() else "❌ Setup Required"}

📊 **Note:** Start trading to see detailed performance metrics."""

            keyboard = [
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")]
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error showing performance: {e}")
            await query.edit_message_text(
                "❌ **Performance data temporarily unavailable.**\n\nPlease try again later.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📊 Dashboard", callback_data="show_dashboard"
                            )
                        ]
                    ]
                ),
            )

    async def _start_trading(self, query, client_id):
        """Start trading functionality - IMPLEMENTED"""
        client = self.client_repo.get_client(client_id)

        if not client.can_start_grid():
            await query.edit_message_text(
                "❌ **Cannot Start Trading**\n\n"
                "Please complete your setup first:\n"
                "• Set up API keys\n"
                "• Configure trading capital",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔐 Setup API Keys", callback_data="setup_api"
                            )
                        ],
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
                ),
                parse_mode="Markdown",
            )
            return

        # Show trading options
        message = f"""🚀 **Start Smart Trading**

**Account Ready:**
💰 Capital: ${client.total_capital:,.2f}
🎯 Risk Level: {client.risk_level.title()}
🔄 Pairs: {", ".join(client.trading_pairs)}

**Available Symbols:**
• ADA/USDT - Cardano
• AVAX/USDT - Avalanche

**Quick Start:**
Choose a symbol and amount, or type a command like `ADA 1000`"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🥇 ADA $500", callback_data="execute_trade_ADA_500"
                ),
                InlineKeyboardButton(
                    "🏔️ AVAX $500", callback_data="execute_trade_AVAX_500"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🥇 ADA $1000", callback_data="execute_trade_ADA_1000"
                ),
                InlineKeyboardButton(
                    "🏔️ AVAX $1000", callback_data="execute_trade_AVAX_1000"
                ),
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _execute_trade(self, query, action):
        """Execute trade command - IMPLEMENTED"""
        client_id = query.from_user.id

        try:
            # Parse action: execute_trade_SYMBOL_AMOUNT
            parts = action.replace("execute_trade_", "").split("_")
            symbol = parts[0]
            amount = float(parts[1])
        except (IndexError, ValueError):
            await query.edit_message_text("❌ Invalid trade parameters")
            return

        await query.edit_message_text("🔄 **Launching Smart Grid...**")

        try:
            # Execute through grid orchestrator
            result = await self.grid_orchestrator.start_client_grid(
                client_id, f"{symbol}USDT", amount
            )

            if result.get("success"):
                message = f"""🎉 **Smart Grid Launched!**

✅ **{symbol}/USDT Grid Active**

**Grid Configuration:**
💰 Capital: ${amount:,.2f}
🤖 Strategy: Smart Adaptive Grid
📊 Status: Active 24/7

**Features Active:**
✅ Automated buy/sell orders
✅ Profit capture on price movements
✅ Risk management system

Your grid will automatically trade when prices move!"""

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
                ]

            else:
                error_message = result.get("error", "Unknown error")
                message = f"""❌ **Grid Launch Failed**

Error: {error_message}

**Common solutions:**
• Check API key permissions
• Ensure sufficient balance
• Verify trading pair availability"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔄 Try Again", callback_data="start_trading"
                        )
                    ],
                    [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")],
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
            self.logger.error(f"Error executing trade: {e}")
            await query.edit_message_text(
                "❌ **System Error**\n\nFailed to start grid. Please try again.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📊 Dashboard", callback_data="show_dashboard"
                            )
                        ]
                    ]
                ),
            )

    async def handle_message(self, update, context):
        """Handle text messages with smart trading commands"""
        client_id = update.effective_user.id
        text = update.message.text.strip()

        self.logger.info(f"Smart message from client {client_id}: {text}")

        # Try common message handlers first (from BaseClientHandler)
        if await self.handle_common_messages(update, context, text):
            return

        # Handle smart trading commands
        if self._is_trading_command(text):
            await self._handle_smart_trading_command(update, client_id, text)
            return

        # Default response with helpful information
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🚀 Start Trading", callback_data="start_trading"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]
        )

        await update.message.reply_text(
            "🧠 **Smart Trading Commands:**\n"
            "• `ADA 1000` - Start ADA grid with $1000\n"
            "• `AVAX 500` - Start AVAX grid with $500\n\n"
            "**Or use the buttons below:**",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    def _is_trading_command(self, text):
        """Check if text is a trading command"""
        parts = text.strip().upper().split()
        if len(parts) == 2:
            try:
                symbol = parts[0]
                amount = float(parts[1])
                return symbol in ["ADA", "AVAX", "BTC", "ETH"] and amount > 0
            except ValueError:
                pass
        return False

    async def _handle_smart_trading_command(self, update, client_id, text):
        """Handle smart trading command like 'ADA 1000'"""
        client = self.client_repo.get_client(client_id)

        if not client or not client.is_active():
            await update.message.reply_text(
                "❌ Please complete your smart trading setup first."
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

            message = f"""🧠 **Smart Grid Trading Setup**

**Symbol:** {symbol}/USDT
**Capital:** ${amount:,.2f}
**Strategy:** Smart Adaptive Grid

**Features:**
✅ Automated grid trading
✅ Smart buy/sell levels
✅ Risk management
✅ 24/7 monitoring

Ready to launch?"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚀 LAUNCH GRID",
                        callback_data=f"execute_trade_{symbol}_{amount}",
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
            self.logger.error(f"Error handling smart trading command: {e}")
            await update.message.reply_text(
                "❌ Invalid format. Use: SYMBOL AMOUNT (e.g., ADA 1000)"
            )

    async def _handle_new_smart_client(self, update, user):
        """Handle new client with smart trading introduction"""
        client = self.client_repo.create_client(
            telegram_id=user.id, username=user.username, first_name=user.first_name
        )

        message = f"""🤖 **Welcome to GridTrader Pro Smart Trading**

Hi {user.first_name}! Welcome to professional grid trading.

**🧠 Smart Features:**
✅ **Automated Grid Trading**
   • Smart buy/sell levels
   • 24/7 market monitoring
   • Automatic profit capture

✅ **Risk Management**
   • Position size controls
   • Stop-loss protection
   • Capital preservation

✅ **Supported Assets**
   • ADA/USDT - Cardano
   • AVAX/USDT - Avalanche

**Setup Steps:**
1. Configure your Binance API keys
2. Set your trading capital
3. Start earning profits!

Ready to begin?"""

        keyboard = [
            [InlineKeyboardButton("🔐 Setup API Keys", callback_data="setup_api")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
        ]

        await update.message.reply_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
