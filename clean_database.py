# scripts/clean_database_for_pure_usdt_testing.py
"""
Database Cleanup Script for Pure USDT Testing
==============================================

This script safely cleans test data from your database to prepare
for clean Pure USDT + Advanced Grid integration testing.
"""

import sqlite3
import logging
from datetime import datetime
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseCleaner:
    """Safe database cleanup for Pure USDT testing"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.backup_created = False

    def clean_for_pure_usdt_testing(self, client_id: int = None):
        """
        Clean database for Pure USDT testing
        
        Args:
            client_id: Specific client to clean (optional)
        """
        try:
            print("🧹 Database Cleanup for Pure USDT Testing")
            print("=" * 50)
            
            # Step 1: Create backup
            self._create_backup()
            
            # Step 2: Show current state
            self._show_current_state(client_id)
            
            # Step 3: Get confirmation
            if not self._get_confirmation():
                print("❌ Cleanup cancelled")
                return False
            
            # Step 4: Perform cleanup
            self._perform_cleanup(client_id)
            
            # Step 5: Verify cleanup
            self._verify_cleanup(client_id)
            
            print("\n✅ Database cleanup completed successfully!")
            print("🚀 Ready for clean Pure USDT testing")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            print(f"❌ Cleanup failed: {e}")
            return False

    def _create_backup(self):
        """Create backup before cleanup"""
        try:
            import shutil
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_before_cleanup_{timestamp}"
            
            shutil.copy2(self.db_path, backup_path)
            self.backup_created = True
            
            print(f"📁 Backup created: {backup_path}")
            
        except Exception as e:
            print(f"❌ Backup creation failed: {e}")
            raise

    def _show_current_state(self, client_id: int = None):
        """Show current database state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                print("\n📊 Current Database State:")
                
                # Show clients
                if client_id:
                    cursor = conn.execute(
                        "SELECT telegram_id, username, total_capital, status FROM clients WHERE telegram_id = ?",
                        (client_id,)
                    )
                    clients = cursor.fetchall()
                    print(f"🔍 Checking specific client: {client_id}")
                else:
                    cursor = conn.execute(
                        "SELECT telegram_id, username, total_capital, status FROM clients"
                    )
                    clients = cursor.fetchall()
                
                print(f"👥 Clients: {len(clients)}")
                for client in clients:
                    print(f"   - {client[1]} (ID: {client[0]}): ${client[2]:.2f} - {client[3]}")
                
                # Show trades
                if client_id:
                    cursor = conn.execute(
                        "SELECT COUNT(*), symbol, side FROM trades WHERE client_id = ? GROUP BY symbol, side",
                        (client_id,)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT COUNT(*), symbol, side FROM trades GROUP BY symbol, side"
                    )
                
                trades = cursor.fetchall()
                print(f"📊 Trades: {sum(t[0] for t in trades)}")
                for trade in trades:
                    print(f"   - {trade[1]} {trade[2]}: {trade[0]} trades")
                
                # Show FIFO cost basis
                if client_id:
                    cursor = conn.execute(
                        "SELECT COUNT(*), symbol FROM fifo_cost_basis WHERE client_id = ? GROUP BY symbol",
                        (client_id,)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT COUNT(*), symbol FROM fifo_cost_basis GROUP BY symbol"
                    )
                
                fifo_records = cursor.fetchall()
                print(f"💰 FIFO Cost Basis Records: {sum(f[0] for f in fifo_records)}")
                for record in fifo_records:
                    print(f"   - {record[1]}: {record[0]} records")
                
        except Exception as e:
            print(f"❌ Error showing current state: {e}")

    def _get_confirmation(self):
        """Get user confirmation for cleanup"""
        print("\n⚠️ CLEANUP ACTIONS:")
        print("1. Clear all test trades")
        print("2. Clear FIFO cost basis records")
        print("3. Reset client grid status")
        print("4. Keep client API keys and settings")
        print("5. Keep database structure intact")
        print("\n📁 Backup created for safety")
        
        response = input("\nProceed with cleanup? (yes/no): ").lower().strip()
        return response in ['yes', 'y']

    def _perform_cleanup(self, client_id: int = None):
        """Perform the actual cleanup"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                print("\n🧹 Performing cleanup...")
                
                # Step 1: Clear trades
                if client_id:
                    cursor = conn.execute("DELETE FROM trades WHERE client_id = ?", (client_id,))
                    print(f"   🗑️ Deleted {cursor.rowcount} trades for client {client_id}")
                else:
                    cursor = conn.execute("DELETE FROM trades")
                    print(f"   🗑️ Deleted {cursor.rowcount} trades")
                
                # Step 2: Clear FIFO cost basis
                if client_id:
                    cursor = conn.execute("DELETE FROM fifo_cost_basis WHERE client_id = ?", (client_id,))
                    print(f"   💰 Deleted {cursor.rowcount} FIFO records for client {client_id}")
                else:
                    cursor = conn.execute("DELETE FROM fifo_cost_basis")
                    print(f"   💰 Deleted {cursor.rowcount} FIFO records")
                
                # Step 3: Reset client grid status (but keep API keys and settings)
                if client_id:
                    conn.execute(
                        "UPDATE clients SET grid_status = 'inactive', updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?",
                        (client_id,)
                    )
                    print(f"   👤 Reset grid status for client {client_id}")
                else:
                    conn.execute(
                        "UPDATE clients SET grid_status = 'inactive', updated_at = CURRENT_TIMESTAMP"
                    )
                    print("   👤 Reset grid status for all clients")
                
                # Step 4: Reset auto-increment counters
                conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('trades', 'fifo_cost_basis')")
                print("   🔄 Reset ID counters")
                
                conn.commit()
                print("✅ Cleanup completed")
                
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            raise

    def _verify_cleanup(self, client_id: int = None):
        """Verify cleanup was successful"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                print("\n🔍 Verifying cleanup...")
                
                # Check trades
                if client_id:
                    cursor = conn.execute("SELECT COUNT(*) FROM trades WHERE client_id = ?", (client_id,))
                else:
                    cursor = conn.execute("SELECT COUNT(*) FROM trades")
                
                trades_count = cursor.fetchone()[0]
                
                # Check FIFO records
                if client_id:
                    cursor = conn.execute("SELECT COUNT(*) FROM fifo_cost_basis WHERE client_id = ?", (client_id,))
                else:
                    cursor = conn.execute("SELECT COUNT(*) FROM fifo_cost_basis")
                
                fifo_count = cursor.fetchone()[0]
                
                # Check clients still exist
                if client_id:
                    cursor = conn.execute("SELECT COUNT(*) FROM clients WHERE telegram_id = ?", (client_id,))
                else:
                    cursor = conn.execute("SELECT COUNT(*) FROM clients")
                
                clients_count = cursor.fetchone()[0]
                
                print(f"   📊 Trades remaining: {trades_count}")
                print(f"   💰 FIFO records remaining: {fifo_count}")
                print(f"   👥 Clients preserved: {clients_count}")
                
                if trades_count == 0 and fifo_count == 0 and clients_count > 0:
                    print("✅ Cleanup verification passed!")
                    return True
                else:
                    print("⚠️ Cleanup verification found issues")
                    return False
                    
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False

    def clean_specific_symbol_data(self, symbol: str, client_id: int = None):
        """Clean data for specific trading symbol"""
        try:
            print(f"\n🧹 Cleaning {symbol} data...")
            
            with sqlite3.connect(self.db_path) as conn:
                if client_id:
                    # Clean trades for specific client and symbol
                    cursor = conn.execute(
                        "DELETE FROM trades WHERE client_id = ? AND symbol = ?",
                        (client_id, symbol)
                    )
                    print(f"   🗑️ Deleted {cursor.rowcount} {symbol} trades for client {client_id}")
                    
                    # Clean FIFO records for specific client and symbol
                    cursor = conn.execute(
                        "DELETE FROM fifo_cost_basis WHERE client_id = ? AND symbol = ?",
                        (client_id, symbol)
                    )
                    print(f"   💰 Deleted {cursor.rowcount} {symbol} FIFO records for client {client_id}")
                else:
                    # Clean all trades for symbol
                    cursor = conn.execute("DELETE FROM trades WHERE symbol = ?", (symbol,))
                    print(f"   🗑️ Deleted {cursor.rowcount} {symbol} trades")
                    
                    # Clean all FIFO records for symbol
                    cursor = conn.execute("DELETE FROM fifo_cost_basis WHERE symbol = ?", (symbol,))
                    print(f"   💰 Deleted {cursor.rowcount} {symbol} FIFO records")
                
                conn.commit()
                print(f"✅ {symbol} data cleanup completed")
                
        except Exception as e:
            print(f"❌ {symbol} cleanup error: {e}")

    def show_cleanup_summary(self):
        """Show what cleanup will do"""
        print("\n📋 CLEANUP SUMMARY")
        print("=" * 30)
        print("✅ WILL BE CLEANED:")
        print("   - All trade records")
        print("   - All FIFO cost basis records") 
        print("   - Client grid status (reset to inactive)")
        print("   - Database ID counters")
        print()
        print("✅ WILL BE PRESERVED:")
        print("   - Client accounts and API keys")
        print("   - Client settings and capital")
        print("   - Database structure and tables")
        print("   - All configuration data")
        print()
        print("🔒 SAFETY:")
        print("   - Full backup created before cleanup")
        print("   - Can be restored if needed")


def main():
    """Main cleanup function"""
    print("🧹 GridTrader Pro Database Cleanup")
    print("=" * 40)
    
    cleaner = DatabaseCleaner()
    
    # Show what cleanup will do
    cleaner.show_cleanup_summary()
    
    # Ask for client ID
    print("\nCleanup Options:")
    print("1. Clean specific client")
    print("2. Clean all data")
    print("3. Clean specific symbol only")
    print("4. Cancel")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        client_id = input("Enter client ID: ").strip()
        try:
            client_id = int(client_id)
            cleaner.clean_for_pure_usdt_testing(client_id)
        except ValueError:
            print("❌ Invalid client ID")
    
    elif choice == "2":
        cleaner.clean_for_pure_usdt_testing()
    
    elif choice == "3":
        symbol = input("Enter symbol (e.g., ADAUSDT): ").strip().upper()
        client_id_input = input("Enter client ID (or press Enter for all clients): ").strip()
        
        client_id = None
        if client_id_input:
            try:
                client_id = int(client_id_input)
            except ValueError:
                print("❌ Invalid client ID")
                return
        
        cleaner.clean_specific_symbol_data(symbol, client_id)
    
    elif choice == "4":
        print("❌ Cleanup cancelled")
    
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()
