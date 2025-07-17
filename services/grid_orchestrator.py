# services/enhanced_grid_orchestrator.py - FIXED VERSION
"""Enhanced Grid Orchestrator - Fixed Market Analysis Issues"""

import logging
import os
from datetime import datetime
from typing import Dict

# Check for advanced features
ADVANCED_FEATURES_ENABLED = os.getenv("ADVANCED_FEATURES", "false").lower() == "true"


from binance.client import Client

from models.client import GridStatus
from repositories.client_repository import ClientRepository
from repositories.trade_repository import TradeRepository
from services.enhanced_dual_scale_manager import (
    EnhancedDualScaleGridManager as GridManager,
)
from services.market_analysis import MarketAnalysisService
from utils.crypto import CryptoUtils
from utils.fifo_telegram_monitor import FIFOMonitoringService


class GridOrchestrator:
    """Fixed enhanced orchestrator with proper error handling"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Advanced Features Support
        self.advanced_features = ADVANCED_FEATURES_ENABLED
        if self.advanced_features:
            self.logger.info(
                "🚀 ADVANCED FEATURES ENABLED - Enhanced Grid Orchestrator loaded"
            )
        else:
            self.logger.info("📊 Standard Grid Orchestrator loaded")
        self.client_repo = ClientRepository()
        self.trade_repo = TradeRepository()
        self.crypto_utils = CryptoUtils()

        # Client connections
        self.binance_clients: Dict[int, Client] = {}

        # Adaptive grid managers for each client
        self.adaptive_managers: Dict[int, GridManager] = {}

        # Market analysis service - initialized per client
        self.market_analysis_services: Dict[int, MarketAnalysisService] = {}

        # Performance tracking
        self.global_performance = {
            "total_clients": 0,
            "active_grids": 0,
            "total_trades": 0,
            "total_profit": 0.0,
            "market_adaptations": 0,
        }

    async def test_client_api(self, client_id: int) -> Dict:
        """Test client's Binance API connection"""
        try:
            client = self.client_repo.get_client(client_id)
            if (
                not client
                or not client.binance_api_key
                or not client.binance_secret_key
            ):
                return {"success": False, "error": "API keys not configured"}

            # Decrypt API keys
            api_key, secret_key = self.client_repo.get_decrypted_api_keys(client)
            if not api_key or not secret_key:
                return {"success": False, "error": "Failed to decrypt API keys"}

            # Create Binance client normally (SIMPLE FIX)
            binance_client = Client(api_key, secret_key, testnet=False)

            # Just set a custom recv_window for get_account specifically
            try:
                account = binance_client.get_account(recvWindow=60000)
            except Exception:
                # Fallback to default if recvWindow not supported
                account = binance_client.get_account()
            # Test connection
            try:
                account = binance_client.get_account(recvWindow=60000)
            except TypeError:
                account = binance_client.get_account()

            # Store client for later use
            self.binance_clients[client_id] = binance_client

            # Initialize market analysis service for this client
            self.market_analysis_services[client_id] = MarketAnalysisService(
                binance_client
            )

            return {
                "success": True,
                "account_type": account.get("accountType"),
                "can_trade": account.get("canTrade", False),
                "permissions": account.get("permissions", []),
                "balances_count": len(account.get("balances", [])),
            }

        except Exception as e:
            self.logger.error(f"❌ API test failed for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def start_client_grid(
        self, client_id: int, symbol: str, capital: float
    ) -> Dict:
        """Start smart adaptive grid trading for a client"""
        try:
            self.logger.info(
                f"🚀 Starting smart grid for client {client_id}: {symbol} with ${capital:,.2f}"
            )

            # Validate minimum capital first
            min_required = 160.0  # 16 orders × $10 minimum
            if capital < min_required:
                return {
                    "success": False,
                    "error": f"Minimum capital required: ${min_required:.2f} for NOTIONAL compliance",
                }

            # Ensure API connection
            if client_id not in self.binance_clients:
                api_test = await self.test_client_api(client_id)
                if not api_test["success"]:
                    return {
                        "success": False,
                        "error": "Failed to connect to Binance API",
                    }

            # Initialize adaptive grid manager for client
            if client_id not in self.adaptive_managers:
                self.adaptive_managers[client_id] = GridManager(
                    self.binance_clients[client_id], client_id
                )

            # Start adaptive grid
            manager = self.adaptive_managers[client_id]
            result = await manager.start_dual_scale_grid(symbol, capital)

            # Unified FIFO logging
            if hasattr(self, "fifo_service"):
                self.fifo_service.log_trade(
                    client_id, symbol, side, quantity, price, order_id
                )

            if result["success"]:
                # Update client status
                client = self.client_repo.get_client(client_id)
                client.grid_status = GridStatus.ACTIVE
                self.client_repo.update_client(client)

                # Update global performance
                self.global_performance["active_grids"] += 1

                # Enhanced result with smart trading info
                result.update(
                    {
                        "smart_trading_enabled": True,
                        "adaptive_grids": {
                            "base_grid": {
                                "always_active": True,
                                "purpose": "Consistent low-volume trading",
                                "capital_allocation": "40%",
                                "risk_level": "Conservative",
                            },
                            "enhanced_grid": {
                                "market_dependent": result.get(
                                    "enhanced_grid_orders", 0
                                )
                                > 0,
                                "purpose": "High-volume directional trading",
                                "capital_allocation": "60%",
                                "risk_level": result.get("risk_level", "Moderate"),
                            },
                        },
                    }
                )

                self.logger.info(
                    f"✅ Smart grid started for client {client_id}: {symbol}"
                )

            return result

        except Exception as e:
            self.logger.error(
                f"❌ Failed to start smart grid for client {client_id}: {e}"
            )
            return {"success": False, "error": str(e)}

    async def stop_all_client_grids(self, client_id: int) -> Dict:
        """Stop all adaptive grids for a client"""
        try:
            if client_id not in self.adaptive_managers:
                return {"success": True, "orders_cancelled": 0, "grids_stopped": 0}

            manager = self.adaptive_managers[client_id]
            total_orders_cancelled = 0

            # Get all active grids
            grids_status = manager.get_all_grids_status()

            # FIFO Integration - Log grid start/trade activity
            # Unified FIFO logging
            if hasattr(self, "fifo_service"):
                self.fifo_service.log_trade(
                    client_id, symbol, side, quantity, price, order_id
                )
            grids_stopped = len(grids_status)

            # Stop each grid
            for symbol in list(grids_status.keys()):
                stop_result = await manager.stop_adaptive_grid(symbol)

                # FIFO Integration - Log grid start/trade activity
                # Unified FIFO logging
                if hasattr(self, "fifo_service"):
                    self.fifo_service.log_trade(
                        client_id, symbol, side, quantity, price, order_id
                    )
                if stop_result["success"]:
                    total_orders_cancelled += 10  # Estimate based on grid size

            # Clean up manager
            del self.adaptive_managers[client_id]

            # Clean up market analysis service
            if client_id in self.market_analysis_services:
                del self.market_analysis_services[client_id]

            # Update client status
            client = self.client_repo.get_client(client_id)
            client.grid_status = GridStatus.INACTIVE
            self.client_repo.update_client(client)

            # Update global performance
            self.global_performance["active_grids"] = max(
                0, self.global_performance["active_grids"] - grids_stopped
            )

            return {
                "success": True,
                "orders_cancelled": total_orders_cancelled,
                "grids_stopped": grids_stopped,
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to stop grids for client {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_client_performance(self, client_id: int) -> Dict:
        """Get comprehensive performance metrics for a client"""
        try:
            # Get basic trade stats
            trade_stats = self.trade_repo.get_client_trade_stats(client_id)

            # Get adaptive grid performance if manager exists
            adaptive_performance = {}
            if client_id in self.adaptive_managers:
                manager = self.adaptive_managers[client_id]
                grids_status = manager.get_all_grids_status()

                # FIFO Integration - Log grid start/trade activity
                # Unified FIFO logging
                if hasattr(self, "fifo_service"):
                    self.fifo_service.log_trade(
                        client_id, symbol, side, quantity, price, order_id
                    )

                for symbol, grid_status in grids_status.items():
                    if grid_status.get("active"):
                        adaptive_performance[symbol] = {
                            "market_condition": grid_status.get("market_condition", {}),
                            "base_grid_active": grid_status.get(
                                "base_grid_active", False
                            ),
                            "enhanced_grid_active": grid_status.get(
                                "enhanced_grid_active", False
                            ),
                            "performance_metrics": grid_status.get(
                                "performance_metrics", {}
                            ),
                            "risk_level": grid_status.get("grid_config", {}).get(
                                "risk_level", "moderate"
                            ),
                        }

            # Enhanced performance data
            enhanced_performance = {
                "client_id": client_id,
                "trading_mode": "Smart Adaptive Grid",
                "basic_stats": {
                    "total_trades": trade_stats.get("total_trades", 0),
                    "total_profit": trade_stats.get("total_profit", 0.0),
                    "total_volume": trade_stats.get("total_volume", 0.0),
                    "win_rate": trade_stats.get("win_rate", 0.0),
                    "avg_profit_per_trade": (
                        trade_stats.get("total_profit", 0.0)
                        / max(1, trade_stats.get("total_trades", 1))
                    ),
                },
                "adaptive_performance": adaptive_performance,
                "smart_trading_insights": self._generate_trading_insights(
                    trade_stats, adaptive_performance
                ),
                "recent_trades": trade_stats.get("recent_trades", []),
            }

            return enhanced_performance

        except Exception as e:
            self.logger.error(
                f"❌ Failed to get performance for client {client_id}: {e}"
            )
            return {"error": str(e)}
        # FIFO Profit Monitoring Integration
        if FIFO_AVAILABLE:
            try:
                from main import GridTradingService

                if (
                    hasattr(GridTradingService, "_instance")
                    and GridTradingService._instance
                ):
                    self.fifo_service = GridTradingService._instance.fifo_service
                else:
                    self.fifo_service = FIFOMonitoringService()
            except:
                self.fifo_service = None
        else:
            self.fifo_service = None

    def _generate_trading_insights(
        self, trade_stats: Dict, adaptive_performance: Dict
    ) -> Dict:
        """Generate smart trading insights"""
        insights = {
            "market_adaptation_score": 0.0,
            "risk_management_score": 0.0,
            "efficiency_score": 0.0,
            "recommendations": [],
        }

        try:
            total_trades = trade_stats.get("total_trades", 0)
            total_profit = trade_stats.get("total_profit", 0.0)

            # Market adaptation score
            total_adaptations = sum(
                perf.get("performance_metrics", {}).get("market_adaptations", 0)
                for perf in adaptive_performance.values()
            )

            if total_adaptations > 0:
                insights["market_adaptation_score"] = min(1.0, total_adaptations / 10)

            # Risk management score
            avg_risk_level = 0.5  # Default moderate
            if adaptive_performance:
                risk_levels = [
                    0.3
                    if perf.get("risk_level") == "conservative"
                    else 0.5
                    if perf.get("risk_level") == "moderate"
                    else 0.7
                    for perf in adaptive_performance.values()
                ]
                avg_risk_level = (
                    sum(risk_levels) / len(risk_levels) if risk_levels else 0.5
                )

            insights["risk_management_score"] = 1.0 - abs(avg_risk_level - 0.5)

            # Efficiency score
            if total_trades > 0:
                profit_per_trade = total_profit / total_trades
                insights["efficiency_score"] = min(1.0, max(0.0, profit_per_trade / 10))

            # Generate recommendations
            if insights["market_adaptation_score"] < 0.3:
                insights["recommendations"].append(
                    "Consider increasing market monitoring frequency for better adaptation"
                )

            if insights["efficiency_score"] < 0.4:
                insights["recommendations"].append(
                    "Review grid spacing and levels for improved efficiency"
                )

            if avg_risk_level > 0.7:
                insights["recommendations"].append(
                    "Consider reducing position sizes in volatile market conditions"
                )

            return insights

        except Exception as e:
            self.logger.error(f"❌ Failed to generate trading insights: {e}")
            return insights

    def get_client_grid_status(self, client_id: int) -> Dict:
        """Get current grid status for a client"""
        try:
            if client_id not in self.adaptive_managers:
                return {"active_grids": {}, "total_grids": 0}

            manager = self.adaptive_managers[client_id]
            grids_status = manager.get_all_grids_status()

            # FIFO Integration - Log grid start/trade activity
            # Unified FIFO logging
            if hasattr(self, "fifo_service"):
                self.fifo_service.log_trade(
                    client_id, symbol, side, quantity, price, order_id
                )

            # Enhanced status with smart trading info
            enhanced_status = {
                "active_grids": {},
                "total_grids": len(grids_status),
                "trading_mode": "Smart Adaptive",
                "global_performance": self.global_performance,
            }

            for symbol, grid_status in grids_status.items():
                enhanced_status["active_grids"][symbol] = {
                    **grid_status,
                    "smart_features": {
                        "market_analysis": True,
                        "adaptive_spacing": True,
                        "dual_grid_system": True,
                        "risk_management": True,
                    },
                }

            return enhanced_status

        except Exception as e:
            self.logger.error(
                f"❌ Failed to get grid status for client {client_id}: {e}"
            )
            return {"error": str(e)}

    def get_all_active_grids(self) -> Dict:
        """Get all active grids across all clients"""
        all_grids = {}

    async def notify_fifo_trade_execution(
        self, client_id: int, symbol: str, side: str, quantity: float, price: float
    ):
        """Notify FIFO service of trade execution"""
        if hasattr(self, "fifo_service") and self.fifo_service:
            try:
                await self.fifo_service.on_trade_executed(
                    client_id=client_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                )
                self.logger.info(
                    f"📊 FIFO: {side} {quantity} {symbol} @ ${price:.4f} for client {client_id}"
                )

                # Get updated profit stats
                if (
                    hasattr(self.fifo_service, "monitors")
                    and client_id in self.fifo_service.monitors
                ):
                    calculator = self.fifo_service.monitors[client_id]
                    stats = calculator.calculate_fifo_profit(client_id)
                    if stats["total_profit"] != 0:
                        self.logger.info(
                            f"💰 Client {client_id} FIFO Profit: ${stats['total_profit']:.2f}"
                        )

            except Exception as e:
                self.logger.warning(f"FIFO notification failed: {e}")

    def get_fifo_stats(self, client_id: int) -> dict:
        """Get current FIFO stats for a client"""
        try:
            if hasattr(self, "fifo_service") and self.fifo_service:
                if (
                    hasattr(self.fifo_service, "monitors")
                    and client_id in self.fifo_service.monitors
                ):
                    calculator = self.fifo_service.monitors[client_id]
                    return calculator.calculate_fifo_profit(client_id)
        except Exception as e:
            self.logger.warning(f"Failed to get FIFO stats: {e}")

        return {"total_profit": 0.0, "total_trades": 0, "win_rate": 0.0}

        for client_id, manager in self.adaptive_managers.items():
            try:
                grids_status = manager.get_all_grids_status()

                # FIFO Integration - Log grid start/trade activity
                # Unified FIFO logging
                if hasattr(self, "fifo_service"):
                    self.fifo_service.log_trade(
                        client_id, symbol, side, quantity, price, order_id
                    )
                if grids_status:
                    all_grids[client_id] = {
                        "client_id": client_id,
                        "grids": grids_status,
                        "trading_mode": "Smart Adaptive",
                    }
            except Exception as e:
                self.logger.error(f"❌ Failed to get grids for client {client_id}: {e}")

        return all_grids

    async def update_all_grids(self):
        """Update all active adaptive grids"""
        for client_id, manager in list(self.adaptive_managers.items()):
            try:
                # The adaptive manager handles its own monitoring
                # We just need to update global performance
                grids_status = manager.get_all_grids_status()

                # FIFO Integration - Log grid start/trade activity
                # Unified FIFO logging
                if hasattr(self, "fifo_service"):
                    self.fifo_service.log_trade(
                        client_id, symbol, side, quantity, price, order_id
                    )

                # Update global stats
                total_trades = 0
                total_profit = 0.0

                for grid_status in grids_status.values():
                    if grid_status.get("active"):
                        metrics = grid_status.get("performance_metrics", {})
                        total_trades += metrics.get("total_trades", 0)
                        total_profit += metrics.get("total_profit", 0.0)

                self.global_performance.update(
                    {"total_trades": total_trades, "total_profit": total_profit}
                )

            except Exception as e:
                self.logger.error(
                    f"❌ Failed to update grids for client {client_id}: {e}"
                )

    async def shutdown_all_grids(self):
        """Gracefully shutdown all adaptive grids"""
        self.logger.info("🛑 Shutting down all smart adaptive grids...")

        for client_id in list(self.adaptive_managers.keys()):
            try:
                await self.stop_all_client_grids(client_id)
            except Exception as e:
                self.logger.error(
                    f"❌ Failed to shutdown grids for client {client_id}: {e}"
                )

        # Clear all connections
        self.binance_clients.clear()
        self.adaptive_managers.clear()
        self.market_analysis_services.clear()

        self.logger.info("✅ All smart adaptive grids shut down")

    async def get_market_overview(self) -> Dict:
        """Get market overview with proper error handling"""
        try:
            # Get all unique symbols being traded
            symbols = set()
            for manager in self.adaptive_managers.values():
                try:
                    grids_status = manager.get_all_grids_status()

                    # FIFO Integration - Log grid start/trade activity
                    # Unified FIFO logging
                    if hasattr(self, "fifo_service"):
                        self.fifo_service.log_trade(
                            client_id, symbol, side, quantity, price, order_id
                        )
                        symbols.update(grids_status.keys())
                except Exception as e:
                    self.logger.warning(f"Failed to get grid status from manager: {e}")

            if not symbols:
                return {
                    "error": "No active trading pairs found",
                    "timestamp": datetime.now().isoformat(),
                    "symbols_tracked": 0,
                    "global_performance": self.global_performance,
                }

            # Get market conditions for each symbol
            market_overview = {}

            # Use any available market analysis service
            market_service = None
            for service in self.market_analysis_services.values():
                market_service = service
                break

            if not market_service:
                return {
                    "error": "Market analysis service not available",
                    "timestamp": datetime.now().isoformat(),
                    "symbols_tracked": len(symbols),
                    "global_performance": self.global_performance,
                }

            for symbol in symbols:
                try:
                    condition = await market_service.get_market_condition(symbol)
                    market_overview[symbol] = condition
                except Exception as e:
                    self.logger.warning(
                        f"❌ Failed to get market condition for {symbol}: {e}"
                    )
                    # Provide fallback condition
                    market_overview[symbol] = {
                        "condition": "neutral",
                        "score": 0.5,
                        "confidence": 0.0,
                        "error": f"Analysis failed: {str(e)}",
                    }

            return {
                "timestamp": datetime.now().isoformat(),
                "symbols_tracked": len(symbols),
                "market_conditions": market_overview,
                "global_performance": self.global_performance,
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to get market overview: {e}")
            return {
                "error": f"Market overview failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "symbols_tracked": 0,
                "global_performance": self.global_performance,
            }

    async def optimize_all_grids(self):
        """Optimize all active grids based on performance"""
        try:
            optimization_results = {}

            for client_id, manager in self.adaptive_managers.items():
                try:
                    grids_status = manager.get_all_grids_status()

                    # FIFO Integration - Log grid start/trade activity
                    # Unified FIFO logging
                    if hasattr(self, "fifo_service"):
                        self.fifo_service.log_trade(
                            client_id, symbol, side, quantity, price, order_id
                        )

                    for symbol, grid_status in grids_status.items():
                        if grid_status.get("active"):
                            # Analyze performance
                            performance = grid_status.get("performance_metrics", {})

                            # Optimization recommendations
                            recommendations = []

                            # Check efficiency
                            efficiency = performance.get("efficiency_score", 0.0)
                            if efficiency < 0.5:
                                recommendations.append(
                                    "Consider adjusting grid spacing"
                                )

                            # Check risk levels
                            risk_score = performance.get("risk_score", 0.0)
                            if risk_score > 0.7:
                                recommendations.append(
                                    "Consider reducing position sizes"
                                )

                            # Check market adaptation
                            adaptations = performance.get("market_adaptations", 0)
                            if adaptations > 10:
                                recommendations.append(
                                    "Market highly volatile, consider wider grids"
                                )

                            optimization_results[f"{client_id}_{symbol}"] = {
                                "performance": performance,
                                "recommendations": recommendations,
                            }

                except Exception as e:
                    self.logger.error(
                        f"❌ Failed to optimize grids for client {client_id}: {e}"
                    )

            return optimization_results

        except Exception as e:
            self.logger.error(f"❌ Grid optimization failed: {e}")
            return {"error": str(e)}

        # Enhanced Features Methods

    async def start_client_grid(
        self, client_id: int, symbol: str, capital: float
    ) -> Dict:
        """Enhanced grid startup with advanced features"""
        try:
            self.logger.info(
                f"🚀 Starting ENHANCED grid for client {client_id}: {symbol} with ${capital:,.2f}"
            )

            # Ensure API connection
            if client_id not in self.binance_clients:
                api_test = await self.test_client_api(client_id)
                if not api_test["success"]:
                    return {
                        "success": False,
                        "error": "Failed to connect to Binance API",
                    }

            # Initialize ENHANCED adaptive grid manager
            if client_id not in self.adaptive_managers:
                self.adaptive_managers[client_id] = EnhancedDualScaleGridManager(
                    self.binance_clients[client_id], client_id
                )
                self.logger.info(f"✅ Enhanced manager created for client {client_id}")

            # Start ENHANCED dual-scale grid
            manager = self.adaptive_managers[client_id]
            result = await manager.start_enhanced_dual_scale_grid(symbol, capital)

            if result["success"]:
                # Update client status

                client = self.client_repo.get_client(client_id)
                client.grid_status = GridStatus.ACTIVE
                self.client_repo.update_client(client)

                # Enhanced logging
                self.logger.info(f"🎉 ENHANCED grid started for client {client_id}:")
                self.logger.info(
                    f"   💰 Compound Management: {result.get('enhanced_features', {}).get('compound_management', {}).get('status', 'Active')}"
                )
                self.logger.info(
                    f"   🛡️ Volatility Regime: {result.get('enhanced_features', {}).get('volatility_management', {}).get('regime', 'Moderate')}"
                )
                self.logger.info(
                    f"   ⏰ Market Session: {result.get('enhanced_features', {}).get('market_timing', {}).get('session', 'Normal')}"
                )

            return result

        except Exception as e:
            self.logger.error(
                f"❌ Enhanced grid startup error for client {client_id}: {e}"
            )
            return {"success": False, "error": str(e)}

    def get_all_active_grids(self) -> Dict:
        """Get all active enhanced grids"""
        all_grids = {}

        for client_id, manager in self.adaptive_managers.items():
            try:
                if hasattr(manager, "get_all_enhanced_grids_status"):
                    grids_status = manager.get_all_enhanced_grids_status()
                    if grids_status and grids_status.get("grids"):
                        all_grids[client_id] = {
                            "client_id": client_id,
                            "grids": grids_status["grids"],
                            "trading_mode": "Enhanced Dual-Scale with Advanced Features",
                            "enhanced_features": grids_status.get(
                                "global_summary", {}
                            ).get("enhanced_features_enabled", {}),
                        }
            except Exception as e:
                self.logger.error(
                    f"❌ Failed to get enhanced grids for client {client_id}: {e}"
                )

        return all_grids
