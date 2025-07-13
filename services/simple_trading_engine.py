"""Ultra-simple real trading engine"""

import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException

class SimpleTradingEngine:
    def __init__(self, api_key: str, secret_key: str, testnet: bool = True):
        self.client = Client(api_key, secret_key, testnet=testnet)
        self.logger = logging.getLogger(__name__)
        self.active_grids = {}
    
    async def start_simple_grid(self, user_id: int, symbol: str, capital_usdt: float):
        """Any coin + amount → instant 50/50 split + grid trading"""
        try:
            trading_pair = f"{symbol.upper()}USDT"
            
            # Get current price
            ticker = self.client.get_symbol_ticker(symbol=trading_pair)
            current_price = float(ticker['price'])
            
            # 50/50 split
            buy_amount = capital_usdt * 0.5  # USDT to buy the coin
            reserve_amount = capital_usdt * 0.5  # USDT for grid orders
            
            # Execute immediate market buy (50% of capital)
            buy_order = self.client.order_market_buy(
                symbol=trading_pair,
                quoteOrderQty=buy_amount
            )
            
            # Get how much coin we actually got
            coin_bought = float(buy_order['executedQty'])
            
            # Place grid orders
            self._place_simple_grid(trading_pair, current_price, reserve_amount, coin_bought)
            
            self.active_grids[user_id] = {
                'pair': trading_pair,
                'entry_price': current_price,
                'capital': capital_usdt
            }
            
            return {
                'success': True,
                'pair': trading_pair,
                'entry_price': current_price,
                'coin_bought': coin_bought,
                'usdt_reserved': reserve_amount
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _place_simple_grid(self, pair, price, usdt_amount, coin_amount):
        """Place 5 buy + 5 sell orders"""
        spacing = 0.02  # 2%
        
        # 5 buy orders below price
        usdt_per_order = usdt_amount / 5
        for i in range(1, 6):
            buy_price = price * (1 - spacing * i)
            quantity = usdt_per_order / buy_price
            
            try:
                self.client.order_limit_buy(
                    symbol=pair,
                    quantity=f"{quantity:.6f}",
                    price=f"{buy_price:.6f}"
                )
            except Exception as e:
                self.logger.error(f"Buy order failed: {e}")
        
        # 5 sell orders above price
        coin_per_order = coin_amount / 5
        for i in range(1, 6):
            sell_price = price * (1 + spacing * i)
            
            try:
                self.client.order_limit_sell(
                    symbol=pair,
                    quantity=f"{coin_per_order:.6f}",
                    price=f"{sell_price:.6f}"
                )
            except Exception as e:
                self.logger.error(f"Sell order failed: {e}")
    
    def get_status(self, user_id):
        """Get trading status"""
        if user_id in self.active_grids:
            grid = self.active_grids[user_id]
            try:
                open_orders = self.client.get_open_orders(symbol=grid['pair'])
                return {
                    'active': True,
                    'pair': grid['pair'],
                    'orders': len(open_orders),
                    'entry_price': grid['entry_price']
                }
            except:
                return {'active': False}
        return {'active': False}
