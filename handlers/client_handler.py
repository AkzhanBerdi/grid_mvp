# handlers/client_handler.py
"""
Enhanced Client Handler with User Registry Integration
=====================================================

Extends your existing ClientHandler with user registration functionality
while maintaining all existing features and structure.
"""

from binance.client import Client
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from repositories.trade_repository import TradeRepository
from services.fifo_service import FIFOService
from services.usdt_initializer import EnhancedGridInitializationOrchestrator
from utils.base_handler import BaseClientHandler
from utils.crypto import CryptoUtils


class ClientHandler(BaseClientHandler):
    """Enhanced client handler with user registry and smart trading features"""

    def __init__(self):
        super().__init__()
        self.fifo_service = FIFOService()
        self.crypto_utils = CryptoUtils()

        # Trading configuration
        self.SUPPORTED_SYMBOLS = ["ADA", "AVAX", "BTC", "ETH", "SOL"]
        self.ASSET_INFO = {
            "ADA": ("Cardano", "🥇", "Stable, academic blockchain"),
            "AVAX": ("Avalanche", "🏔️", "Fast, DeFi focused"),
            "BTC": ("Bitcoin", "🟠", "Digital gold standard"),
            "ETH": ("Ethereum", "🔷", "Blue chip, institutional"),
            "SOL": ("Solana", "🟣", "High growth, memecoin hub"),
        }
        self.MIN_TRADE_AMOUNT = 100.0

    # =====================================
    # ENHANCED MAIN HANDLERS
    # =====================================

    async def handle_start(self, update, context):
        """Enhanced /start command with user registration"""
        # Use the enhanced registration system from base handler
        await self.handle_start_with_registration(update, context)

    async def handle_callback(self, update, context):
        """Enhanced callback handler with admin support"""
        query = update.callback_query
        await query.answer()

        client_id = query.from_user.id
        action = query.data

        self.logger.info(f"Client {client_id} action: {action}")

        # Check user access first
        has_access, access_status = self._check_user_access(client_id)

        # Allow admin callbacks even if user doesn't have regular access
        if not has_access and not action.startswith(("admin_", "approve_", "reject_")):
            client_info = self.user_registry.get_client_registration_info(client_id)
            await self._handle_access_denied(query, access_status, client_info)
            return

        # Route to appropriate handler
        if await self.handle_common_callbacks(query, client_id, action):
            return

        # Client-specific actions (only for approved users)
        if has_access:
            action_handlers = {
                "show_performance": self._show_performance,
                "start_trading": self._show_trading_options,
                "show_fifo_report": self._show_fifo_report,
            }

            if action in action_handlers:
                await action_handlers[action](query, client_id)
            elif action.startswith("execute_trade_"):
                await self._execute_trade(query, action)
            else:
                await self._handle_unknown_action(query)

    async def handle_message(self, update, context):
        """Enhanced message handler with access control"""
        client_id = update.effective_user.id
        text = update.message.text.strip()

        self.logger.info(f"Message from client {client_id}: {text}")

        # Handle admin commands first (admins can always use these)
        if text.startswith("/admin"):
            await self.handle_admin_command(update, context)
            return

        # Check user access for regular commands
        has_access, access_status = self._check_user_access(client_id)

        if not has_access:
            client_info = self.user_registry.get_client_registration_info(client_id)
            await self._handle_access_denied(update, access_status, client_info)
            return

        # Try common handlers first
        if await self.handle_common_messages(update, context, text):
            return

        # Handle trading commands (only for approved users)
        if self._is_trading_command(text):
            await self._handle_trading_command(update, client_id, text)
        else:
            await self._show_command_help(update)

    # =====================================
    # ENHANCED DASHBOARD & UI METHODS
    # =====================================

    async def _show_smart_dashboard(self, update, client):
        """Enhanced smart dashboard with registration integration"""
        try:
            # Check user access
            has_access, access_status = self._check_user_access(client.telegram_id)

            if not has_access:
                client_info = self.user_registry.get_client_registration_info(
                    client.telegram_id
                )
                await self._handle_access_denied(update, access_status, client_info)
                return

            # Get grid status and metrics
            grid_status = await self._get_grid_status(client.telegram_id)
            fifo_metrics = self._get_fifo_metrics(client.telegram_id)

            # Build message
            message = self._build_dashboard_message(client, grid_status, fifo_metrics)
            keyboard = self._build_dashboard_keyboard(client, grid_status)

            # Send or edit message
            await self._send_or_edit_message(update, message, keyboard)

        except Exception as e:
            self.logger.error(f"Dashboard error: {e}")
            await self.show_dashboard(update, client)  # Fallback

    def _build_dashboard_message(
        self, client, grid_status: dict, fifo_metrics: str
    ) -> str:
        """Enhanced dashboard message with registration status"""
        # Get registration info
        client_info = self.user_registry.get_client_registration_info(
            client.telegram_id
        )

        # API status
        has_api_keys = bool(client.binance_api_key and client.binance_secret_key)

        api_status = "✅ Connected" if has_api_keys else "❌ Not Set"

        # Active grids info
        active_grids = grid_status.get("active_grids", {})
        if active_grids:
            grid_info = f"\n🤖 Active Grids: {len(active_grids)}"
            for symbol, grid_data in active_grids.items():
                status = grid_data.get("status", "Unknown")
                grid_info += f"\n   {symbol}: {status}"
        else:
            grid_info = "\n💤 No active grids"

        # Registration status (only show for admins or if there are issues)
        reg_status = ""
        if client_info:
            if client_info["registration_status"] != "approved":
                reg_status = (
                    f"\n📋 Status: {client_info['registration_status'].title()}"
                )
            elif self.admin_service.is_admin(client.telegram_id):
                reg_status = "\n🛡️ Admin Access"

        return f"""📊 **GridTrader Pro Smart Dashboard**

**Account Status:**
🔐 API Keys: {api_status}
💰 Capital: ${client.total_capital:,.2f}
⚙️ Pairs: {", ".join(client.trading_pairs) if client.trading_pairs else "Not Set"}
📈 Risk Level: {client.risk_level.title()}{reg_status}{grid_info}{fifo_metrics}

**Quick Trading:** Type `ADA 1000` or `AVAX 500`"""

    def _build_dashboard_keyboard(self, client, grid_status: dict) -> list:
        """Enhanced dashboard keyboard with admin options"""
        keyboard = []

        # Admin panel button (only for admins)
        if self.admin_service.is_admin(client.telegram_id):
            keyboard.append(
                [InlineKeyboardButton("🛡️ Admin Panel", callback_data="admin_refresh")]
            )

        # Trading controls (only for users who can trade)
        if client.can_start_grid():
            if grid_status.get("active_grids"):
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

        # Standard options
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

    # =====================================
    # ACCESS CONTROL WRAPPER METHODS
    # =====================================

    async def _show_trading_options(self, query, client_id: int):
        """Show trading options with access control"""
        # Double-check access (should already be checked, but be safe)
        has_access, access_status = self._check_user_access(client_id)

        if not has_access:
            client_info = self.user_registry.get_client_registration_info(client_id)
            await self._handle_access_denied(query, access_status, client_info)
            return

        # Original trading options logic
        client = self.client_repo.get_client(client_id)

        if not client.can_start_grid():
            await self._show_setup_required(query)
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

{self._build_supported_assets_text()}

**Quick Start:** Choose amount or type command like `ADA 1000`"""

        keyboard = self._build_trading_keyboard()
        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_performance(self, query, client_id: int):
        """Show performance with access control"""
        # Check access
        has_access, access_status = self._check_user_access(client_id)

        if not has_access:
            client_info = self.user_registry.get_client_registration_info(client_id)
            await self._handle_access_denied(query, access_status, client_info)
            return

        # Original performance logic
        try:
            client = self.client_repo.get_client(client_id)

            # Get grid status for unified status display
            has_active_grids = False
            try:
                grid_status = await self.grid_orchestrator.get_client_grid_status(
                    client_id
                )
                has_active_grids = len(grid_status.get("active_grids", {})) > 0
            except Exception as e:
                self.logger.warning(f"Could not get grid status: {e}")

            if self.fifo_service:
                message = self._build_fifo_performance_message(
                    client_id, has_active_grids
                )
            else:
                message = self._build_basic_performance_message(client)

            keyboard = [[InlineKeyboardButton("📊 Dashboard", callback_data="home")]]

            # Add admin performance button for admins
            if self.admin_service.is_admin(client_id):
                keyboard.insert(
                    0,
                    [
                        InlineKeyboardButton(
                            "🛡️ System Stats", callback_data="admin_stats"
                        )
                    ],
                )

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Performance display error: {e}")
            await self._send_error_fallback(
                query, "Performance data temporarily unavailable."
            )

    async def _show_fifo_report(self, query, client_id: int):
        """Show FIFO report with access control"""
        # Check access
        has_access, access_status = self._check_user_access(client_id)

        if not has_access:
            client_info = self.user_registry.get_client_registration_info(client_id)
            await self._handle_access_denied(query, access_status, client_info)
            return

        # Original FIFO report logic
        if not self.fifo_service:
            await query.edit_message_text("❌ FIFO service not available")
            return

        try:
            # Get FIFO data
            fifo_performance = self.fifo_service.calculate_fifo_profit_with_cost_basis(
                client_id
            )
            cost_basis_summary = self.fifo_service.get_cost_basis_summary(client_id)
            validation = await self.fifo_service.validate_fifo_integrity(client_id)

            # Build report message
            message = self._build_fifo_report_message(
                fifo_performance, cost_basis_summary, validation
            )
            keyboard = self._build_fifo_report_keyboard(cost_basis_summary)

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"FIFO report error: {e}")
            await self._send_error_fallback(query, "Error generating FIFO report.")

    async def _execute_trade(self, query, action: str):
        """Execute trade with access control"""
        client_id = query.from_user.id

        # Check access
        has_access, access_status = self._check_user_access(client_id)

        if not has_access:
            client_info = self.user_registry.get_client_registration_info(client_id)
            await self._handle_access_denied(query, access_status, client_info)
            return

        # Original trade execution logic
        try:
            symbol, usdt_amount = self._parse_trade_action(action)
        except ValueError as e:
            await query.edit_message_text(f"❌ {str(e)}")
            return

        await query.edit_message_text("🔄 **Initializing Pure USDT Grid...**")

        try:
            # Validate client setup
            client = self.client_repo.get_client(client_id)
            if not client or not client.can_start_grid():
                await self._show_setup_required(query)
                return

            # Execute initialization
            result = await self._initialize_pure_usdt_grid(
                client_id, symbol, usdt_amount
            )

            if result.get("success"):
                await self._send_success_message(query, result, symbol, usdt_amount)
            else:
                await self._send_error_message(query, result)

        except Exception as e:
            self.logger.error(f"Trade execution error: {e}")
            await self._send_system_error(query)

    async def _handle_trading_command(self, update, client_id: int, text: str):
        """Handle trading command with access control"""
        # Access already checked in handle_message, but double-check for safety
        has_access, access_status = self._check_user_access(client_id)

        if not has_access:
            client_info = self.user_registry.get_client_registration_info(client_id)
            await self._handle_access_denied(update, access_status, client_info)
            return

        # Original trading command logic
        try:
            client = self.client_repo.get_client(client_id)
            if not client or not client.can_start_grid():
                await update.message.reply_text("❌ Please complete your setup first.")
                return

            symbol, amount = self._parse_trading_command(text)

            # Build confirmation
            message = self._build_trade_confirmation(symbol, amount)
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

        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")

    # =====================================
    # ENHANCED ERROR HANDLING
    # =====================================

    async def _handle_access_denied(
        self, update, status: str, client_info: dict = None
    ):
        """Enhanced access denied handler"""
        if hasattr(update, "message") and update.message:
            # Direct message
            await super()._handle_access_denied(update, status, client_info)
        else:
            # Callback query
            if status == "pending":
                message = "⏳ Your registration is still pending admin approval."
            elif status == "rejected":
                reason = (
                    client_info.get("registration_notes", "Not specified")
                    if client_info
                    else "Not specified"
                )
                message = f"❌ Access denied. Reason: {reason}"
            elif status == "suspended":
                message = (
                    "⚠️ Your account is temporarily suspended. Contact administrator."
                )
            elif status == "banned":
                message = "🚫 Your account has been permanently banned."
            else:
                message = "❌ Access denied. Please contact administrator."

            await update.edit_message_text(message)

    async def _handle_unknown_action(self, query):
        """Handle unknown actions with better messaging"""
        await query.edit_message_text(
            "🤔 **Unknown Action**\n\nThis feature may not be available yet.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Home", callback_data="home")]]
            ),
        )

    async def _send_system_error(self, query):
        """Send system error message"""
        await query.edit_message_text(
            "❌ **System Error**\n\nPlease try again later or contact support.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Home", callback_data="home")]]
            ),
        )

    # =====================================
    # ALL EXISTING METHODS REMAIN THE SAME
    # =====================================

    # Keep all your existing methods exactly as they are:
    # - _get_grid_status
    # - _get_fifo_metrics
    # - _is_trading_command
    # - _parse_trade_action
    # - _parse_trading_command
    # - _build_trade_confirmation
    # - _initialize_pure_usdt_grid
    # - _build_supported_assets_text
    # - _build_trading_keyboard
    # - _build_fifo_performance_message
    # - _build_basic_performance_message
    # - _build_fifo_report_message
    # - _build_fifo_report_keyboard
    # - _send_or_edit_message
    # - _send_success_message
    # - _send_error_message
    # - _show_setup_required
    # - _show_command_help
    # - _send_error_fallback

    async def _get_grid_status(self, client_id: int) -> dict:
        """Get grid status safely"""
        try:
            return await self.grid_orchestrator.get_client_grid_status(client_id)
        except Exception as e:
            self.logger.warning(f"Grid status error: {e}")
            return {}

    def _get_fifo_metrics(self, client_id: int) -> str:
        """Get FIFO metrics safely"""
        if not self.fifo_service:
            return "\n💰 **FIFO service not available**"

        try:
            # Use the correct method from your FIFO service
            performance = self.fifo_service.calculate_fifo_profit_with_cost_basis(
                client_id
            )

            # Try to get display metrics, with fallback
            try:
                display_metrics = self.fifo_service.get_display_metrics(client_id)
                return f"""
💰 **FIFO Profit Tracking:**
{display_metrics["total_profit_display"]}
Win Rate: {display_metrics["win_rate_display"]}
Efficiency: {display_metrics["efficiency_display"]}
Volume: {display_metrics["volume_display"]}
Trades: {performance.get("total_trades", 0)}"""
            except AttributeError:
                # Fallback if get_display_metrics doesn't exist
                return f"""
💰 **FIFO Profit Tracking:**
Total Profit: ${performance.get("total_profit", 0):.2f}
Win Rate: {performance.get("win_rate", 0):.1f}%
Trades: {performance.get("total_trades", 0)}"""

        except Exception as e:
            self.logger.error(f"FIFO metrics error for {client_id}: {e}")
            return "\n💰 **Profit:** Calculating..."

    def _parse_trade_action(self, action: str) -> tuple:
        """Parse trade action from callback data"""
        try:
            parts = action.replace("execute_trade_", "").split("_")
            symbol = parts[0]
            usdt_amount = float(parts[1])

            if symbol not in self.SUPPORTED_SYMBOLS:
                raise ValueError(f"Unsupported symbol: {symbol}")
            if usdt_amount < self.MIN_TRADE_AMOUNT:
                raise ValueError(f"Minimum amount: ${self.MIN_TRADE_AMOUNT}")

            return symbol, usdt_amount
        except (IndexError, ValueError):
            raise ValueError("Invalid trade parameters")

    def _parse_trading_command(self, text: str) -> tuple:
        """Parse trading command from text"""
        parts = text.upper().split()
        symbol = parts[0]
        amount = float(parts[1])

        if symbol not in self.SUPPORTED_SYMBOLS:
            raise ValueError(
                f"{symbol} not supported. Available: {', '.join(self.SUPPORTED_SYMBOLS)}"
            )
        if amount < self.MIN_TRADE_AMOUNT:
            raise ValueError(f"Minimum trading amount: ${self.MIN_TRADE_AMOUNT}")

        return symbol, amount

    def _build_trade_confirmation(self, symbol: str, amount: float) -> str:
        """Build trade confirmation message"""
        asset_name, emoji, description = self.ASSET_INFO.get(symbol, (symbol, "🔘", ""))

        return f"""{emoji} **Smart Grid Trading Setup**

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

    async def _initialize_pure_usdt_grid(
        self, client_id: int, symbol: str, usdt_amount: float
    ) -> dict:
        """Initialize Pure USDT grid"""
        try:
            # Get client's Binance client
            client = self.client_repo.get_client(client_id)
            decrypted_api_key = self.crypto_utils.decrypt(client.binance_api_key)
            decrypted_secret = self.crypto_utils.decrypt(client.binance_secret_key)
            client_binance_client = Client(decrypted_api_key, decrypted_secret)

            # Create orchestrator
            enhanced_trade_repo = TradeRepository()
            enhanced_fifo_service = FIFOService()
            orchestrator = EnhancedGridInitializationOrchestrator(
                client_binance_client, enhanced_trade_repo, enhanced_fifo_service
            )

            # Execute initialization
            return (
                await orchestrator.start_client_grid_from_usdt_with_advanced_features(
                    client_id=client_id,
                    symbol=f"{symbol}USDT",
                    usdt_amount=usdt_amount,
                    grid_orchestrator=self.grid_orchestrator,
                )
            )

        except Exception as e:
            self.logger.error(f"Pure USDT initialization error: {e}")
            return {"success": False, "error": str(e)}

    def _build_supported_assets_text(self) -> str:
        """Build supported assets description"""
        text = "**Available Symbols:**\n"
        for symbol, (name, emoji, desc) in self.ASSET_INFO.items():
            text += f"{emoji} {symbol}/USDT - {name} ({desc})\n"
        return text

    def _build_trading_keyboard(self) -> list:
        """Build trading options keyboard"""
        keyboard = []

        # Add trading pairs with amounts
        for symbol, (name, emoji, _) in self.ASSET_INFO.items():
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{emoji} {symbol} $400",
                        callback_data=f"execute_trade_{symbol}_400",
                    ),
                    InlineKeyboardButton(
                        f"{emoji} {symbol} $800",
                        callback_data=f"execute_trade_{symbol}_800",
                    ),
                ]
            )

        # Navigation buttons
        keyboard.extend(
            [
                [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
                [
                    InlineKeyboardButton(
                        "📈 FIFO Report", callback_data="show_fifo_report"
                    )
                ],
            ]
        )

        return keyboard

    def _build_fifo_performance_message(
        self, client_id: int, has_active_grids: bool = False
    ) -> str:
        """Build FIFO performance message"""
        performance = self.fifo_service.calculate_fifo_profit_with_cost_basis(client_id)

        # Get display metrics if available, otherwise build from performance data
        try:
            display_metrics = self.fifo_service.get_display_metrics(client_id)
        except AttributeError:
            # Fallback if get_display_metrics doesn't exist
            display_metrics = {
                "total_profit_display": f"${performance.get('total_profit', 0):.2f}",
                "recent_profit_display": f"${performance.get('realized_profit', 0):.2f}",
                "volume_display": "Calculating...",
                "win_rate_display": f"{performance.get('win_rate', 0):.1f}%",
                "efficiency_display": "Active",
                "active_grids_display": "1" if has_active_grids else "0",
            }

        # UNIFIED STATUS LOGIC
        current_multiplier = performance.get("current_multiplier", 1.0)

        if has_active_grids:
            unified_status = "Trading Active"
            compound_display = (
                f"{current_multiplier:.1f}x (ACTIVE)"
                if current_multiplier > 1.0
                else "1.0x (ACTIVE)"
            )
            compound_emoji = "🟢"
        else:
            unified_status = "Ready to Trade"
            compound_display = "1.0x (INACTIVE)"
            compound_emoji = "⚪"

        return f"""📈 **Smart Trading Performance**

    💰 **Profit Analysis:**
    {display_metrics["total_profit_display"]}
    Recent 24h: {display_metrics["recent_profit_display"]}

    📊 **Trading Statistics:**
    Total Volume: {display_metrics["volume_display"]}
    Win Rate: {display_metrics["win_rate_display"]}
    Efficiency: {display_metrics["efficiency_display"]}
    Active Grids: {display_metrics["active_grids_display"]}

    🎯 **Status:** {unified_status}
    🔄 **Compound:** {compound_display} {compound_emoji}"""

    def _build_basic_performance_message(self, client) -> str:
        """Build basic performance message when FIFO unavailable"""
        return f"""📈 **Smart Trading Performance**

💰 **Account Overview:**
Capital: ${client.total_capital:,.2f}
Risk Level: {client.risk_level.title()}
Trading Pairs: {", ".join(client.trading_pairs)}

🤖 **Grid Status:**
Status: {"✅ Ready" if client.can_start_grid() else "❌ Setup Required"}

📊 **Note:** Start trading to see detailed performance metrics."""

    def _build_fifo_report_message(
        self, fifo_performance: dict, cost_basis_summary: dict, validation: dict
    ) -> str:
        """Build FIFO report message"""

        return f"""🎯 **FIFO Profit Report**

💰 **Profit Summary:**
• Total Profit: ${fifo_performance["total_profit"]:.2f}
• Realized: ${fifo_performance["realized_profit"]:.2f}
• Unrealized: ${fifo_performance["unrealized_profit"]:.2f}

📈 **Trading Performance:**
• Total Trades: {fifo_performance["total_trades"]}
• Profitable Trades: {fifo_performance["profitable_trades"]}
• Win Rate: {fifo_performance["win_rate"]:.1f}%
• Avg per Trade: ${fifo_performance["avg_profit_per_trade"]:.2f}

🔍 **Cost Basis Details:**
• Records: {cost_basis_summary.get("total_cost_basis_records", 0)}
• Initial Investment: ${cost_basis_summary.get("total_initial_investment", 0):.2f}
• Method: {fifo_performance["calculation_method"]}

**Accuracy:** {"✅ VERIFIED" if validation["validation_passed"] else "📊 CALCULATED"}"""

    def _build_fifo_report_keyboard(self, cost_basis_summary: dict) -> list:
        """Build FIFO report keyboard"""
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="show_fifo_report")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
        ]
        return keyboard

    async def _send_or_edit_message(self, update, message: str, keyboard: list):
        """Send or edit message based on update type"""
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

    async def _send_success_message(
        self, query, result: dict, symbol: str, usdt_amount: float
    ):
        """Send success message for Pure USDT initialization"""
        init_details = result["initialization_results"]

        message = f"""🎉 **Pure USDT Grid Initialized!**

✅ **{symbol}/USDT Perfect FIFO Tracking**

💰 **Pure USDT Investment:**
• Total USDT: ${usdt_amount:,.2f}
• USDT Reserve: ${init_details["initialization"]["usdt_reserve"]:.2f}
• Asset Purchase: {init_details["initialization"]["asset_quantity"]:.4f} {symbol}
• Cost Basis: ${init_details["initialization"]["asset_cost_basis"]:.4f}

🎯 **Perfect FIFO Tracking ACTIVE:**
✅ All future sells have accurate cost basis
✅ Real profit calculations from day one
✅ Professional-grade accounting
✅ Zero cost basis guesswork

📊 **Your Account Status:**
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
• Minimum amount is ${self.MIN_TRADE_AMOUNT} USDT
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

    async def _show_setup_required(self, query):
        """Show setup required message"""
        message = """❌ **Cannot Start Trading**

Please complete your setup first:
• Set up API keys
• Configure trading capital"""

        keyboard = [
            [InlineKeyboardButton("🔐 Setup API Keys", callback_data="setup_api")],
            [InlineKeyboardButton("💰 Set Capital", callback_data="set_capital")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_command_help(self, update):
        """Show command help message"""
        keyboard = [
            [InlineKeyboardButton("🚀 Start Trading", callback_data="start_trading")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="home")],
        ]

        await update.message.reply_text(
            """🧠 **Smart Trading Commands:**
• `ETH 2000` - Start ETH grid with $2000
• `SOL 1500` - Start SOL grid with $1500
• `ADA 1000` - Start ADA grid with $1000
• `/admin` - Admin panel (admins only)

**Or use the buttons below:**""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _send_error_fallback(self, query, error_text: str):
        """Send generic error fallback message"""
        await query.edit_message_text(
            f"❌ **{error_text}**\n\nPlease try again later.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📊 Dashboard", callback_data="home")]]
            ),
        )
