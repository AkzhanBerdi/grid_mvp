# health_check.py
"""Health check endpoint for monitoring"""

import asyncio
import logging
import sqlite3
from datetime import datetime

from config import Config


class HealthCheck:
    """System health monitoring"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def check_system_health(self) -> dict:
        """Comprehensive system health check"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {},
        }

        try:
            # Database connectivity
            health_status["checks"]["database"] = self._check_database()

            # Configuration validation
            health_status["checks"]["config"] = self._check_config()

            # Active bot instances
            health_status["checks"]["bots"] = await self._check_bot_instances()

            # Memory usage
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
                cursor = conn.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]

                return {
                    "healthy": True,
                    "user_count": user_count,
                    "message": "Database accessible",
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
            return {
                "healthy": is_valid,
                "environment": Config.ENVIRONMENT,
                "message": "Configuration valid"
                if is_valid
                else "Missing required config",
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "message": "Configuration check failed",
            }

    async def _check_bot_instances(self) -> dict:
        """Check active bot instances"""
        try:
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.execute("""
                    SELECT status, COUNT(*) 
                    FROM bot_instances 
                    GROUP BY status
                """)

                status_counts = dict(cursor.fetchall())
                active_bots = status_counts.get("active", 0)

                return {
                    "healthy": True,
                    "active_bots": active_bots,
                    "status_breakdown": status_counts,
                    "message": f"{active_bots} bots active",
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "message": "Bot instance check failed",
            }

    def _check_memory_usage(self) -> dict:
        """Check memory usage"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_usage_mb = (memory.total - memory.available) / (1024 * 1024)
            memory_percent = memory.percent

            # Alert if memory usage > 80%
            is_healthy = memory_percent < 80

            return {
                "healthy": is_healthy,
                "usage_mb": round(memory_usage_mb, 2),
                "usage_percent": memory_percent,
                "message": f"Memory usage: {memory_percent}%",
            }
        except ImportError:
            return {
                "healthy": True,
                "message": "Memory monitoring not available (psutil not installed)",
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "message": "Memory check failed"}


if __name__ == "__main__":

    async def main():
        health_check = HealthCheck()
        status = await health_check.check_system_health()
        print(f"System Status: {status['status']}")
        for check_name, check_result in status["checks"].items():
            status_icon = "✅" if check_result["healthy"] else "❌"
            print(f"{status_icon} {check_name}: {check_result['message']}")

    asyncio.run(main())
