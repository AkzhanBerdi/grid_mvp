"""
Client Handler - Clean Production Version
========================================

Enhanced client handler with smart adaptive trading and clean FIFO integration.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.base_handler import BaseClientHandler


class ClientHandler(BaseClientHandler):
    """Clean client handler with smart trading features"""

    def __init__(self):
        super().__init__()

        # Initialize FIFO service safely
        try:
            from services.enhanced_fifo_service import EnhancedFIFOService

            self.fifo_service = EnhancedFIFOService()
        except ImportError:
            self.logger.warning("FIFO service not available")
            self.fifo_service = None

    async def handle_start(self, update, context):
        """Handle /start command"""
        user = update.effective_user
        client = self.client_repo.get_client(user.id)

        if client and client.is_active():
            await self._show_smart_dashboard(update, client)
        else:
            await self._handle_new_client(update, user)

    async def _handle_new_client(self, update, user):
        """Handle new client registration"""
        # Create new client logic here
        client = self.client_repo.create_client(
            user.id, user.username or f"user_{user.id}"
        )
        await self._show_smart_dashboard(update, client)

    async def _show_smart_dashboard(self, update, client):
        """Smart dashboard with FIFO metrics integration"""
        try:
            # Get grid status
            grid_status = {}
            try:
                grid_status = await self.grid_orchestrator.get_client_grid_status(
                    client.telegram_id
                )
            except Exception as e:
                self.logger.warning(f"Grid status error: {e}")

            # Check API keys
            has_api_keys = bool(client.binance_api_key and client.binance_secret_key)
            api_status = "✅ Connected" if has_api_keys else "❌ Not Set"

            # Get FIFO metrics if available
            fifo_metrics = self._get_fifo_metrics(client.telegram_id)

            # Active grids info
            active_grids = grid_status.get("active_grids", {})
            active_info = (
                f"\n🤖 Active Grids: {len(active_grids)}"
                if active_grids
                else "\n💤 No active grids"
            )

            if active_grids:
                for symbol, grid_info in active_grids.items():
                    status = grid_info.get("status", "Unknown")
                    active_info += f"\n   {symbol}: {status}"

            message = f"""📊 **GridTrader Pro Smart Dashboard**

**Account Status:**
🔐 API Keys: {api_status}
💰 Capital: ${client.total_capital:,.2f}
⚙️ Pairs: {", ".join(client.trading_pairs) if client.trading_pairs else "Not Set"}
📈 Risk Level: {client.risk_level.title()}{active_info}{fifo_metrics}

**Quick Trading:** Type `ADA 1000` or `AVAX 500`"""

            # Build keyboard
            keyboard = self._build_dashboard_keyboard(client, grid_status)

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
            # Fallback to base dashboard
            await self.show_dashboard(update, client)

    def _get_fifo_metrics(self, client_id: int) -> str:
        """Get FIFO metrics safely"""
        if not self.fifo_service:
            return "\n💰 **FIFO service not available**"

        try:
            display_metrics = self.fifo_service.get_display_metrics(client_id)
            performance = self.fifo_service.calculate_fifo_performance(client_id)

            return f"""
💰 **FIFO Profit Tracking:**
{display_metrics["total_profit_display"]}
Win Rate: {display_metrics["win_rate_display"]}
Efficiency: {display_metrics["efficiency_display"]}
Volume: {display_metrics["volume_display"]}
Trades: {performance.get("total_trades", 0)}"""

        except Exception as e:
            self.logger.error(f"Error getting FIFO metrics for {client_id}: {e}")
            return "\n💰 **Profit:** Calculating..."

    def _build_dashboard_keyboard(self, client, grid_status):
        """Build dashboard keyboard based on client state"""
        keyboard = []

        # Trading controls
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

        # Standard buttons
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

        return keyboard

    async def handle_callback(self, update, context):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()

        client_id = query.from_user.id
        action = query.data

        self.logger.info(f"Smart client {client_id} action: {action}")

        # Try common handlers first
        if await self.handle_common_callbacks(query, client_id, action):
            return

        # Smart-specific actions
        if action == "show_performance":
            await self._show_performance(query, client_id)
        elif action == "start_trading":
            await self._start_trading(query, client_id)
        elif action.startswith("execute_trade_"):
            await self._execute_trade(query, action)
        elif action == "show_fifo_report":
            await self.show_fifo_report(query, client_id)
        elif action == "explain_pure_usdt_upgrade":
            await self.explain_pure_usdt_upgrade(query, client_id)
        else:
            await query.edit_message_text(
                "❌ **Unknown Action**\n\nPlease use the dashboard buttons.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📊 Dashboard", callback_data="home")]]
                ),
            )

    async def _show_performance(self, query, client_id: int):
        """Show performance data"""
        try:
            client = self.client_repo.get_client(client_id)

            if self.fifo_service:
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
                message = f"""📈 **Smart Trading Performance**

💰 **Account Overview:**
Capital: ${client.total_capital:,.2f}
Risk Level: {client.risk_level.title()}
Trading Pairs: {", ".join(client.trading_pairs)}

🤖 **Grid Status:**
Status: {"✅ Ready" if client.can_start_grid() else "❌ Setup Required"}

📊 **Note:** Start trading to see detailed performance metrics."""

            keyboard = [[InlineKeyboardButton("📊 Dashboard", callback_data="home")]]

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
                    [[InlineKeyboardButton("📊 Dashboard", callback_data="home")]]
                ),
            )

    async def _start_trading(self, query, client_id: int):
        """Start trading functionality"""
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
                        [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
                    ]
                ),
                parse_mode="Markdown",
            )
            return

        message = f"""🚀 **Pure USDT Grid Trading**

**🎯 NEW: Perfect Profit Tracking!**
Professional FIFO accounting for accurate profits.

**Account Ready:**
💰 Capital: ${client.total_capital:,.2f}
🎯 Risk Level: {client.risk_level.title()}
🔄 Pairs: {", ".join(client.trading_pairs)}

**How Pure USDT Works:**
1. You provide pure USDT (no existing assets)
2. System splits 50/50: USDT reserve + asset purchase
3. Perfect cost basis for all future profit tracking

**Available Symbols:**
🥇 ADA/USDT - Cardano (Stable, academic blockchain)
🏔️ AVAX/USDT - Avalanche (Fast, DeFi focused)
🔷 ETH/USDT - Ethereum (Blue chip, institutional)
🟣 SOL/USDT - Solana (High growth, memecoin hub)

**Quick Start:**
Choose amount or type command like `ADA 1000`"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🥇 ADA $400", callback_data="execute_trade_ADA_400"
                ),
                InlineKeyboardButton(
                    "🥇 ADA $800", callback_data="execute_trade_ADA_800"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏔️ AVAX $400", callback_data="execute_trade_AVAX_400"
                ),
                InlineKeyboardButton(
                    "🏔️ AVAX $800", callback_data="execute_trade_AVAX_800"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔷 ETH $400", callback_data="execute_trade_ETH_400"
                ),
                InlineKeyboardButton(
                    "🔷 ETH $800", callback_data="execute_trade_ETH_800"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🟣 SOL $400", callback_data="execute_trade_SOL_400"
                ),
                InlineKeyboardButton(
                    "🟣 SOL $800", callback_data="execute_trade_SOL_800"
                ),
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
            [InlineKeyboardButton("📈 FIFO Report", callback_data="show_fifo_report")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _execute_trade(self, query, action: str):
        """Execute trade with Pure USDT"""
        client_id = query.from_user.id

        try:
            # Parse action
            parts = action.replace("execute_trade_", "").split("_")
            symbol = parts[0]
            usdt_amount = float(parts[1])
        except (IndexError, ValueError):
            await query.edit_message_text("❌ Invalid trade parameters")
            return

        await query.edit_message_text("🔄 **Initializing Pure USDT Grid...**")

        try:
            # Check client setup
            client = self.client_repo.get_client(client_id)
            if not client or not client.can_start_grid():
                await query.edit_message_text(
                    "❌ **Setup Required**\n\nPlease configure API keys and capital first.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "⚙️ Setup", callback_data="setup_api"
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "📊 Dashboard", callback_data="home"
                                )
                            ],
                        ]
                    ),
                    parse_mode="Markdown",
                )
                return

            # Execute Pure USDT initialization
            result = await self._initialize_pure_usdt_grid(
                client_id, symbol, usdt_amount
            )

            if result.get("success"):
                await self._send_success_message(query, result, symbol, usdt_amount)
            else:
                await self._send_error_message(query, result)

        except Exception as e:
            self.logger.error(f"Pure USDT execution error: {e}")
            await query.edit_message_text(
                "❌ **System Error**\n\nFailed to initialize Pure USDT grid.\nPlease try again or contact support.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 Retry", callback_data="start_trading"
                            )
                        ],
                        [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
                    ]
                ),
                parse_mode="Markdown",
            )

    async def _initialize_pure_usdt_grid(
        self, client_id: int, symbol: str, usdt_amount: float
    ):
        """Initialize Pure USDT grid"""
        # Import required services
        from binance.client import Client

        from repositories.enhanced_trade_repository import EnhancedTradeRepository
        from services.enhanced_fifo_service import EnhancedFIFOService
        from services.pure_usdt_grid_initializer import (
            EnhancedGridInitializationOrchestrator,
        )
        from utils.crypto import CryptoUtils

        # Get client's Binance client
        client = self.client_repo.get_client(client_id)
        crypto_utils = CryptoUtils()

        decrypted_api_key = crypto_utils.decrypt(client.binance_api_key)
        decrypted_secret = crypto_utils.decrypt(client.binance_secret_key)
        client_binance_client = Client(decrypted_api_key, decrypted_secret)

        # Create Pure USDT orchestrator
        enhanced_trade_repo = EnhancedTradeRepository()
        enhanced_fifo_service = EnhancedFIFOService()
        orchestrator = EnhancedGridInitializationOrchestrator(
            client_binance_client, enhanced_trade_repo, enhanced_fifo_service
        )

        # Execute Pure USDT initialization
        return await orchestrator.start_client_grid_from_usdt_with_advanced_features(
            client_id=client_id,
            symbol=f"{symbol}USDT",
            usdt_amount=usdt_amount,
            grid_orchestrator=self.grid_orchestrator,
        )

    async def _send_success_message(
        self, query, result: dict, symbol: str, usdt_amount: float
    ):
        """Send success message for Pure USDT initialization"""
        init_details = result["initialization_results"]

        message = f"""🎉 **Pure USDT Grid Initialized!**

✅ **{symbol}/USDT Perfect FIFO Tracking**

**💰 Pure USDT Investment:**
• Total USDT: ${usdt_amount:,.2f}
• USDT Reserve: ${init_details["initialization"]["usdt_reserve"]:.2f}
• Asset Purchase: {init_details["initialization"]["asset_quantity"]:.4f} {symbol}
• Cost Basis: ${init_details["initialization"]["asset_cost_basis"]:.4f}

**🎯 Perfect FIFO Tracking ACTIVE:**
✅ All future sells have accurate cost basis
✅ Real profit calculations from day one
✅ Professional-grade accounting
✅ Zero cost basis guesswork

**📊 Your Account Status:**
• Ready for precise profit tracking
• Manual trading enabled with perfect FIFO
• Can add more capital for automated grids

Perfect FIFO profit tracking is now ACTIVE! 🎯"""

        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
            [InlineKeyboardButton("📈 FIFO Report", callback_data="show_fifo_report")],
            [
                InlineKeyboardButton(
                    "💰 Add More Capital", callback_data="start_trading"
                )
            ],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _send_error_message(self, query, result: dict):
        """Send error message for failed initialization"""
        error_message = result.get("error", "Unknown error")

        message = f"""❌ **Pure USDT Initialization Failed**

Error: {error_message}

**Common causes:**
• Insufficient balance in Binance account
• API keys need spot trading permissions  
• Minimum amount is $40 USDT
• Network connectivity issues

**Your FIFO tracking is NOT active yet.**
Please resolve the issue and try again."""

        keyboard = [
            [InlineKeyboardButton("🔄 Try Again", callback_data="start_trading")],
            [InlineKeyboardButton("⚙️ Check Settings", callback_data="show_settings")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def handle_message(self, update, context):
        """Handle text messages with smart trading commands"""
        client_id = update.effective_user.id
        text = update.message.text.strip()

        self.logger.info(f"📨 ClientHandler message from client {client_id}: {text}")

        # Try common message handlers first
        if await self.handle_common_messages(update, context, text):
            return

        # Handle smart trading commands
        if self._is_trading_command(text):
            self.logger.info(f"🎯 Processing trading command: {text}")
            await self._handle_smart_trading_command(update, client_id, text)
            return

        # Default response
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🚀 Start Trading", callback_data="start_trading"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
            ]
        )

        await update.message.reply_text(
            "🧠 **Smart Trading Commands:**\n"
            "• `ETH 2000` - Start ETH grid with $2000\n"
            "• `SOL 1500` - Start SOL grid with $1500\n"
            "• `ADA 1000` - Start ADA grid with $1000\n\n"
            "**Or use the buttons below:**",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    async def _handle_smart_trading_command(self, update, client_id: int, text: str):
        """Handle smart trading command like 'ADA 1000'"""
        try:
            client = self.client_repo.get_client(client_id)

            if not client or not client.is_active() or not client.can_start_grid():
                await update.message.reply_text("❌ Please complete your setup first.")
                return

            # Parse command
            parts = text.upper().split()
            symbol = parts[0]
            amount = float(parts[1])

            # Validation
            if amount < 100:
                await update.message.reply_text("💰 Minimum trading amount: $100")
                return

            if symbol not in ["ADA", "AVAX", "BTC", "ETH", "SOL"]:
                await update.message.reply_text(
                    f"❌ {symbol} not supported yet. Available: ADA, AVAX, BTC, ETH, SOL"
                )
                return

            # Create confirmation message
            asset_info = {
                "ADA": ("Cardano", "🔵"),
                "AVAX": ("Avalanche", "🏔️"),
                "BTC": ("Bitcoin", "🟠"),
                "ETH": ("Ethereum", "🔷"),
                "SOL": ("Solana", "🟣"),
            }

            asset_name, emoji = asset_info.get(symbol, (symbol, "🔘"))

            message = f"""{emoji} **Smart Grid Trading Setup**

**Asset:** {asset_name} ({symbol}/USDT)
**Capital:** ${amount:,.2f}
**Strategy:** Advanced Dual-Scale Grid

**Features:**
✅ Automated precision order handling
✅ Volatility-based risk management
✅ Compound interest growth
✅ 24/7 market monitoring
✅ FIFO profit tracking

Ready to launch?"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚀 LAUNCH GRID",
                        callback_data=f"execute_trade_{symbol}_{int(amount)}",
                    )
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="home")],
            ]

            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"❌ Smart trading command error: {e}")
            await update.message.reply_text(
                "❌ Invalid format. Use: SYMBOL AMOUNT (e.g., ETH 800)"
            )

    # FIFO Report Methods
    async def show_fifo_report(self, query, client_id: int):
        """Show detailed FIFO profit report"""
        if not self.fifo_service:
            await query.edit_message_text("❌ FIFO service not available")
            return

        try:
            fifo_performance = self.fifo_service.calculate_fifo_profit_with_cost_basis(
                client_id
            )
            cost_basis_summary = self.fifo_service.get_cost_basis_summary(client_id)
            validation = await self.fifo_service.validate_fifo_integrity(client_id)

            # Determine client status
            if cost_basis_summary.get("has_initialization_records"):
                status = "✅ PERFECT TRACKING"
                status_icon = "🎯"
                tracking_note = "Using precise cost basis from Pure USDT initialization"
            else:
                status = "📊 LEGACY CLIENT"
                status_icon = "⚠️"
                tracking_note = (
                    "Using estimated calculations - consider upgrading to Pure USDT"
                )

            message = f"""{status_icon} **FIFO Profit Report**

**🎯 Tracking Status:** {status}

**💰 Profit Summary:**
• Total Profit: ${fifo_performance["total_profit"]:.2f}
• Realized: ${fifo_performance["realized_profit"]:.2f}
• Unrealized: ${fifo_performance["unrealized_profit"]:.2f}

**📈 Trading Performance:**
• Total Trades: {fifo_performance["total_trades"]}
• Profitable Trades: {fifo_performance["profitable_trades"]}
• Win Rate: {fifo_performance["win_rate"]:.1f}%
• Avg per Trade: ${fifo_performance["avg_profit_per_trade"]:.2f}

**🔍 Cost Basis Details:**
• Records: {cost_basis_summary.get("total_cost_basis_records", 0)}
• Initial Investment: ${cost_basis_summary.get("total_initial_investment", 0):.2f}
• Method: {fifo_performance["calculation_method"]}

**📋 Note:** {tracking_note}

**Accuracy:** {"✅ VERIFIED" if validation["validation_passed"] else "⚠️ ESTIMATED"}"""

            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="show_fifo_report")],
                [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
            ]

            # Add upgrade option for legacy clients
            if not cost_basis_summary.get("has_initialization_records"):
                keyboard.insert(
                    1,
                    [
                        InlineKeyboardButton(
                            "🚀 Upgrade to Pure USDT",
                            callback_data="explain_pure_usdt_upgrade",
                        )
                    ],
                )

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"FIFO report error: {e}")
            await query.edit_message_text(
                "❌ Error generating FIFO report. Please try again."
            )

    async def explain_pure_usdt_upgrade(self, query, client_id: int):
        """Explain Pure USDT upgrade benefits"""
        message = """🚀 **Upgrade to Pure USDT Tracking**

**Current Status:** Legacy client with estimated profits

**Why Upgrade?**
✅ **Perfect Accuracy:** 99.5% profit calculation precision
✅ **Professional Tracking:** Enterprise-level FIFO accounting  
✅ **No Guesswork:** Exact cost basis for every trade
✅ **Tax Compliance:** Proper records for tax reporting
✅ **Future-Proof:** Latest technology stack

**How It Works:**
1. **Stop Current Grids:** Gracefully close existing positions
2. **Convert to USDT:** Cash out all assets to pure USDT
3. **Re-Initialize:** Start new grids with Perfect FIFO tracking
4. **Perfect Tracking:** All future trades have exact profit calculations

**Example Difference:**
• **Legacy:** "Estimated profit: ~$45.23" 
• **Pure USDT:** "Exact profit: $45.23 (verified)"

**⏱️ Upgrade Time:** ~30 minutes
**🔒 Risk:** Minimal (just improved tracking)

Ready to upgrade for perfect profit tracking?"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Yes, I Want Perfect Tracking", callback_data="start_trading"
                )
            ],
            [InlineKeyboardButton("📋 Learn More", callback_data="show_fifo_report")],
            [InlineKeyboardButton("📊 Keep Current Setup", callback_data="home")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
