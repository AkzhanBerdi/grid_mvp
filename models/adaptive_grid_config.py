# models/adaptive_grid_config.py
"""Adaptive Grid Configuration Model"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from models.grid_config import GridConfig


@dataclass
class AdaptiveGridConfig:
    """Configuration for adaptive two-scale grid trading"""
    
    symbol: str
    client_id: int
    total_capital: float
    market_condition: Dict
    grid_config: Dict
    
    # Grid instances
    base_grid: GridConfig = field(default=None)
    enhanced_grid: GridConfig = field(default=None)
    
    # Grid state
    enhanced_grid_active: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Performance tracking
    performance_metrics: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize grid configurations"""
        if self.base_grid is None:
            # Base grid - always active, conservative
            self.base_grid = GridConfig(
                symbol=self.symbol,
                client_id=self.client_id,
                grid_spacing=0.025,  # 2.5% spacing
                grid_levels=8,
                order_size=self.total_capital * 0.4 / 16  # 40% of capital, 16 total orders
            )
        
        if self.enhanced_grid is None:
            # Enhanced grid - market-dependent, aggressive
            self.enhanced_grid = GridConfig(
                symbol=self.symbol,
                client_id=self.client_id,
                grid_spacing=self.grid_config.get('base_grid_spacing', 0.02),
                grid_levels=self.grid_config.get('base_grid_levels', 10),
                order_size=self.total_capital * 0.6 / 20  # 60% of capital, 20 total orders
            )
        
        # Initialize performance metrics
        if not self.performance_metrics:
            self.performance_metrics = {
                'total_trades': 0,
                'total_profit': 0.0,
                'base_grid_trades': 0,
                'enhanced_grid_trades': 0,
                'market_adaptations': 0,
                'efficiency_score': 0.0,
                'risk_score': 0.0
            }
    
    def update_market_condition(self, new_market_condition: Dict) -> bool:
        """Update market condition and return if significant change occurred"""
        old_condition = self.market_condition.get('condition')
        new_condition = new_market_condition.get('condition')
        
        # Check for significant changes
        condition_changed = old_condition != new_condition
        score_changed = abs(
            new_market_condition.get('score', 0.5) - 
            self.market_condition.get('score', 0.5)
        ) > 0.3
        
        if condition_changed or score_changed:
            self.market_condition = new_market_condition
            self.last_updated = datetime.now()
            self.performance_metrics['market_adaptations'] += 1
            return True
        
        return False
    
    def calculate_capital_allocation(self) -> Dict:
        """Calculate optimal capital allocation between grids"""
        market_score = self.market_condition.get('score', 0.5)
        confidence = self.market_condition.get('confidence', 0.0)
        
        # Base allocation
        base_allocation = 0.4  # 40% baseline
        
        # Adjust based on market condition and confidence
        if confidence > 0.7:
            if market_score > 0.7:  # Strong bullish
                base_allocation = 0.3  # Reduce base, increase enhanced
            elif market_score < 0.3:  # Strong bearish
                base_allocation = 0.35  # Slightly reduce base
            else:  # Neutral with high confidence
                base_allocation = 0.6  # Increase base, reduce enhanced
        
        enhanced_allocation = 1.0 - base_allocation
        
        return {
            'base_allocation': base_allocation,
            'enhanced_allocation': enhanced_allocation,
            'base_capital': self.total_capital * base_allocation,
            'enhanced_capital': self.total_capital * enhanced_allocation
        }
    
    def get_risk_level(self) -> str:
        """Get current risk level based on market conditions"""
        market_score = self.market_condition.get('score', 0.5)
        confidence = self.market_condition.get('confidence', 0.0)
        volatility = self.market_condition.get('indicators', {}).get('volatility', 0.0)
        
        # Calculate risk score
        risk_score = 0.0
        
        # Market direction risk
        if market_score > 0.8 or market_score < 0.2:
            risk_score += 0.3  # Extreme conditions
        elif market_score > 0.7 or market_score < 0.3:
            risk_score += 0.2  # Strong conditions
        
        # Confidence risk
        if confidence > 0.8:
            risk_score += 0.2  # High confidence can be risky
        elif confidence < 0.3:
            risk_score += 0.1  # Low confidence is safer
        
        # Volatility risk
        if volatility > 0.5:
            risk_score += 0.4  # High volatility
        elif volatility > 0.3:
            risk_score += 0.2  # Moderate volatility
        
        # Determine risk level
        if risk_score > 0.7:
            return 'high'
        elif risk_score > 0.4:
            return 'moderate'
        else:
            return 'low'
    
    def should_activate_enhanced_grid(self) -> bool:
        """Determine if enhanced grid should be activated"""
        condition = self.market_condition.get('condition')
        confidence = self.market_condition.get('confidence', 0.0)
        
        # Activate enhanced grid in strong market conditions
        return (condition in ['bullish', 'bearish'] and confidence > 0.6)
    
    def get_optimal_grid_spacing(self, grid_type: str = 'base') -> float:
        """Get optimal grid spacing based on market conditions"""
        volatility = self.market_condition.get('indicators', {}).get('volatility', 0.0)
        condition = self.market_condition.get('condition')
        
        if grid_type == 'base':
            # Base grid: conservative spacing
            if volatility > 0.5:
                return 0.03  # Wider spacing for high volatility
            elif volatility > 0.3:
                return 0.025  # Standard spacing
            else:
                return 0.02  # Tighter spacing for low volatility
        
        else:  # enhanced grid
            # Enhanced grid: adaptive spacing
            if condition == 'bullish':
                return 0.015 if volatility < 0.3 else 0.02
            elif condition == 'bearish':
                return 0.02 if volatility < 0.3 else 0.025
            else:
                return 0.025  # Neutral spacing
    
    def get_optimal_grid_levels(self, grid_type: str = 'base') -> int:
        """Get optimal number of grid levels"""
        volatility = self.market_condition.get('indicators', {}).get('volatility', 0.0)
        condition = self.market_condition.get('condition')
        
        if grid_type == 'base':
            # Base grid: stable levels
            return 8 if volatility < 0.4 else 6
        
        else:  # enhanced grid
            # Enhanced grid: adaptive levels
            if condition == 'bullish':
                return 12 if volatility < 0.3 else 10
            elif condition == 'bearish':
                return 8 if volatility < 0.3 else 6
            else:
                return 8
    
    def update_performance_metrics(self, trade_stats: Dict) -> None:
        """Update performance metrics"""
        self.performance_metrics.update({
            'total_trades': trade_stats.get('total_trades', 0),
            'total_profit': trade_stats.get('total_profit', 0.0),
            'win_rate': trade_stats.get('win_rate', 0.0),
            'avg_profit_per_trade': (
                trade_stats.get('total_profit', 0.0) / 
                max(1, trade_stats.get('total_trades', 1))
            )
        })
        
        # Calculate efficiency score
        total_trades = self.performance_metrics['total_trades']
        if total_trades > 0:
            base_efficiency = self.performance_metrics['base_grid_trades'] / total_trades
            enhanced_efficiency = self.performance_metrics['enhanced_grid_trades'] / total_trades
            
            # Efficiency score based on profit per trade and trade frequency
            self.performance_metrics['efficiency_score'] = (
                base_efficiency * 0.4 + enhanced_efficiency * 0.6
            )
        
        # Update risk score
        self.performance_metrics['risk_score'] = self._calculate_risk_score()
    
    def _calculate_risk_score(self) -> float:
        """Calculate current risk score"""
        volatility = self.market_condition.get('indicators', {}).get('volatility', 0.0)
        market_score = self.market_condition.get('score', 0.5)
        
        # Base risk from market conditions
        market_risk = abs(market_score - 0.5) * 2  # 0-1 scale
        
        # Volatility risk
        volatility_risk = min(1.0, volatility * 2)  # 0-1 scale
        
        # Capital allocation risk
        allocation = self.calculate_capital_allocation()
        allocation_risk = allocation['enhanced_allocation']  # Higher enhanced = higher risk
        
        # Combined risk score
        risk_score = (market_risk * 0.4 + volatility_risk * 0.4 + allocation_risk * 0.2)
        
        return min(1.0, risk_score)
    
    def get_status_summary(self) -> Dict:
        """Get comprehensive status summary"""
        return {
            'symbol': self.symbol,
            'market_condition': self.market_condition.get('condition'),
            'market_score': self.market_condition.get('score', 0.5),
            'confidence': self.market_condition.get('confidence', 0.0),
            'base_grid_active': True,
            'enhanced_grid_active': self.enhanced_grid_active,
            'total_capital': self.total_capital,
            'capital_allocation': self.calculate_capital_allocation(),
            'risk_level': self.get_risk_level(),
            'performance_metrics': self.performance_metrics,
            'last_updated': self.last_updated.isoformat()
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'client_id': self.client_id,
            'total_capital': self.total_capital,
            'market_condition': self.market_condition,
            'grid_config': self.grid_config,
            'enhanced_grid_active': self.enhanced_grid_active,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'performance_metrics': self.performance_metrics
        }
