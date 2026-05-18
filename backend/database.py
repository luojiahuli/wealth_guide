"""
数据库模块 - SQLite 持久化存储
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

DATABASE_PATH = Path(__file__).parent.parent / "data" / "wealth_guide.db"


class Database:
    """SQLite 数据库管理"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATABASE_PATH)
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        """确保数据目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            c = conn.cursor()

            # 资产数据表
            c.execute("""
                CREATE TABLE IF NOT EXISTS asset_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 组合配置表
            c.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_capital REAL NOT NULL,
                    allocation_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    method TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 推荐历史表
            c.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    recommendation_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 市场情绪指标表
            c.execute("""
                CREATE TABLE IF NOT EXISTS market_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    indicators_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 每日净值历史表
            c.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_nav_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    nav REAL NOT NULL,
                    daily_return REAL,
                    total_value REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            c.execute("CREATE INDEX IF NOT EXISTS idx_asset_data_type ON asset_data(asset_type)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_date ON portfolio_history(date)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_nav_history_date ON portfolio_nav_history(date)")

            conn.commit()

    def save_asset_data(self, asset_type: str, data: list[dict]):
        """保存资产数据"""
        timestamp = datetime.now().isoformat()
        data_json = json.dumps(data, ensure_ascii=False)
        
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO asset_data (timestamp, asset_type, data_json)
                VALUES (?, ?, ?)
            """, (timestamp, asset_type, data_json))
            conn.commit()

    def get_latest_asset_data(self, asset_type: str, hours: int = 24) -> Optional[list[dict]]:
        """获取最新的资产数据"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT data_json FROM asset_data
                WHERE asset_type = ? AND timestamp >= ?
                ORDER BY timestamp DESC LIMIT 1
            """, (asset_type, cutoff))
            
            row = c.fetchone()
            if row:
                return json.loads(row["data_json"])
            return None

    def save_portfolio(self, date: str, total_capital: float, 
                      allocation: dict, metrics: dict, method: str = "risk_parity"):
        """保存组合配置"""
        allocation_json = json.dumps(allocation, ensure_ascii=False)
        metrics_json = json.dumps(metrics, ensure_ascii=False)
        
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO portfolio_history 
                (date, total_capital, allocation_json, metrics_json, method)
                VALUES (?, ?, ?, ?, ?)
            """, (date, total_capital, allocation_json, metrics_json, method))
            conn.commit()

    def get_portfolio(self, date: Optional[str] = None) -> Optional[dict]:
        """获取组合配置"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM portfolio_history
                WHERE date = ?
                ORDER BY created_at DESC LIMIT 1
            """, (date,))
            
            row = c.fetchone()
            if row:
                return {
                    "date": row["date"],
                    "total_capital": row["total_capital"],
                    "allocation": json.loads(row["allocation_json"]),
                    "metrics": json.loads(row["metrics_json"]),
                    "method": row["method"]
                }
            return None

    def get_portfolio_history(self, days: int = 30) -> list[dict]:
        """获取组合历史"""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM portfolio_history
                ORDER BY date DESC LIMIT ?
            """, (days,))
            
            return [
                {
                    "date": row["date"],
                    "total_capital": row["total_capital"],
                    "allocation": json.loads(row["allocation_json"]),
                    "metrics": json.loads(row["metrics_json"]),
                    "method": row["method"]
                }
                for row in c.fetchall()
            ]

    def save_recommendation(self, recommendation: dict):
        """保存推荐"""
        date = recommendation.get("date", datetime.now().strftime("%Y-%m-%d"))
        rec_json = json.dumps(recommendation, ensure_ascii=False)
        
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO recommendation_history (date, recommendation_json)
                VALUES (?, ?)
            """, (date, rec_json))
            conn.commit()

    def get_recommendation(self, date: Optional[str] = None) -> Optional[dict]:
        """获取推荐"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT recommendation_json FROM recommendation_history
                WHERE date = ?
            """, (date,))
            
            row = c.fetchone()
            if row:
                return json.loads(row["recommendation_json"])
            return None

    def save_market_indicators(self, indicators: dict):
        """保存市场情绪指标"""
        timestamp = datetime.now().isoformat()
        indicators_json = json.dumps(indicators, ensure_ascii=False)
        
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO market_indicators (timestamp, indicators_json)
                VALUES (?, ?)
            """, (timestamp, indicators_json))
            conn.commit()

    def get_market_indicators(self, hours: int = 24) -> Optional[dict]:
        """获取市场情绪指标"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT indicators_json FROM market_indicators
                WHERE timestamp >= ?
                ORDER BY timestamp DESC LIMIT 1
            """, (cutoff,))
            
            row = c.fetchone()
            if row:
                return json.loads(row["indicators_json"])
            return None

    def save_portfolio_nav(self, date: str, nav: float, daily_return: float, 
                          total_value: float):
        """保存组合净值"""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO portfolio_nav_history 
                (date, nav, daily_return, total_value)
                VALUES (?, ?, ?, ?)
            """, (date, nav, daily_return, total_value))
            conn.commit()

    def get_portfolio_nav_history(self, days: int = 30) -> pd.DataFrame:
        """获取组合净值历史"""
        with self._get_connection() as conn:
            df = pd.read_sql_query("""
                SELECT date, nav, daily_return, total_value
                FROM portfolio_nav_history
                ORDER BY date DESC
                LIMIT ?
            """, conn, params=(days,))
            return df

    def calculate_performance(self, days: int = 30) -> dict:
        """计算组合表现"""
        df = self.get_portfolio_nav_history(days)
        
        if df.empty:
            return {
                "total_return": 0,
                "annualized_return": 0,
                "max_drawdown": 0,
                "volatility": 0
            }
        
        df = df.sort_values("date")
        
        total_return = (df["nav"].iloc[-1] / df["nav"].iloc[0] - 1) if len(df) > 1 else 0
        
        # 年化收益
        n_years = len(df) / 252
        annualized = (1 + total_return) ** (1/n_years) - 1 if n_years > 0 else 0
        
        # 最大回撤
        cummax = df["nav"].cummax()
        drawdown = (df["nav"] - cummax) / cummax
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # 波动率
        returns = df["daily_return"].dropna()
        volatility = returns.std() * (252 ** 0.5) if len(returns) > 1 else 0
        
        return {
            "total_return": total_return,
            "annualized_return": annualized,
            "max_drawdown": max_drawdown,
            "volatility": volatility,
            "days": len(df)
        }


# 全局实例
_database: Database | None = None


def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database()
    return _database
