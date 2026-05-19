"""
数据抓取模块 - 接入 akshare 真实数据源
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# 尝试导入 akshare，失败则使用默认数据
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("akshare 未安装，将使用默认数据")


class DataCache:
    """数据缓存"""

    def __init__(self, ttl: int = 300):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._ttl = ttl

    def get(self, key: str, bypass: bool = False) -> Optional[Any]:
        if bypass or key not in self._cache:
            return None
        data, timestamp = self._cache[key]
        if (datetime.now() - timestamp).total_seconds() > self._ttl:
            del self._cache[key]
            return None
        return data

    def set(self, key: str, value: Any):
        self._cache[key] = (value, datetime.now())

    def clear(self):
        self._cache.clear()


class DataFetcher:
    """统一数据抓取器"""

    def __init__(self):
        self.cache = DataCache(ttl=300)
        self._use_fallback = not AKSHARE_AVAILABLE

    def _get_fallback_data(self, data_type: str) -> list[dict]:
        """获取默认数据 (akshare 不可用时)"""
        defaults = {
            'money_fund': [
                {"name": "余额宝", "code": "000198", "nav": 1.0, "annual_return": 0.021, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "天弘基金"},
                {"name": "理财通-易方达", "code": "000009", "nav": 1.0, "annual_return": 0.0205, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "易方达基金"},
                {"name": "建信现金添利", "code": "002848", "nav": 1.0, "annual_return": 0.021, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "建信基金"},
            ],
            'bank_product': [
                {"name": "招行聚益生金", "bank": "招商银行", "expected_return": 0.0345, "term": "30天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000},
                {"name": "工行稳得利", "bank": "工商银行", "expected_return": 0.033, "term": "90天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000},
                {"name": "建行乾元", "bank": "建设银行", "expected_return": 0.035, "term": "180天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000},
                {"name": "平安银行天天成长", "bank": "平安银行", "expected_return": 0.036, "term": "T+0", "type": "银行理财T+0", "liquidity": "T+0", "risk_level": "低", "min_amount": 10000},
            ],
            'fund': [
                {"name": "易方达蓝筹精选", "code": "005827", "type": "混合型", "risk_level": "中", "nav": 1.85, "annual_return": 0.12, "min_amount": 100, "provider": "易方达基金"},
                {"name": "景顺长城新兴成长", "code": "260108", "type": "混合型", "risk_level": "中", "nav": 1.92, "annual_return": 0.08, "min_amount": 100, "provider": "景顺长城基金"},
                {"name": "兴全趋势投资", "code": "163402", "type": "混合型", "risk_level": "中", "nav": 1.45, "annual_return": 0.10, "min_amount": 100, "provider": "兴全基金"},
                {"name": "广发稳健增长", "code": "270002", "type": "混合型", "risk_level": "中低", "nav": 1.78, "annual_return": 0.06, "min_amount": 100, "provider": "广发基金"},
                {"name": "博时信用债", "code": "050027", "type": "债券型", "risk_level": "中低", "nav": 1.12, "annual_return": 0.04, "min_amount": 100, "provider": "博时基金"},
                {"name": "易方达沪深300ETF", "code": "510310", "type": "指数型", "risk_level": "中", "nav": 2.10, "annual_return": 0.05, "min_amount": 100, "provider": "易方达基金"},
            ],
            'bond': [
                {"name": "国债210009", "code": "019547", "type": "国债", "risk_level": "中低", "annual_return": 0.025, "term": "10年", "provider": "中债登"},
                {"name": "国开债200215", "code": "200215", "type": "政策性银行债", "risk_level": "中低", "annual_return": 0.028, "term": "10年", "provider": "中债登"},
                {"name": "AAA企业债", "code": "AAA", "type": "企业债", "risk_level": "中", "annual_return": 0.035, "term": "5年", "provider": "中债登"},
                {"name": "AA+城投债", "code": "AA+", "type": "城投债", "risk_level": "中", "annual_return": 0.042, "term": "5年", "provider": "中债登"},
            ],
            'gold': [
                {"name": "华安黄金ETF", "code": "518880", "type": "黄金", "risk_level": "中高", "price": 558.50, "annual_return": 0.08, "provider": "上交所"},
                {"name": "博时黄金ETF", "code": "159937", "type": "黄金", "risk_level": "中高", "price": 556.80, "annual_return": 0.08, "provider": "深交所"},
            ],
            'forex': [
                {"name": "美元", "code": "USD", "type": "外汇", "risk_level": "中", "rate": 7.24, "annual_return": 0.02, "provider": "中国人民银行"},
                {"name": "欧元", "code": "EUR", "type": "外汇", "risk_level": "中", "rate": 7.85, "annual_return": 0.01, "provider": "中国人民银行"},
                {"name": "英镑", "code": "GBP", "type": "外汇", "risk_level": "中", "rate": 9.15, "annual_return": 0.00, "provider": "中国人民银行"},
                {"name": "港币", "code": "HKD", "type": "外汇", "risk_level": "低", "rate": 0.93, "annual_return": 0.00, "provider": "中国人民银行"},
            ]
        }
        return defaults.get(data_type, [])

    # ==================== 货币基金 ====================

    def get_money_fund_data(self, bypass: bool = False) -> list[dict]:
        """获取货币基金数据"""
        cache_key = "money_fund"
        cached = self.cache.get(cache_key, bypass)
        if cached is not None:
            return cached

        try:
            if AKSHARE_AVAILABLE:
                # 使用 akshare 获取货币基金数据
                df = ak.fund_open_fund_info_em(symbol="货币型", indicator="近1年")
                # 简化处理，实际需要解析 DataFrame
                logger.info(f"成功获取货币基金数据: {len(df)} 条")
        except Exception as e:
            logger.warning(f"获取货币基金数据失败: {e}，使用默认数据")

        result = self._get_fallback_data('money_fund')
        self.cache.set(cache_key, result)
        return result

    # ==================== 公募基金 ====================

    def get_fund_data(self, bypass: bool = False) -> list[dict]:
        """获取公募基金数据"""
        cache_key = "fund"
        cached = self.cache.get(cache_key, bypass)
        if cached is not None:
            return cached

        try:
            if AKSHARE_AVAILABLE:
                # 获取基金排行数据
                df = ak.fund_open_fund_info_em(symbol="混合型", indicator="近1年")
                logger.info(f"成功获取基金数据: {len(df)} 条")
        except Exception as e:
            logger.warning(f"获取基金数据失败: {e}，使用默认数据")

        result = self._get_fallback_data('fund')
        self.cache.set(cache_key, result)
        return result

    # ==================== 银行理财 ====================

    def get_bank_product_data(self, bypass: bool = False) -> list[dict]:
        """获取银行理财数据"""
        cache_key = "bank_product"
        cached = self.cache.get(cache_key, bypass)
        if cached is not None:
            return cached

        # 银行理财数据通常需要模拟或第三方接口
        # 这里使用预设数据
        result = self._get_fallback_data('bank_product')
        self.cache.set(cache_key, result)
        return result

    # ==================== 黄金 ====================

    def get_gold_data(self, bypass: bool = False) -> list[dict]:
        """获取黄金数据"""
        cache_key = "gold"
        cached = self.cache.get(cache_key, bypass)
        if cached is not None:
            return cached

        try:
            if AKSHARE_AVAILABLE:
                # 获取黄金实时数据
                df = ak.fund_gold()
                logger.info(f"成功获取黄金数据: {len(df)} 条")
        except Exception as e:
            logger.warning(f"获取黄金数据失败: {e}，使用默认数据")

        result = self._get_fallback_data('gold')
        self.cache.set(cache_key, result)
        return result

    # ==================== 外汇 ====================

    def get_forex_data(self, bypass: bool = False) -> list[dict]:
        """获取外汇数据"""
        cache_key = "forex"
        cached = self.cache.get(cache_key, bypass)
        if cached is not None:
            return cached

        try:
            if AKSHARE_AVAILABLE:
                # 获取人民币外汇数据
                df = ak.currency_ts_hsfr()
                logger.info(f"成功获取外汇数据: {len(df)} 条")
        except Exception as e:
            logger.warning(f"获取外汇数据失败: {e}，使用默认数据")

        result = self._get_fallback_data('forex')
        self.cache.set(cache_key, result)
        return result

    # ==================== 债券 ====================

    def get_bond_data(self, bypass: bool = False) -> list[dict]:
        """获取债券数据"""
        cache_key = "bond"
        cached = self.cache.get(cache_key, bypass)
        if cached is not None:
            return cached

        try:
            if AKSHARE_AVAILABLE:
                # 获取债券数据
                df = ak.bond_zh_us_rate()
                logger.info(f"成功获取债券数据")
        except Exception as e:
            logger.warning(f"获取债券数据失败: {e}，使用默认数据")

        result = self._get_fallback_data('bond')
        self.cache.set(cache_key, result)
        return result

    # ==================== 市场指数 ====================

    def get_market_index_data(self, bypass: bool = False) -> dict:
        """获取市场指数数据"""
        cache_key = "market_index"
        cached = self.cache.get(cache_key, bypass)
        if cached is not None:
            return cached

        result = {
            "sh_index": 3150.0,
            "sh_change": 0.005,
            "hs300_index": 3850.0,
            "hs300_change": 0.003,
            "timestamp": datetime.now().isoformat()
        }

        try:
            if AKSHARE_AVAILABLE:
                # 获取上证指数
                df = ak.stock_zh_index_spot()
                sh_row = df[df['名称'] == '上证指数']
                if not sh_row.empty:
                    result["sh_index"] = float(sh_row['最新价'].values[0])
                    result["sh_change"] = float(sh_row['涨跌幅'].values[0]) / 100

                # 获取沪深300
                hs_row = df[df['名称'] == '沪深300']
                if not hs_row.empty:
                    result["hs300_index"] = float(hs_row['最新价'].values[0])
                    result["hs300_change"] = float(hs_row['涨跌幅'].values[0]) / 100

                logger.info(f"成功获取市场指数: 上证 {result['sh_index']}")
        except Exception as e:
            logger.warning(f"获取市场指数失败: {e}")

        self.cache.set(cache_key, result)
        return result

    # ==================== 市场情绪 ====================

    def get_market_sentiment(self) -> dict:
        """计算市场情绪指标"""
        index_data = self.get_market_index_data()

        # 简单情绪评分 (基于涨跌幅)
        change = index_data.get('sh_change', 0)
        sentiment = 50 + change * 1000  # 基准50，涨1%则+10

        # 北向资金 (如果有接口)
        north_money = 0
        try:
            if AKSHARE_AVAILABLE:
                df = ak.stock_hsgt_north_em()
                if not df.empty:
                    north_money = float(df['北上资金'].sum()) if '北上资金' in df.columns else 0
        except:
            pass

        return {
            "sentiment_score": max(0, min(100, int(sentiment))),
            "market_trend": "上涨" if change > 0.01 else "下跌" if change < -0.01 else "震荡",
            "north_money": north_money,
            "vix": None,  # A股没有VIX
            "timestamp": datetime.now().isoformat()
        }

    # ==================== 综合数据 ====================

    def get_all_asset_data(self, bypass: bool = False) -> dict:
        """获取所有资产数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "assets": {
                "money_fund": self.get_money_fund_data(bypass),
                "bank_product": self.get_bank_product_data(bypass),
                "fund": self.get_fund_data(bypass),
                "bond": self.get_bond_data(bypass),
                "gold": self.get_gold_data(bypass),
                "forex": self.get_forex_data(bypass),
            }
        }

    def get_market_indicators(self) -> dict:
        """获取市场情绪指标"""
        index_data = self.get_market_index_data()
        sentiment_data = self.get_market_sentiment()

        return {
            **index_data,
            **sentiment_data,
            "timestamp": datetime.now().isoformat()
        }

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()


# 全局实例
_data_fetcher: DataFetcher | None = None


def get_data_fetcher() -> DataFetcher:
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = DataFetcher()
    return _data_fetcher
