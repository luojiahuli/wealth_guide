"""
数据抓取模块 - 使用默认数据（避免外部API阻塞）
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class DataFetcher:
    """统一数据抓取器（默认数据版本）"""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 缓存1小时

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self.cache:
            return False
        _, timestamp = self.cache[key]
        return (datetime.now() - timestamp).total_seconds() < self.cache_ttl

    def _set_cache(self, key: str, data: Any):
        self.cache[key] = (data, datetime.now())

    # ==================== 货币基金 ====================

    def get_money_fund_data(self) -> list[dict]:
        """获取货币基金数据（默认数据）"""
        cache_key = "money_fund"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        result = [
            {"name": "余额宝", "code": "000198", "nav": 1.0, "annual_return": 1.98, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "天弘基金"},
            {"name": "理财通-易方达", "code": "000009", "nav": 1.0, "annual_return": 2.05, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "易方达基金"},
            {"name": "建信现金添利", "code": "002848", "nav": 1.0, "annual_return": 2.10, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "建信基金"},
            {"name": "兴全货币", "code": "340005", "nav": 1.0, "annual_return": 2.15, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "兴全基金"},
            {"name": "汇添富现金宝", "code": "000600", "nav": 1.0, "annual_return": 2.08, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "汇添富基金"},
        ]
        self._set_cache(cache_key, result)
        return result

    # ==================== 银行理财 ====================

    def get_bank_product_data(self) -> list[dict]:
        """获取银行理财产品数据（默认数据）"""
        cache_key = "bank_product"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        result = [
            {"name": "招行聚益生金", "bank": "招商银行", "expected_return": 3.45, "term": "30天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "招商银行"},
            {"name": "工行稳得利", "bank": "工商银行", "expected_return": 3.30, "term": "90天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "工商银行"},
            {"name": "建行乾元", "bank": "建设银行", "expected_return": 3.50, "term": "180天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "建设银行"},
            {"name": "农行金钥匙", "bank": "农业银行", "expected_return": 3.40, "term": "1年", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "农业银行"},
            {"name": "中行中银理财", "bank": "中国银行", "expected_return": 3.35, "term": "6个月", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "中国银行"},
            {"name": "平安银行天天成长", "bank": "平安银行", "expected_return": 3.60, "term": "T+0", "type": "银行理财T+0", "liquidity": "T+0", "risk_level": "低", "min_amount": 10000, "provider": "平安银行"},
        ]
        self._set_cache(cache_key, result)
        return result

    # ==================== 公募基金 ====================

    def get_fund_data(self) -> list[dict]:
        """获取公募基金数据（默认数据）"""
        cache_key = "fund"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        result = [
            {"name": "易方达蓝筹精选", "code": "005827", "type": "混合型", "risk_level": "中", "nav": 1.85, "annual_return": 0.12, "min_amount": 100, "provider": "易方达基金"},
            {"name": "景顺长城新兴成长", "code": "260108", "type": "混合型", "risk_level": "中", "nav": 1.92, "annual_return": 0.08, "min_amount": 100, "provider": "景顺长城基金"},
            {"name": "兴全趋势投资", "code": "163402", "type": "混合型", "risk_level": "中", "nav": 1.45, "annual_return": 0.10, "min_amount": 100, "provider": "兴全基金"},
            {"name": "广发稳健增长", "code": "270002", "type": "混合型", "risk_level": "中低", "nav": 1.78, "annual_return": 0.06, "min_amount": 100, "provider": "广发基金"},
            {"name": "博时信用债", "code": "050027", "type": "债券型", "risk_level": "中低", "nav": 1.12, "annual_return": 0.04, "min_amount": 100, "provider": "博时基金"},
            {"name": "易方达沪深300ETF", "code": "510310", "type": "指数型", "risk_level": "中", "nav": 2.10, "annual_return": 0.05, "min_amount": 100, "provider": "易方达基金"},
        ]
        self._set_cache(cache_key, result)
        return result

    # ==================== 债券 ====================

    def get_bond_data(self) -> list[dict]:
        """获取债券数据（默认数据）"""
        cache_key = "bond"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        result = [
            {"name": "国债210009", "code": "019547", "type": "国债", "risk_level": "中低", "annual_return": 0.025, "term": "10年", "provider": "中债登"},
            {"name": "国债230023", "code": "230023", "type": "国债", "risk_level": "中低", "annual_return": 0.022, "term": "30年", "provider": "中债登"},
            {"name": "国开债200215", "code": "200215", "type": "政策性银行债", "risk_level": "中低", "annual_return": 0.028, "term": "10年", "provider": "中债登"},
            {"name": "AAA企业债", "code": "AAA", "type": "企业债", "risk_level": "中", "annual_return": 0.035, "term": "5年", "provider": "中债登"},
            {"name": "AA+城投债", "code": "AA+", "type": "城投债", "risk_level": "中", "annual_return": 0.042, "term": "5年", "provider": "中债登"},
        ]
        self._set_cache(cache_key, result)
        return result

    # ==================== 外汇 ====================

    def get_forex_data(self) -> list[dict]:
        """获取外汇数据（默认数据）"""
        cache_key = "forex"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        result = [
            {"name": "美元", "code": "USD", "type": "外汇", "risk_level": "中", "rate": 7.24, "annual_return": 0.02, "provider": "中国人民银行"},
            {"name": "欧元", "code": "EUR", "type": "外汇", "risk_level": "中", "rate": 7.85, "annual_return": 0.01, "provider": "中国人民银行"},
            {"name": "英镑", "code": "GBP", "type": "外汇", "risk_level": "中", "rate": 9.15, "annual_return": 0.00, "provider": "中国人民银行"},
            {"name": "港币", "code": "HKD", "type": "外汇", "risk_level": "低", "rate": 0.93, "annual_return": 0.00, "provider": "中国人民银行"},
        ]
        self._set_cache(cache_key, result)
        return result

    # ==================== 黄金 ====================

    def get_gold_data(self) -> list[dict]:
        """获取黄金数据（默认数据）"""
        cache_key = "gold"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        result = [
            {"name": "华安黄金ETF", "code": "518880", "type": "黄金", "risk_level": "中高", "price": 558.50, "annual_return": 0.08, "provider": "上交所"},
            {"name": "博时黄金ETF", "code": "159937", "type": "黄金", "risk_level": "中高", "price": 556.80, "annual_return": 0.08, "provider": "深交所"},
        ]
        self._set_cache(cache_key, result)
        return result

    # ==================== 综合数据获取 ====================

    def get_all_asset_data(self) -> dict:
        """获取所有资产类别数据（同步版本）"""
        return {
            "timestamp": datetime.now().isoformat(),
            "assets": {
                "money_fund": self.get_money_fund_data(),
                "bank_product": self.get_bank_product_data(),
                "fund": self.get_fund_data(),
                "bond": self.get_bond_data(),
                "forex": self.get_forex_data(),
                "gold": self.get_gold_data(),
            }
        }

    def get_market_indicators(self) -> dict:
        """获取市场情绪指标（默认数据）"""
        return {
            "vix": None,
            "credit_spread": None,
            "market_trend": "震荡",
            "sh_index": 3150.0,
            "sh_change": 0.005,
            "hs300_index": 3850.0,
            "hs300_change": 0.003,
            "timestamp": datetime.now().isoformat()
        }

    async def close(self):
        """关闭会话"""
        pass


# 全局实例
_data_fetcher: DataFetcher | None = None


def get_data_fetcher() -> DataFetcher:
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = DataFetcher()
    return _data_fetcher
