# utils/formatters.py
"""Message formatting utilities"""

from typing import Dict


class MessageFormatter:
    """Format messages and data for Telegram display"""

    @staticmethod
    def format_currency(amount: float) -> str:
        """Format currency amount"""
        if amount >= 1000000:
            return f"${amount / 1000000:.2f}M"
        elif amount >= 1000:
            return f"${amount / 1000:.1f}K"
        else:
            return f"${amount:.2f}"

    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage value"""
        return f"{value:.1f}%"

    @staticmethod
    def format_client_dashboard(client, grid_status: Dict) -> str:
        """Format client dashboard message"""
        api_status = "✅ Connected" if client.binance_api_key else "❌ Not Setup"

        active_grids = len(grid_status.get("active_grids", {}))

        if active_grids > 0:
            grid_info = f"\n🤖 Active Grids: {active_grids}"
            total_trades = sum(
                g.get("trades", 0) for g in grid_status["active_grids"].values()
            )
            grid_info += f"\n📊 Total Trades: {total_trades}"
        else:
            grid_info = "\n🤖 No active grids"

        return f"""📊 **GridTrader Pro Dashboard**

Welcome back, {client.first_name}!

**Account Status:**
🔐 API Keys: {api_status}
💰 Capital: {MessageFormatter.format_currency(client.total_capital)}
⚙️ Pairs: {", ".join(client.trading_pairs)}
📈 Risk Level: {client.risk_level.title()}{grid_info}

**Quick Trading:** Type `ADA 1000` or `AVAX 500`"""
