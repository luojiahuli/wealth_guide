"""
组合分析模块 - 归因分析、风险分解
"""
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RiskDecomposition:
    """风险分解"""
    asset: str
    risk_contribution: float  # 风险贡献百分比
    weight: float
    volatility: float


@dataclass
class AttributionAnalysis:
    """收益归因"""
    asset: str
    return_contribution: float  # 收益贡献
    weight: float
    asset_return: float


class PortfolioAnalytics:
    """组合分析工具"""

    def __init__(self):
        pass

    def calculate_risk_contribution(self, weights: dict[str, float], volatilities: dict[str, float]) -> list[RiskDecomposition]:
        """计算各资产风险贡献"""
        total_risk = sum(w * v for w, v in zip(weights.values(), volatilities.values()))

        if total_risk == 0:
            return []

        contributions = []
        for asset in weights:
            w = weights[asset]
            v = volatilities.get(asset, 0)
            risk_contrib = (w * v) / total_risk if total_risk > 0 else 0
            contributions.append(RiskDecomposition(
                asset=asset,
                risk_contribution=risk_contrib,
                weight=w,
                volatility=v
            ))

        # 按风险贡献排序
        contributions.sort(key=lambda x: x.risk_contribution, reverse=True)
        return contributions

    def calculate_return_attribution(self, weights: dict[str, float], returns: dict[str, float]) -> list[AttributionAnalysis]:
        """计算收益归因"""
        total_return = sum(w * r for w, r in zip(weights.values(), returns.values()))

        attributions = []
        for asset in weights:
            w = weights[asset]
            r = returns.get(asset, 0)
            return_contrib = w * r / total_return if total_return != 0 else 0
            attributions.append(AttributionAnalysis(
                asset=asset,
                return_contribution=return_contrib,
                weight=w,
                asset_return=r
            ))

        attributions.sort(key=lambda x: x.return_contribution, reverse=True)
        return attributions

    def calculate_diversification_benefit(self, weights: dict[str, float], volatilities: dict[str, float]) -> float:
        """计算分散化收益"""
        # 加权平均波动率
        weighted_vol = sum(w * v for w, v in zip(weights.values(), volatilities.values()))

        # 假设完全相关，实际组合波动率
        portfolio_vol = weighted_vol  # 简化计算

        # 分散化收益 = 加权波动 - 组合波动
        diversification_benefit = weighted_vol - portfolio_vol

        return diversification_benefit

    def generate_analysis_report(self, portfolio_metrics: dict, allocation: list[dict]) -> dict:
        """生成分析报告"""
        # 提取权重和收益
        weights = {a['asset']: a['ratio'] for a in allocation}
        returns = {a['asset']: a.get('expected_return', 0) for a in allocation}

        # 估算波动率 (简化)
        vol_map = {
            '货币基金': 0.005,
            '银行理财': 0.02,
            '债券': 0.05,
            '公募基金': 0.18,
            '黄金': 0.15,
            '外汇': 0.10
        }
        volatilities = {a['asset']: vol_map.get(a['asset'], 0.1) for a in allocation}

        # 风险分解
        risk_contrib = self.calculate_risk_contribution(weights, volatilities)

        # 收益归因
        return_attr = self.calculate_return_attribution(weights, returns)

        # 分散化收益
        div_benefit = self.calculate_diversification_benefit(weights, volatilities)

        return {
            "risk_decomposition": [
                {"asset": r.asset, "risk_contribution": r.risk_contribution, "weight": r.weight, "volatility": r.volatility}
                for r in risk_contrib
            ],
            "return_attribution": [
                {"asset": r.asset, "return_contribution": r.return_contribution, "weight": r.weight, "asset_return": r.asset_return}
                for r in return_attr
            ],
            "diversification_benefit": div_benefit,
            "portfolio_metrics": portfolio_metrics,
            "summary": {
                "max_risk_asset": risk_contrib[0].asset if risk_contrib else None,
                "max_return_asset": return_attr[0].asset if return_attr else None,
                "risk_concentration": risk_contrib[0].risk_contribution if risk_contrib else 0,
                "return_concentration": return_attr[0].return_contribution if return_attr else 0
            }
        }


# 全局实例
_analytics: Optional[PortfolioAnalytics] = None


def get_analytics() -> PortfolioAnalytics:
    global _analytics
    if _analytics is None:
        _analytics = PortfolioAnalytics()
    return _analytics
