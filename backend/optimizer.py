"""
投资组合优化引擎
基于 Modern Portfolio Theory (MPT)、Risk Parity、Black-Litterman 模型
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class AssetClass:
    """资产类别"""
    name: str
    expected_return: float  # 年化预期收益
    volatility: float       # 年化波动率
    sharpe_ratio: float     # 夏普比率
    liquidity: str          # 流动性 T+0, T+1, T+2
    risk_level: str         # 风险等级
    weight: float = 0.0     # 当前权重


@dataclass
class PortfolioMetrics:
    """组合指标"""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float
    weights: dict[str, float]


class PortfolioOptimizer:
    """投资组合优化器"""

    def __init__(self, total_capital: float = 5000000):
        self.total_capital = total_capital
        self.risk_free_rate = 0.02  # 无风险利率 2%
        self.asset_classes: dict[str, AssetClass] = {}
        
        # 配置约束
        self.constraints = {
            "liquidity_min": 0.20,      # 最低流动性资产 20%
            "fixed_income_min": 0.30,   # 固定收益最低 30%
            "fixed_income_max": 0.60,   # 固定收益最高 60%
            "equity_min": 0.20,         # 权益最低 20%
            "equity_max": 0.50,         # 权益最高 50%
            "alternative_max": 0.15,    # 另类投资最高 15%
        }
        
        # 目标配置 (优化后的目标比例)
        self.target_allocation = {
            "货币基金": 0.15,
            "银行理财": 0.40,
            "债券": 0.15,
            "公募基金": 0.15,
            "黄金": 0.05,
            "外汇": 0.10,
        }

    def add_asset_class(self, name: str, expected_return: float, 
                       volatility: float, liquidity: str = "T+1", 
                       risk_level: str = "中"):
        """添加资产类别"""
        sharpe = (expected_return - self.risk_free_rate) / volatility if volatility > 0 else 0
        self.asset_classes[name] = AssetClass(
            name=name,
            expected_return=expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe,
            liquidity=liquidity,
            risk_level=risk_level
        )

    def estimate_volatility(self, asset_type: str, expected_return: float) -> float:
        """根据资产类型估算波动率"""
        # 基于历史数据的年化波动率估算
        volatility_map = {
            "货币基金": 0.005,        # 几乎无波动
            "银行理财": 0.02,         # 低波动
            "银行理财T+0": 0.015,
            "债券": 0.05,            # 中低波动
            "国债": 0.04,
            "企业债": 0.06,
            "混合型": 0.15,           # 中等波动
            "股票型": 0.25,           # 高波动
            "指数型": 0.20,
            "债券型": 0.05,
            "黄金": 0.15,             # 中高波动
            "外汇": 0.10,             # 中等波动
        }
        base_vol = volatility_map.get(asset_type, 0.10)
        
        # 波动率调整：如果预期收益显著高于/低于历史平均，可能需要调整
        return base_vol

    def build_asset_classes_from_data(self, asset_data: dict):
        """从数据构建资产类别"""
        
        # 货币基金
        for item in asset_data.get("money_fund", []):
            name = f"货币基金-{item['name']}"
            ret = item.get("annual_return", 0.02)
            vol = self.estimate_volatility("货币基金", ret)
            self.add_asset_class(name, ret, vol, "T+0", "极低")
        
        # 银行理财
        for item in asset_data.get("bank_product", []):
            name = f"银行理财-{item['name']}"
            ret = item.get("expected_return", 0.035)
            vol = self.estimate_volatility(item.get("type", "银行理财"), ret)
            liq = item.get("liquidity", "T+1")
            self.add_asset_class(name, ret, vol, liq, "低")
        
        # 公募基金
        for item in asset_data.get("fund", []):
            name = f"基金-{item['name']}"
            ret = item.get("annual_return", 0.08)
            vol = self.estimate_volatility(item.get("type", "混合型"), ret)
            risk = item.get("risk_level", "中")
            self.add_asset_class(name, ret, vol, "T+2", risk)
        
        # 债券
        for item in asset_data.get("bond", []):
            name = f"债券-{item['name']}"
            ret = item.get("annual_return", 0.04)
            vol = self.estimate_volatility(item.get("type", "债券"), ret)
            self.add_asset_class(name, ret, vol, "T+1", "中低")
        
        # 黄金
        for item in asset_data.get("gold", []):
            name = f"黄金-{item['name']}"
            ret = item.get("annual_return", 0.03)
            vol = self.estimate_volatility("黄金", ret)
            self.add_asset_class(name, ret, vol, "T+1", "中高")
        
        # 外汇
        for item in asset_data.get("forex", []):
            name = f"外汇-{item['name']}"
            ret = item.get("annual_return", 0.01)
            vol = self.estimate_volatility("外汇", ret)
            self.add_asset_class(name, ret, vol, "T+1", "中")

    def optimize_risk_parity(self) -> dict[str, float]:
        """
        风险平价优化
        每个资产对组合总风险的贡献相等
        """
        if not self.asset_classes:
            return {}
        
        assets = list(self.asset_classes.keys())
        n = len(assets)
        
        if n == 0:
            return {}
        
        # 获取波动率
        volatilities = np.array([
            self.asset_classes[a].volatility for a in assets
        ])
        
        # 风险平价：每个资产的risk contribution相等
        # RC_i = w_i * sigma_i / sum(w_j * sigma_j) = 1/n
        # 简化：w_i proportional to 1/sigma_i
        
        # 避免零波动率
        vols = np.maximum(volatilities, 0.001)
        
        # 风险平价权重
        weights = 1.0 / vols
        weights = weights / weights.sum()
        
        # 应用约束
        weights = self._apply_constraints(assets, weights)
        
        return dict(zip(assets, weights))

    def optimize_max_sharpe(self) -> dict[str, float]:
        """
        最大夏普比率优化
        使用简化的优化方法
        """
        if not self.asset_classes:
            return {}
        
        assets = list(self.asset_classes.keys())
        n = len(assets)
        
        if n == 0:
            return {}
        
        # 获取预期收益和波动率
        returns = np.array([
            self.asset_classes[a].expected_return for a in assets
        ])
        volatilities = np.array([
            self.asset_classes[a].volatility for a in assets
        ])
        
        # 夏普比率
        sharpes = (returns - self.risk_free_rate) / np.maximum(volatilities, 0.001)
        
        # 简化优化：基于夏普比率分配权重
        # 但要避免极端权重
        pos_sharpes = np.maximum(sharpes, 0.001)
        weights = pos_sharpes ** 2  # 放大差异
        weights = weights / weights.sum()
        
        # 应用约束
        weights = self._apply_constraints(assets, weights)
        
        return dict(zip(assets, weights))

    def optimize_mpt(self) -> dict[str, float]:
        """
        现代投资组合理论 (Mean-Variance Optimization)
        最大化预期收益，同时控制风险
        """
        if not self.asset_classes:
            return {}
        
        assets = list(self.asset_classes.keys())
        n = len(assets)
        
        if n == 0:
            return {}
        
        # 获取预期收益和波动率
        returns = np.array([
            self.asset_classes[a].expected_return for a in assets
        ])
        volatilities = np.array([
            self.asset_classes[a].volatility for a in assets
        ])
        
        # 简化的有效前沿计算
        # 目标：最大化 return - 0.5 * risk_aversion * variance
        
        risk_aversion = 1.0  # 风险厌恶系数
        
        # 构建协方差矩阵 (简化：使用对角线)
        cov_matrix = np.diag(volatilities ** 2)
        
        # 优化
        try:
            from cvxpy import Variable, Problem, Maximize, quad_form, sum
            
            w = Variable(n)
            portfolio_return = returns @ w
            portfolio_variance = quad_form(w, cov_matrix)
            
            # 最大化效用
            objective = Maximize(portfolio_return - risk_aversion * portfolio_variance)
            
            # 约束
            constraints = [
                sum(w) == 1,
                w >= 0,
            ]
            
            prob = Problem(objective, constraints)
            prob.solve(solver="ECOS")
            
            if prob.status in ["optimal", "optimal_inaccurate"]:
                weights = np.array(w.value).flatten()
                weights = np.maximum(weights, 0)
                weights = weights / weights.sum()
            else:
                # fallback to risk parity
                return self.optimize_risk_parity()
                
        except ImportError:
            # cvxpy not available, use simplified approach
            # 有效前沿上取一个中庸点
            weights = self._simplified_mpt(assets, returns, volatilities)
        
        # 应用约束
        weights = self._apply_constraints(assets, weights)
        
        return dict(zip(assets, weights))

    def _simplified_mpt(self, assets: list, returns: np.ndarray, 
                       volatilities: np.ndarray) -> np.ndarray:
        """简化版 MPT"""
        n = len(assets)
        
        # 最小方差点
        min_var_weights = 1.0 / (volatilities ** 2)
        min_var_weights = min_var_weights / min_var_weights.sum()
        
        # 最大收益点
        max_ret_weights = np.zeros(n)
        max_ret_weights[np.argmax(returns)] = 1.0
        
        # 中庸组合 (两者之间)
        alpha = 0.6  # 偏向最小方差
        weights = alpha * min_var_weights + (1 - alpha) * max_ret_weights
        
        return weights

    def _apply_constraints(self, assets: list, weights: np.ndarray) -> np.ndarray:
        """应用配置约束"""
        n = len(assets)
        
        # 按资产类型分组
        category_map = {
            "货币基金": "liquidity",
            "银行理财T+0": "liquidity",
            "银行理财": "fixed_income",
            "债券": "fixed_income",
            "基金": "equity",
            "黄金": "alternative",
            "外汇": "alternative",
        }
        
        def get_category(name: str) -> str:
            for cat, key in category_map.items():
                if cat in name:
                    return key
            return "other"
        
        # 简单约束应用：按比例缩放
        liquidity_weight = 0.0
        fixed_income_weight = 0.0
        equity_weight = 0.0
        alternative_weight = 0.0
        
        for i, name in enumerate(assets):
            cat = get_category(name)
            if cat == "liquidity":
                liquidity_weight += weights[i]
            elif cat == "fixed_income":
                fixed_income_weight += weights[i]
            elif cat == "equity":
                equity_weight += weights[i]
            elif cat == "alternative":
                alternative_weight += weights[i]
        
        # 如果违反约束，按比例调整
        if liquidity_weight < self.constraints["liquidity_min"]:
            # 需要增加流动性资产
            excess = self.constraints["liquidity_min"] - liquidity_weight
            # 从其他类别抽取
            donors = ["fixed_income", "equity", "alternative"]
            donor_weights = [fixed_income_weight, equity_weight, alternative_weight]
            total_donor = sum(donor_weights)
            if total_donor > 0:
                for i, name in enumerate(assets):
                    cat = get_category(name)
                    if cat in donors:
                        donor_idx = donors.index(cat)
                        reduction = excess * (donor_weights[donor_idx] / total_donor)
                        weights[i] *= (1 - reduction / donor_weights[donor_idx] if donor_weights[donor_idx] > 0 else 0)
        
        # 重新归一化
        weights = np.maximum(weights, 0)
        total = weights.sum()
        if total > 0:
            weights = weights / total
        
        return weights

    def optimize_target_allocation(self) -> dict[str, float]:
        """
        直接使用目标配置，不做复杂优化
        用于固定配置比例的场景
        """
        # 使用更新后的目标配置（银行理财35%）
        self.target_allocation = {
            "货币基金": 0.20,
            "银行理财": 0.35,
            "债券": 0.15,
            "公募基金": 0.20,
            "黄金": 0.05,
            "外汇": 0.05,
        }

        # 定义各资产类别的预期收益和波动率
        asset_params = {
            "货币基金-余额宝": {"return": 0.021, "vol": 0.005, "liquidity": "T+0", "risk": "极低"},
            "银行理财-招行聚益生金": {"return": 0.035, "vol": 0.02, "liquidity": "T+1", "risk": "低"},
            "债券-AAA企业债": {"return": 0.040, "vol": 0.05, "liquidity": "T+1", "risk": "中低"},
            "基金-易方达蓝筹精选": {"return": 0.08, "vol": 0.18, "liquidity": "T+2", "risk": "中"},
            "黄金-华安黄金ETF": {"return": 0.03, "vol": 0.15, "liquidity": "T+1", "risk": "中高"},
            "外汇-美元": {"return": 0.02, "vol": 0.10, "liquidity": "T+1", "risk": "中"},
        }

        # 添加到 asset_classes
        for name, params in asset_params.items():
            self.asset_classes[name] = AssetClass(
                name=name,
                expected_return=params["return"],
                volatility=params["vol"],
                sharpe_ratio=(params["return"] - self.risk_free_rate) / params["vol"] if params["vol"] > 0 else 0,
                liquidity=params["liquidity"],
                risk_level=params["risk"]
            )

        # 构建详细权重
        detailed = {}
        for cat, ratio in self.target_allocation.items():
            asset_map = {
                "货币基金": "货币基金-余额宝",
                "银行理财": "银行理财-招行聚益生金",
                "债券": "债券-AAA企业债",
                "公募基金": "基金-易方达蓝筹精选",
                "黄金": "黄金-华安黄金ETF",
                "外汇": "外汇-美元",
            }
            if cat in asset_map:
                detailed[asset_map[cat]] = ratio

        return detailed

    def aggregate_to_target_categories(self, detailed_weights: dict[str, float]) -> dict[str, dict]:
        """
        将详细资产权重聚合到目标资产类别
        """
        categories = {
            "货币基金": {"amount": 0, "expected_return": 0, "weight": 0},
            "银行理财": {"amount": 0, "expected_return": 0, "weight": 0},
            "债券": {"amount": 0, "expected_return": 0, "weight": 0},
            "公募基金": {"amount": 0, "expected_return": 0, "weight": 0},
            "黄金": {"amount": 0, "expected_return": 0, "weight": 0},
            "外汇": {"amount": 0, "expected_return": 0, "weight": 0},
        }
        
        def get_target_category(name: str) -> str:
            name_lower = name.lower()
            if "货币基金" in name:
                return "货币基金"
            elif "银行理财" in name:
                return "银行理财"
            elif "债券" in name:
                return "债券"
            elif "基金" in name:
                return "公募基金"
            elif "黄金" in name or "gold" in name_lower:
                return "黄金"
            elif "外汇" in name or "forex" in name_lower:
                return "外汇"
            return None
        
        for asset_name, weight in detailed_weights.items():
            cat = get_target_category(asset_name)
            if cat and cat in categories:
                if asset_name in self.asset_classes:
                    asset = self.asset_classes[asset_name]
                    categories[cat]["amount"] += weight * self.total_capital
                    categories[cat]["expected_return"] = max(
                        categories[cat]["expected_return"],
                        asset.expected_return
                    )
                    categories[cat]["weight"] += weight
        
        # 计算实际权重比例
        for cat in categories:
            if categories[cat]["weight"] > 0:
                categories[cat]["amount"] = categories[cat]["weight"] * self.total_capital
        
        return categories

    def calculate_portfolio_metrics(self, weights: dict[str, float]) -> PortfolioMetrics:
        """计算组合指标"""
        
        returns = []
        volatilities = []
        
        for asset_name, weight in weights.items():
            if asset_name in self.asset_classes:
                asset = self.asset_classes[asset_name]
                returns.append(asset.expected_return * weight)
                volatilities.append((asset.volatility * weight) ** 2)
        
        portfolio_return = sum(returns)
        portfolio_variance = sum(volatilities)
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
        
        # VaR (95%) - 假设正态分布
        var_95 = 1.65 * portfolio_volatility
        
        # 最大回撤估算
        max_drawdown = 2 * portfolio_volatility  # 简化估计
        
        return PortfolioMetrics(
            expected_return=portfolio_return,
            volatility=portfolio_volatility,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            var_95=var_95,
            weights=weights
        )

    def optimize(self, method: str = "target") -> dict:
        """
        执行优化
        target: 直接使用目标配置（推荐）
        risk_parity: 风险平价
        max_sharpe: 最大夏普比率
        mpt: 现代投资组合理论
        """
        if method == "target":
            detailed_weights = self.optimize_target_allocation()
        elif method == "risk_parity":
            detailed_weights = self.optimize_risk_parity()
        elif method == "max_sharpe":
            detailed_weights = self.optimize_max_sharpe()
        elif method == "mpt":
            detailed_weights = self.optimize_mpt()
        else:
            detailed_weights = self.optimize_target_allocation()
        
        # 聚合到目标类别
        aggregated = self.aggregate_to_target_categories(detailed_weights)
        
        # 计算指标
        metrics = self.calculate_portfolio_metrics(detailed_weights)
        
        return {
            "total_capital": self.total_capital,
            "optimization_method": method,
            "detailed_allocation": detailed_weights,
            "target_allocation": self.target_allocation,
            "aggregated_allocation": aggregated,
            "metrics": {
                "expected_return": metrics.expected_return,
                "volatility": metrics.volatility,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "var_95": metrics.var_95,
            }
        }


# 全局实例
_optimizer: PortfolioOptimizer | None = None


def get_optimizer() -> PortfolioOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = PortfolioOptimizer()
    return _optimizer
