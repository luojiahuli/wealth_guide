"""
Pydantic 数据模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AssetBase(BaseModel):
    """资产基础模型"""
    name: str
    code: Optional[str] = None
    type: str
    risk_level: str = "中"
    provider: str = ""


class MoneyFund(AssetBase):
    """货币基金"""
    nav: float = Field(description="万份收益")
    annual_return: float = Field(description="7日年化收益率")
    liquidity: str = "T+0"
    min_amount: float = 0.01


class BankProduct(AssetBase):
    """银行理财"""
    bank: str = ""
    expected_return: float = Field(description="预期收益率")
    term: str = "3个月"
    liquidity: str = "T+1"
    min_amount: float = 10000


class Fund(AssetBase):
    """公募基金"""
    fund_type: str = Field(alias="type")
    nav: float = Field(description="单位净值")
    annual_return: float = Field(description="近1年收益率")
    min_amount: float = 100


class Bond(AssetBase):
    """债券"""
    annual_return: float = Field(description="到期收益率")
    term: str = "5年"


class Forex(AssetBase):
    """外汇"""
    rate: float = Field(description="汇率")
    annual_return: float = Field(description="预期年化收益")


class Gold(AssetBase):
    """黄金"""
    price: float = Field(description="当前价格")
    annual_return: float = Field(description="年化收益")


class AllocationItem(BaseModel):
    """配置项"""
    asset: str
    ratio: float
    amount: float
    expected_return: float
    current_ratio: Optional[float] = None
    action: Optional[str] = None  # 买入/卖出/持有


class PortfolioMetrics(BaseModel):
    """组合指标"""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float


class Portfolio(BaseModel):
    """投资组合"""
    total_capital: float
    allocation: list[AllocationItem]
    portfolio_metrics: PortfolioMetrics
    last_updated: datetime = Field(default_factory=datetime.now)


class RebalanceAction(BaseModel):
    """再平衡操作"""
    asset: str
    action: str  # 买入/卖出
    amount: float
    reason: str


class TopPick(BaseModel):
    """精选推荐"""
    name: str
    type: str
    expected_return: float
    risk: str
    reason: str = ""


class Recommendation(BaseModel):
    """每日推荐"""
    date: str
    rebalance_actions: list[RebalanceAction] = []
    top_picks: list[TopPick] = []
    market_outlook: str = ""
    portfolio: Optional[Portfolio] = None


class AssetDataResponse(BaseModel):
    """资产数据响应"""
    timestamp: str
    assets: dict


class MarketIndicators(BaseModel):
    """市场情绪指标"""
    vix: Optional[float] = None
    credit_spread: Optional[float] = None
    market_trend: Optional[str] = None
    sh_index: Optional[float] = None
    sh_change: Optional[float] = None
    hs300_index: Optional[float] = None
    hs300_change: Optional[float] = None
    timestamp: str = ""


class HealthCheck(BaseModel):
    """健康检查"""
    status: str
    timestamp: str
    data_freshness: str
