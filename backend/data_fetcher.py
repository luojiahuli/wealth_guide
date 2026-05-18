"""
数据抓取模块 - 从各公开数据源获取投资产品数据
数据源: 天天基金(公募基金)、新浪(债券/外汇)、融360(银行理财)、exchangerate-api(外汇)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


class DataFetcher:
    """统一数据抓取器"""

    def __init__(self):
        self.session = None
        self.cache = {}
        self.cache_ttl = 3600  # 缓存1小时

    async def get_session(self) -> httpx.AsyncClient:
        if self.session is None:
            self.session = httpx.AsyncClient(timeout=30.0)
        return self.session

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self.cache:
            return False
        _, timestamp = self.cache[key]
        return (datetime.now() - timestamp).total_seconds() < self.cache_ttl

    def _set_cache(self, key: str, data: Any):
        self.cache[key] = (data, datetime.now())

    # ==================== 货币基金 ====================

    async def get_money_fund_data(self) -> list[dict]:
        """
        获取货币基金数据
        数据来源: 天天基金网货币基金列表
        """
        cache_key = "money_fund"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        try:
            # 使用 akshare 获取货币基金数据
            import akshare as ak
            
            # 获取货币基金列表
            mf_df = ak.fund_money_fund_info_em()
            
            # 取前20个主要货币基金
            top_funds = mf_df.head(20)
            
            result = []
            for _, row in top_funds.iterrows():
                result.append({
                    "name": str(row.get("基金简称", "")),
                    "code": str(row.get("基金代码", "")),
                    "nav": float(row.get("万份收益", 1.0)),
                    "annual_return": float(row.get("7日年化", 2.0)),
                    "type": "货币基金",
                    "liquidity": "T+0",
                    "risk_level": "极低",
                    "min_amount": 1,
                    "provider": "天天基金"
                })
            
            # 如果akshare失败，使用默认数据
            if not result:
                result = self._get_default_money_funds()
                
        except Exception as e:
            logger.warning(f"获取货币基金数据失败: {e}, 使用默认数据")
            result = self._get_default_money_funds()

        self._set_cache(cache_key, result)
        return result

    def _get_default_money_funds(self) -> list[dict]:
        """默认货币基金数据(备选)"""
        return [
            {"name": "余额宝", "code": "000198", "nav": 1.0, "annual_return": 1.98, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "天弘基金"},
            {"name": "理财通-易方达", "code": "000009", "nav": 1.0, "annual_return": 2.05, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "易方达"},
            {"name": "建信现金添利", "code": "002848", "nav": 1.0, "annual_return": 2.10, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "建信基金"},
            {"name": "兴全货币", "code": "340005", "nav": 1.0, "annual_return": 2.15, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "兴全基金"},
            {"name": "汇添富现金宝", "code": "000600", "nav": 1.0, "annual_return": 2.08, "type": "货币基金", "liquidity": "T+0", "risk_level": "极低", "min_amount": 0.01, "provider": "汇添富"},
        ]

    # ==================== 银行理财 ====================

    async def get_bank_product_data(self) -> list[dict]:
        """
        获取银行理财产品数据
        数据来源: 基于市场平均数据
        """
        cache_key = "bank_product"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        try:
            import akshare as ak
            
            # 尝试获取银行理财数据
            try:
                bf_df = ak.financial_product_issue_em()
                if not bf_df.empty:
                    result = []
                    for _, row in bf_df.head(15).iterrows():
                        result.append({
                            "name": str(row.get("产品名称", "")),
                            "bank": str(row.get("发行银行", "")),
                            "expected_return": float(row.get("预期收益率", 3.5)),
                            "term": str(row.get("投资期限", "3个月")),
                            "type": "银行理财",
                            "liquidity": "T+1",
                            "risk_level": "低",
                            "min_amount": 10000,
                            "provider": row.get("发行银行", "银行")
                        })
                    if result:
                        self._set_cache(cache_key, result)
                        return result
            except:
                pass
        except Exception as e:
            logger.warning(f"获取银行理财数据失败: {e}")

        # 默认银行理财数据
        result = self._get_default_bank_products()
        self._set_cache(cache_key, result)
        return result

    def _get_default_bank_products(self) -> list[dict]:
        """默认银行理财数据"""
        return [
            {"name": "招行聚益生金", "bank": "招商银行", "expected_return": 3.45, "term": "30天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "招商银行"},
            {"name": "工行稳得利", "bank": "工商银行", "expected_return": 3.30, "term": "90天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "工商银行"},
            {"name": "建行乾元", "bank": "建设银行", "expected_return": 3.50, "term": "180天", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "建设银行"},
            {"name": "农行金钥匙", "bank": "农业银行", "expected_return": 3.40, "term": "1年", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "农业银行"},
            {"name": "中行中银理财", "bank": "中国银行", "expected_return": 3.35, "term": "6个月", "type": "银行理财", "liquidity": "T+1", "risk_level": "低", "min_amount": 10000, "provider": "中国银行"},
            {"name": "平安银行天天成长", "bank": "平安银行", "expected_return": 3.60, "term": "T+0", "type": "银行理财T+0", "liquidity": "T+0", "risk_level": "低", "min_amount": 10000, "provider": "平安银行"},
        ]

    # ==================== 公募基金 ====================

    async def get_fund_data(self) -> list[dict]:
        """
        获取公募基金数据
        数据来源: 天天基金网
        """
        cache_key = "fund"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        try:
            import akshare as ak
            
            result = []
            
            # 股票型基金
            try:
                stock_df = ak.fund_individual_basic_info_xq(symbol="普通股票型")
                for _, row in stock_df.head(5).iterrows():
                    result.append({
                        "name": str(row.get("基金名称", "")),
                        "code": str(row.get("基金代码", "")),
                        "type": "股票型",
                        "risk_level": "中高",
                        "nav": float(row.get("最新净值", 1.0)),
                        "annual_return": float(row.get("近1年收益率", 0)) / 100,
                        "min_amount": 100,
                        "provider": "天天基金"
                    })
            except:
                pass
            
            # 混合型基金
            try:
                mix_df = ak.fund_individual_basic_info_xq(symbol="灵活配置型")
                for _, row in mix_df.head(5).iterrows():
                    result.append({
                        "name": str(row.get("基金名称", "")),
                        "code": str(row.get("基金代码", "")),
                        "type": "混合型",
                        "risk_level": "中",
                        "nav": float(row.get("最新净值", 1.0)),
                        "annual_return": float(row.get("近1年收益率", 0)) / 100,
                        "min_amount": 100,
                        "provider": "天天基金"
                    })
            except:
                pass
                
            # 债券型基金
            try:
                bond_fund_df = ak.fund_individual_basic_info_xq(symbol="中长期纯债型")
                for _, row in bond_fund_df.head(5).iterrows():
                    result.append({
                        "name": str(row.get("基金名称", "")),
                        "code": str(row.get("基金代码", "")),
                        "type": "债券型",
                        "risk_level": "中低",
                        "nav": float(row.get("最新净值", 1.0)),
                        "annual_return": float(row.get("近1年收益率", 0)) / 100,
                        "min_amount": 100,
                        "provider": "天天基金"
                    })
            except:
                pass
                
            if not result:
                result = self._get_default_funds()
                
        except Exception as e:
            logger.warning(f"获取基金数据失败: {e}")
            result = self._get_default_funds()

        self._set_cache(cache_key, result)
        return result

    def _get_default_funds(self) -> list[dict]:
        """默认基金数据"""
        return [
            {"name": "易方达蓝筹精选", "code": "005827", "type": "混合型", "risk_level": "中", "nav": 1.85, "annual_return": 0.12, "min_amount": 100, "provider": "易方达基金"},
            {"name": "景顺长城新兴成长", "code": "260108", "type": "混合型", "risk_level": "中", "nav": 1.92, "annual_return": 0.08, "min_amount": 100, "provider": "景顺长城基金"},
            {"name": "兴全趋势投资", "code": "163402", "type": "混合型", "risk_level": "中", "nav": 1.45, "annual_return": 0.10, "min_amount": 100, "provider": "兴全基金"},
            {"name": "广发稳健增长", "code": "270002", "type": "混合型", "risk_level": "中低", "nav": 1.78, "annual_return": 0.06, "min_amount": 100, "provider": "广发基金"},
            {"name": "博时信用债", "code": "050027", "type": "债券型", "risk_level": "中低", "nav": 1.12, "annual_return": 0.04, "min_amount": 100, "provider": "博时基金"},
            {"name": "易方达沪深300ETF", "code": "510310", "type": "指数型", "risk_level": "中", "nav": 2.10, "annual_return": 0.05, "min_amount": 100, "provider": "易方达基金"},
        ]

    # ==================== 债券 ====================

    async def get_bond_data(self) -> list[dict]:
        """
        获取债券数据
        数据来源: 新浪债券、国债收益率曲线
        """
        cache_key = "bond"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        try:
            import akshare as ak
            
            result = []
            
            # 国债收益率
            try:
                treasury_df = ak.bond_zh_us_rate()
                if not treasury_df.empty:
                    result.append({
                        "name": "美国国债收益率",
                        "type": "国债",
                        "risk_level": "中低",
                        "annual_return": float(treasury_df.iloc[0].get("成功率", 0)) / 100 if len(treasury_df) > 0 else 0.04,
                        "term": "10年",
                        "provider": "Sina"
                    })
            except:
                pass
            
            # 中国国债
            try:
                cn_bond_df = ak.bond_zh_cov()
                for _, row in cn_bond_df.head(5).iterrows():
                    result.append({
                        "name": str(row.get("债券名称", "")),
                        "code": str(row.get("债券代码", "")),
                        "type": "国债/企债",
                        "risk_level": "中低",
                        "annual_return": float(row.get("到期收益率", 0)) / 100 if pd.notna(row.get("到期收益率")) else 0.04,
                        "term": str(row.get("剩余期限", "5年")),
                        "provider": "中债估值"
                    })
            except:
                pass
                
            if not result:
                result = self._get_default_bonds()
                
        except Exception as e:
            logger.warning(f"获取债券数据失败: {e}")
            result = self._get_default_bonds()

        self._set_cache(cache_key, result)
        return result

    def _get_default_bonds(self) -> list[dict]:
        """默认债券数据"""
        return [
            {"name": "国债210009", "code": "019547", "type": "国债", "risk_level": "中低", "annual_return": 0.025, "term": "10年", "provider": "中债登"},
            {"name": "国债230023", "code": "230023", "type": "国债", "risk_level": "中低", "annual_return": 0.022, "term": "30年", "provider": "中债登"},
            {"name": "国开债200215", "code": "200215", "type": "政策性银行债", "risk_level": "中低", "annual_return": 0.028, "term": "10年", "provider": "中债登"},
            {"name": "AAA企业债", "code": "AAA", "type": "企业债", "risk_level": "中", "annual_return": 0.035, "term": "5年", "provider": "中债登"},
            {"name": "AA+城投债", "code": "AA+", "type": "城投债", "risk_level": "中", "annual_return": 0.042, "term": "5年", "provider": "中债登"},
        ]

    # ==================== 外汇 ====================

    async def get_forex_data(self) -> list[dict]:
        """
        获取外汇数据
        数据来源: exchangerate-api / Yahoo Finance
        """
        cache_key = "forex"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        result = []
        
        try:
            # 使用 exchangerate-api
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        "https://api.exchangerate-api.com/v4/latest/CNY"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        rates = data.get("rates", {})
                        
                        forex_list = [
                            ("USD", "美元"), ("EUR", "欧元"), ("GBP", "英镑"),
                            ("HKD", "港币"), ("JPY", "日元"), ("AUD", "澳元"),
                            ("CHF", "瑞士法郎"), ("CAD", "加元")
                        ]
                        
                        for code, name in forex_list:
                            if code in rates:
                                rate = rates[code]
                                # 预期收益基于利差和通胀差异估算
                                expected_return = self._estimate_forex_return(code)
                                result.append({
                                    "name": name,
                                    "code": code,
                                    "type": "外汇",
                                    "risk_level": "中",
                                    "rate": rate,
                                    "annual_return": expected_return,
                                    "provider": "exchangerate-api"
                                })
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"获取外汇数据失败: {e}")

        if not result:
            result = self._get_default_forex()

        self._set_cache(cache_key, result)
        return result

    def _estimate_forex_return(self, code: str) -> float:
        """估算外汇预期收益"""
        # 基于购买力平价和利差估算
        estimates = {
            "USD": 0.02,   # 美元相对稳定
            "EUR": 0.01,   # 欧元
            "GBP": 0.00,   # 英镑
            "HKD": 0.00,   # 港币联系汇率
            "JPY": -0.02,  # 日元低息货币
            "AUD": 0.01,   # 澳元
            "CHF": 0.00,   # 瑞士法郎
            "CAD": 0.01,   # 加元
        }
        return estimates.get(code, 0.0)

    def _get_default_forex(self) -> list[dict]:
        """默认外汇数据"""
        return [
            {"name": "美元", "code": "USD", "type": "外汇", "risk_level": "中", "rate": 7.24, "annual_return": 0.02, "provider": "中国人民银行"},
            {"name": "欧元", "code": "EUR", "type": "外汇", "risk_level": "中", "rate": 7.85, "annual_return": 0.01, "provider": "中国人民银行"},
            {"name": "英镑", "code": "GBP", "type": "外汇", "risk_level": "中", "rate": 9.15, "annual_return": 0.00, "provider": "中国人民银行"},
            {"name": "港币", "code": "HKD", "type": "外汇", "risk_level": "低", "rate": 0.93, "annual_return": 0.00, "provider": "中国人民银行"},
        ]

    # ==================== 黄金/大宗商品 ====================

    async def get_gold_data(self) -> list[dict]:
        """
        获取黄金数据
        数据来源: Yahoo Finance / 新浪
        """
        cache_key = "gold"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]

        result = []
        
        try:
            import akshare as ak
            
            # 黄金ETF
            try:
                gold_df = ak.fund_etf_hist_em(symbol="518880")  # 华安黄金ETF
                if not gold_df.empty:
                    latest = gold_df.iloc[-1]
                    price = float(latest.get("收盘", 0))
                    change = float(latest.get("涨跌幅", 0)) / 100
                    result.append({
                        "name": "华安黄金ETF",
                        "code": "518880",
                        "type": "黄金",
                        "risk_level": "中高",
                        "price": price,
                        "annual_return": change,
                        "provider": "上交所"
                    })
            except:
                pass
                
        except Exception as e:
            logger.warning(f"获取黄金数据失败: {e}")

        if not result:
            result = self._get_default_gold()

        self._set_cache(cache_key, result)
        return result

    def _get_default_gold(self) -> list[dict]:
        """默认黄金数据"""
        return [
            {"name": "华安黄金ETF", "code": "518880", "type": "黄金", "risk_level": "中高", "price": 558.50, "annual_return": 0.08, "provider": "上交所"},
            {"name": "博时黄金ETF", "code": "159937", "type": "黄金", "risk_level": "中高", "price": 556.80, "annual_return": 0.08, "provider": "深交所"},
        ]

    # ==================== 综合数据获取 ====================

    async def get_all_asset_data(self) -> dict:
        """获取所有资产类别数据"""
        tasks = {
            "money_fund": self.get_money_fund_data(),
            "bank_product": self.get_bank_product_data(),
            "fund": self.get_fund_data(),
            "bond": self.get_bond_data(),
            "forex": self.get_forex_data(),
            "gold": self.get_gold_data(),
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "assets": {
                key: value if not isinstance(value, Exception) else []
                for key, value in zip(tasks.keys(), results)
            }
        }

    async def get_market_indicators(self) -> dict:
        """
        获取市场情绪指标
        用于辅助投资决策
        """
        indicators = {
            "vix": None,
            "credit_spread": None,
            "market_trend": None,
        }
        
        try:
            import akshare as ak
            
            # 上证指数
            try:
                sh_df = ak.stock_zh_index_spot()
                sh = sh_df[sh_df["名称"] == "上证指数"].iloc[0]
                indicators["sh_index"] = float(sh["最新指数"])
                indicators["sh_change"] = float(sh["涨跌幅"]) / 100
            except:
                pass
                
            # 沪深300
            try:
                hs300_df = ak.stock_zh_index_spot()
                hs300 = hs300_df[hs300_df["名称"] == "沪深300"].iloc[0]
                indicators["hs300_index"] = float(hs300["最新指数"])
                indicators["hs300_change"] = float(hs300["涨跌幅"]) / 100
            except:
                pass
                
        except Exception as e:
            logger.warning(f"获取市场指标失败: {e}")
        
        indicators["timestamp"] = datetime.now().isoformat()
        return indicators

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.aclose()


# 全局实例
_data_fetcher: DataFetcher | None = None


def get_data_fetcher() -> DataFetcher:
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = DataFetcher()
    return _data_fetcher
