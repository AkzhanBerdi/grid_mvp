# health_check.py
#!/usr/bin/env python3
"""Health check script for GridTrader Pro Service"""

import asyncio
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config


class HealthCheck:
    """System health monitoring for GridTrader Pro Service"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def check_system_health(self) -> dict:
        """Comprehensive system health check"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "service": "GridTrader Pro Client Service",
            "checks": {},
        }

        try:
            # Database connectivity
            health_status["checks"]["database"] = self._check_database()

            # Configuration validation
            health_status["checks"]["config"] = self._check_config()

            # File system access
            health_status["checks"]["filesystem"] = self._check_filesystem()

            # Memory usage (if psutil available)
            health_status["checks"]["memory"] = self._check_memory_usage()

            # Determine overall status
            failed_checks = [
                check
                for check in health_status["checks"].values()
                if not check["healthy"]
            ]

            if failed_checks:
                health_status["status"] = "unhealthy"
                health_status["failed_checks"] = len(failed_checks)

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            health_status["status"] = "error"
            health_status["error"] = str(e)

        return health_status

    def _check_database(self) -> dict:
        """Check database connectivity and integrity"""
        try:
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                # Check if tables exist
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in cursor.fetchall()]

                required_tables = ["clients", "trades", "grid_orders", "grid_instances"]
                missing_tables = [
                    table for table in required_tables if table not in tables
                ]

                if missing_tables:
                    return {
                        "healthy": False,
                        "error": f"Missing tables: {missing_tables}",
                        "message": "Database structure incomplete",
                    }

                # Count clients
                cursor = conn.execute("SELECT COUNT(*) FROM clients")
                client_count = cursor.fetchone()[0]

                return {
                    "healthy": True,
                    "client_count": client_count,
                    "tables": len(tables),
                    "message": "Database accessible and complete",
                }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "message": "Database connection failed",
            }

    def _check_config(self) -> dict:
        """Validate configuration"""
        try:
            is_valid = Config.validate()

            issues = []
            if not Config.TELEGRAM_BOT_TOKEN:
                issues.append("Missing TELEGRAM_BOT_TOKEN")
            if len(Config.ENCRYPTION_KEY) < 16:
                issues.append("ENCRYPTION_KEY too short")

            return {
                "healthy": is_valid and not issues,
                "environment": Config.ENVIRONMENT,
                "issues": issues if issues else None,
                "message": "Configuration valid"
                if is_valid and not issues
                else "Configuration issues found",
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "message": "Configuration check failed",
            }

    def _check_filesystem(self) -> dict:
        """Check file system access"""
        try:
            # Check if data directories exist and are writable
            data_dir = Path("data")
            logs_dir = Path("data/logs")
            backups_dir = Path("data/backups")

            # Create directories if they don't exist
            logs_dir.mkdir(parents=True, exist_ok=True)
            backups_dir.mkdir(parents=True, exist_ok=True)

            # Test write access
            test_file = logs_dir / "health_check_test.txt"
            test_file.write_text("test")
            test_file.unlink()

            return {
                "healthy": True,
                "data_dir_exists": data_dir.exists(),
                "logs_dir_writable": True,
                "message": "File system access OK",
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "message": "File system access failed",
            }

    def _check_memory_usage(self) -> dict:
        """Check memory usage if psutil is available"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_usage_mb = (memory.total - memory.available) / (1024 * 1024)
            memory_percent = memory.percent

            # Alert if memory usage > 90%
            is_healthy = memory_percent < 90

            return {
                "healthy": is_healthy,
                "usage_mb": round(memory_usage_mb, 2),
                "usage_percent": memory_percent,
                "available_mb": round(memory.available / (1024 * 1024), 2),
                "message": f"Memory usage: {memory_percent:.1f}%",
            }

        except ImportError:
            return {
                "healthy": True,
                "message": "Memory monitoring not available (psutil not installed)",
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "message": "Memory check failed"}


async def main():
    """Main health check function"""
    health_check = HealthCheck()
    status = await health_check.check_system_health()

    print("🏥 GridTrader Pro Health Check")
    print(f"⏰ {status['timestamp']}")
    print(f"📊 Overall Status: {status['status'].upper()}")
    print("=" * 50)

    for check_name, check_result in status["checks"].items():
        status_icon = "✅" if check_result["healthy"] else "❌"
        print(f"{status_icon} {check_name.title()}: {check_result['message']}")

        if not check_result["healthy"] and "error" in check_result:
            print(f"   Error: {check_result['error']}")

    print("=" * 50)

    # Return appropriate exit code
    if status["status"] == "healthy":
        print("✅ All systems operational")
        return 0
    else:
        print("❌ System issues detected")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
