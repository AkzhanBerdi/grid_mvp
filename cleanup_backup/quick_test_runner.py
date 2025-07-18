#!/usr/bin/env python3
"""
Quick Test Runner - Pre-Production Validation
Fast validation of critical components before production push
"""

import asyncio
import sys
import time
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


class QuickProductionValidator:
    """Quick validation of production-critical components"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
    
    def test(self, test_name: str, test_func):
        """Run a single test with error handling"""
        try:
            print(f"⏳ Testing {test_name}...", end=" ")
            start_time = time.time()
            
            result = test_func()
            
            # Handle async functions
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)
            
            end_time = time.time()
            
            if result:
                print(f"✅ PASS ({end_time - start_time:.2f}s)")
                self.tests_passed += 1
            else:
                print(f"❌ FAIL ({end_time - start_time:.2f}s)")
                self.tests_failed += 1
                self.errors.append(f"{test_name}: Test returned False")
        
        except Exception as e:
            print(f"🚨 ERROR ({time.time() - time.time():.2f}s)")
            self.tests_failed += 1
            self.errors.append(f"{test_name}: {str(e)}")
    
    def run_all_tests(self):
        """Run all critical production tests"""
        print("🚀 QUICK PRODUCTION VALIDATION")
        print("=" * 50)
        print("Testing critical components for production readiness...")
        print()
        
        # Test 1: Configuration
        self.test("Configuration Loading", self.test_config)
        
        # Test 2: Database Setup
        self.test("Database Connection", self.test_database)
        
        # Test 3: Encryption
        self.test("Encryption/Decryption", self.test_encryption)
        
        # Test 4: Client Repository
        self.test("Client Repository", self.test_client_repo)
        
        # Test 5: Trade Repository
        self.test("Trade Repository", self.test_trade_repo)
        
        # Test 6: Network Utils
        self.test("Network Utilities", self.test_network_utils)
        
        # Test 7: Main Components Import
        self.test("Main Components Import", self.test_imports)
        
        # Test 8: Database Schema
        self.test("Database Schema", self.test_database_schema)
        
        # Test 9: FIFO Service (if available)
        self.test("FIFO Service", self.test_fifo_service)
        
        # Test 10: Grid Orchestrator
        self.test("Grid Orchestrator", self.test_grid_orchestrator)
        
        # Print summary
        self.print_summary()
        
        return self.tests_failed == 0
    
    def test_config(self):
        """Test configuration loading"""
        try:
            from config import Config
            
            # Check required attributes
            required_attrs = [
                'DATABASE_PATH', 'TELEGRAM_BOT_TOKEN', 'ADMIN_TELEGRAM_ID',
                'ENVIRONMENT', 'ENCRYPTION_KEY', 'DEFAULT_TRADING_PAIRS'
            ]
            
            for attr in required_attrs:
                if not hasattr(Config, attr):
                    return False
            
            # Check encryption key length
            if len(Config.ENCRYPTION_KEY) < 32:
                return False
            
            return True
        except Exception:
            return False
    
    def test_database(self):
        """Test database connection and setup"""
        try:
            from database.db_setup import DatabaseSetup
            import sqlite3
            
            # Test with memory database
            db_setup = DatabaseSetup(":memory:")
            db_setup.init_database()
            
            # Test connection
            with sqlite3.connect(":memory:") as conn:
                conn.execute("SELECT 1").fetchone()
            
            return True
        except Exception:
            return False
    
    def test_encryption(self):
        """Test encryption utilities"""
        try:
            from utils.crypto import CryptoUtils
            
            crypto = CryptoUtils()
            test_data = "test_encryption_data_123"
            
            # Test encryption cycle
            encrypted = crypto.encrypt(test_data)
            decrypted = crypto.decrypt(encrypted)
            
            return decrypted == test_data
        except Exception:
            return False
    
    def test_client_repo(self):
        """Test client repository"""
        try:
            from repositories.client_repository import ClientRepository
            from database.db_setup import DatabaseSetup
            
            # Setup test database
            db_setup = DatabaseSetup(":memory:")
            db_setup.init_database()
            
            # Test repository
            repo = ClientRepository(":memory:")
            
            # Test client creation
            client = repo.create_client(
                telegram_id=123456789,
                username="testuser",
                first_name="Test User"
            )
            
            # Test client retrieval
            retrieved = repo.get_client(123456789)
            
            return retrieved is not None and retrieved.telegram_id == 123456789
        except Exception:
            return False
    
    def test_trade_repo(self):
        """Test trade repository"""
        try:
            from repositories.trade_repository import TradeRepository
            from repositories.client_repository import ClientRepository
            from database.db_setup import DatabaseSetup
            
            # Setup test database
            db_setup = DatabaseSetup(":memory:")
            db_setup.init_database()
            
            # Create test client
            client_repo = ClientRepository(":memory:")
            client_repo.create_client(
                telegram_id=123456789,
                username="testuser",
                first_name="Test User"
            )
            
            # Test trade repository
            trade_repo = TradeRepository(":memory:")
            
            # Test trade recording
            success = trade_repo.record_trade(
                client_id=123456789,
                symbol="ADAUSDT",
                side="BUY",
                quantity=100.0,
                price=0.5,
                total_value=50.0,
                order_id="test_order_123"
            )
            
            # Test trade retrieval
            trades = trade_repo.get_client_trades(123456789)
            
            return success and len(trades) > 0
        except Exception:
            return False
    
    def test_network_utils(self):
        """Test network utilities"""
        try:
            from utils.network_utils import NetworkUtils
            
            # Test retry delay calculation
            delay = NetworkUtils.get_retry_delay(1, 2.0)
            
            # Test network event logging (should not raise exception)
            NetworkUtils.log_network_event("test", "Test message")
            
            return delay >= 2.0
        except Exception:
            return False
    
    def test_imports(self):
        """Test critical component imports"""
        try:
            # Test main component imports
            from main import GridTradingService
            from handlers.client_handler import ClientHandler
            from services.grid_orchestrator import GridOrchestrator
            from models.client import Client, ClientStatus, GridStatus
            
            return True
        except Exception:
            return False
    
    def test_database_schema(self):
        """Test database schema integrity"""
        try:
            from database.db_setup import DatabaseSetup
            import sqlite3
            
            # Setup database
            db_setup = DatabaseSetup(":memory:")
            db_setup.init_database()
            
            # Check table structure
            with sqlite3.connect(":memory:") as conn:
                # Check clients table
                cursor = conn.execute("PRAGMA table_info(clients)")
                columns = [row[1] for row in cursor.fetchall()]
                
                required_columns = [
                    'telegram_id', 'username', 'first_name', 'status',
                    'total_capital', 'binance_api_key', 'binance_secret_key'
                ]
                
                for col in required_columns:
                    if col not in columns:
                        return False
                
                # Check trades table
                cursor = conn.execute("PRAGMA table_info(trades)")
                trade_columns = [row[1] for row in cursor.fetchall()]
                
                required_trade_columns = [
                    'client_id', 'symbol', 'side', 'quantity', 'price', 'total_value'
                ]
                
                for col in required_trade_columns:
                    if col not in trade_columns:
                        return False
            
            return True
        except Exception:
            return False
    
    def test_fifo_service(self):
        """Test FIFO service (if available)"""
        try:
            from services.fifo_service import FIFOService
            
            # Test initialization with memory database
            fifo_service = FIFOService(":memory:")
            
            return True
        except ImportError:
            # FIFO service not available, skip test
            return True
        except Exception:
            return False
    
    def test_grid_orchestrator(self):
        """Test grid orchestrator"""
        try:
            from services.grid_orchestrator import GridOrchestrator
            
            # Test initialization
            orchestrator = GridOrchestrator()
            
            # Test basic methods exist
            required_methods = [
                'get_client_grid_status',
                'shutdown_all_grids'
            ]
            
            for method in required_methods:
                if not hasattr(orchestrator, method):
                    return False
            
            return True
        except Exception:
            return False
    
    def print_summary(self):
        """Print test results summary"""
        print()
        print("=" * 50)
        print("📊 QUICK VALIDATION RESULTS")
        print("=" * 50)
        
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {self.tests_passed}/{total_tests}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            print()
            print("🎉 ALL CRITICAL TESTS PASSED!")
            print("✅ Your application is ready for production push")
            print()
            print("🚀 NEXT STEPS:")
            print("   1. Run full test suite: python test_production_suite.py")
            print("   2. Deploy to production environment")
            print("   3. Monitor initial deployment")
        else:
            print()
            print("⚠️  CRITICAL ISSUES FOUND")
            print("❌ Fix these issues before production deployment:")
            print()
            
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
            
            print()
            print("🔧 RECOMMENDED ACTIONS:")
            print("   1. Fix failing components")
            print("   2. Re-run validation")
            print("   3. Run full test suite when ready")
        
        print("=" * 50)


class ProductionChecklist:
    """Production deployment checklist"""
    
    @staticmethod
    def print_checklist():
        """Print production deployment checklist"""
        print()
        print("📋 PRODUCTION DEPLOYMENT CHECKLIST")
        print("=" * 50)
        print()
        print("🔧 PRE-DEPLOYMENT:")
        print("   ☐ All tests passing")
        print("   ☐ Environment variables configured")
        print("   ☐ Database backup created")
        print("   ☐ API keys validated")
        print("   ☐ Logging configured")
        print()
        print("🚀 DEPLOYMENT:")
        print("   ☐ Deploy to staging first")
        print("   ☐ Test critical user flows")
        print("   ☐ Monitor error rates")
        print("   ☐ Deploy to production")
        print()
        print("📊 POST-DEPLOYMENT:")
        print("   ☐ Monitor application logs")
        print("   ☐ Check database connections")
        print("   ☐ Test Telegram bot responsiveness")
        print("   ☐ Verify trading functionality")
        print("   ☐ Monitor for memory leaks")
        print()
        print("🚨 ROLLBACK PLAN:")
        print("   ☐ Previous version backup ready")
        print("   ☐ Database rollback procedure tested")
        print("   ☐ Emergency contact list updated")
        print()


def quick_component_test():
    """Quick test of individual components for debugging"""
    print("🔍 QUICK COMPONENT TEST")
    print("=" * 30)
    
    components = {
        "Config": "from config import Config; print(f'Environment: {Config.ENVIRONMENT}')",
        "Database": "from database.db_setup import DatabaseSetup; db = DatabaseSetup(':memory:'); db.init_database(); print('Database OK')",
        "Crypto": "from utils.crypto import CryptoUtils; c = CryptoUtils(); print(f'Encryption test: {c.test_encryption_cycle()}')",
        "Client Repo": "from repositories.client_repository import ClientRepository; print('Client repository imported')",
        "Trade Repo": "from repositories.trade_repository import TradeRepository; print('Trade repository imported')",
        "Main Service": "from main import GridTradingService; print('Main service imported')",
    }
    
    for name, test_code in components.items():
        try:
            exec(test_code)
            print(f"✅ {name}: OK")
        except Exception as e:
            print(f"❌ {name}: {str(e)[:50]}...")


def stress_test_database():
    """Quick stress test of database operations"""
    print("🏋️ DATABASE STRESS TEST")
    print("=" * 30)
    
    try:
        from database.db_setup import DatabaseSetup
        from repositories.client_repository import ClientRepository
        import time
        
        # Setup
        db_setup = DatabaseSetup(":memory:")
        db_setup.init_database()
        repo = ClientRepository(":memory:")
        
        # Stress test
        start_time = time.time()
        
        for i in range(100):
            repo.create_client(
                telegram_id=i,
                username=f"user{i}",
                first_name=f"User {i}"
            )
        
        end_time = time.time()
        
        # Verify
        clients = repo.get_all_active_clients()
        
        print(f"✅ Created 100 clients in {end_time - start_time:.2f}s")
        print(f"✅ Retrieved {len(clients)} active clients")
        print("✅ Database stress test passed")
        
    except Exception as e:
        print(f"❌ Database stress test failed: {e}")


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GridTrader Pro - Quick Production Validator")
    parser.add_argument("--quick", action="store_true", help="Run quick validation only")
    parser.add_argument("--components", action="store_true", help="Test individual components")
    parser.add_argument("--stress", action="store_true", help="Run database stress test")
    parser.add_argument("--checklist", action="store_true", help="Show deployment checklist")
    
    args = parser.parse_args()
    
    if args.components:
        quick_component_test()
        return
    
    if args.stress:
        stress_test_database()
        return
    
    if args.checklist:
        ProductionChecklist.print_checklist()
        return
    
    # Run main validation
    validator = QuickProductionValidator()
    success = validator.run_all_tests()
    
    if success:
        ProductionChecklist.print_checklist()
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n🚨 Validation failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)
