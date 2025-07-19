# Updated handlers/smart_client_handler.py
# Fix the "Coming soon" buttons by implementing the actual functionality


from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import SingleGridPortfolioManager
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
        """Handle text messages with smart trading commands - OVERRIDE BASE HANDLER"""
        client_id = update.effective_user.id
        text = update.message.text.strip()

        self.logger.info(f"📨 ClientHandler message from client {client_id}: {text}")

        # Try common message handlers first (from BaseClientHandler)
        try:
            common_handled = await self.handle_common_messages(update, context, text)
            self.logger.info(f"🔍 Common message handled: {common_handled}")
            if common_handled:
                return
        except Exception as e:
            self.logger.error(f"❌ Error in common message handler: {e}")

        # Handle smart trading commands - THIS METHOD EXISTS IN THIS CLASS
        try:
            is_trading_cmd = self._is_trading_command(text)
            self.logger.info(f"🔍 Is trading command: {is_trading_cmd}")

            if is_trading_cmd:
                self.logger.info(
                    f"🎯 Processing as trading command in ClientHandler: {text}"
                )
                try:
                    self.logger.info("🔍 About to call _handle_smart_trading_command")
                    await self._handle_smart_trading_command(update, client_id, text)
                    self.logger.info(
                        "🔍 _handle_smart_trading_command completed successfully"
                    )
                    return
                except Exception as method_error:
                    self.logger.error(
                        f"❌ Error calling _handle_smart_trading_command: {method_error}"
                    )
                    import traceback

                    self.logger.error(
                        f"Method call traceback: {traceback.format_exc()}"
                    )
                    raise
        except Exception as e:
            self.logger.error(f"❌ Error checking/handling trading command: {e}")
            import traceback

            self.logger.error(f"Stack trace: {traceback.format_exc()}")

        # Default response
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
            "• `ETH 2000` - Start ETH grid with $2000\n"
            "• `SOL 1500` - Start SOL grid with $1500\n"
            "• `ADA 1000` - Start ADA grid with $1000\n\n"
            "**Or use the buttons below:**",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    async def _handle_smart_trading_command(self, update, client_id, text):
        """Handle smart trading command like 'ADA 1000' - WITH FULL DEBUGGING"""
        try:
            self.logger.info(
                f"🔍 ENTERING _handle_smart_trading_command: {text} for client {client_id}"
            )

            client = self.client_repo.get_client(client_id)
            self.logger.info(f"🔍 Client retrieved: {client is not None}")

            if not client:
                self.logger.warning(f"🔍 No client found for {client_id}")
                await update.message.reply_text(
                    "❌ Please complete your smart trading setup first."
                )
                return

            if not client.is_active():
                self.logger.warning(
                    f"🔍 Client {client_id} is not active: {client.status}"
                )
                await update.message.reply_text(
                    "❌ Please complete your smart trading setup first."
                )
                return

            self.logger.info("🔍 Client active check passed")

            can_start = client.can_start_grid()
            self.logger.info(f"🔍 Client can start grid: {can_start}")
            self.logger.info(
                f"🔍 Client API key exists: {bool(client.binance_api_key)}"
            )
            self.logger.info(
                f"🔍 Client secret key exists: {bool(client.binance_secret_key)}"
            )
            self.logger.info(f"🔍 Client capital: {client.total_capital}")

            if not can_start:
                await update.message.reply_text(
                    "❌ Please set up your API keys and capital first."
                )
                return

            self.logger.info("🔍 All client checks passed, parsing command")

            # Parse command
            parts = text.upper().split()
            symbol = parts[0]
            amount = float(parts[1])

            self.logger.info(f"🔍 Parsed - Symbol: {symbol}, Amount: ${amount}")

            # Validation
            if amount < 100:
                self.logger.warning(f"🔍 Amount too small: ${amount}")
                await update.message.reply_text("💰 Minimum trading amount: $100")
                return

            if symbol not in ["ADA", "AVAX", "BTC", "ETH", "SOL"]:
                self.logger.warning(f"🔍 Symbol not supported: {symbol}")
                await update.message.reply_text(
                    f"❌ {symbol} not supported yet. Available: ADA, AVAX, BTC, ETH, SOL"
                )
                return

            self.logger.info("🔍 All validations passed, creating confirmation message")

            # Get asset info for display
            asset_names = {
                "ADA": "Cardano",
                "AVAX": "Avalanche",
                "BTC": "Bitcoin",
                "ETH": "Ethereum",
                "SOL": "Solana",
            }
            asset_emojis = {
                "ADA": "🔵",
                "AVAX": "🏔️",
                "BTC": "🟠",
                "ETH": "🔷",
                "SOL": "🟣",
            }

            # Create confirmation message
            message = f"""{asset_emojis.get(symbol, "🔘")} **Smart Grid Trading Setup**

    **Asset:** {asset_names.get(symbol, symbol)} ({symbol}/USDT)
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
                [InlineKeyboardButton("❌ Cancel", callback_data="show_dashboard")],
            ]

            self.logger.info("🔍 Sending confirmation message")

            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

            self.logger.info(f"✅ Smart command processed successfully: {text}")

        except Exception as e:
            self.logger.error(f"❌ EXCEPTION in _handle_smart_trading_command: {e}")
            import traceback

            self.logger.error(f"Full traceback: {traceback.format_exc()}")

            try:
                await update.message.reply_text(
                    "❌ Invalid format. Use: SYMBOL AMOUNT (e.g., ETH 800)"
                )
            except Exception as reply_error:
                self.logger.error(f"❌ Failed to send error message: {reply_error}")

    async def _handle_force_command(self, update, client_id, symbol, amount):
        """Handle FORCE commands that bypass safety checks"""
        try:
            client = self.client_repo.get_client(client_id)
            if not client:
                await update.message.reply_text("❌ Client not found")
                return

            # Force mode bypasses normal safety checks
            symbol_with_usdt = f"{symbol}USDT"

            # Import high-risk portfolio manager
            from services.high_risk_portfolio_manager import HighRiskPortfolioManager

            portfolio_manager = HighRiskPortfolioManager()

            # Get aggressive parameters for this symbol
            params = portfolio_manager.get_optimized_grid_parameters(symbol_with_usdt)

            # Override safety checks and start aggressive grid
            await update.message.reply_text(
                f"🚀 **FORCE MODE ACTIVATED**\n\n"
                f"Symbol: {symbol_with_usdt}\n"
                f"Capital: ${amount:,.2f}\n"
                f"Mode: AGGRESSIVE TRADING\n\n"
                f"⚠️ This bypasses all safety limits!"
            )

            # Start the grid with aggressive parameters
            # You'll need to integrate with your existing grid manager
            # grid_result = await self.grid_manager.start_aggressive_grid(...)

        except Exception as e:
            await update.message.reply_text(f"❌ FORCE command failed: {e}")

    def _is_trading_command(self, text):
        """Check if text is a trading command - WITH ETH AND SOL SUPPORT"""
        try:
            parts = text.strip().upper().split()
            self.logger.info(
                f"🔍 Checking if trading command: '{text}' -> parts: {parts}"
            )

            if len(parts) == 2:
                symbol = parts[0]
                try:
                    amount = float(parts[1])
                    # ✅ ADD ETH AND SOL TO SUPPORTED SYMBOLS
                    is_valid = (
                        symbol in ["ADA", "AVAX", "BTC", "ETH", "SOL"] and amount > 0
                    )
                    self.logger.info(
                        f"🔍 Trading command check: {symbol} ${amount} -> Valid: {is_valid}"
                    )
                    return is_valid
                except ValueError as e:
                    self.logger.warning(
                        f"🔍 Invalid amount in command: {parts[1]} -> {e}"
                    )
                    return False
            else:
                self.logger.info(f"🔍 Wrong number of parts: {len(parts)} (expected 2)")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error checking trading command: {e}")
            return False

    async def handle_portfolio_command(self, update, context):
        """Handle 'PORTFOLIO' command for 3-asset strategy"""
        client_id = update.effective_user.id

        # Extract amount from command (e.g., "PORTFOLIO 5000")
        try:
            text = update.message.text.strip()
            if text.upper().startswith("PORTFOLIO"):
                parts = text.split()
                if len(parts) == 2:
                    total_amount = float(parts[1])

                    if total_amount < 1000:
                        await update.message.reply_text(
                            "💰 Minimum portfolio amount: $1000"
                        )
                        return

                    # Create portfolio manager
                    portfolio = SingleGridPortfolioManager(total_amount)
                    summary = portfolio.get_portfolio_summary()

                    message = f"""💼 **3-Asset Portfolio Strategy**

    **Total Capital:** ${total_amount:,.2f}
    **Strategy:** ETH (40%), SOL (30%), ADA (30%)
    **Total Grids:** 30 (10 per asset)

    **Asset Allocation:**
    🔷 **ETH:** ${summary["assets"]["ETHUSDT"]["capital"]} (40%)
    • Order size: {summary["assets"]["ETHUSDT"]["order_size"]}
    • Expected return: {summary["assets"]["ETHUSDT"]["expected_return"]}

    🟣 **SOL:** ${summary["assets"]["SOLUSDT"]["capital"]} (30%)
    • Order size: {summary["assets"]["SOLUSDT"]["order_size"]}
    • Expected return: {summary["assets"]["SOLUSDT"]["expected_return"]}

    🔵 **ADA:** ${summary["assets"]["ADAUSDT"]["capital"]} (30%)
    • Order size: {summary["assets"]["ADAUSDT"]["order_size"]}
    • Expected return: {summary["assets"]["ADAUSDT"]["expected_return"]}

    **Portfolio Metrics:**
    📊 Risk Profile: {summary["risk_profile"]}
    📈 Expected Return: {summary["expected_annual_return"]}
    📉 Max Drawdown: {summary["max_drawdown_estimate"]}

    Ready to deploy all 30 grids?"""

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "🚀 DEPLOY PORTFOLIO",
                                callback_data=f"deploy_portfolio_{int(total_amount)}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "❌ Cancel", callback_data="show_dashboard"
                            )
                        ],
                    ]

                    await update.message.reply_text(
                        message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="Markdown",
                    )
                    return

        except Exception as e:
            self.logger.error(f"Error handling portfolio command: {e}")

        await update.message.reply_text(
            "💼 **Portfolio Command Usage:**\n\n"
            "`PORTFOLIO 5000` - Deploy 3-asset strategy with $5000\n"
            "`PORTFOLIO 10000` - Deploy 3-asset strategy with $10000\n\n"
            "**Strategy:** ETH (40%), SOL (30%), ADA (30%)\n"
            "**Total Grids:** 30 (10 per asset)"
        )

    async def handle_portfolio_deployment(self, query, total_amount: float):
        """Deploy the complete 3-asset portfolio"""
        client_id = query.from_user.id

        try:
            await query.edit_message_text("🔄 **Deploying 3-Asset Portfolio...**")

            portfolio = SingleGridPortfolioManager(total_amount)

            # Deploy each asset sequentially
            deployment_results = {}

            for symbol in ["ETHUSDT", "SOLUSDT", "ADAUSDT"]:
                config = portfolio.get_asset_configuration(symbol)

                self.logger.info(
                    f"🚀 Deploying {symbol} with ${config['capital']:,.2f}"
                )

                # Use your existing grid deployment
                result = await self.grid_orchestrator.start_client_grid(
                    client_id, symbol, config["capital"]
                )

                deployment_results[symbol] = {
                    "success": result.get("success", False),
                    "orders": result.get("total_orders_placed", 0),
                    "capital": config["capital"],
                    "error": result.get("error", None),
                }

                # Small delay between deployments
                await asyncio.sleep(2)

            # Calculate results
            successful_deploys = sum(
                1 for r in deployment_results.values() if r["success"]
            )
            total_orders = sum(r["orders"] for r in deployment_results.values())
            total_deployed = sum(
                r["capital"] for r in deployment_results.values() if r["success"]
            )

            if successful_deploys == 3:
                message = f"""🎉 **Portfolio Deployment Complete!**

    ✅ **All 3 Assets Deployed Successfully**

    **Deployment Summary:**
    🔷 ETH: {deployment_results["ETHUSDT"]["orders"]} orders
    🟣 SOL: {deployment_results["SOLUSDT"]["orders"]} orders  
    🔵 ADA: {deployment_results["ADAUSDT"]["orders"]} orders

    **Portfolio Status:**
    📊 Total Orders: {total_orders}
    💰 Capital Deployed: ${total_deployed:,.2f}
    🎯 Strategy: ACTIVE 24/7

    Your diversified portfolio is now hunting for profits across 3 major cryptocurrencies!"""
            else:
                failed_assets = [
                    s for s, r in deployment_results.items() if not r["success"]
                ]
                message = f"""⚠️ **Partial Portfolio Deployment**

    **Successful:** {successful_deploys}/3 assets
    **Failed:** {", ".join(failed_assets)}

    **Next Steps:**
    1. Check API permissions
    2. Verify sufficient balance
    3. Retry failed deployments

    Contact support if issues persist."""

            keyboard = [
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")]
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Portfolio deployment error: {e}")
            await query.edit_message_text(
                f"❌ **Portfolio Deployment Failed**\n\nError: {str(e)}\n\nPlease try again or contact support."
            )
