"""
飞书推送模块
"""

import logging
import os
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class FeishuPusher:
    """飞书推送器"""

    def __init__(self):
        self.webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "")
        self.chat_id = os.getenv("FEISHU_CHAT_ID", "")
        self.enabled = bool(self.webhook_url)

    def push_text(self, text: str) -> bool:
        """推送文本消息"""
        if not self.enabled:
            logger.warning("飞书推送未配置，跳过")
            return False

        payload = {
            "msg_type": "text",
            "content": {"text": text}
        }

        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"飞书推送失败: {e}")
            return False

    def push_daily_report(self, recommendation: dict, portfolio: dict) -> bool:
        """推送每日理财报告"""
        if not self.enabled:
            logger.warning("飞书推送未配置，跳过")
            return False

        # 构建消息
        date_str = datetime.now().strftime("%Y年%m月%d日")
        
        # 资产配置
        allocation = portfolio.get("allocation", [])
        alloc_lines = []
        for item in allocation:
            ratio = item.get("ratio", 0) * 100
            amount = item.get("amount", 0)
            alloc_lines.append(f"• {item['asset']}: {ratio:.1f}% (¥{amount/10000:.0f}万)")
        
        # 指标
        metrics = portfolio.get("portfolio_metrics", {})
        expected_return = metrics.get("expected_return", 0) * 100
        sharpe = metrics.get("sharpe_ratio", 0)
        var_95 = metrics.get("var_95", 0) * 100
        
        # 操作建议
        actions = recommendation.get("rebalance_actions", [])
        action_lines = []
        for action in actions[:3]:
            action_lines.append(f"• [{action['action']}] {action['asset']} ¥{action['amount']/10000:.0f}万")
        
        # 精选推荐
        picks = recommendation.get("top_picks", [])
        pick_lines = []
        for pick in picks[:3]:
            pick_lines.append(f"• {pick['name']} (预期{pick['expected_return']*100:.1f}%)")
        
        # 市场展望
        outlook = recommendation.get("market_outlook", "维持当前配置")

        # 组装消息
        alloc_text = "\n".join(alloc_lines)
        action_text = "\n".join(action_lines) if action_lines else "• 暂无调仓建议"
        pick_text = "\n".join(pick_lines) if pick_lines else "• 暂无精选推荐"

        message = f"""📊 每日理财指南 | {date_str}

💰 资产状况
总资产: ¥{portfolio.get('total_capital', 5000000)/10000:.0f}万
预期年化收益: {expected_return:.2f}%
夏普比率: {sharpe:.2f}
VaR(95%): {var_95:.2f}%

📈 最优配置建议
{alloc_text}

💡 今日操作建议
{action_text}

🎯 精选推荐
{pick_text}

📋 市场展望
{outlook}

⚠️ 风险提示: 本建议仅供参考，投资有风险，入市需谨慎"""

        payload = {
            "msg_type": "text",
            "content": {"text": message}
        }

        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("飞书日报推送成功")
                return True
            else:
                logger.error(f"飞书推送失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"飞书推送异常: {e}")
            return False

    def push_rich_text(self, title: str, content: str) -> bool:
        """推送富文本消息"""
        if not self.enabled:
            return False

        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": [[
                            {"tag": "text", "text": content}
                        ]]
                    }
                }
            }
        }

        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"飞书富文本推送失败: {e}")
            return False


# 全局实例
_feishu_pusher: Optional[FeishuPusher] = None


def get_feishu_pusher() -> FeishuPusher:
    global _feishu_pusher
    if _feishu_pusher is None:
        _feishu_pusher = FeishuPusher()
    return _feishu_pusher
