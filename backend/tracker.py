"""
收益追踪模块 - 每日组合净值记录
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """收益追踪器"""

    def __init__(self):
        self.records = []  # 内存记录，实际应存数据库

    def record_daily_value(self, date: str, total_value: float, allocation: dict) -> dict:
        """记录每日净值"""
        record = {
            "date": date,
            "total_value": total_value,
            "allocation": allocation,
            "timestamp": datetime.now().isoformat()
        }
        self.records.append(record)
        return record

    def calculate_returns(self, days: int = 30) -> dict:
        """计算收益统计"""
        if len(self.records) < 2:
            return {
                "total_return": 0,
                "annualized_return": 0,
                "best_day": 0,
                "worst_day": 0,
                "avg_daily_return": 0
            }

        # 简化计算
        sorted_records = sorted(self.records, key=lambda x: x['date'], reverse=True)[:days]
        if len(sorted_records) < 2:
            return {"total_return": 0, "annualized_return": 0}

        start_value = sorted_records[-1]['total_value']
        end_value = sorted_records[0]['total_value']
        total_return = (end_value - start_value) / start_value if start_value > 0 else 0

        # 日收益
        daily_returns = []
        for i in range(1, len(sorted_records)):
            prev = sorted_records[i]['total_value']
            curr = sorted_records[i-1]['total_value']
            if prev > 0:
                daily_returns.append((curr - prev) / prev)

        return {
            "total_return": total_return,
            "annualized_return": (1 + total_return) ** (252 / len(sorted_records)) - 1 if len(sorted_records) > 0 else 0,
            "best_day": max(daily_returns) if daily_returns else 0,
            "worst_day": min(daily_returns) if daily_returns else 0,
            "avg_daily_return": sum(daily_returns) / len(daily_returns) if daily_returns else 0,
            "days": len(sorted_records)
        }

    def get_history(self, days: int = 30) -> list[dict]:
        """获取历史记录"""
        return sorted(self.records, key=lambda x: x['date'], reverse=True)[:days]


# 全局实例
_tracker: Optional[PerformanceTracker] = None


def get_tracker() -> PerformanceTracker:
    global _tracker
    if _tracker is None:
        _tracker = PerformanceTracker()
    return _tracker
