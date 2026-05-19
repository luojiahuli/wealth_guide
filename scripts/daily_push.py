#!/usr/bin/env python3
"""
每日推送脚本 - 定时推送到飞书
Usage: python scripts/daily_push.py [--screenshot PATH]
Crontab: 0 9 * * 1-5 cd ~/workspace/wealth_guide && python scripts/daily_push.py
"""
import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.data_fetcher import get_data_fetcher
from backend.optimizer import get_optimizer
from backend.recommender import get_recommender
from backend.feishu_pusher import get_feishu_pusher
from backend.database import get_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_report():
    """生成每日报告"""
    logger.info("开始生成每日报告...")

    # 初始化组件
    data_fetcher = get_data_fetcher()
    optimizer = get_optimizer()
    recommender = get_recommender(optimizer)
    database = get_database()
    pusher = get_feishu_pusher()

    # 获取资产数据
    logger.info("获取资产数据...")
    asset_data = data_fetcher.get_all_asset_data()

    # 优化组合
    logger.info("优化投资组合...")
    optimizer.build_asset_classes_from_data(asset_data["assets"])
    result = optimizer.optimize(method="target")

    # 生成推荐
    logger.info("生成推荐...")
    market_indicators = data_fetcher.get_market_indicators()
    recommendation = recommender.generate_recommendation(
        result,
        asset_data["assets"],
        market_indicators
    )

    # 保存到数据库
    try:
        database.save_portfolio(
            date=datetime.now().strftime("%Y-%m-%d"),
            total_capital=result["total_capital"],
            allocation=result["aggregated_allocation"],
            metrics=result["metrics"],
            method=result["optimization_method"]
        )
        database.save_recommendation(recommendation.model_dump())
        logger.info("数据已保存到数据库")
    except Exception as e:
        logger.warning(f"数据库保存失败: {e}")

    return recommendation.model_dump(), result


def push_report(screenshot_path: str = None):
    """推送报告到飞书"""
    try:
        # 生成报告
        recommendation, portfolio = asyncio.run(generate_report())

        # 获取飞书推送器
        pusher = get_feishu_pusher()

        if not pusher.enabled:
            logger.warning("飞书推送未配置，跳过推送")
            print("❌ 飞书推送未配置，请设置 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_CHAT_ID 环境变量")
            return False

        # 构建组合字典
        portfolio_dict = {
            "total_capital": portfolio["total_capital"],
            "allocation": [
                {
                    "asset": k,
                    "ratio": v["weight"],
                    "amount": v["amount"],
                    "expected_return": v["expected_return"]
                }
                for k, v in portfolio["aggregated_allocation"].items()
            ],
            "portfolio_metrics": portfolio["metrics"]
        }

        # 推送卡片日报
        success = pusher.push_card_report(portfolio_dict, recommendation)

        if success:
            logger.info("✅ 飞书日报推送成功")
            print("✅ 飞书日报推送成功")
        else:
            logger.error("❌ 飞书日报推送失败")
            print("❌ 飞书日报推送失败")

        # 推送截图（可选）
        if screenshot_path and Path(screenshot_path).exists():
            screenshot_success = pusher.push_screenshot(str(screenshot_path))
            if screenshot_success:
                logger.info("✅ 截图推送成功")
                print("✅ 截图推送成功")
            else:
                logger.error("❌ 截图推送失败")
                print("❌ 截图推送失败")
        elif screenshot_path:
            logger.warning(f"截图文件不存在: {screenshot_path}")

        return success

    except Exception as e:
        logger.error(f"推送过程出错: {e}")
        print(f"❌ 推送过程出错: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wealth Guide 每日推送")
    parser.add_argument("--screenshot", "-s", type=str, default=None,
                        help="前端页面截图路径，推送截图到飞书")
    args = parser.parse_args()

    print("=" * 50)
    print("📊 Wealth Guide 每日推送")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    success = push_report(screenshot_path=args.screenshot)
    sys.exit(0 if success else 1)
