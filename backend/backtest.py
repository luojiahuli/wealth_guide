"""
回测引擎 - 基于历史数据模拟交易
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float
    annualized_return: float
    volatility: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    trades: int


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital: float = 5000000):
        self.initial_capital = initial_capital

    def run_backtest(self, allocation: dict, days: int = 252) -> BacktestResult:
        """
        运行回测

        Args:
            allocation: 资产配置比例 {"货币基金": 0.2, ...}
            days: 回测天数

        Returns:
            BacktestResult: 回测结果
        """
        # 简化回测：使用随机模拟
        np.random.seed(42)

        # 各资产年化收益和波动率
        asset_params = {
            '货币基金': {'return': 0.02, 'vol': 0.005},
            '银行理财': {'return': 0.035, 'vol': 0.02},
            '债券': {'return': 0.04, 'vol': 0.05},
            '公募基金': {'return': 0.08, 'vol': 0.18},
            '黄金': {'return': 0.03, 'vol': 0.15},
            '外汇': {'return': 0.02, 'vol': 0.10}
        }

        # 生成日收益序列
        daily_returns = []
        for asset, weight in allocation.items():
            params = asset_params.get(asset, {'return': 0.05, 'vol': 0.15})
            # 日收益 = 年化收益 / 252 + 随机波动
            daily_ret = params['return'] / 252 + np.random.normal(0, params['vol'] / np.sqrt(252))
            daily_returns.append(daily_ret * weight)

        # 组合日收益
        portfolio_returns = np.sum(daily_returns, axis=0) if isinstance(daily_returns, list) else daily_returns

        # 计算累计收益
        cumulative = np.cumprod(1 + portfolio_returns)

        # 计算指标
        total_return = cumulative[-1] - 1 if len(cumulative) > 0 else 0
        annualized_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        volatility = np.std(portfolio_returns) * np.sqrt(252) if len(portfolio_returns) > 0 else 0

        # 最大回撤
        cummax = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - cummax) / cummax
        max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0

        # 夏普比率
        risk_free = 0.02
        sharpe = (annualized_return - risk_free) / volatility if volatility > 0 else 0

        # 简化胜率
        win_rate = np.mean(portfolio_returns > 0) if len(portfolio_returns) > 0 else 0.5

        return BacktestResult(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            trades=0  # 简化，不计算交易次数
        )

    def compare_strategies(self, strategy_a: dict, strategy_b: dict) -> dict:
        """比较两个策略"""
        result_a = self.run_backtest(strategy_a)
        result_b = self.run_backtest(strategy_b)

        return {
            "strategy_a": {
                "total_return": result_a.total_return,
                "annualized_return": result_a.annualized_return,
                "sharpe_ratio": result_a.sharpe_ratio,
                "max_drawdown": result_a.max_drawdown
            },
            "strategy_b": {
                "total_return": result_b.total_return,
                "annualized_return": result_b.annualized_return,
                "sharpe_ratio": result_b.sharpe_ratio,
                "max_drawdown": result_b.max_drawdown
            },
            "recommendation": "A" if result_a.sharpe_ratio > result_b.sharpe_ratio else "B"
        }


# 全局实例
_backtest: Optional[BacktestEngine] = None


def get_backtest() -> BacktestEngine:
    global _backtest
    if _backtest is None:
        _backtest = BacktestEngine()
    return _backtest
