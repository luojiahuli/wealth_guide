"""
风险预警模块 - VaR/波动率超标提醒
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """预警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RiskAlert:
    """风险预警"""
    level: AlertLevel
    title: str
    message: str
    metric: str
    value: float
    threshold: float
    timestamp: str


class RiskAlertManager:
    """风险预警管理器"""

    def __init__(self):
        self.alerts = []
        # 阈值配置
        self.thresholds = {
            "var_95": 0.03,        # VaR 超过 3%
            "volatility": 0.20,    # 波动率超过 20%
            "max_drawdown": 0.15,  # 最大回撤超过 15%
            "liquidity_ratio": 0.15,  # 流动性资产低于 15%
        }

    def check_portfolio_risk(self, portfolio_metrics: dict, allocation: list[dict]) -> list[RiskAlert]:
        """检查组合风险"""
        new_alerts = []

        # VaR 检查
        var_95 = portfolio_metrics.get("var_95", 0)
        if var_95 > self.thresholds["var_95"]:
            new_alerts.append(RiskAlert(
                level=AlertLevel.WARNING if var_95 < 0.05 else AlertLevel.CRITICAL,
                title="VaR 风险预警",
                message=f"组合 VaR(95%) 为 {var_95*100:.2f}%，超过阈值 {self.thresholds['var_95']*100:.1f}%",
                metric="var_95",
                value=var_95,
                threshold=self.thresholds["var_95"],
                timestamp=datetime.now().isoformat()
            ))

        # 波动率检查
        volatility = portfolio_metrics.get("volatility", 0)
        if volatility > self.thresholds["volatility"]:
            new_alerts.append(RiskAlert(
                level=AlertLevel.WARNING,
                title="波动率预警",
                message=f"组合年化波动率为 {volatility*100:.2f}%，超过阈值 {self.thresholds['volatility']*100:.1f}%",
                metric="volatility",
                value=volatility,
                threshold=self.thresholds["volatility"],
                timestamp=datetime.now().isoformat()
            ))

        # 最大回撤检查
        max_dd = portfolio_metrics.get("max_drawdown", 0)
        if max_dd > self.thresholds["max_drawdown"]:
            new_alerts.append(RiskAlert(
                level=AlertLevel.CRITICAL,
                title="最大回撤预警",
                message=f"组合最大回撤为 {max_dd*100:.2f}%，超过阈值 {self.thresholds['max_drawdown']*100:.1f}%",
                metric="max_drawdown",
                value=max_dd,
                threshold=self.thresholds["max_drawdown"],
                timestamp=datetime.now().isoformat()
            ))

        # 流动性检查
        liquidity_assets = sum(a.get("ratio", 0) for a in allocation if "货币" in a.get("asset", "") or "T+0" in a.get("asset", ""))
        if liquidity_assets < self.thresholds["liquidity_ratio"]:
            new_alerts.append(RiskAlert(
                level=AlertLevel.INFO,
                title="流动性预警",
                message=f"高流动性资产比例为 {liquidity_assets*100:.1f}%，低于建议值 {self.thresholds['liquidity_ratio']*100:.1f}%",
                metric="liquidity_ratio",
                value=liquidity_assets,
                threshold=self.thresholds["liquidity_ratio"],
                timestamp=datetime.now().isoformat()
            ))

        # 保存新警报
        self.alerts.extend(new_alerts)

        # 只保留最近100条
        self.alerts = self.alerts[-100:]

        return new_alerts

    def get_active_alerts(self) -> list[RiskAlert]:
        """获取活跃预警"""
        return self.alerts[-10:]  # 最近10条

    def clear_alerts(self):
        """清除所有预警"""
        self.alerts = []


# 全局实例
_alert_manager: Optional[RiskAlertManager] = None


def get_alert_manager() -> RiskAlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = RiskAlertManager()
    return _alert_manager
