"""
Wealth Guide - 每日理财指南 API
FastAPI 后端服务 v2.0
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .analytics import get_analytics
from .backtest import get_backtest
from .data_fetcher import DataFetcher, get_data_fetcher
from .database import Database, get_database
from .feishu_pusher import FeishuPusher, get_feishu_pusher
from .models import (
    AllocationItem, AssetDataResponse, HealthCheck,
    MarketIndicators, Portfolio, PortfolioMetrics,
    Recommendation, RebalanceAction, TopPick
)
from .optimizer import PortfolioOptimizer, get_optimizer
from .recommender import Recommender, get_recommender
from .risk_alert import get_alert_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_data_fetcher: Optional[DataFetcher] = None
_optimizer: Optional[PortfolioOptimizer] = None
_recommender: Optional[Recommender] = None
_database: Optional[Database] = None
_feishu_pusher: Optional[FeishuPusher] = None
_cached_portfolio: Optional[Portfolio] = None
_cached_recommendation: Optional[Recommendation] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _data_fetcher, _optimizer, _recommender, _database, _feishu_pusher

    logger.info("初始化 Wealth Guide v2.0...")

    _data_fetcher = get_data_fetcher()
    _optimizer = get_optimizer()
    _recommender = get_recommender(_optimizer)
    _database = get_database()
    _feishu_pusher = get_feishu_pusher()

    try:
        cached = _database.get_recommendation()
        if cached:
            logger.info("从数据库加载缓存推荐")
    except Exception as e:
        logger.warning(f"数据库加载失败: {e}")

    yield

    logger.info("Wealth Guide 关闭")


app = FastAPI(
    title="Wealth Guide - 每日理财指南",
    description="500万资产组合优化与每日理财建议 v2.0",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/health")
async def health_check() -> HealthCheck:
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        data_freshness="实时"
    )


@app.get("/api/portfolio")
async def get_portfolio() -> Portfolio:
    global _cached_portfolio

    try:
        if _cached_portfolio:
            return _cached_portfolio

        if not all([_data_fetcher, _optimizer, _recommender]):
            raise HTTPException(status_code=503, detail="服务初始化中")

        logger.info("正在获取资产数据...")
        asset_data = _data_fetcher.get_all_asset_data()

        _optimizer.build_asset_classes_from_data(asset_data["assets"])

        logger.info("正在优化组合...")
        result = _optimizer.optimize(method="target")

        logger.info("正在生成推荐...")
        recommendation = _recommender.generate_recommendation(
            result,
            asset_data["assets"]
        )

        try:
            _database.save_portfolio(
                date=datetime.now().strftime("%Y-%m-%d"),
                total_capital=result["total_capital"],
                allocation=result["aggregated_allocation"],
                metrics=result["metrics"],
                method=result["optimization_method"]
            )
            _database.save_recommendation(recommendation.model_dump())
        except Exception as e:
            logger.warning(f"数据库保存失败: {e}")

        _cached_portfolio = recommendation.portfolio
        return recommendation.portfolio

    except Exception as e:
        logger.error(f"获取组合失败: {e}")
        return Portfolio(
            total_capital=5000000,
            allocation=[
                AllocationItem(asset="货币基金", ratio=0.20, amount=1000000, expected_return=0.021, risk_level="极低"),
                AllocationItem(asset="银行理财", ratio=0.35, amount=1750000, expected_return=0.035, risk_level="低"),
                AllocationItem(asset="债券", ratio=0.15, amount=750000, expected_return=0.040, risk_level="中低"),
                AllocationItem(asset="公募基金", ratio=0.20, amount=1000000, expected_return=0.080, risk_level="中"),
                AllocationItem(asset="黄金", ratio=0.05, amount=250000, expected_return=0.030, risk_level="中高"),
                AllocationItem(asset="外汇", ratio=0.05, amount=250000, expected_return=0.020, risk_level="中"),
            ],
            portfolio_metrics=PortfolioMetrics(
                expected_return=0.0405,
                volatility=0.082,
                sharpe_ratio=1.42,
                max_drawdown=0.12,
                var_95=0.015
            ),
            last_updated=datetime.now()
        )


@app.get("/api/recommendations")
async def get_recommendations() -> Recommendation:
    global _cached_recommendation

    try:
        if not all([_data_fetcher, _optimizer, _recommender]):
            raise HTTPException(status_code=503, detail="服务初始化中")

        asset_data = _data_fetcher.get_all_asset_data()
        market_indicators = _data_fetcher.get_market_indicators()

        _optimizer.build_asset_classes_from_data(asset_data["assets"])
        result = _optimizer.optimize(method="target")

        recommendation = _recommender.generate_recommendation(
            result,
            asset_data["assets"],
            market_indicators
        )

        # 风险检查
        alert_manager = get_alert_manager()
        alerts = alert_manager.check_portfolio_risk(
            result["metrics"],
            recommendation.portfolio.allocation if recommendation.portfolio else []
        )

        # 如果有新警报，推送
        for alert in alerts:
            _feishu_pusher.push_risk_alert({
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp
            })

        _cached_recommendation = recommendation
        return recommendation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assets/{asset_type}")
async def get_assets(asset_type: str):
    try:
        if not _data_fetcher:
            raise HTTPException(status_code=503, detail="服务初始化中")

        data = _data_fetcher.get_all_asset_data()

        if asset_type == "all":
            return AssetDataResponse(
                timestamp=data["timestamp"],
                assets=data["assets"]
            )

        if asset_type not in data["assets"]:
            raise HTTPException(status_code=404, detail=f"资产类型 {asset_type} 不存在")

        return data["assets"][asset_type]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取资产数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market")
async def get_market() -> MarketIndicators:
    try:
        if not _data_fetcher:
            raise HTTPException(status_code=503, detail="服务初始化中")

        indicators = _data_fetcher.get_market_indicators()
        return MarketIndicators(**indicators)

    except Exception as e:
        logger.error(f"获取市场指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refresh")
async def refresh_data():
    global _cached_portfolio, _cached_recommendation

    try:
        _cached_portfolio = None
        _cached_recommendation = None

        if not _data_fetcher:
            raise HTTPException(status_code=503, detail="服务初始化中")

        await _data_fetcher.get_all_asset_data()
        return {"status": "success", "message": "数据已刷新"}

    except Exception as e:
        logger.error(f"刷新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/push")
async def push_to_feishu():
    global _cached_recommendation, _cached_portfolio

    try:
        if not _cached_recommendation or not _cached_portfolio:
            portfolio = await get_portfolio()
            recommendation = await get_recommendations()
            _cached_recommendation = recommendation
            _cached_portfolio = portfolio

        success = _feishu_pusher.push_daily_report(
            _cached_recommendation.model_dump(),
            _cached_portfolio.model_dump()
        )

        if success:
            return {"status": "success", "message": "推送成功"}
        else:
            return {"status": "warning", "message": "推送失败，请检查飞书配置"}

    except Exception as e:
        logger.error(f"飞书推送失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history(days: int = 30):
    try:
        if not _database:
            raise HTTPException(status_code=503, detail="数据库未初始化")

        performance = _database.calculate_performance(days)
        nav_history = _database.get_portfolio_nav_history(days)

        return {
            "performance": performance,
            "nav_history": nav_history.to_dict(orient="records") if not nav_history.empty else []
        }

    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest")
async def run_backtest(days: int = 252):
    """运行回测"""
    try:
        backtest = get_backtest()
        allocation = {
            "货币基金": 0.20,
            "银行理财": 0.35,
            "债券": 0.15,
            "公募基金": 0.20,
            "黄金": 0.05,
            "外汇": 0.05,
        }
        result = backtest.run_backtest(allocation, days)
        return {
            "total_return": result.total_return,
            "annualized_return": result.annualized_return,
            "volatility": result.volatility,
            "max_drawdown": result.max_drawdown,
            "sharpe_ratio": result.sharpe_ratio,
            "win_rate": result.win_rate
        }
    except Exception as e:
        logger.error(f"回测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics")
async def get_analytics_data():
    """获取组合分析"""
    try:
        portfolio = await get_portfolio()
        analytics = get_analytics()

        if portfolio and portfolio.allocation:
            result = analytics.generate_analysis_report(
                portfolio.portfolio_metrics.model_dump(),
                [a.model_dump() for a in portfolio.allocation]
            )
            return result
        return {"error": "暂无数据"}

    except Exception as e:
        logger.error(f"分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts")
async def get_alerts():
    """获取风险预警"""
    try:
        alert_manager = get_alert_manager()
        alerts = alert_manager.get_active_alerts()
        return {
            "alerts": [
                {
                    "level": a.level.value,
                    "title": a.title,
                    "message": a.message,
                    "metric": a.metric,
                    "value": a.value,
                    "threshold": a.threshold,
                    "timestamp": a.timestamp
                }
                for a in alerts
            ]
        }
    except Exception as e:
        logger.error(f"获取警报失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run_server()
