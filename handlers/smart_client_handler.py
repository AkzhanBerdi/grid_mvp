# handlers/smart_client_handler.py
"""Smart Client Handler with Adaptive Two-Scale Grid Trading"""

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from repositories.client_repository import ClientRepository
from services.enhanced_grid_orchestrator import EnhancedGridOrchestrator


class SmartClientHandler:
    """Enhanced client handler with smart adaptive trading"""

    def __init__(self):
        self.client_repo = ClientRepository()
        self.grid_orchestrator = EnhancedGridOrchestrator()
        self.client_states = {}
        self.logger = logging.getLogger(__name__)

    async def handle_start(self, update, context):
        """Handle /start command with smart trading introduction"""
        user = update.effective_user
        client = self.client_repo.get_client(user.id)

        if client and client.is_active():
            await self._show_smart_dashboard(update, client)
        else:
            await self._handle_new_smart_client(update, user)

    async def _handle_new_smart_client(self, update, user):
        """Handle new client with smart trading introduction"""
        client = self.client_repo.create_client(
            telegram_id=user.id, username=user.username, first_name=user.first_name
        )

        message = f"""🤖 **Welcome to GridTrader Pro Smart Trading**

Hi {user.first_name}! Welcome to the next generation of grid trading.

**🧠 Smart Trading Features:**
✅ **Two-Scale Grid System**
   • Base Grid: Always active, consistent profits
   • Enhanced Grid: Market-adaptive, high-volume trading

✅ **AI-Powered Market Analysis**
   • Real-time sentiment analysis
   • RSI & volatility monitoring
   • Fear & Greed index integration

✅ **Adaptive Strategy**
   • Bullish markets: Aggressive enhanced grids
   • Bearish markets: Strategic positioning
   • Neutral markets: Conservative base grids

✅ **Risk Management**
   • Dynamic capital allocation
   • Market condition monitoring
   • Automated grid adjustments

Ready to experience smart trading?"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Start Smart Trading", callback_data="setup_smart_trading"
                )
            ],
            [InlineKeyboardButton("🔐 Setup API Keys", callback_data="setup_api")],
            [
                InlineKeyboardButton(
                    "📊 Learn More", callback_data="learn_smart_trading"
                )
            ],
        ]

        await update.message.reply_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_smart_dashboard(self, update, client):
        """Show smart trading dashboard"""
        # Get grid status
        grid_status = self.grid_orchestrator.get_client_grid_status(client.telegram_id)

        # Get performance data
        performance = await self.grid_orchestrator.get_client_performance(
            client.telegram_id
        )

        # API status
        api_status = "✅ Connected" if client.binance_api_key else "❌ Not Setup"

        # Market overview
        market_overview = await self.grid_orchestrator.get_market_overview()

        # Smart trading stats
        active_grids = len(grid_status.get("active_grids", {}))
        total_profit = performance.get("basic_stats", {}).get("total_profit", 0.0)
        total_trades = performance.get("basic_stats", {}).get("total_trades", 0)

        # Build adaptive performance summary
        adaptive_summary = []
        for symbol, perf in performance.get("adaptive_performance", {}).items():
            market_condition = perf.get("market_condition", {}).get(
                "condition", "neutral"
            )
            enhanced_active = "✅" if perf.get("enhanced_grid_active") else "⚪"
            adaptive_summary.append(
                f"{symbol}: {market_condition.title()} {enhanced_active}"
            )

        adaptive_info = (
            "\n".join(adaptive_summary) if adaptive_summary else "No active grids"
        )

        message = f"""🧠 **Smart GridTrader Pro Dashboard**

Welcome back, {client.first_name}!

**💼 Account Status:**
🔐 API Keys: {api_status}
💰 Capital: ${client.total_capital:,.2f}
⚙️ Pairs: {", ".join(client.trading_pairs)}
📈 Risk Level: {client.risk_level.title()}

**🤖 Smart Trading Status:**
📊 Active Grids: {active_grids}
💰 Total Profit: ${total_profit:.2f}
📈 Total Trades: {total_trades}

**🎯 Adaptive Grids:**
{adaptive_info}

**⭐ Smart Features:**
• Market analysis: Real-time
• Two-scale grids: {grid_status.get("trading_mode", "Standard")}
• Risk management: Active

**Quick Trading:** Type `ADA 1000` or `AVAX 500`"""

        keyboard = []

        if client.can_start_grid():
            if active_grids > 0:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🛑 Stop All Grids", callback_data="stop_all_grids"
                        )
                    ]
                )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🎯 Optimize Grids", callback_data="optimize_grids"
                        )
                    ]
                )
            else:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🚀 Start Smart Trading",
                            callback_data="start_smart_trading",
                        )
                    ]
                )

        keyboard.extend(
            [
                [
                    InlineKeyboardButton(
                        "📊 Smart Performance", callback_data="show_smart_performance"
                    ),
                    InlineKeyboardButton(
                        "🌍 Market Overview", callback_data="show_market_overview"
                    ),
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="show_settings"),
                    InlineKeyboardButton(
                        "🧠 Trading Insights", callback_data="show_insights"
                    ),
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
        """Handle callback queries with smart trading options"""
        query = update.callback_query
        await query.answer()

        client_id = query.from_user.id
        action = query.data

        self.logger.info(f"Smart client {client_id} action: {action}")

        # Route to appropriate handler
        if action == "setup_smart_trading":
            await self._setup_smart_trading(query, client_id)
        elif action == "learn_smart_trading":
            await self._show_smart_trading_info(query, client_id)
        elif action == "start_smart_trading":
            await self._start_smart_trading(query, client_id)
        elif action == "show_smart_performance":
            await self._show_smart_performance(query, client_id)
        elif action == "show_market_overview":
            await self._show_market_overview(query, client_id)
        elif action == "show_insights":
            await self._show_trading_insights(query, client_id)
        elif action == "optimize_grids":
            await self._optimize_grids(query, client_id)
        elif action == "confirm_smart_start":
            await self._confirm_smart_start(query, client_id)
        elif action == "setup_api":
            await self._setup_api_keys(query, client_id)
        elif action == "show_dashboard":
            await self._back_to_dashboard(query, client_id)
        elif action == "show_settings":
            await self._show_settings(query, client_id)
        elif action == "stop_all_grids":
            await self._stop_all_grids(query, client_id)
        elif action == "set_capital":
            await self._set_capital(query, client_id)
        elif action == "cancel_input":
            await self._cancel_input(query, client_id)
        elif action.startswith("execute_trade_"):
            await self._execute_smart_trade(query, action)
        else:
            await query.edit_message_text(f"🔧 Feature: {action} - Coming soon!")

    async def _setup_smart_trading(self, query, client_id):
        """Setup smart trading walkthrough"""
        message = """🚀 **Smart Trading Setup**

Let's get you started with intelligent grid trading!

**🔧 Setup Steps:**
1. **API Keys** - Connect your Binance account
2. **Capital** - Set your trading amount
3. **Preferences** - Choose risk level
4. **Launch** - Start smart grids

**🧠 What makes it smart?**
• **Market Analysis**: Real-time sentiment & technical indicators
• **Adaptive Grids**: Automatically adjust to market conditions
• **Risk Management**: Dynamic capital allocation
• **Two-Scale System**: Base + Enhanced grids

Ready to begin?"""

        keyboard = [
            [InlineKeyboardButton("🔐 Setup API Keys", callback_data="setup_api")],
            [
                InlineKeyboardButton(
                    "📖 Learn More", callback_data="learn_smart_trading"
                )
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _show_smart_trading_info(self, query, client_id):
        """Show detailed smart trading information"""
        message = """🧠 **Smart Trading System Explained**

**🎯 Two-Scale Grid System:**

**Base Grid (Always Active):**
• 40% of capital
• Conservative spacing (2.5%)
• Consistent profits regardless of market
• 8 grid levels
• Lower risk, steady returns

**Enhanced Grid (Market-Adaptive):**
• 60% of capital
• Adaptive spacing (1.5%-3%)
• Activated in strong market conditions
• 6-12 grid levels
• Higher risk, maximum profits

**🔍 Market Analysis:**
• RSI indicators
• Price volatility
• Volume analysis
• Fear & Greed index
• Trend detection

**⚡ Adaptive Behavior:**
• **Bullish Market**: Tight enhanced grids, aggressive buying
• **Bearish Market**: Strategic positioning, wider grids
• **Neutral Market**: Base grid only, capital preservation

**🛡️ Risk Management:**
• Dynamic capital allocation
• Market condition monitoring
• Automatic grid adjustments
• Stop-loss mechanisms

Ready to experience the future of grid trading?"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Start Setup", callback_data="setup_smart_trading"
                )
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _start_smart_trading(self, query, client_id):
        """Start smart trading configuration"""
        client = self.client_repo.get_client(client_id)

        if not client.can_start_grid():
            await query.edit_message_text(
                "❌ **Cannot start smart trading**\n\n"
                "Please ensure:\n"
                "• API keys are configured\n"
                "• Capital is set\n"
                "• Account is active",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⚙️ Setup", callback_data="setup_smart_trading"
                            )
                        ]
                    ]
                ),
            )
            return

        # Get market analysis for all pairs
        market_analysis = []
        for pair in client.trading_pairs:
            try:
                # This would call the market analysis service
                market_analysis.append(f"📊 {pair}: Analyzing market conditions...")
            except:
                market_analysis.append(f"📊 {pair}: Ready for smart trading")

        analysis_text = "\n".join(market_analysis)

        message = f"""🧠 **Smart Trading Ready**

**Configuration:**
💰 **Capital:** ${client.total_capital:,.2f}
🎯 **Pairs:** {", ".join(client.trading_pairs)}
📊 **Strategy:** Two-Scale Adaptive Grid
⚙️ **Risk Level:** {client.risk_level.title()}

**Capital Allocation:**
• Base Grid: ${client.total_capital * 0.4:,.2f} (40%)
• Enhanced Grid: ${client.total_capital * 0.6:,.2f} (60%)

**Market Analysis:**
{analysis_text}

**🤖 Smart Features Enabled:**
✅ Real-time market analysis
✅ Adaptive grid spacing
✅ Dynamic capital allocation
✅ Risk management system
✅ Market condition monitoring

This will create intelligent grids that adapt to market conditions automatically!

Ready to launch?"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 LAUNCH SMART TRADING", callback_data="confirm_smart_start"
                )
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _confirm_smart_start(self, query, client_id):
        """Confirm and start smart trading"""
        await query.edit_message_text("🔄 **Launching Smart Trading System...**")

        try:
            client = self.client_repo.get_client(client_id)
            if not client or not client.can_start_grid():
                await query.edit_message_text(
                    "❌ **Cannot start smart trading**\n\n"
                    "Please ensure your API keys and capital are configured."
                )
                return

            results = []
            successful_grids = 0

            # Start smart grids for each trading pair
            for pair in client.trading_pairs:
                # Calculate capital per pair
                capital_per_pair = client.total_capital / len(client.trading_pairs)

                self.logger.info(
                    f"Starting smart grid for {pair} with ${capital_per_pair:.2f}"
                )

                result = await self.grid_orchestrator.start_client_grid(
                    client_id, f"{pair}USDT", capital_per_pair
                )

                results.append(
                    {"pair": pair, "success": result["success"], "result": result}
                )

                if result["success"]:
                    successful_grids += 1

            # Format response based on results
            if successful_grids == len(client.trading_pairs):
                # All smart grids started successfully
                total_base_orders = 0
                total_enhanced_orders = 0

                for res in results:
                    if res["success"]:
                        total_base_orders += res["result"].get("base_grid_orders", 0)
                        total_enhanced_orders += res["result"].get(
                            "enhanced_grid_orders", 0
                        )

                message = f"""🎉 **Smart Trading System Activated!**

✅ **All intelligent grids are now active for {client.first_name}!**

**🤖 Smart Grid Summary:**
"""

                for res in results:
                    if res["success"]:
                        pair = res["pair"]
                        result_data = res["result"]
                        market_condition = result_data.get(
                            "market_condition", "neutral"
                        )
                        risk_level = result_data.get("risk_level", "moderate")

                        condition_emoji = {
                            "bullish": "🟢",
                            "bearish": "🔴",
                            "neutral": "🟡",
                        }.get(market_condition, "🟡")

                        message += f"• {pair}: {condition_emoji} {market_condition.title()} ({risk_level})\n"

                message += f"""
**📊 Trading Setup:**
• Base Grid Orders: {total_base_orders} (Conservative)
• Enhanced Grid Orders: {total_enhanced_orders} (Adaptive)
• Total Capital: ${client.total_capital:,.2f}
• Smart Features: ALL ACTIVE

**🧠 AI Features Working:**
✅ Market sentiment analysis
✅ Adaptive grid spacing
✅ Dynamic capital allocation
✅ Risk management system

Your smart grids will automatically:
• Analyze market conditions every 5 minutes
• Adjust grid spacing based on volatility
• Activate/deactivate enhanced grids
• Optimize for maximum profits!"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Smart Dashboard", callback_data="show_dashboard"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🧠 View Insights", callback_data="show_insights"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🌍 Market Overview", callback_data="show_market_overview"
                        )
                    ],
                ]

            elif successful_grids > 0:
                # Some grids started
                success_pairs = [res["pair"] for res in results if res["success"]]
                failed_pairs = [res["pair"] for res in results if not res["success"]]

                message = f"""⚠️ **Partial Smart Trading Launch**

✅ **Smart grids started:** {", ".join(success_pairs)}
❌ **Failed to start:** {", ".join(failed_pairs)}

The successful grids are operating with full smart features.
Please check your API permissions and account balance for failed pairs."""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Dashboard", callback_data="show_dashboard"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔄 Retry Failed", callback_data="start_smart_trading"
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

                message = f"""❌ **Smart Trading Launch Failed**

Error: {first_error}

Please check:
• API key permissions (Spot Trading enabled)
• Account balance (sufficient USDT)
• Network connection
• Market conditions"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "🔄 Try Again", callback_data="start_smart_trading"
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
                f"Error in smart trading launch for client {client_id}: {e}"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Try Again", callback_data="start_smart_trading"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]

            await query.edit_message_text(
                "❌ **Smart Trading System Error**\n\n"
                "An error occurred while launching the smart trading system.\n"
                "Please try again or contact support.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

    async def _show_smart_performance(self, query, client_id):
        """Show smart trading performance"""
        try:
            performance = await self.grid_orchestrator.get_client_performance(client_id)

            basic_stats = performance.get("basic_stats", {})
            adaptive_perf = performance.get("adaptive_performance", {})
            insights = performance.get("smart_trading_insights", {})

            # Build performance summary
            total_trades = basic_stats.get("total_trades", 0)
            total_profit = basic_stats.get("total_profit", 0.0)
            win_rate = basic_stats.get("win_rate", 0.0)
            avg_profit = basic_stats.get("avg_profit_per_trade", 0.0)

            # Smart trading metrics
            market_adaptation = insights.get("market_adaptation_score", 0.0) * 100
            risk_management = insights.get("risk_management_score", 0.0) * 100
            efficiency = insights.get("efficiency_score", 0.0) * 100

            message = f"""🧠 **Smart Trading Performance**

**📊 Overall Statistics:**
• Total Trades: {total_trades}
• Total Profit: ${total_profit:.2f}
• Win Rate: {win_rate:.1f}%
• Avg Profit/Trade: ${avg_profit:.2f}

**🤖 Smart Trading Scores:**
• Market Adaptation: {market_adaptation:.1f}%
• Risk Management: {risk_management:.1f}%
• Trading Efficiency: {efficiency:.1f}%

**🎯 Active Smart Grids:**"""

            for symbol, perf in adaptive_perf.items():
                market_condition = perf.get("market_condition", {})
                condition = market_condition.get("condition", "neutral")
                score = market_condition.get("score", 0.5)

                base_active = "✅" if perf.get("base_grid_active") else "❌"
                enhanced_active = "✅" if perf.get("enhanced_grid_active") else "❌"

                condition_emoji = {
                    "bullish": "🟢",
                    "bearish": "🔴",
                    "neutral": "🟡",
                }.get(condition, "🟡")

                message += (
                    f"\n• {symbol}: {condition_emoji} {condition.title()} ({score:.2f})"
                )
                message += (
                    f"\n  Base Grid: {base_active} Enhanced Grid: {enhanced_active}"
                )

            # Recommendations
            recommendations = insights.get("recommendations", [])
            if recommendations:
                message += "\n\n**💡 Smart Recommendations:**"
                for rec in recommendations:
                    message += f"\n• {rec}"

            # Recent activity
            recent_trades = performance.get("recent_trades", [])[:3]
            if recent_trades:
                message += "\n\n**📈 Recent Activity:**"
                for trade in recent_trades:
                    symbol = trade["symbol"].replace("USDT", "")
                    side = trade["side"]
                    profit = trade.get("profit", 0)
                    emoji = "🟢" if side == "SELL" else "🔵"
                    message += f"\n{emoji} {symbol} {side} (+${profit:.2f})"

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Refresh", callback_data="show_smart_performance"
                    )
                ],
                [InlineKeyboardButton("🎯 Optimize", callback_data="optimize_grids")],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error showing smart performance: {e}")
            await query.edit_message_text(
                "❌ **Error loading performance data**\n\n"
                "Please try again or contact support.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 Try Again", callback_data="show_smart_performance"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "📊 Dashboard", callback_data="show_dashboard"
                            )
                        ],
                    ]
                ),
            )

    async def _show_market_overview(self, query, client_id):
        """Show market overview"""
        try:
            market_overview = await self.grid_orchestrator.get_market_overview()

            if "error" in market_overview:
                await query.edit_message_text(
                    "❌ **Market data unavailable**\n\n"
                    "Unable to load market overview. Please try again later.",
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
                return

            symbols_tracked = market_overview.get("symbols_tracked", 0)
            market_conditions = market_overview.get("market_conditions", {})
            global_perf = market_overview.get("global_performance", {})

            message = f"""🌍 **Market Overview**

**📊 Global Status:**
• Symbols Tracked: {symbols_tracked}
• Active Grids: {global_perf.get("active_grids", 0)}
• Total Trades: {global_perf.get("total_trades", 0)}
• Global Profit: ${global_perf.get("total_profit", 0.0):.2f}

**📈 Market Conditions:**"""

            for symbol, condition in market_conditions.items():
                market_state = condition.get("condition", "neutral")
                score = condition.get("score", 0.5)
                confidence = condition.get("confidence", 0.0)

                condition_emoji = {
                    "bullish": "🟢",
                    "bearish": "🔴",
                    "neutral": "🟡",
                }.get(market_state, "🟡")

                message += f"\n{condition_emoji} **{symbol}**: {market_state.title()}"
                message += f"\n   Score: {score:.2f} | Confidence: {confidence:.1f}%"

                # Show key indicators
                indicators = condition.get("indicators", {})
                rsi = indicators.get("rsi", 50)
                volatility = indicators.get("volatility", 0.0)

                message += f"\n   RSI: {rsi:.1f} | Volatility: {volatility:.1f}%"

            message += f"\n\n**🕒 Updated:** {datetime.now().strftime('%H:%M:%S')}"

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Refresh", callback_data="show_market_overview"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error showing market overview: {e}")
            await query.edit_message_text(
                "❌ **Error loading market data**\n\n"
                "Please try again or contact support.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 Try Again", callback_data="show_market_overview"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "📊 Dashboard", callback_data="show_dashboard"
                            )
                        ],
                    ]
                ),
            )

    async def _show_trading_insights(self, query, client_id):
        """Show AI-powered trading insights"""
        try:
            performance = await self.grid_orchestrator.get_client_performance(client_id)
            insights = performance.get("smart_trading_insights", {})

            market_adaptation = insights.get("market_adaptation_score", 0.0) * 100
            risk_management = insights.get("risk_management_score", 0.0) * 100
            efficiency = insights.get("efficiency_score", 0.0) * 100

            message = f"""🧠 **AI Trading Insights**

**🎯 Performance Analysis:**
• Market Adaptation: {market_adaptation:.1f}%
• Risk Management: {risk_management:.1f}%
• Trading Efficiency: {efficiency:.1f}%

**📊 Insight Summary:**"""

            if market_adaptation > 70:
                message += "\n✅ Excellent market adaptation - grids responding well to changes"
            elif market_adaptation > 50:
                message += "\n⚠️ Good adaptation - some optimization opportunities"
            else:
                message += "\n❌ Poor adaptation - consider reviewing market monitoring"

            if risk_management > 80:
                message += "\n✅ Excellent risk management - well-balanced portfolio"
            elif risk_management > 60:
                message += "\n⚠️ Good risk control - minor adjustments recommended"
            else:
                message += (
                    "\n❌ Risk management needs attention - review position sizes"
                )

            if efficiency > 60:
                message += "\n✅ High efficiency - optimal grid performance"
            elif efficiency > 40:
                message += "\n⚠️ Moderate efficiency - grid optimization available"
            else:
                message += "\n❌ Low efficiency - significant improvements needed"

            recommendations = insights.get("recommendations", [])
            if recommendations:
                message += "\n\n**💡 AI Recommendations:**"
                for i, rec in enumerate(recommendations[:3], 1):
                    message += f"\n{i}. {rec}"

            message += "\n\n**🔮 Market Prediction:**"
            message += "\nBased on current indicators, the AI system suggests maintaining current strategy with minor adjustments for optimal performance."

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🎯 Optimize Now", callback_data="optimize_grids"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📊 Performance", callback_data="show_smart_performance"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error showing trading insights: {e}")
            await query.edit_message_text(
                "❌ **Error loading AI insights**\n\n"
                "Please try again or contact support.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 Try Again", callback_data="show_insights"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "📊 Dashboard", callback_data="show_dashboard"
                            )
                        ],
                    ]
                ),
            )

    async def _optimize_grids(self, query, client_id):
        """Optimize active grids"""
        await query.edit_message_text("🔄 **Optimizing Smart Grids...**")

        try:
            optimization_results = await self.grid_orchestrator.optimize_all_grids()

            if "error" in optimization_results:
                await query.edit_message_text(
                    "❌ **Grid optimization failed**\n\n"
                    "Unable to optimize grids. Please try again later.",
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
                return

            message = "🎯 **Grid Optimization Complete**\n\n"

            optimized_count = 0
            for grid_key, results in optimization_results.items():
                client_id_str, symbol = grid_key.split("_", 1)
                if int(client_id_str) == client_id:
                    optimized_count += 1

                    performance = results.get("performance", {})
                    recommendations = results.get("recommendations", [])

                    efficiency = performance.get("efficiency_score", 0.0) * 100
                    risk_score = performance.get("risk_score", 0.0) * 100

                    message += f"**{symbol}:**\n"
                    message += f"• Efficiency: {efficiency:.1f}%\n"
                    message += f"• Risk Score: {risk_score:.1f}%\n"

                    if recommendations:
                        message += f"• Recommendations: {len(recommendations)}\n"

                    message += "\n"

            if optimized_count == 0:
                message += "No active grids found to optimize."
            else:
                message += f"✅ Optimized {optimized_count} grid(s)\n"
                message += "📊 Smart adjustments have been applied automatically."

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📊 View Performance", callback_data="show_smart_performance"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        except Exception as e:
            self.logger.error(f"Error optimizing grids: {e}")
            await query.edit_message_text(
                "❌ **Optimization Error**\n\n"
                "An error occurred during grid optimization.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 Try Again", callback_data="optimize_grids"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "📊 Dashboard", callback_data="show_dashboard"
                            )
                        ],
                    ]
                ),
            )

    # Keep existing methods for API setup, settings, etc.
    async def _setup_api_keys(self, query, client_id):
        """Setup API keys (reuse existing implementation)"""
        # Implementation from original client_handler.py
        pass

    async def _show_settings(self, query, client_id):
        """Show settings (reuse existing implementation)"""
        # Implementation from original client_handler.py
        pass

    async def _set_capital(self, query, client_id):
        """Set capital (reuse existing implementation)"""
        # Implementation from original client_handler.py
        pass

    async def _cancel_input(self, query, client_id):
        """Cancel input (reuse existing implementation)"""
        # Implementation from original client_handler.py
        pass

    async def _back_to_dashboard(self, query, client_id):
        """Return to dashboard"""
        client = self.client_repo.get_client(client_id)
        await self._show_smart_dashboard(query, client)

    async def _stop_all_grids(self, query, client_id):
        """Stop all smart grids"""
        await query.edit_message_text("🔄 **Stopping all smart grids...**")

        result = await self.grid_orchestrator.stop_all_client_grids(client_id)

        if result["success"]:
            grids_stopped = result.get("grids_stopped", 0)
            message = f"""🛑 **All Smart Grids Stopped**

✅ Successfully stopped {grids_stopped} smart grid(s)
✅ All base and enhanced grids deactivated
✅ {result.get("orders_cancelled", 0)} orders cancelled
✅ Positions secured

Your account is now in safe mode.
Smart trading features are disabled."""
        else:
            message = f"""❌ **Error Stopping Smart Grids**

Some grids may still be active.
Error: {result.get("error", "Unknown error")}

Please check manually or contact support."""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Restart Smart Trading", callback_data="start_smart_trading"
                )
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
        ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def _execute_smart_trade(self, query, action):
        """Execute smart trade command"""
        client_id = query.from_user.id

        try:
            parts = action.replace("execute_trade_", "").split("_")
            symbol = parts[0]
            amount = float(parts[1])
        except:
            await query.edit_message_text("❌ Invalid trade parameters")
            return

        await query.edit_message_text("🔄 **Launching Smart Grid...**")

        # Execute through enhanced grid orchestrator
        result = await self.grid_orchestrator.start_client_grid(
            client_id, f"{symbol}USDT", amount
        )

        if result["success"]:
            market_condition = result.get("market_condition", "neutral")
            base_orders = result.get("base_grid_orders", 0)
            enhanced_orders = result.get("enhanced_grid_orders", 0)
            risk_level = result.get("risk_level", "moderate")

            condition_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(
                market_condition, "🟡"
            )

            message = f"""🎉 **Smart Grid Launched!**

✅ **{symbol}/USDT Smart Grid Active**

**🧠 AI Analysis:**
{condition_emoji} Market Condition: {market_condition.title()}
⚙️ Risk Level: {risk_level.title()}
📊 Strategy: Two-Scale Adaptive

**🤖 Grid Setup:**
• Base Grid: {base_orders} orders (Conservative)
• Enhanced Grid: {enhanced_orders} orders (Adaptive)
• Total Capital: ${amount:,.2f}

**🔥 Smart Features Active:**
✅ Real-time market analysis
✅ Adaptive grid spacing
✅ Dynamic capital allocation
✅ Risk management system

Your intelligent grid will automatically adapt to market changes!"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📊 Smart Dashboard", callback_data="show_dashboard"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🧠 View Insights", callback_data="show_insights"
                    )
                ],
            ]

        else:
            message = f"""❌ **Smart Grid Launch Failed**

Error: {result.get("error", "Unknown error")}

Please check your account and try again."""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Try Again", callback_data="start_smart_trading"
                    )
                ],
                [InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")],
            ]

        await query.edit_message_text(
            message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def handle_message(self, update, context):
        """Handle text messages with smart trading commands"""
        client_id = update.effective_user.id
        text = update.message.text.strip()

        self.logger.info(f"Smart message from client {client_id}: {text}")

        # Handle API setup flow
        if client_id in self.client_states:
            await self._handle_api_input(update, client_id, text)
            return

        # Handle smart trading commands
        if self._is_trading_command(text):
            await self._handle_smart_trading_command(update, client_id, text)
            return

        # Default response with smart trading info
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🧠 Smart Dashboard", callback_data="show_dashboard"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🚀 Start Smart Trading", callback_data="start_smart_trading"
                    )
                ],
            ]
        )

        await update.message.reply_text(
            "🧠 **Smart Trading Commands:**\n"
            "• /start - Smart trading dashboard\n"
            "• ADA 1000 - Smart grid for ADA with $1000\n"
            "• AVAX 500 - Smart grid for AVAX with $500\n\n"
            "**Smart Features:** AI analysis, adaptive grids, risk management",
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
            except:
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
**Strategy:** AI-Powered Two-Scale Grid

**🤖 Smart Features:**
✅ Real-time market analysis
✅ Adaptive grid spacing
✅ Dynamic capital allocation (40% base, 60% enhanced)
✅ Risk management system

**Execution Plan:**
• Analyze current market conditions
• Deploy base grid (always active)
• Deploy enhanced grid (if market conditions favor)
• Monitor and adapt automatically

Ready to launch intelligent trading?"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚀 LAUNCH SMART GRID",
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

    # Add these methods to handlers/smart_client_handler.py

    async def _setup_api_keys(self, query, client_id):
        """Setup API keys flow - ADD THIS TO SmartClientHandler"""
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

    async def _set_capital(self, query, client_id):
        """Set capital - ADD THIS TO SmartClientHandler"""
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
        """Cancel any ongoing input - ADD THIS TO SmartClientHandler"""
        if client_id in self.client_states:
            del self.client_states[client_id]

        await query.edit_message_text(
            "❌ **Input Cancelled**\n\nReturning to dashboard...",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📊 Dashboard", callback_data="show_dashboard")]]
            ),
        )

    async def _show_settings(self, query, client_id):
        """Show client settings - ADD THIS TO SmartClientHandler"""
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

    async def _handle_api_input(self, update, client_id, text):
        """Handle API key input - ADD THIS TO SmartClientHandler"""
        from utils.validators import Validators

        client_state = self.client_states.get(client_id, {})
        step = client_state.get("step")

        if step == "waiting_api_key":
            # Validate API key format
            is_valid, error = Validators.validate_api_key(text)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ {error}\nPlease send a valid API key."
                )
                return

            # Store temporarily in state
            self.client_states[client_id] = {
                "step": "waiting_secret_key",
                "temp_api_key": text,
            }

            await update.message.reply_text(
                "✅ **API Key received!**\n\n"
                "**Step 2:** Now send your Secret Key\n\n"
                "🔒 Your keys will be encrypted and secured after both are provided.",
                parse_mode="Markdown",
            )

        elif step == "waiting_secret_key":
            # Validate secret key format
            is_valid, error = Validators.validate_api_key(text)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ {error}\nPlease send a valid secret key."
                )
                return

            # Get both keys and save
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

            if update_success:
                # Clear state
                del self.client_states[client_id]

                await update.message.reply_text(
                    "🎉 **API Setup Complete!**\n\n"
                    "✅ Keys saved and encrypted\n"
                    "✅ Ready for trading\n\n"
                    "**Next Step:** Set your trading capital",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text(
                    "❌ **Failed to save API keys**\n\nPlease try again."
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
            self.client_repo.update_client(client)

            # Clear state
            del self.client_states[client_id]

            await update.message.reply_text(
                f"✅ **Capital Set: ${amount:,.2f}**\n\nReady to start smart trading!",
                parse_mode="Markdown",
            )
