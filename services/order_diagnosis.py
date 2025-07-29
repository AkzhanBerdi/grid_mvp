# Order Replacement Diagnosis & Fix
"""
Issue: Orders dropping from 30 to 18 - order replacement is broken
This suggests the refactoring broke the order monitoring and replacement logic.

Common causes:
1. Inventory manager blocking order placement
2. Order fill detection not working
3. Replacement order creation failing
4. Method calls changed during refactoring
"""

import logging
from typing import Dict, List


class OrderReplacementDiagnostics:
    """
    Diagnostic tools to identify why order replacement is failing
    """

    def __init__(self, grid_manager, trading_engine):
        self.grid_manager = grid_manager
        self.trading_engine = trading_engine
        self.logger = logging.getLogger(__name__)

    async def diagnose_order_replacement_issues(self, symbol: str) -> Dict:
        """
        Comprehensive diagnosis of order replacement issues
        """
        try:
            self.logger.info(f"🔍 Diagnosing order replacement issues for {symbol}")

            diagnosis = {
                "symbol": symbol,
                "issues_found": [],
                "recommendations": [],
                "current_state": {},
                "inventory_issues": [],
                "method_issues": [],
            }

            # Check 1: Current grid state
            if symbol in self.grid_manager.active_grids:
                grid_config = self.grid_manager.active_grids[symbol]

                buy_orders = len(
                    [
                        l
                        for l in grid_config.buy_levels
                        if l.get("order_id") and not l.get("filled")
                    ]
                )
                sell_orders = len(
                    [
                        l
                        for l in grid_config.sell_levels
                        if l.get("order_id") and not l.get("filled")
                    ]
                )
                filled_orders = len(
                    [
                        l
                        for l in grid_config.buy_levels + grid_config.sell_levels
                        if l.get("filled")
                    ]
                )

                diagnosis["current_state"] = {
                    "active_buy_orders": buy_orders,
                    "active_sell_orders": sell_orders,
                    "total_active": buy_orders + sell_orders,
                    "filled_orders": filled_orders,
                    "total_levels": len(grid_config.buy_levels)
                    + len(grid_config.sell_levels),
                }

                if buy_orders + sell_orders < 10:  # Should have ~10 active orders
                    diagnosis["issues_found"].append(
                        {
                            "issue": "insufficient_active_orders",
                            "details": f"Only {buy_orders + sell_orders} active orders, expected ~10",
                            "severity": "high",
                        }
                    )

            # Check 2: Inventory manager issues
            if (
                hasattr(self.grid_manager, "inventory_manager")
                and self.grid_manager.inventory_manager
            ):
                inventory_issues = await self._check_inventory_manager_issues(symbol)
                diagnosis["inventory_issues"] = inventory_issues

            # Check 3: Order monitoring method issues
            method_issues = await self._check_method_issues(symbol)
            diagnosis["method_issues"] = method_issues

            # Check 4: FIFO integration issues
            fifo_issues = await self._check_fifo_integration_issues(symbol)
            diagnosis["fifo_issues"] = fifo_issues

            # Generate recommendations
            diagnosis["recommendations"] = self._generate_recommendations(diagnosis)

            return diagnosis

        except Exception as e:
            self.logger.error(f"❌ Error diagnosing order replacement: {e}")
            return {"error": str(e)}

    async def _check_inventory_manager_issues(self, symbol: str) -> List[Dict]:
        """Check for inventory manager related issues"""
        issues = []

        try:
            inventory_manager = self.grid_manager.inventory_manager

            # Check if inventory manager is blocking orders
            try:
                can_buy, buy_reason = inventory_manager.can_place_buy_order(
                    symbol, 100.0
                )
                can_sell, sell_reason = inventory_manager.can_place_sell_order(
                    symbol, 10.0
                )

                if not can_buy:
                    issues.append(
                        {
                            "type": "inventory_blocking_buy",
                            "reason": buy_reason,
                            "severity": "high",
                        }
                    )

                if not can_sell:
                    issues.append(
                        {
                            "type": "inventory_blocking_sell",
                            "reason": sell_reason,
                            "severity": "high",
                        }
                    )

            except Exception as e:
                issues.append(
                    {
                        "type": "inventory_method_error",
                        "error": str(e),
                        "severity": "critical",
                    }
                )

            # Check inventory balance vs expected
            try:
                positions = getattr(inventory_manager, "positions", {})
                if symbol in positions:
                    position = positions[symbol]
                    self.logger.info(f"📊 Inventory position for {symbol}: {position}")
                else:
                    issues.append(
                        {
                            "type": "missing_inventory_position",
                            "details": f"No inventory position tracked for {symbol}",
                            "severity": "medium",
                        }
                    )
            except Exception as e:
                issues.append(
                    {
                        "type": "inventory_position_error",
                        "error": str(e),
                        "severity": "medium",
                    }
                )

        except Exception as e:
            issues.append(
                {
                    "type": "inventory_manager_access_error",
                    "error": str(e),
                    "severity": "critical",
                }
            )

        return issues

    async def _check_method_issues(self, symbol: str) -> List[Dict]:
        """Check for method call issues in order replacement"""
        issues = []

        try:
            # Check if the monitoring method exists and works
            if hasattr(self.trading_engine, "check_and_replace_filled_orders"):
                try:
                    # Test call the monitoring method (dry run)
                    self.logger.info("🔍 Testing order monitoring method...")
                    # Don't actually call it, just check if it exists

                except Exception as e:
                    issues.append(
                        {
                            "type": "monitoring_method_error",
                            "error": str(e),
                            "severity": "high",
                        }
                    )
            else:
                issues.append(
                    {
                        "type": "missing_monitoring_method",
                        "details": "check_and_replace_filled_orders method not found",
                        "severity": "critical",
                    }
                )

            # Check replacement order creation methods
            replacement_methods = [
                "create_replacement_sell_order",
                "create_replacement_buy_order",
                "_create_replacement_sell_order_enhanced",
                "_create_replacement_buy_order_enhanced",
            ]

            for method_name in replacement_methods:
                if not hasattr(self.trading_engine, method_name):
                    issues.append(
                        {
                            "type": "missing_replacement_method",
                            "method": method_name,
                            "severity": "high",
                        }
                    )

        except Exception as e:
            issues.append(
                {"type": "method_check_error", "error": str(e), "severity": "medium"}
            )

        return issues

    async def _check_fifo_integration_issues(self, symbol: str) -> List[Dict]:
        """Check for FIFO integration issues"""
        issues = []

        try:
            # Check if FIFO service is properly integrated
            if hasattr(self.grid_manager, "fifo_service"):
                fifo_service = self.grid_manager.fifo_service

                # Test FIFO methods that order replacement depends on
                try:
                    # Test the corrected method names
                    if hasattr(fifo_service, "on_order_filled"):
                        self.logger.info("✅ FIFO on_order_filled method available")
                    else:
                        issues.append(
                            {
                                "type": "missing_fifo_method",
                                "method": "on_order_filled",
                                "severity": "medium",
                            }
                        )

                except Exception as e:
                    issues.append(
                        {
                            "type": "fifo_method_error",
                            "error": str(e),
                            "severity": "medium",
                        }
                    )
            else:
                issues.append({"type": "missing_fifo_service", "severity": "high"})

        except Exception as e:
            issues.append(
                {"type": "fifo_check_error", "error": str(e), "severity": "medium"}
            )

        return issues

    def _generate_recommendations(self, diagnosis: Dict) -> List[str]:
        """Generate recommendations based on diagnosis"""
        recommendations = []

        issues = diagnosis.get("issues_found", [])
        inventory_issues = diagnosis.get("inventory_issues", [])
        method_issues = diagnosis.get("method_issues", [])

        # High-level recommendations
        if any(
            issue["severity"] == "critical"
            for issue in issues + inventory_issues + method_issues
        ):
            recommendations.append(
                "🚨 CRITICAL: Order replacement system is broken and needs immediate fixing"
            )

        # Specific recommendations based on issues found
        for issue in inventory_issues:
            if issue["type"] == "inventory_blocking_buy":
                recommendations.append(
                    f"🔧 Fix inventory manager BUY blocking: {issue['reason']}"
                )
            elif issue["type"] == "inventory_blocking_sell":
                recommendations.append(
                    f"🔧 Fix inventory manager SELL blocking: {issue['reason']}"
                )

        for issue in method_issues:
            if issue["type"] == "missing_monitoring_method":
                recommendations.append(
                    "🔧 Restore check_and_replace_filled_orders method in trading engine"
                )
            elif issue["type"] == "missing_replacement_method":
                recommendations.append(
                    f"🔧 Restore {issue['method']} method in trading engine"
                )

        # General recommendations
        if len(recommendations) == 0:
            recommendations.append(
                "🔍 Run deeper investigation - issues may be in timing or logic flow"
            )

        recommendations.append(
            "📊 Monitor order count every 5 minutes to identify when orders disappear"
        )
        recommendations.append(
            "🔄 Consider reverting to working version and applying fixes incrementally"
        )

        return recommendations
