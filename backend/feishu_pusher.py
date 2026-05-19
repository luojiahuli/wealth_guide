"""
飞书推送模块 - 使用 Feishu Bot API (app_id/app_secret)
通过 Hermes 的飞书机器人配置推送消息
"""
import logging
import os
import json
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Feishu Bot API 配置（从环境变量读取，兼容 Hermes 的飞书配置）
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_CHAT_ID = os.getenv("FEISHU_CHAT_ID", "")  # Hermes 飞书群/对话 ID


class FeishuPusher:
    """飞书推送器 - 使用 Bot API (OAuth2) 而非 Webhook"""

    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.chat_id = FEISHU_CHAT_ID
        self.enabled = bool(self.app_id and self.app_secret and self.chat_id)
        self._token = None
        self._token_expires_at = 0

    def _get_access_token(self) -> Optional[str]:
        """获取 tenant access token"""
        now = datetime.now().timestamp()
        if self._token and now < self._token_expires_at - 60:
            return self._token

        try:
            resp = httpx.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
                timeout=10
            )
            data = resp.json()
            if data.get("code") == 0:
                self._token = data["tenant_access_token"]
                self._token_expires_at = now + data.get("expire", 7200)
                logger.info("Feishu access token 获取成功")
                return self._token
            else:
                logger.error(f"Feishu token 获取失败: {data}")
                return None
        except Exception as e:
            logger.error(f"Feishu token 请求异常: {e}")
            return None

    def _send_message(self, payload: dict) -> bool:
        """发送消息到飞书 (IM API)"""
        if not self.enabled:
            logger.warning("飞书推送未配置，跳过")
            return False

        token = self._get_access_token()
        if not token:
            logger.error("无法获取 access token")
            return False

        try:
            resp = httpx.post(
                f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            result = resp.json()
            if result.get("code") == 0:
                logger.info("飞书消息发送成功")
                return True
            else:
                logger.error(f"飞书消息发送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"飞书消息发送异常: {e}")
            return False

    def push_text(self, text: str) -> bool:
        """推送文本消息"""
        if not self.enabled:
            logger.warning("飞书推送未配置，跳过")
            return False

        payload = {
            "receive_id": self.chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text})
        }
        return self._send_message(payload)

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
            "receive_id": self.chat_id,
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"📊 每日理财指南 | {date_str}",
                        "content": [
                            [
                                {"tag": "text", "text": "💰 资产状况\n"},
                                {"tag": "text", "text": f"总资产: ¥{portfolio.get('total_capital', 5000000)/10000:.0f}万\n"},
                                {"tag": "text", "text": f"预期年化收益: {expected_return:.2f}%\n"},
                                {"tag": "text", "text": f"夏普比率: {sharpe:.2f}\n"},
                                {"tag": "text", "text": f"VaR(95%): {var_95:.2f}%\n"},
                                {"tag": "text", "text": f"波动率: {volatility:.2f}%\n"},
                                {"tag": "text", "text": f"最大回撤: {max_dd:.2f}%"}
                            ],
                            [{"tag": "text", "text": "\n📈 最优配置建议\n"}] + alloc_lines,
                            [{"tag": "text", "text": "\n💡 今日操作建议\n"}] + (action_lines if action_lines else [{"tag": "text", "text": "• 暂无调仓建议"}]),
                            [{"tag": "text", "text": "\n🎯 精选推荐\n"}] + (pick_lines if pick_lines else [{"tag": "text", "text": "• 暂无精选推荐"}]),
                            [{"tag": "text", "text": f"\n📋 市场展望\n{outlook}"}],
                            [{"tag": "at", "text": ""}, {"tag": "text", "text": "\n⚠️ 风险提示: 本建议仅供参考，投资有风险，入市需谨慎"}]
                        ]
                    }
                }
            }
        }
        return self._send_message(payload)

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
            "receive_id": self.chat_id,
            "msg_type": "interactive",
            "content": json.dumps({
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": f"📊 每日理财指南 | {date_str}"},
                    "template": "blue"
                },
                "elements": [
                    # 资产总览
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"💰 **总资产** ¥{portfolio.get('total_capital', 5000000)/10000:.0f}万  |  📈 **预期收益** {expected_return:.2f}%  |  ⚖️ **夏普比率** {sharpe:.2f}"
                        }
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
                    *(action_elements if action_elements else [{"tag": "div", "text": {"tag": "lark_md", "content": "✅ 暂无调仓建议"}}]),
                    {"tag": "hr"},
                    # 精选推荐
                    {"tag": "div", "text": {"tag": "lark_md", "content": "**🎯 精选推荐**"}},
                    *(pick_elements[:3] if pick_elements else [{"tag": "div", "text": {"tag": "lark_md", "content": "暂无推荐"}}]),
                    {"tag": "hr"},
                    # 风险提示
                    {
                        "tag": "note",
                        "elements": [
                            {"tag": "plain_text", "content": "⚠️ 本建议仅供参考，投资有风险，入市需谨慎"}
                        ]
                    }
                ]
            })
        }
        return self._send_message(payload)

    def push_risk_alert(self, alert: dict) -> bool:
        """推送风险预警"""
        if not self.enabled:
            return False

        level_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
        level_color = {"info": "grey", "warning": "orange", "critical": "red"}

        payload = {
            "receive_id": self.chat_id,
            "msg_type": "interactive",
            "content": json.dumps({
                "header": {
                    "title": {"tag": "plain_text", "content": f"{level_emoji.get(alert.get('level', 'info'), '⚠️')} 风险预警 - {alert.get('title', '')}"},
                    "template": level_color.get(alert.get('level', 'warning'), "orange")
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": alert.get('message', '')}},
                    {"tag": "hr"},
                    {"tag": "div", "text": {"tag": "plain_text", "content": f"检测时间: {alert.get('timestamp', '')}"}}
                ]
            })
        }
        return self._send_message(payload)

    def push_daily_report(self, recommendation: dict, portfolio: dict) -> bool:
        """推送每日报告 (默认使用卡片格式)"""
        return self.push_card_report(portfolio, recommendation)

    def push_screenshot(self, image_path: str) -> bool:
        """推送本地截图到飞书"""
        if not self.enabled:
            logger.warning("飞书推送未配置，跳过")
            return False

        import mimetypes
        token = self._get_access_token()
        if not token:
            logger.error("无法获取 access token")
            return False

        mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
        filename = os.path.basename(image_path)

        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            # 上传图片
            from io import BytesIO
            resp = httpx.post(
                "https://open.feishu.cn/open-apis/im/v1/images",
                headers={"Authorization": f"Bearer {token}"},
                data={"image_type": "message"},
                files={"image": (filename, BytesIO(image_data), mime_type)},
                timeout=15
            )
            result = resp.json()
            if result.get("code") != 0:
                logger.error(f"图片上传失败: {result}")
                return False

            image_key = result["data"]["image_key"]
            logger.info(f"图片上传成功: {image_key}")

            # 发送图片消息
            payload = {
                "receive_id": self.chat_id,
                "msg_type": "image",
                "content": json.dumps({"image_key": image_key})
            }
            return self._send_message(payload)

        except Exception as e:
            logger.error(f"截图推送异常: {e}")
            return False


# 全局实例
_feishu_pusher: Optional[FeishuPusher] = None


def get_feishu_pusher() -> FeishuPusher:
    global _feishu_pusher
    if _feishu_pusher is None:
        _feishu_pusher = FeishuPusher()
    return _feishu_pusher
