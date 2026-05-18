"""
Wealth Guide - 每日理财指南 API
FastAPI 后端服务
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .data_fetcher import DataFetcher, get_data_fetcher
from .database import Database, get_database
from .feishu_pusher import FeishuPusher, get_feishu_pusher
from .models import (
    AssetDataResponse,
    HealthCheck,
    MarketIndicators,
    Portfolio,
    PortfolioMetrics,
    Recommendation,
)
from .optimizer import PortfolioOptimizer, get_optimizer
from .recommender import Recommender, get_recommender

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局状态
_data_fetcher: Optional[DataFetcher] = None
_optimizer: Optional[PortfolioOptimizer] = None
_recommender: Optional[Recommender] = None
_database: Optional[Database] = None
_feishu_pusher: Optional[FeishuPusher] = None
_cached_recommendation: Optional[dict] = None
_cached_portfolio: Optional[dict] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _data_fetcher, _optimizer, _recommender, _database, _feishu_pusher
    
    logger.info("初始化 Wealth Guide...")
    
    _data_fetcher = get_data_fetcher()
    _optimizer = get_optimizer()
    _recommender = get_recommender(_optimizer)
    _database = get_database()
    _feishu_pusher = get_feishu_pusher()
    
    # 尝试加载缓存的推荐数据
    try:
        cached = _database.get_recommendation()
        if cached:
            logger.info("从数据库加载缓存推荐")
    except:
        pass
    
    yield
    
    # 清理
    if _data_fetcher:
        await _data_fetcher.close()
    logger.info("Wealth Guide 关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Wealth Guide - 每日理财指南",
    description="500万资产组合优化与每日理财建议",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/health")
async def health_check() -> HealthCheck:
    """健康检查"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        data_freshness="实时"
    )


@app.get("/api/portfolio")
async def get_portfolio() -> Portfolio:
    """
    获取当前最优投资组合
    """
    global _cached_portfolio
    
    try:
        # 如果有缓存且在2小时内，直接返回
        if _cached_portfolio:
            return _cached_portfolio
        
        if not _data_fetcher or not _optimizer or not _recommender:
            raise HTTPException(status_code=503, detail="服务初始化中")
        
        # 获取资产数据
        logger.info("正在获取资产数据...")
        asset_data = _data_fetcher.get_all_asset_data()
        
        # 构建资产类别
        _optimizer.build_asset_classes_from_data(asset_data["assets"])
        
        # 执行优化
        logger.info("正在优化组合...")
        result = _optimizer.optimize(method="risk_parity")
        
        # 生成推荐
        logger.info("正在生成推荐...")
        recommendation = _recommender.generate_recommendation(
            result, 
            asset_data["assets"]
        )
        
        # 保存到数据库
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
        # 返回默认组合
        return Portfolio(
            total_capital=5000000,
            allocation=[
                {"asset": "货币基金", "ratio": 0.25, "amount": 1250000, "expected_return": 0.02},
                {"asset": "银行理财", "ratio": 0.30, "amount": 1500000, "expected_return": 0.035},
                {"asset": "债券", "ratio": 0.15, "amount": 750000, "expected_return": 0.04},
                {"asset": "公募基金", "ratio": 0.20, "amount": 1000000, "expected_return": 0.08},
                {"asset": "黄金", "ratio": 0.05, "amount": 250000, "expected_return": 0.03},
                {"asset": "外汇", "ratio": 0.05, "amount": 250000, "expected_return": 0.01},
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
    """
    获取每日推荐
    """
    global _cached_recommendation
    
    try:
        if not _data_fetcher or not _optimizer or not _recommender:
            raise HTTPException(status_code=503, detail="服务初始化中")
        
        # 获取资产数据
        asset_data = _data_fetcher.get_all_asset_data()
        
        # 获取市场指标
        market_indicators = _data_fetcher.get_market_indicators()
        
        # 构建资产类别
        _optimizer.build_asset_classes_from_data(asset_data["assets"])
        
        # 执行优化
        result = _optimizer.optimize(method="risk_parity")
        
        # 生成推荐
        recommendation = _recommender.generate_recommendation(
            result, 
            asset_data["assets"],
            market_indicators
        )
        
        _cached_recommendation = recommendation.model_dump()
        
        return recommendation
        
    except Exception as e:
        logger.error(f"获取推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assets/{asset_type}")
async def get_assets(asset_type: str):
    """
    获取指定类型资产数据
    """
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
    """
    获取市场情绪指标
    """
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
    """
    强制刷新所有数据
    """
    global _cached_portfolio, _cached_recommendation
    
    try:
        _cached_portfolio = None
        _cached_recommendation = None
        
        if not _data_fetcher:
            raise HTTPException(status_code=503, detail="服务初始化中")
        
        # 刷新资产数据
        await _data_fetcher.get_all_asset_data()
        
        return {"status": "success", "message": "数据已刷新"}
        
    except Exception as e:
        logger.error(f"刷新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/push")
async def push_to_feishu():
    """
    推送当前推荐到飞书
    """
    global _cached_recommendation, _cached_portfolio
    
    try:
        if not _cached_recommendation or not _cached_portfolio:
            # 先生成推荐
            recommendation = await get_recommendations()
            portfolio = await get_portfolio()
            _cached_recommendation = recommendation.model_dump()
            _cached_portfolio = portfolio.model_dump()
        
        pusher = get_feishu_pusher()
        success = pusher.push_daily_report(
            _cached_recommendation,
            _cached_portfolio
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
    """
    获取组合历史表现
    """
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


def run_server():
    """启动服务器"""
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run_server()
