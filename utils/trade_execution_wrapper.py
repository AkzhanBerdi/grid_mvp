# utils/trade_execution_wrapper.py
"""
Trade execution wrapper to ensure FIFO logging happens
"""

import logging


class TradeExecutionWrapper:
    """Wrapper to ensure FIFO logging happens on trade execution"""

    def __init__(self, fifo_service=None):
        self.fifo_service = fifo_service
        self.logger = logging.getLogger(__name__)

    async def log_trade_execution(
        self, client_id: int, symbol: str, side: str, quantity: float, price: float
    ):
        """Log trade execution to FIFO service"""
        try:
            if self.fifo_service:
                await self.fifo_service.on_trade_executed(
                    client_id=client_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                )
                self.logger.info(f"📊 FIFO: {side} {quantity} {symbol} @ ${price:.4f}")
            else:
                self.logger.warning("FIFO service not available")
        except Exception as e:
            self.logger.error(f"FIFO logging failed: {e}")

    def get_profit_stats(self, client_id: int) -> dict:
        """Get current profit stats"""
        try:
            if self.fifo_service and hasattr(self.fifo_service, "monitors"):
                if client_id in self.fifo_service.monitors:
                    calculator = self.fifo_service.monitors[client_id]
                    return calculator.calculate_fifo_profit(client_id)
        except Exception as e:
            self.logger.warning(f"Failed to get profit stats: {e}")

        return {"total_profit": 0.0, "total_trades": 0}
