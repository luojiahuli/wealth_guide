#!/usr/bin/env python3
"""
每日理财指南推送脚本
用于 cronjob 每日 09:00 自动推送飞书日报
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data_fetcher import get_data_fetcher
from backend.database import get_database
from backend.feishu_pusher import get_feishu_pusher
from backend.optimizer import get_optimizer
from backend.recommender import get_recommender

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始生成每日理财指南...")
    
    try:
        # 初始化组件
        data_fetcher = get_data_fetcher()
        optimizer = get_optimizer()
        recommender = get_recommender(optimizer)
        feishu_pusher = get_feishu_pusher()
        database = get_database()
        
        # 检查飞书配置
        if not feishu_pusher.enabled:
            logger.warning("飞书推送未配置，跳过推送")
            return
        
        # 1. 获取资产数据
        logger.info("正在获取资产数据...")
        asset_data = await data_fetcher.get_all_asset_data()
        
        # 2. 获取市场指标
        logger.info("正在获取市场指标...")
        market_indicators = await data_fetcher.get_market_indicators()
        
        # 3. 构建资产类别
        logger.info("正在构建资产组合...")
        optimizer.build_asset_classes_from_data(asset_data["assets"])
        
        # 4. 执行优化
        logger.info("正在优化资产配置...")
        optimization_result = optimizer.optimize(method="risk_parity")
        
        # 5. 生成推荐
        logger.info("正在生成推荐...")
        recommendation = recommender.generate_recommendation(
            optimization_result,
            asset_data["assets"],
            market_indicators
        )
        
        # 6. 保存到数据库
        logger.info("正在保存数据...")
        database.save_portfolio(
            date=datetime.now().strftime("%Y-%m-%d"),
            total_capital=optimization_result["total_capital"],
            allocation=optimization_result["aggregated_allocation"],
            metrics=optimization_result["metrics"],
            method=optimization_result["optimization_method"]
        )
        database.save_recommendation(recommendation.model_dump())
        database.save_market_indicators(market_indicators)
        
        # 7. 推送到飞书
        logger.info("正在推送飞书...")
        success = feishu_pusher.push_daily_report(
            recommendation.model_dump(),
            recommendation.portfolio.model_dump() if recommendation.portfolio else optimization_result
        )
        
        if success:
            logger.info("✅ 每日理财指南推送成功!")
        else:
            logger.error("❌ 飞书推送失败")
        
        # 关闭
        await data_fetcher.close()
        
    except Exception as e:
        logger.error(f"❌ 生成失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
