# services/async_database_manager.py
"""
Async Database Manager for GridTrader Pro
Addresses the critical performance bottleneck of blocking SQLite operations
"""

import asyncio
import logging
import sqlite3
import time
from typing import Dict, List, Optional, Any
import aiosqlite
from contextlib import asynccontextmanager

from config import Config


class AsyncDatabaseManager:
    """
    High-performance async database manager
    Solves the blocking SQLite operations that cause 3-5 second delays
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        self._connection_pool = {}
        self._pool_size = 5
        
    @asynccontextmanager
    async def get_connection(self):
        """Get async database connection"""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")
            yield db
    
    async def execute_async(self, query: str, params: tuple = None) -> List[Any]:
        """Execute query asynchronously - non-blocking"""
        try:
            async with self.get_connection() as db:
                async with db.execute(query, params or ()) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Async query failed: {e}")
            return []
    
    async def execute_many_async(self, query: str, params_list: List[tuple]) -> bool:
        """Execute multiple statements asynchronously"""
        try:
            async with self.get_connection() as db:
                await db.executemany(query, params_list)
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Async executemany failed: {e}")
            return False
    
    def execute_sync(self, query: str, params: tuple = None) -> List[Any]:
        """Execute query synchronously - use only for critical operations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params or ())
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Sync query failed: {e}")
            return []


class AsyncTradeRepository:
    """
    Async version of trade repository
    Non-blocking trade recording for better performance
    """
    
    def __init__(self, db_manager: AsyncDatabaseManager = None):
        self.db_manager = db_manager or AsyncDatabaseManager()
        self.logger = logging.getLogger(__name__)
    
    async def record_trade_async(
        self, 
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        total_value: float,
        order_id: str = None,
        is_initialization: bool = False
    ) -> bool:
        """Record trade asynchronously - non-blocking"""
        
        query = """
            INSERT INTO trades (
                client_id, symbol, side, quantity, price, total_value, 
                order_id, is_initialization, executed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        params = (
            client_id, symbol, side, quantity, price, total_value,
            order_id, is_initialization
        )
        
        try:
            # This won't block the main thread
            async with self.db_manager.get_connection() as db:
                await db.execute(query, params)
                await db.commit()
                
            self.logger.debug(f"✅ Trade recorded async: {symbol} {side} {quantity}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Async trade recording failed: {e}")
            return False
    
    def record_trade_sync(
        self,
        client_id: int,
        symbol: str, 
        side: str,
        quantity: float,
        price: float,
        total_value: float,
        order_id: str = None,
        is_initialization: bool = False
    ) -> bool:
        """Record trade synchronously - for critical operations only"""
        
        query = """
            INSERT INTO trades (
                client_id, symbol, side, quantity, price, total_value,
                order_id, is_initialization, executed_at  
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        params = (
            client_id, symbol, side, quantity, price, total_value,
            order_id, is_initialization
        )
        
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.execute(query, params)
                conn.commit()
                
            self.logger.debug(f"✅ Trade recorded sync: {symbol} {side} {quantity}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Sync trade recording failed: {e}")
            return False


class AsyncClientRepository:
    """
    Async version of client repository
    Non-blocking client operations
    """
    
    def __init__(self, db_manager: AsyncDatabaseManager = None):
        self.db_manager = db_manager or AsyncDatabaseManager()
        self.logger = logging.getLogger(__name__)
    
    async def get_client_async(self, telegram_id: int) -> Optional[Dict]:
        """Get client data asynchronously"""
        
        query = """
            SELECT telegram_id, username, first_name, status, grid_status,
                   total_capital, risk_level, trading_pairs, grid_spacing,
                   grid_levels, order_size, registration_status
            FROM clients WHERE telegram_id = ?
        """
        
        try:
            result = await self.db_manager.execute_async(query, (telegram_id,))
            
            if result:
                row = result[0]
                return {
                    'total_profit': round(total_sells - total_buys, 2),
                    'total_sells': round(total_sells, 2),
                    'total_buys': round(total_buys, 2),
                    'total_trades': total_trades,
                    'avg_profit_per_trade': round((total_sells - total_buys) / max(total_trades, 1), 2)
                }
            
            return {
                'total_profit': 0.0,
                'total_sells': 0.0,
                'total_buys': 0.0,
                'total_trades': 0,
                'avg_profit_per_trade': 0.0
            }
            
        except Exception as e:
            self.logger.error(f"❌ Async profit calculation failed: {e}")
            return {
                'total_profit': 0.0,
                'total_sells': 0.0,
                'total_buys': 0.0,
                'total_trades': 0,
                'avg_profit_per_trade': 0.0
            }
    
    async def get_recent_trades_async(self, client_id: int, limit: int = 10) -> List[Dict]:
        """Get recent trades asynchronously"""
        
        query = """
            SELECT executed_at, symbol, side, quantity, price, total_value
            FROM trades 
            WHERE client_id = ?
            ORDER BY executed_at DESC
            LIMIT ?
        """
        
        try:
            result = await self.db_manager.execute_async(query, (client_id, limit))
            
            return [
                {
                    'executed_at': row[0],
                    'symbol': row[1],
                    'side': row[2],
                    'quantity': row[3],
                    'price': row[4],
                    'total_value': row[5]
                }
                for row in result
            ]
            
        except Exception as e:
            self.logger.error(f"❌ Async recent trades failed: {e}")
            return []


class DatabasePerformanceMonitor:
    """
    Monitor database performance and suggest optimizations
    """
    
    def __init__(self, db_manager: AsyncDatabaseManager = None):
        self.db_manager = db_manager or AsyncDatabaseManager()
        self.logger = logging.getLogger(__name__)
        self.query_times = {}
    
    async def measure_query_performance(self, query_name: str, query: str, params: tuple = None):
        """Measure and log query performance"""
        start_time = time.time()
        
        try:
            result = await self.db_manager.execute_async(query, params)
            execution_time = time.time() - start_time
            
            # Track query performance
            if query_name not in self.query_times:
                self.query_times[query_name] = []
            
            self.query_times[query_name].append(execution_time)
            
            # Keep only last 100 measurements
            if len(self.query_times[query_name]) > 100:
                self.query_times[query_name] = self.query_times[query_name][-100:]
            
            # Log slow queries
            if execution_time > 1.0:  # Queries taking more than 1 second
                self.logger.warning(f"🐌 Slow query '{query_name}': {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Query '{query_name}' failed after {execution_time:.2f}s: {e}")
            return []
    
    def get_performance_report(self) -> Dict:
        """Get database performance report"""
        report = {}
        
        for query_name, times in self.query_times.items():
            if times:
                report[query_name] = {
                    'avg_time': round(sum(times) / len(times), 3),
                    'max_time': round(max(times), 3),
                    'min_time': round(min(times), 3),
                    'call_count': len(times),
                    'total_time': round(sum(times), 3)
                }
        
        return report
    
    async def analyze_database_health(self) -> Dict:
        """Analyze overall database health"""
        try:
            # Check database size
            size_query = "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            size_result = await self.db_manager.execute_async(size_query)
            db_size = size_result[0][0] if size_result else 0
            
            # Check table sizes
            tables_query = """
                SELECT name, 
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as row_count
                FROM sqlite_master m WHERE type='table'
            """
            tables_result = await self.db_manager.execute_async(tables_query)
            
            # Check for missing indexes
            slow_tables = []
            for query_name, times in self.query_times.items():
                avg_time = sum(times) / len(times) if times else 0
                if avg_time > 0.5:  # Queries taking more than 500ms on average
                    slow_tables.append({
                        'query': query_name,
                        'avg_time': round(avg_time, 3)
                    })
            
            return {
                'database_size_mb': round(db_size / (1024 * 1024), 2),
                'table_info': [{'name': row[0], 'estimated_rows': row[1]} for row in tables_result],
                'slow_queries': slow_tables,
                'performance_summary': self.get_performance_report(),
                'health_status': 'good' if len(slow_tables) == 0 else 'needs_attention'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Database health analysis failed: {e}")
            return {'health_status': 'error', 'error': str(e)}


# Integration example for your existing services
class HybridGridManager:
    """
    Example of how to integrate async operations into your existing GridManager
    Use async for non-critical operations, sync for critical trading operations
    """
    
    def __init__(self, client_id: int):
        self.client_id = client_id
        self.async_db = AsyncDatabaseManager()
        self.async_trades = AsyncTradeRepository()
        self.async_analytics = AsyncAnalytics()
        self.logger = logging.getLogger(__name__)
    
    async def place_order_and_record(self, order_data: Dict) -> bool:
        """Place order and record trade with optimal performance"""
        
        try:
            # 1. Place order synchronously (critical operation)
            order_result = await self.place_binance_order_sync(order_data)
            
            if not order_result.get('success'):
                return False
            
            # 2. Record trade asynchronously (non-critical for trading)
            # This won't block the next order placement
            asyncio.create_task(
                self.async_trades.record_trade_async(
                    client_id=self.client_id,
                    symbol=order_data['symbol'],
                    side=order_data['side'],
                    quantity=order_result['quantity'],
                    price=order_result['price'],
                    total_value=order_result['total_value'],
                    order_id=order_result['order_id']
                )
            )
            
            self.logger.info(f"✅ Order placed: {order_data['symbol']} {order_data['side']}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Order placement failed: {e}")
            return False
    
    async def get_dashboard_data_async(self) -> Dict:
        """Get dashboard data without blocking trading operations"""
        
        # All dashboard queries run asynchronously
        profit_task = self.async_analytics.get_client_profit_async(self.client_id)
        trades_task = self.async_analytics.get_recent_trades_async(self.client_id, 5)
        client_task = AsyncClientRepository().get_client_async(self.client_id)
        
        # Wait for all dashboard data concurrently
        profit_data, recent_trades, client_data = await asyncio.gather(
            profit_task, trades_task, client_task, return_exceptions=True
        )
        
        return {
            'profit': profit_data if not isinstance(profit_data, Exception) else {},
            'recent_trades': recent_trades if not isinstance(recent_trades, Exception) else [],
            'client': client_data if not isinstance(client_data, Exception) else {},
            'generated_at': time.time()
        }
    
    async def place_binance_order_sync(self, order_data: Dict) -> Dict:
        """Placeholder for your actual Binance order placement"""
        # Your existing Binance order logic here
        # This should remain synchronous for reliability
        pass


# Usage example and migration guide
class AsyncMigrationHelper:
    """
    Helper class to gradually migrate your existing code to async
    """
    
    @staticmethod
    def identify_blocking_operations():
        """Identify which operations should be made async"""
        return {
            'high_priority_async': [
                'Trade recording',
                'Client status updates', 
                'Analytics calculations',
                'Dashboard data retrieval',
                'Log writing',
                'Performance metrics'
            ],
            'keep_sync': [
                'Order placement',
                'Balance checking',
                'Critical error handling',
                'Transaction-critical operations'
            ],
            'migration_order': [
                '1. Trade recording (biggest impact)',
                '2. Dashboard operations (user experience)',
                '3. Status updates (performance)',
                '4. Analytics (scalability)'
            ]
        }
    
    @staticmethod
    def get_migration_checklist():
        """Get step-by-step migration checklist"""
        return [
            "✅ Install aiosqlite: pip install aiosqlite",
            "✅ Add AsyncDatabaseManager to your project", 
            "✅ Replace trade recording with async version",
            "✅ Update dashboard handlers to use async",
            "✅ Migrate client status updates",
            "✅ Add performance monitoring",
            "✅ Test with multiple clients",
            "✅ Monitor query performance",
            "✅ Optimize slow queries identified"
        ]


if __name__ == "__main__":
    """Test the async database system"""
    import asyncio
    
    async def test_async_performance():
        """Test async vs sync performance"""
        
        # Test async operations
        async_db = AsyncDatabaseManager()
        async_trades = AsyncTradeRepository()
        
        print("🧪 Testing Async Database Performance...")
        
        # Test concurrent trade recording
        start_time = time.time()
        
        tasks = []
        for i in range(10):
            task = async_trades.record_trade_async(
                client_id=123456789,
                symbol="ADAUSDT",
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=100.0,
                price=1.0,
                total_value=100.0,
                order_id=f"test_order_{i}"
            )
            tasks.append(task)
        
        # Execute all trades concurrently
        results = await asyncio.gather(*tasks)
        async_time = time.time() - start_time
        
        print(f"✅ Async: 10 trades recorded in {async_time:.3f}s")
        print(f"✅ Successful recordings: {sum(results)}/10")
        
        # Test performance monitoring
        monitor = DatabasePerformanceMonitor()
        health_report = await monitor.analyze_database_health()
        print(f"📊 Database health: {health_report['health_status']}")
        print(f"📊 Database size: {health_report.get('database_size_mb', 0)}MB")
    
    # Run the test
    try:
        asyncio.run(test_async_performance())
        print("\n🎉 Async Database System Ready!")
        print("\nNext steps:")
        print("1. Replace sync trade recording with async version")
        print("2. Update dashboard handlers")
        print("3. Monitor performance improvements")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Check database path and permissions")
                    'telegram_id': row[0],
                    'username': row[1],
                    'first_name': row[2],
                    'status': row[3],
                    'grid_status': row[4],
                    'total_capital': row[5],
                    'risk_level': row[6],
                    'trading_pairs': row[7].split(',') if row[7] else [],
                    'grid_spacing': row[8],
                    'grid_levels': row[9],
                    'order_size': row[10],
                    'registration_status': row[11] if len(row) > 11 else 'approved'
                }
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Async get client failed: {e}")
            return None
    
    async def get_active_clients_async(self) -> List[int]:
        """Get active client IDs asynchronously"""
        
        query = """
            SELECT telegram_id FROM clients 
            WHERE status = 'active' AND binance_api_key IS NOT NULL
        """
        
        try:
            result = await self.db_manager.execute_async(query)
            return [row[0] for row in result]
            
        except Exception as e:
            self.logger.error(f"❌ Async get active clients failed: {e}")
            return []
    
    async def update_client_status_async(
        self, 
        telegram_id: int, 
        grid_status: str = None,
        client_status: str = None
    ) -> bool:
        """Update client status asynchronously"""
        
        updates = []
        params = []
        
        if grid_status:
            updates.append("grid_status = ?")
            params.append(grid_status)
            
        if client_status:
            updates.append("status = ?")
            params.append(client_status)
            
        if not updates:
            return True
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(telegram_id)
        
        query = f"UPDATE clients SET {', '.join(updates)} WHERE telegram_id = ?"
        
        try:
            async with self.db_manager.get_connection() as db:
                await db.execute(query, params)
                await db.commit()
                
            self.logger.debug(f"✅ Client status updated async: {telegram_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Async status update failed: {e}")
            return False


class AsyncAnalytics:
    """
    Async analytics for dashboard operations
    Prevents dashboard from blocking trading operations
    """
    
    def __init__(self, db_manager: AsyncDatabaseManager = None):
        self.db_manager = db_manager or AsyncDatabaseManager()
        self.logger = logging.getLogger(__name__)
    
    async def get_client_profit_async(self, client_id: int) -> Dict:
        """Get client profit asynchronously - non-blocking"""
        
        query = """
            SELECT 
                SUM(CASE WHEN side = 'SELL' THEN total_value ELSE 0 END) as total_sells,
                SUM(CASE WHEN side = 'BUY' THEN total_value ELSE 0 END) as total_buys,
                COUNT(*) as total_trades
            FROM trades WHERE client_id = ?
        """
        
        try:
            result = await self.db_manager.execute_async(query, (client_id,))
            
            if result:
                row = result[0]
                total_sells = row[0] or 0.0
                total_buys = row[1] or 0.0
                total_trades = row[2] or 0
                
                return {
                    '
