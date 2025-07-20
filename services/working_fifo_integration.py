# services/working_fifo_integration.py
"""
Working FIFO Integration that bypasses the broken FIFOService
Uses FIFOProfitCalculator directly for accurate results
FIXED: Uses existing telegram_notifier instead of deleted final_perfect_notifier
"""

import logging
from datetime import datetime

from analytics.fifo_profit_tracker import FIFOProfitCalculator
from services.telegram_notifier import TelegramNotifier  # ✅ Use existing notifier


class WorkingFIFOIntegration:
    """Working integration that uses FIFOProfitCalculator directly"""

    def __init__(self, client_id: int):
        self.client_id = client_id
        self.calculator = FIFOProfitCalculator()  # Use working calculator
        self.telegram = TelegramNotifier()  # ✅ Use existing telegram notifier
        self.logger = logging.getLogger(__name__)

        # Milestone tracking
        self.milestones_reached = set()

    async def on_order_filled(
        self, symbol: str, side: str, quantity: float, price: float, level: int = None
    ):
        """Perfect order fill handler with working FIFO data"""
        try:
            # Get profit from working calculator
            performance = self.calculator.calculate_fifo_profit(self.client_id)
            total_profit = performance.get("total_profit", 0)

            order_value = quantity * price
            profit_estimate = 0
            if side == "SELL":
                profit_estimate = order_value * 0.025

            if symbol == "ADAUSDT":
                qty_str = f"{quantity:.1f}"
            else:
                qty_str = f"{quantity:.4f}"

            message = f"""{symbol} {side} ORDER FILLED

Amount: {qty_str} @ ${price:.4f}
Value: ${order_value:.2f}"""

            if level:
                message += f"\nLevel: {level}"

            if profit_estimate > 0:
                message += f"\nEstimated Profit: ${profit_estimate:.2f}"

            message += f"\nTotal Profit: ${total_profit:.2f}"
            message += f"\nTime: {datetime.now().strftime('%H:%M:%S')}"

            # ✅ Use existing telegram notifier (no parse_mode parameter)
            success = await self.telegram.send_message(message)

            # Check milestones with working data
            if side == "SELL" and success:
                milestones = [25, 50, 100, 250, 500, 1000]
                for milestone in milestones:
                    if (
                        total_profit >= milestone
                        and milestone not in self.milestones_reached
                    ):
                        await self._notify_milestone(total_profit, milestone)
                        self.milestones_reached.add(milestone)
                        break

            return success

        except Exception as e:
            self.logger.error(f"Error in working FIFO integration: {e}")
            return False

    async def _notify_milestone(self, total_profit: float, milestone: float):
        """Notify milestone with working data"""
        message = f"""🎉 PROFIT MILESTONE REACHED!

🎯 Milestone: ${milestone:.0f}
💰 Current Profit: ${total_profit:.2f}
👤 Client: {self.client_id}

🚀 Excellent trading performance!"""

        # ✅ Use existing telegram notifier
        await self.telegram.send_message(message)
