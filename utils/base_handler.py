"""
Base Client Handler - Clean Production Version
=============================================

Shared functionality for all client handlers with minimal code duplication.
"""

import logging
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from repositories.client_repository import ClientRepository
from services.grid_orchestrator import GridOrchestrator


class BaseClientHandler:
    """Clean base handler with shared functionality"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client_repo = ClientRepository()
        self.grid_orchestrator = GridOrchestrator()
        self.client_states = {}

        self.logger.info(
            f"🎯 Base_handler.py using GridOrchestrator instance ID: {id(self.grid_orchestrator)}"
        )

    # CORE SHARED METHODS

    async def handle_common_callbacks(self, query, client_id: int, action: str) -> bool:
        """Handle common callback actions. Returns True if handled."""
        handlers = {
            "setup_api": self.setup_api_keys,
            "show_settings": self.show_settings,
            "stop_all_grids": self.stop_all_grids,
            "set_capital": self.set_capital,
            "cancel_input": self.cancel_input,
            "show_dashboard": self.go_home,
            "home": self.go_home,
        }

        handler = handlers.get(action)
        if handler:
            await handler(query, client_id)
            return True
        return False

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

    # INPUT HANDLERS

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

    async def _handle_secret_input(
        self, update, client_id: int, text: str, state: dict
    ) -> bool:
        """Handle secret key input"""
        secret_key = text.strip()
        if len(secret_key) < 20:
            await update.message.reply_text(
                "❌ Invalid secret key format. Please try again."
            )
            return True

        try:
            # Save API keys
            client = self.client_repo.get_client(client_id)
            client.api_key = state.get("api_key")
            client.secret_key = secret_key
            self.client_repo.update_client(client)

            # Clear state
            del self.client_states[client_id]

            await update.message.reply_text(
                "✅ **API Keys Saved Successfully**\n\n"
                "🔒 Your keys are encrypted and secure.\n"
                "Ready to start trading!"
            )

            await self.show_dashboard(update, client)

        except Exception as e:
            self.logger.error(f"Error saving API keys: {e}")
            await update.message.reply_text(
                "❌ Error saving API keys. Please try again."
            )

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

    # UI METHODS

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
        """Show main dashboard - to be overridden by child classes"""
        try:
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
