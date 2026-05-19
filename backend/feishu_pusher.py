"""
飞书推送模块 - 富文本消息、卡片消息、风险预警
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

    def push_rich_report(self, portfolio: dict, recommendation: dict) -> bool:
        """推送富文本日报 (post类型消息)"""
        if not self.enabled:
            logger.warning("飞书推送未配置，跳过")
            return False

        date_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        # 资产配置
        allocation = portfolio.get("allocation", [])
        alloc_lines = []
        for item in allocation:
            ratio = item.get("ratio", 0) * 100
            amount = item.get("amount", 0)
            alloc_lines.append({
                "tag": "text",
                "text": f"• {item['asset']}: {ratio:.1f}% (¥{amount/10000:.0f}万)"
            })

        # 指标
        metrics = portfolio.get("portfolio_metrics", {})
        expected_return = metrics.get("expected_return", 0) * 100
        sharpe = metrics.get("sharpe_ratio", 0)
        var_95 = metrics.get("var_95", 0) * 100
        volatility = metrics.get("volatility", 0) * 100
        max_dd = metrics.get("max_drawdown", 0) * 100

        # 操作建议
        actions = recommendation.get("rebalance_actions", [])
        action_lines = []
        for action in actions[:3]:
            emoji = "📈" if action['action'] == '买入' else "📉"
            action_lines.append({
                "tag": "text",
                "text": f"{emoji} [{action['action']}] {action['asset']} ¥{action['amount']/10000:.0f}万\n    {action.get('reason', '')}"
            })

        # 精选推荐
        picks = recommendation.get("top_picks", [])
        pick_lines = []
        for pick in picks[:3]:
            pick_lines.append({
                "tag": "text",
                "text": f"🎯 {pick['name']} (预期{pick['expected_return']*100:.1f}%)"
            })

        # 市场展望
        outlook = recommendation.get("market_outlook", "维持当前配置，关注再平衡机会")

        # 构建富文本消息
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"📊 每日理财指南 | {date_str}",
                        "content": [
                            # 资产状况
                            [
                                {"tag": "text", "text": "💰 资产状况\n"},
                                {"tag": "text", "text": f"总资产: ¥{portfolio.get('total_capital', 5000000)/10000:.0f}万\n"},
                                {"tag": "text", "text": f"预期年化收益: {expected_return:.2f}%\n"},
                                {"tag": "text", "text": f"夏普比率: {sharpe:.2f}\n"},
                                {"tag": "text", "text": f"VaR(95%): {var_95:.2f}%\n"},
                                {"tag": "text", "text": f"波动率: {volatility:.2f}%\n"},
                                {"tag": "text", "text": f"最大回撤: {max_dd:.2f}%"}
                            ],
                            # 配置建议
                            [
                                {"tag": "text", "text": "\n📈 最优配置建议\n"},
                            ] + alloc_lines,
                            # 操作建议
                            [
                                {"tag": "text", "text": "\n💡 今日操作建议\n"},
                            ] + (action_lines if action_lines else [{"tag": "text", "text": "• 暂无调仓建议"}]),
                            # 精选推荐
                            [
                                {"tag": "text", "text": "\n🎯 精选推荐\n"},
                            ] + (pick_lines if pick_lines else [{"tag": "text", "text": "• 暂无精选推荐"}]),
                            # 市场展望
                            [
                                {"tag": "text", "text": f"\n📋 市场展望\n{outlook}"},
                            ],
                            # 风险提示
                            [
                                {"tag": "at", "text": ""},
                                {"tag": "text", "text": "\n⚠️ 风险提示: 本建议仅供参考，投资有风险，入市需谨慎"},
                            ]
                        ]
                    }
                }
            }
        }

        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("飞书富文本日报推送成功")
                return True
            else:
                logger.error(f"飞书推送失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"飞书推送异常: {e}")
            return False

    def push_card_report(self, portfolio: dict, recommendation: dict) -> bool:
        """推送卡片消息 (更美观)"""
        if not self.enabled:
            logger.warning("飞书推送未配置，跳过")
            return False

        date_str = datetime.now().strftime("%Y年%m月%d日")
        metrics = portfolio.get("portfolio_metrics", {})
        expected_return = metrics.get("expected_return", 0) * 100
        sharpe = metrics.get("sharpe_ratio", 0)

        # 操作建议卡片
        actions = recommendation.get("rebalance_actions", [])
        action_elements = []
        for action in actions[:3]:
            color = "#00B42A" if action['action'] == '买入' else "#F53F3F"
            action_elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{'📈 买入' if action['action'] == '买入' else '📉 卖出'}** {action['asset']}\n¥{action['amount']/10000:.0f}万\n_{action.get('reason', '')}_"
                }
            })

        # 精选推荐卡片
        picks = recommendation.get("top_picks", [])
        pick_elements = []
        for pick in picks[:3]:
            pick_elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{pick['name']}** | {pick['type']}\n预期收益: **{pick['expected_return']*100:.1f}%** | {pick['risk']}风险"
                }
            })

        # 构建卡片消息
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": f"📊 每日理财指南 | {date_str}"},
                    "template": "blue"
                },
                "elements": [
                    # 资产总览
                    {
                        "tag": "table",
                        "columns": [
                            {"tag": "col", "width": "33%"},
                            {"tag": "col", "width": "33%"},
                            {"tag": "col", "width": "34%"}
                        ],
                        "cells": [[
                            [
                                {"tag": "plain_text", "content": f"💰 总资产", "extra": {"tag": "plain_text", "content": f"\n¥{portfolio.get('total_capital', 5000000)/10000:.0f}万"}}
                            ],
                            [
                                {"tag": "plain_text", "content": f"📈 预期收益", "extra": {"tag": "plain_text", "content": f"\n{expected_return:.2f}%"}}
                            ],
                            [
                                {"tag": "plain_text", "content": f"⚖️ 夏普比率", "extra": {"tag": "plain_text", "content": f"\n{sharpe:.2f}"}}
                            ]
                        ]]
                    },
                    {"tag": "hr"},
                    # 配置比例
                    {"tag": "div", "text": {"tag": "lark_md", "content": "**📈 资产配置**"}},
                    {
                        "tag": "column_set",
                        "flex_mode": "center",
                        "children": [
                            {
                                "tag": "column",
                                "width": "auto",
                                "elements": [
                                    {"tag": "div", "text": {"tag": "lark_md", "content": f"💰 货币基金\n**{next((a['ratio']*100 for a in portfolio.get('allocation', []) if '货币' in a['asset']), 0):.1f}%**"}}
                                ]
                            },
                            {
                                "tag": "column",
                                "width": "auto",
                                "elements": [
                                    {"tag": "div", "text": {"tag": "lark_md", "content": f"🏦 银行理财\n**{next((a['ratio']*100 for a in portfolio.get('allocation', []) if '银行' in a['asset']), 0):.1f}%**"}}
                                ]
                            },
                            {
                                "tag": "column",
                                "width": "auto",
                                "elements": [
                                    {"tag": "div", "text": {"tag": "lark_md", "content": f"📄 债券\n**{next((a['ratio']*100 for a in portfolio.get('allocation', []) if '债券' in a['asset']), 0):.1f}%**"}}
                                ]
                            },
                            {
                                "tag": "column",
                                "width": "auto",
                                "elements": [
                                    {"tag": "div", "text": {"tag": "lark_md", "content": f"📈 公募基金\n**{next((a['ratio']*100 for a in portfolio.get('allocation', []) if '基金' in a['asset']), 0):.1f}%**"}}
                                ]
                            }
                        ]
                    },
                    {"tag": "hr"},
                    # 操作建议
                    {"tag": "div", "text": {"tag": "lark_md", "content": "**💡 今日操作建议**"}},
                    *action_elements if action_elements else [{"tag": "div", "text": {"tag": "lark_md", "content": "✅ 暂无调仓建议"}}],
                    {"tag": "hr"},
                    # 精选推荐
                    {"tag": "div", "text": {"tag": "lark_md", "content": "**🎯 精选推荐**"}},
                    *pick_elements[:3] if pick_elements else [{"tag": "div", "text": {"tag": "lark_md", "content": "暂无推荐"}}],
                    {"tag": "hr"},
                    # 风险提示
                    {
                        "tag": "note",
                        "elements": [
                            {"tag": "plain_text", "content": "⚠️ 本建议仅供参考，投资有风险，入市需谨慎"}
                        ]
                    }
                ]
            }
        }

        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("飞书卡片日报推送成功")
                return True
            else:
                logger.error(f"飞书推送失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"飞书推送异常: {e}")
            return False

    def push_risk_alert(self, alert: dict) -> bool:
        """推送风险预警"""
        if not self.enabled:
            return False

        level_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
        level_color = {"info": "grey", "warning": "orange", "critical": "red"}

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"{level_emoji.get(alert.get('level', 'info'), '⚠️')} 风险预警 - {alert.get('title', '')}"},
                    "template": level_color.get(alert.get('level', 'warning'), "orange")
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": alert.get('message', '')}},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "plain_text", "content": f"检测时间: {alert.get('timestamp', '')}"}}
                ]
            }
        }

        try:
            response = httpx.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"风险预警推送失败: {e}")
            return False

    def push_daily_report(self, recommendation: dict, portfolio: dict) -> bool:
        """推送每日报告 (默认使用卡片格式)"""
        # 优先使用卡片格式
        return self.push_card_report(portfolio, recommendation)


# 全局实例
_feishu_pusher: Optional[FeishuPusher] = None


def get_feishu_pusher() -> FeishuPusher:
    global _feishu_pusher
    if _feishu_pusher is None:
        _feishu_pusher = FeishuPusher()
    return _feishu_pusher
