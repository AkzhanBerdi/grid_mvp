# repositories/enhanced_trade_repository.py
"""
Enhanced Trade Repository for Pure USDT Grid Integration
=======================================================

Properly handles the database schema and provides methods for:
1. Creating trades with initialization flags
2. FIFO-aware trade queries
3. Cost basis integration
"""

import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional

from config import Config


class EnhancedTradeRepository:
    """
    Enhanced Trade Repository that supports Pure USDT Grid initialization

    Extends your existing trade repository with:
    - Initialization trade tracking
    - FIFO-aware queries
    - Cost basis integration
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure database schema supports enhanced features"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if trades table has required columns
                cursor.execute("PRAGMA table_info(trades)")
                columns = [col[1] for col in cursor.fetchall()]

                if "is_initialization" not in columns:
                    self.logger.warning(
                        "⚠️ Database not migrated. Run migration script first!"
                    )

        except Exception as e:
            self.logger.error(f"❌ Schema check failed: {e}")

    async def create_trade(
        self,
        client_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        total_value: float,
        executed_at: Optional[float] = None,
        is_initialization: bool = False,
        trade_id: Optional[str] = None,
    ) -> str:
        """
        Create a new trade record with enhanced features

        Args:
            client_id: Client identifier
            symbol: Trading pair (e.g., "ADAUSDT")
            side: "BUY" or "SELL"
            quantity: Amount of asset traded
            price: Price per unit
            total_value: Total USD value of trade
            executed_at: Timestamp (defaults to now)
            is_initialization: Whether this is an initialization trade
            trade_id: Optional external trade ID

        Returns:
            Database trade ID as string
        """
        try:
            executed_timestamp = executed_at or time.time()
            executed_datetime = datetime.fromtimestamp(executed_timestamp)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if is_initialization column exists
                cursor.execute("PRAGMA table_info(trades)")
                columns = [col[1] for col in cursor.fetchall()]

                if "is_initialization" in columns:
                    # Use enhanced schema
                    cursor.execute(
                        """
                        INSERT INTO trades 
                        (client_id, symbol, side, quantity, price, total_value, executed_at, is_initialization)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            client_id,
                            symbol,
                            side,
                            quantity,
                            price,
                            total_value,
                            executed_datetime,
                            is_initialization,
                        ),
                    )
                else:
                    # Fallback to original schema
                    self.logger.warning(
                        "⚠️ Using fallback schema - run database migration!"
                    )
                    cursor.execute(
                        """
                        INSERT INTO trades 
                        (client_id, symbol, side, quantity, price, total_value, executed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            client_id,
                            symbol,
                            side,
                            quantity,
                            price,
                            total_value,
                            executed_datetime,
                        ),
                    )

                db_trade_id = cursor.lastrowid

                self.logger.info(
                    f"✅ Trade created: ID={db_trade_id}, {side} {quantity:.4f} {symbol} @ ${price:.4f}"
                )
                if is_initialization:
                    self.logger.info("   🏁 Marked as initialization trade")

                return str(db_trade_id)

        except Exception as e:
            self.logger.error(f"❌ Error creating trade: {e}")
            raise

    def get_client_trades(
        self,
        client_id: int,
        symbol: Optional[str] = None,
        include_initialization: bool = True,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get trades for a client with optional filtering

        Args:
            client_id: Client identifier
            symbol: Optional symbol filter
            include_initialization: Whether to include initialization trades
            limit: Optional limit on results

        Returns:
            List of trade dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Build query
                base_query = """
                    SELECT id, client_id, symbol, side, quantity, price, total_value, 
                           executed_at, 
                           COALESCE(is_initialization, 0) as is_initialization
                    FROM trades 
                    WHERE client_id = ?
                """
                params = [client_id]

                # Add symbol filter
                if symbol:
                    base_query += " AND symbol = ?"
                    params.append(symbol)

                # Add initialization filter
                if not include_initialization:
                    base_query += " AND COALESCE(is_initialization, 0) = 0"

                # Add ordering and limit
                base_query += " ORDER BY executed_at ASC"
                if limit:
                    base_query += f" LIMIT {limit}"

                cursor = conn.execute(base_query, params)
                rows = cursor.fetchall()

                # Convert to dictionaries
                trades = []
                for row in rows:
                    trade = {
                        "id": row[0],
                        "client_id": row[1],
                        "symbol": row[2],
                        "side": row[3],
                        "quantity": row[4],
                        "price": row[5],
                        "total_value": row[6],
                        "executed_at": row[7],
                        "is_initialization": bool(row[8]),
                    }
                    trades.append(trade)

                return trades

        except Exception as e:
            self.logger.error(f"❌ Error getting client trades: {e}")
            return []

    def get_fifo_trade_sequence(self, client_id: int, symbol: str) -> List[Dict]:
        """
        Get trades in FIFO order for profit calculation

        Returns trades ordered by execution time for accurate FIFO processing
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, symbol, side, quantity, price, total_value, executed_at,
                           COALESCE(is_initialization, 0) as is_initialization
                    FROM trades 
                    WHERE client_id = ? AND symbol = ?
                    ORDER BY executed_at ASC
                """,
                    (client_id, symbol),
                )

                rows = cursor.fetchall()

                trades = []
                for row in rows:
                    trade = {
                        "id": row[0],
                        "symbol": row[1],
                        "side": row[2],
                        "quantity": row[3],
                        "price": row[4],
                        "total_value": row[5],
                        "executed_at": row[6],
                        "is_initialization": bool(row[7]),
                    }
                    trades.append(trade)

                return trades

        except Exception as e:
            self.logger.error(f"❌ Error getting FIFO trade sequence: {e}")
            return []

    def get_initialization_trades(self, client_id: int) -> List[Dict]:
        """Get all initialization trades for a client"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, symbol, side, quantity, price, total_value, executed_at
                    FROM trades 
                    WHERE client_id = ? AND COALESCE(is_initialization, 0) = 1
                    ORDER BY executed_at ASC
                """,
                    (client_id,),
                )

                rows = cursor.fetchall()

                trades = []
                for row in rows:
                    trade = {
                        "id": row[0],
                        "symbol": row[1],
                        "side": row[2],
                        "quantity": row[3],
                        "price": row[4],
                        "total_value": row[5],
                        "executed_at": row[6],
                        "is_initialization": True,
                    }
                    trades.append(trade)

                return trades

        except Exception as e:
            self.logger.error(f"❌ Error getting initialization trades: {e}")
            return []

    def get_trade_statistics(
        self, client_id: int, symbol: Optional[str] = None
    ) -> Dict:
        """Get comprehensive trade statistics for a client"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                base_query = """
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN side = 'BUY' THEN 1 END) as buy_trades,
                        COUNT(CASE WHEN side = 'SELL' THEN 1 END) as sell_trades,
                        SUM(CASE WHEN side = 'BUY' THEN total_value ELSE 0 END) as total_bought,
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE 0 END) as total_sold,
                        AVG(total_value) as avg_trade_size,
                        MIN(executed_at) as first_trade,
                        MAX(executed_at) as last_trade,
                        COUNT(CASE WHEN COALESCE(is_initialization, 0) = 1 THEN 1 END) as initialization_trades
                    FROM trades 
                    WHERE client_id = ?
                """

                params = [client_id]
                if symbol:
                    base_query += " AND symbol = ?"
                    params.append(symbol)

                cursor = conn.execute(base_query, params)
                row = cursor.fetchone()

                if row:
                    stats = {
                        "total_trades": row[0] or 0,
                        "buy_trades": row[1] or 0,
                        "sell_trades": row[2] or 0,
                        "total_bought": row[3] or 0.0,
                        "total_sold": row[4] or 0.0,
                        "avg_trade_size": row[5] or 0.0,
                        "first_trade": row[6],
                        "last_trade": row[7],
                        "initialization_trades": row[8] or 0,
                        "simple_profit": (row[4] or 0.0) - (row[3] or 0.0),
                        "has_initialization": (row[8] or 0) > 0,
                    }

                    return stats
                else:
                    return self._empty_statistics()

        except Exception as e:
            self.logger.error(f"❌ Error getting trade statistics: {e}")
            return self._empty_statistics()

    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            "total_trades": 0,
            "buy_trades": 0,
            "sell_trades": 0,
            "total_bought": 0.0,
            "total_sold": 0.0,
            "avg_trade_size": 0.0,
            "first_trade": None,
            "last_trade": None,
            "initialization_trades": 0,
            "simple_profit": 0.0,
            "has_initialization": False,
        }

    def delete_test_trades(self, client_id: int) -> bool:
        """Delete test trades for a specific client (for testing only)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM trades WHERE client_id = ?
                """,
                    (client_id,),
                )

                deleted_count = cursor.rowcount
                self.logger.info(
                    f"🗑️ Deleted {deleted_count} test trades for client {client_id}"
                )

                return True

        except Exception as e:
            self.logger.error(f"❌ Error deleting test trades: {e}")
            return False

    def verify_database_schema(self) -> Dict:
        """Verify that database schema supports enhanced features"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check trades table
                cursor.execute("PRAGMA table_info(trades)")
                trades_columns = [col[1] for col in cursor.fetchall()]

                # Check FIFO cost basis table
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='fifo_cost_basis'
                """)
                fifo_table_exists = cursor.fetchone() is not None

                fifo_columns = []
                if fifo_table_exists:
                    cursor.execute("PRAGMA table_info(fifo_cost_basis)")
                    fifo_columns = [col[1] for col in cursor.fetchall()]

                required_trades_columns = [
                    "id",
                    "client_id",
                    "symbol",
                    "side",
                    "quantity",
                    "price",
                    "total_value",
                    "executed_at",
                    "is_initialization",
                ]

                required_fifo_columns = [
                    "id",
                    "client_id",
                    "symbol",
                    "quantity",
                    "cost_per_unit",
                    "total_cost",
                    "remaining_quantity",
                    "is_initialization",
                ]

                missing_trades_columns = [
                    col for col in required_trades_columns if col not in trades_columns
                ]

                missing_fifo_columns = (
                    [col for col in required_fifo_columns if col not in fifo_columns]
                    if fifo_table_exists
                    else required_fifo_columns
                )

                schema_valid = (
                    len(missing_trades_columns) == 0
                    and fifo_table_exists
                    and len(missing_fifo_columns) == 0
                )

                return {
                    "schema_valid": schema_valid,
                    "trades_table_ok": len(missing_trades_columns) == 0,
                    "fifo_table_exists": fifo_table_exists,
                    "fifo_table_ok": len(missing_fifo_columns) == 0,
                    "missing_trades_columns": missing_trades_columns,
                    "missing_fifo_columns": missing_fifo_columns,
                    "current_trades_columns": trades_columns,
                    "current_fifo_columns": fifo_columns,
                    "recommendation": "Run database migration script"
                    if not schema_valid
                    else "Schema is ready",
                }

        except Exception as e:
            return {
                "schema_valid": False,
                "error": str(e),
                "recommendation": "Check database connectivity and run migration script",
            }


# Helper function for backward compatibility
def create_enhanced_trade_repository(
    db_path: Optional[str] = None,
) -> EnhancedTradeRepository:
    """Factory function to create enhanced trade repository"""
    return EnhancedTradeRepository(db_path)


# Test function
async def test_enhanced_trade_repository():
    """Test the enhanced trade repository functionality"""

    print("🧪 Testing Enhanced Trade Repository")
    print("=" * 40)

    try:
        # Create repository instance
        repo = EnhancedTradeRepository()

        # Test 1: Schema verification
        print("1️⃣ Testing schema verification...")
        schema_check = repo.verify_database_schema()

        print(f"   Schema valid: {schema_check['schema_valid']}")
        print(f"   Trades table OK: {schema_check['trades_table_ok']}")
        print(f"   FIFO table exists: {schema_check['fifo_table_exists']}")
        print(f"   Recommendation: {schema_check['recommendation']}")

        if not schema_check["schema_valid"]:
            print("❌ Schema validation failed - run migration first!")
            return False

        # Test 2: Create test initialization trade
        print("\n2️⃣ Testing initialization trade creation...")
        test_client_id = 99999

        trade_id = await repo.create_trade(
            client_id=test_client_id,
            symbol="TESTUSDT",
            side="BUY",
            quantity=1000.0,
            price=1.0,
            total_value=1000.0,
            is_initialization=True,
        )

        print(f"   ✅ Initialization trade created: ID={trade_id}")

        # Test 3: Create regular trade
        print("\n3️⃣ Testing regular trade creation...")

        regular_trade_id = await repo.create_trade(
            client_id=test_client_id,
            symbol="TESTUSDT",
            side="SELL",
            quantity=100.0,
            price=1.05,
            total_value=105.0,
            is_initialization=False,
        )

        print(f"   ✅ Regular trade created: ID={regular_trade_id}")

        # Test 4: Get client trades
        print("\n4️⃣ Testing trade retrieval...")

        all_trades = repo.get_client_trades(test_client_id)
        init_trades = repo.get_initialization_trades(test_client_id)
        fifo_sequence = repo.get_fifo_trade_sequence(test_client_id, "TESTUSDT")

        print(f"   All trades: {len(all_trades)}")
        print(f"   Initialization trades: {len(init_trades)}")
        print(f"   FIFO sequence: {len(fifo_sequence)}")

        # Test 5: Get trade statistics
        print("\n5️⃣ Testing trade statistics...")

        stats = repo.get_trade_statistics(test_client_id)
        print(f"   Total trades: {stats['total_trades']}")
        print(f"   Buy trades: {stats['buy_trades']}")
        print(f"   Sell trades: {stats['sell_trades']}")
        print(f"   Has initialization: {stats['has_initialization']}")
        print(f"   Simple profit: ${stats['simple_profit']:.2f}")

        # Test 6: Cleanup
        print("\n6️⃣ Cleaning up test data...")
        cleanup_success = repo.delete_test_trades(test_client_id)
        print(f"   Cleanup successful: {cleanup_success}")

        print("\n✅ All tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_enhanced_trade_repository())
