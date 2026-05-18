"""
推荐引擎 - 生成每日投资建议
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np

from .models import (
    AllocationItem,
    Portfolio,
    PortfolioMetrics,
    RebalanceAction,
    Recommendation,
    TopPick,
)
from .optimizer import PortfolioOptimizer, get_optimizer

logger = logging.getLogger(__name__)


class Recommender:
    """投资推荐引擎"""

    def __init__(self, optimizer: Optional[PortfolioOptimizer] = None):
        self.optimizer = optimizer or get_optimizer()
        self.current_allocation: dict[str, float] = {}
        self.rebalance_threshold = 0.05  # 5% 阈值

    def set_current_allocation(self, allocation: dict[str, float]):
        """设置当前配置"""
        self.current_allocation = allocation

    def generate_rebalance_actions(self, target_allocation: dict[str, dict]) -> list[RebalanceAction]:
        """
        生成再平衡建议
        """
        actions = []
        
        for asset_name, target_data in target_allocation.items():
            target_ratio = target_data.get("weight", 0)
            current_ratio = self.current_allocation.get(asset_name, 0)
            drift = target_ratio - current_ratio
            
            # 如果偏离超过阈值
            if abs(drift) > self.rebalance_threshold:
                amount = abs(drift) * self.optimizer.total_capital
                
                if drift > 0:
                    action = "买入"
                    reason = f"当前配置{current_ratio*100:.1f}%，低于目标{target_ratio*100:.1f}%，需增持{amount/10000:.0f}万"
                else:
                    action = "卖出"
                    reason = f"当前配置{current_ratio*100:.1f}%，高于目标{target_ratio*100:.1f}%，需减持{amount/10000:.0f}万"
                
                actions.append(RebalanceAction(
                    asset=asset_name,
                    action=action,
                    amount=amount,
                    reason=reason
                ))
        
        return actions

    def select_top_picks(self, asset_data: dict, n: int = 5) -> list[TopPick]:
        """
        精选推荐
        基于夏普比率和风险调整后收益筛选
        """
        picks = []
        
        # 公募基金精选
        for fund in asset_data.get("fund", [])[:3]:
            risk_score = {"低": 1, "中低": 2, "中": 3, "中高": 4, "高": 5}.get(
                fund.get("risk_level", "中"), 3
            )
            # 风险调整后收益
            adj_return = fund.get("annual_return", 0) / risk_score
            picks.append(TopPick(
                name=fund.get("name", ""),
                type=fund.get("type", "混合型"),
                expected_return=fund.get("annual_return", 0),
                risk=fund.get("risk_level", "中"),
                reason=f"风险调整后收益较高，年化{adj_return*100:.1f}%"
            ))
        
        # 银行理财精选
        for bank in asset_data.get("bank_product", [])[:2]:
            picks.append(TopPick(
                name=bank.get("name", ""),
                type="银行理财",
                expected_return=bank.get("expected_return", 0),
                risk="低",
                reason=f"收益率{bank.get('expected_return', 0)*100:.2f}%，{bank.get('term', '')}期限"
            ))
        
        # 按预期收益排序
        picks.sort(key=lambda x: x.expected_return, reverse=True)
        
        return picks[:n]

    def generate_market_outlook(self, market_indicators: dict, 
                                portfolio_metrics: PortfolioMetrics) -> str:
        """
        生成市场展望
        """
        outlook_parts = []
        
        # 股市展望
        if market_indicators.get("sh_change"):
            change = market_indicators["sh_change"]
            if change > 0.02:
                outlook_parts.append("今日A股强势上涨，关注成长股机会")
            elif change > 0:
                outlook_parts.append("A股小幅上涨，维持稳健配置")
            elif change > -0.02:
                outlook_parts.append("A股震荡调整，可适当增持防御性资产")
            else:
                outlook_parts.append("A股下跌，控制权益类仓位，增加固收配置")
        
        # 债市展望
        outlook_parts.append("近期债市收益率整体下行，债券类资产配置价值提升")
        
        # 组合特定建议
        if portfolio_metrics.volatility > 0.15:
            outlook_parts.append("组合波动率偏高，建议适当增加低风险资产比例")
        elif portfolio_metrics.sharpe_ratio < 1.0:
            outlook_parts.append("当前夏普比率偏低，可考虑优化大类资产配置")
        
        return "；".join(outlook_parts) if outlook_parts else "维持当前配置，关注再平衡机会"

    def build_portfolio_response(self, optimization_result: dict) -> Portfolio:
        """
        构建 Portfolio 响应对象
        """
        aggregated = optimization_result.get("aggregated_allocation", {})
        metrics_data = optimization_result.get("metrics", {})
        
        allocation_items = []
        for asset_name, data in aggregated.items():
            weight = data.get("weight", 0)
            if weight > 0.001:  # 过滤掉太小的配置
                allocation_items.append(AllocationItem(
                    asset=asset_name,
                    ratio=weight,
                    amount=data.get("amount", weight * optimization_result.get("total_capital", 5000000)),
                    expected_return=data.get("expected_return", 0),
                    current_ratio=weight,
                    action="持有"
                ))
        
        portfolio_metrics = PortfolioMetrics(
            expected_return=metrics_data.get("expected_return", 0),
            volatility=metrics_data.get("volatility", 0),
            sharpe_ratio=metrics_data.get("sharpe_ratio", 0),
            max_drawdown=metrics_data.get("max_drawdown", 0),
            var_95=metrics_data.get("var_95", 0)
        )
        
        return Portfolio(
            total_capital=optimization_result.get("total_capital", 5000000),
            allocation=allocation_items,
            portfolio_metrics=portfolio_metrics,
            last_updated=datetime.now()
        )

    def generate_recommendation(self, optimization_result: dict, 
                               asset_data: dict,
                               market_indicators: Optional[dict] = None) -> Recommendation:
        """
        生成完整的每日推荐
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 更新当前配置
        aggregated = optimization_result.get("aggregated_allocation", {})
        current_alloc = {k: v.get("weight", 0) for k, v in aggregated.items()}
        self.set_current_allocation(current_alloc)
        
        # 生成再平衡建议
        rebalance_actions = self.generate_rebalance_actions(aggregated)
        
        # 精选推荐
        top_picks = self.select_top_picks(asset_data)
        
        # 市场展望
        metrics_data = optimization_result.get("metrics", {})
        metrics = PortfolioMetrics(
            expected_return=metrics_data.get("expected_return", 0),
            volatility=metrics_data.get("volatility", 0),
            sharpe_ratio=metrics_data.get("sharpe_ratio", 0),
            max_drawdown=metrics_data.get("max_drawdown", 0),
            var_95=metrics_data.get("var_95", 0)
        )
        
        market_outlook = self.generate_market_outlook(
            market_indicators or {}, metrics
        )
        
        # 构建组合
        portfolio = self.build_portfolio_response(optimization_result)
        
        return Recommendation(
            date=today,
            rebalance_actions=rebalance_actions,
            top_picks=top_picks,
            market_outlook=market_outlook,
            portfolio=portfolio
        )


# 全局实例
_recommender: Recommender | None = None


def get_recommender() -> Recommender:
    global _recommender
    if _recommender is None:
        _recommender = Recommender()
    return _recommender
