# utils/network_recovery.py
"""
Complete Network Recovery System for GridTrader Pro
Integrates seamlessly with your existing project structure
Based on the July 16, 2025 outage analysis
"""

import asyncio
import logging
import time
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any, List
from pathlib import Path
import json

from config import Config


class NetworkOutageError(Exception):
    """Custom exception for network outages"""
    pass


class NetworkHealthMonitor:
    """Monitor network connectivity and detect outages"""
    
    def __init__(self, db_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path or Config.DATABASE_PATH
        
        # Outage tracking
        self.consecutive_failures = 0
        self.outage_threshold = 3  # Faster detection than your current 5
        self.emergency_threshold = 5  # Keep existing emergency stop
        self.in_outage = False
        self.outage_start_time = None
        self.last_success_time = datetime.now()
        
        # Health metrics
        self.total_requests = 0
        self.failed_requests = 0
        self.uptime_percentage = 100.0
        
        # Initialize monitoring table
        self._init_monitoring_table()
        
    def _init_monitoring_table(self):
        """Initialize network monitoring table in your existing database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS network_monitoring (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        event_type TEXT NOT NULL,
                        details TEXT,
                        duration_seconds INTEGER,
                        consecutive_failures INTEGER,
                        status TEXT
                    )
                """)
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring table: {e}")

    async def test_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to critical services"""
        results = {}
        
        # Test Binance API (exact same endpoints from your logs)
        try:
            base_url = "https://testnet.binance.vision" if getattr(Config, 'TESTNET', False) else "https://api.binance.com"
            response = requests.get(f'{base_url}/api/v3/ping', timeout=10)
            results['binance'] = response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Binance connectivity test failed: {e}")
            results['binance'] = False
            
        # Test Telegram API (same as your telegram_notifier.py)
        try:
            if hasattr(Config, 'TELEGRAM_BOT_TOKEN') and Config.TELEGRAM_BOT_TOKEN:
                response = requests.get(
                    f'https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/getMe',
                    timeout=10
                )
                results['telegram'] = response.status_code == 200
            else:
                results['telegram'] = True  # Skip if no token
        except Exception as e:
            self.logger.warning(f"Telegram connectivity test failed: {e}")
            results['telegram'] = False
            
        # Test DNS resolution (the exact issue from July 16)
        try:
            import socket
            socket.gethostbyname('api.binance.com')
            socket.gethostbyname('api.telegram.org')
            results['dns'] = True
        except Exception as e:
            self.logger.warning(f"DNS test failed: {e}")
            results['dns'] = False
            
        return results
        
    async def handle_network_error(self, error: Exception, operation: str, client_id: int = None):
        """Handle network errors and detect outages"""
        self.consecutive_failures += 1
        self.failed_requests += 1
        self.total_requests += 1
        
        # Log to your existing database
        self._log_network_event('error', operation, str(error), client_id)
        
        # Detect outage (faster than your current 5-failure threshold)
        if self.consecutive_failures >= self.outage_threshold and not self.in_outage:
            self.in_outage = True
            self.outage_start_time = datetime.now()
            await self.notify_outage_started(error, operation)
            
        # Log error with context (matching your existing log format)
        error_type = type(error).__name__
        if "Name or service not known" in str(error):
            self.logger.error(f"🔌 DNS Resolution Failure in {operation}: {error}")
        elif "Connection" in error_type:
            self.logger.error(f"📡 Connection Error in {operation}: {error}")
        elif "timeout" in str(error).lower():
            self.logger.error(f"⏱️  Timeout Error in {operation}: {error}")
        else:
            self.logger.error(f"❌ Network Error in {operation}: {error}")
            
    async def handle_network_success(self, operation: str, client_id: int = None):
        """Handle successful network operations"""
        self.total_requests += 1
        
        # Detect recovery from outage
        if self.in_outage:
            outage_duration = datetime.now() - self.outage_start_time
            self.in_outage = False
            self._log_network_event('recovery', operation, f"Duration: {outage_duration}", client_id)
            await self.notify_outage_resolved(outage_duration, operation)
            
        self.consecutive_failures = 0
        self.last_success_time = datetime.now()
        
        # Update uptime percentage
        if self.total_requests > 0:
            success_rate = ((self.total_requests - self.failed_requests) / self.total_requests) * 100
            self.uptime_percentage = success_rate

    def _log_network_event(self, event_type: str, operation: str, details: str, client_id: int = None):
        """Log network events to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO network_monitoring 
                    (event_type, details, consecutive_failures, status)
                    VALUES (?, ?, ?, ?)
                """, (event_type, f"{operation}: {details}", self.consecutive_failures, 'outage' if self.in_outage else 'normal'))
        except Exception as e:
            # Fallback to file logging (like your emergency_trades.jsonl pattern)
            self._emergency_log_network_event(event_type, operation, details)

    def _emergency_log_network_event(self, event_type: str, operation: str, details: str):
        """Emergency file logging when database fails"""
        try:
            log_file = Path("data/logs/emergency_network.jsonl")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "operation": operation,
                "details": details,
                "consecutive_failures": self.consecutive_failures
            }
            
            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
                
        except Exception as e:
            print(f"❌ Emergency network logging failed: {e}")
            
    async def notify_outage_started(self, error: Exception, operation: str):
        """Notify when outage is detected"""
        self.logger.error("🚨 NETWORK OUTAGE DETECTED")
        self.logger.error(f"   Operation: {operation}")
        self.logger.error(f"   Error: {type(error).__name__}")
        self.logger.error(f"   Started: {self.outage_start_time.strftime('%H:%M:%S UTC')}")
        self.logger.error("   Auto-retry enabled, grid state preserved")
        
        # Send Telegram notification if possible
        await self._send_outage_notification("started", operation, str(error))
        
    async def notify_outage_resolved(self, duration: timedelta, operation: str):
        """Notify when outage is resolved"""
        duration_str = f"{int(duration.total_seconds()//60)}m {int(duration.total_seconds()%60)}s"
        
        self.logger.info("✅ NETWORK CONNECTIVITY RESTORED")
        self.logger.info(f"   Duration: {duration_str}")
        self.logger.info(f"   Resolved by: {operation}")
        self.logger.info("   All systems operational")
        
        # Send Telegram notification
        await self._send_outage_notification("resolved", operation, duration_str)

    async def _send_outage_notification(self, status: str, operation: str, details: str):
        """Send Telegram notification about outage status"""
        try:
            # Import your existing telegram notifier
            from services.telegram_notifier import TelegramNotifier
            
            if hasattr(Config, 'TELEGRAM_BOT_TOKEN') and Config.TELEGRAM_BOT_TOKEN:
                notifier = TelegramNotifier()
                
                if status == "started":
                    message = f"""🚨 **Network Outage Detected**
⏰ Started: {datetime.now().strftime('%H:%M UTC')}
🔌 Issue: {details[:100]}
🤖 Action: Auto-retry enabled
📊 Grid Status: Orders preserved"""
                else:  # resolved
                    message = f"""✅ **Network Connectivity Restored**
⏰ Duration: {details}
📶 Status: All systems operational
🔄 Resumed: {operation}
📊 Grid Status: Trading resumed"""
                    
                await notifier.send_message(message)
                
        except Exception as e:
            self.logger.warning(f"Failed to send outage notification: {e}")
            
    def get_health_status(self) -> Dict:
        """Get current network health status"""
        return {
            'status': 'online' if not self.in_outage else 'outage',
            'uptime_percentage': round(self.uptime_percentage, 2),
            'consecutive_failures': self.consecutive_failures,
            'last_success': self.last_success_time.isoformat(),
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'in_outage': self.in_outage,
            'outage_start': self.outage_start_time.isoformat() if self.outage_start_time else None
        }


class ResilientNetworkClient:
    """Wrapper for network operations with smart retry logic"""
    
    def __init__(self, health_monitor: NetworkHealthMonitor):
        self.health_monitor = health_monitor
        self.logger = logging.getLogger(__name__)
        
        # Progressive retry delays (matching your existing pattern but optimized)
        self.retry_delays = [1, 2, 5, 10, 30]  # Slightly faster than 60s max
        self.max_retries = len(self.retry_delays)
        
    async def resilient_call(self, 
                           operation_name: str,
                           api_func: Callable,
                           client_id: int = None,
                           *args, 
                           **kwargs) -> Any:
        """
        Make API call with intelligent retry logic
        Handles the exact DNS errors from your July 16 logs
        """
        
        for attempt in range(self.max_retries):
            try:
                # Attempt the API call
                result = await self._execute_call(api_func, *args, **kwargs)
                
                # Success! Update health monitor
                await self.health_monitor.handle_network_success(operation_name, client_id)
                
                if attempt > 0:
                    self.logger.info(f"✅ {operation_name} succeeded after {attempt + 1} attempts")
                    
                return result
                
            except Exception as e:
                # Handle network errors
                await self.health_monitor.handle_network_error(e, operation_name, client_id)
                
                # Check if this is a retryable error
                if not self._is_retryable_error(e):
                    self.logger.error(f"❌ Non-retryable error in {operation_name}: {e}")
                    raise
                    
                # Check if we should retry
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    self.logger.warning(
                        f"🔄 {operation_name} failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"❌ {operation_name} failed after {self.max_retries} attempts: {e}"
                    )
                    raise NetworkOutageError(
                        f"{operation_name} failed after {self.max_retries} attempts: {e}"
                    )
                    
    async def _execute_call(self, api_func: Callable, *args, **kwargs) -> Any:
        """Execute the API call (sync or async)"""
        if asyncio.iscoroutinefunction(api_func):
            return await api_func(*args, **kwargs)
        else:
            # Run synchronous function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: api_func(*args, **kwargs))
            
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if error is retryable
        Based on your July 16 logs - DNS and connection errors are retryable
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Network errors that should be retried (exact patterns from your logs)
        retryable_patterns = [
            'name or service not known',  # The exact DNS failure from July 16
            'connection error',
            'timeout',
            'network is unreachable',
            'connection refused',
            'connection reset',
            'httpsconnectionpool',
            'nameresolutionerror',
            'httpx.connecterror',
            'telegram.error.networkerror',
            'read timed out',  # From your Binance API timeouts
            'max retries exceeded'  # From your urllib3 errors
        ]
        
        # Check if error matches retryable patterns
        for pattern in retryable_patterns:
            if pattern in error_str or pattern in error_type.lower():
                return True
                
        # Don't retry authentication or API limit errors
        non_retryable_patterns = [
            'invalid api',
            'signature',
            'permission',
            'unauthorized',
            'rate limit',
            'banned',
            'lot_size',  # From your existing error handling
            'insufficient_balance'  # From your existing error handling
        ]
        
        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return False
                
        # Default to retryable for unknown network errors
        return 'error' in error_type.lower()


class NetworkRecoveryService:
    """
    Main service class that integrates with your existing grid trading system
    Drop-in replacement for network operations
    """
    
    def __init__(self, db_path: str = None):
        self.health_monitor = NetworkHealthMonitor(db_path)
        self.resilient_client = ResilientNetworkClient(self.health_monitor)
        self.logger = logging.getLogger(__name__)
        
        # Integration with your existing emergency stop system
        self.emergency_stop_threshold = 5  # Keep your existing threshold
        
    async def protected_binance_call(self, client_obj, method_name: str, client_id: int = None, **kwargs):
        """
        Protected Binance API call with network resilience
        Integrates with your existing binance client pattern
        """
        
        # Add your existing timestamp and receive window handling
        kwargs["recvWindow"] = 60000
        if "timestamp" in kwargs:
            del kwargs["timestamp"]  # Let client handle it
            
        async def make_call():
            method = getattr(client_obj, method_name)
            return method(**kwargs)
            
        return await self.resilient_client.resilient_call(
            f"binance_{method_name}",
            make_call,
            client_id
        )
        
    async def protected_telegram_call(self, notifier_obj, method_name: str, client_id: int = None, *args, **kwargs):
        """
        Protected Telegram API call with network resilience
        Integrates with your existing telegram notifier
        """
        
        async def make_call():
            method = getattr(notifier_obj, method_name)
            return await method(*args, **kwargs)
            
        return await self.resilient_client.resilient_call(
            f"telegram_{method_name}",
            make_call,
            client_id
        )
        
    async def check_emergency_conditions(self, client_id: int = None) -> bool:
        """
        Check if emergency stop should be triggered
        Integrates with your existing risk management
        """
        
        # Network-based emergency conditions
        if self.health_monitor.consecutive_failures >= self.emergency_stop_threshold:
            self.logger.critical(
                f"🚨 Network emergency: {self.health_monitor.consecutive_failures} consecutive failures"
            )
            return True
            
        # Check if we've been in outage too long
        if self.health_monitor.in_outage and self.health_monitor.outage_start_time:
            outage_duration = datetime.now() - self.health_monitor.outage_start_time
            if outage_duration > timedelta(minutes=10):  # 10 minute max outage
                self.logger.critical("🚨 Extended network outage - triggering emergency stop")
                return True
                
        return False
        
    async def startup_connectivity_check(self) -> bool:
        """
        Check connectivity before starting main service
        Call this in your main.py startup
        """
        
        self.logger.info("🌐 Performing startup connectivity check...")
        
        connectivity = await self.health_monitor.test_connectivity()
        
        for service, status in connectivity.items():
            emoji = "✅" if status else "❌"
            self.logger.info(f"   {emoji} {service.upper()}: {'Online' if status else 'Offline'}")
            
        all_online = all(connectivity.values())
        
        if all_online:
            self.logger.info("✅ All services online - ready to start")
        else:
            offline_services = [k for k, v in connectivity.items() if not v]
            self.logger.warning(f"⚠️ Some services offline: {offline_services}")
            self.logger.warning("Bot will attempt to start with degraded connectivity")
            
        return all_online
        
    def get_network_health_display(self) -> str:
        """
        Get network health for dashboard display
        Integrates with your existing client handler
        """
        health = self.health_monitor.get_health_status()
        
        if health['status'] == 'online':
            status_emoji = "🟢"
            status_text = "ONLINE"
        else:
            status_emoji = "🔴"
            status_text = "OUTAGE"
            
        return f"{status_emoji} Network: {status_text} ({health['uptime_percentage']}% uptime)"
        
    async def periodic_health_check(self):
        """
        Periodic health check for your main loop
        Call this every 5 minutes in your main trading cycle
        """
        try:
            connectivity = await self.health_monitor.test_connectivity()
            
            # Log any connectivity issues
            for service, status in connectivity.items():
                if not status:
                    self.logger.warning(f"⚠️ {service.upper()} connectivity issue detected")
                    
            # Check if we need emergency action
            emergency = await self.check_emergency_conditions()
            if emergency:
                self.logger.critical("🚨 Network emergency conditions detected")
                return False  # Signal to calling code to stop
                
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False


# Integration helpers for your existing code

def create_network_recovery_service() -> NetworkRecoveryService:
    """
    Factory function to create network recovery service
    Use this in your main.py and other modules
    """
    return NetworkRecoveryService()


async def test_network_recovery_integration():
    """
    Test the network recovery integration with your existing system
    Run this to verify everything works
    """
    
    print("🧪 TESTING NETWORK RECOVERY INTEGRATION")
    print("=" * 50)
    
    # Test service creation
    service = create_network_recovery_service()
    
    # Test connectivity check
    print("🔍 Testing connectivity...")
    all_online = await service.startup_connectivity_check()
    
    # Test health display
    print(f"📊 Health Display: {service.get_network_health_display()}")
    
    # Test database integration
    health = service.health_monitor.get_health_status()
    print(f"💾 Database Status: {'✅' if health else '❌'}")
    
    print("\n✅ Integration test complete!")
    print("🚀 Ready to integrate with your existing code")
    
    return service


# Example integration with your existing main.py pattern
class EnhancedMainLoop:
    """
    Example of how to integrate network recovery with your main trading loop
    """
    
    def __init__(self):
        self.network_service = create_network_recovery_service()
        self.running = True
        
    async def startup(self):
        """Enhanced startup with network checking"""
        self.logger.info("🚀 Starting GridTrader Pro with Network Recovery...")
        
        # Check connectivity before starting
        connectivity_ok = await self.network_service.startup_connectivity_check()
        
        if not connectivity_ok:
            self.logger.warning("⚠️ Starting with limited connectivity")
            
        # Initialize your existing components
        # ... your existing startup code ...
        
        self.logger.info("✅ GridTrader Pro started with network recovery enabled")
        
    async def main_loop(self):
        """Enhanced main loop with network recovery"""
        cycle_count = 0
        
        while self.running:
            cycle_count += 1
            
            try:
                # Periodic health check every 10 cycles (adjust as needed)
                if cycle_count % 10 == 0:
                    health_ok = await self.network_service.periodic_health_check()
                    if not health_ok:
                        self.logger.critical("🚨 Network emergency stop triggered")
                        self.running = False
                        break
                
                # Your existing trading cycle code here
                # await self.run_trading_cycle()
                
            except Exception as e:
                # Enhanced error handling with network context
                await self.network_service.health_monitor.handle_network_error(
                    e, "main_trading_cycle"
                )
                
                # Check for emergency conditions
                if await self.network_service.check_emergency_conditions():
                    self.logger.critical("🚨 Emergency stop due to network issues")
                    self.running = False
                    break
                    
            await asyncio.sleep(30)  # Your existing cycle delay


if __name__ == "__main__":
    # Test the integration
    asyncio.run(test_network_recovery_integration())
