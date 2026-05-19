# 每日理财指南系统 - 项目规格说明书 v2.0

## 项目概述

- **项目名称**: Wealth Guide (每日理财指南)
- **资金规模**: 500万人民币
- **核心功能**: 每日自动抓取各类投资产品数据，通过量化模型计算最优资产配置，推送个性化理财建议到飞书
- **目标用户**: 高净值个人投资者，追求稳健增值
- **版本**: v2.0 (2026-05-19)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Wealth Guide v2.0                            │
├─────────────────────────────────────────────────────────────────────┤
│  数据层 (Data Layer)                                                  │
│  ├── akshare 实时行情 (基金、黄金、外汇、指数)                         │
│  ├── 银行理财数据 (预设 + 预期收益)                                   │
│  ├── 债券数据 (国债、企业债收益率)                                     │
│  └── 数据缓存 (5分钟 TTL)                                            │
├─────────────────────────────────────────────────────────────────────┤
│  优化层 (Optimization Layer)                                          │
│  ├── Modern Portfolio Theory (MPT)                                   │
│  ├── Risk Parity (风险平价)                                          │
│  ├── Black-Litterman Model                                           │
│  └── CVXPY 约束优化                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  分析层 (Analytics Layer)                                             │
│  ├── 回测引擎 (历史模拟)                                              │
│  ├── 收益追踪 (每日净值记录)                                          │
│  ├── 风险预警 (VaR/波动率监控)                                        │
│  └── 组合分析 (归因、风险分解)                                        │
├─────────────────────────────────────────────────────────────────────┤
│  应用层 (Application Layer)                                          │
│  ├── FastAPI 后端 (API 服务)                                          │
│  ├── SQLite 数据库 (历史数据)                                         │
│  └── HTML5 前端 (现代化 Dashboard)                                    │
├─────────────────────────────────────────────────────────────────────┤
│  推送层 (Notification Layer)                                          │
│  ├── 飞书卡片消息 (富文本日报)                                        │
│  ├── 风险预警推送                                                     │
│  └── 定时推送 (每日 09:00)                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 资产分类与配置约束

### 资产类别

| 类别 | 子类 | 预期年化收益 | 风险等级 | 流动性 |
|------|------|--------------|----------|--------|
| 货币基金 | 余额宝、理财通、朝朝宝 | 1.5-2.5% | 极低 | T+0 |
| 银行理财 | 短期(3月)、中期(6月)、长期(1年) | 2.5-4.5% | 低 | T+0~T+1 |
| 债券 | 国债、企债、信用债 | 2.5-5.5% | 中低 | T+1 |
| 公募基金 | 股票型、混合型、债券型、指数型 | -20%~+30% | 中高 | T+2 |
| 黄金/商品 | 黄金ETF、大宗商品 | -10%~+20% | 中高 | T+1 |
| 外汇 | 美元、欧元、英镑、港币 | 汇率波动 | 中 | T+1 |

### 目标配置 (v2.0 优化)

- **货币基金**: 20% (100万) - 高流动性
- **银行理财**: 35% (175万) - 稳定收益
- **债券**: 15% (75万) - 中低风险
- **公募基金**: 20% (100万) - 权益类
- **黄金**: 5% (25万) - 避险
- **外汇**: 5% (25万) - 分散

### 配置约束

- **流动性要求**: ≥20% (100万) 放置于高流动性产品
- **固定收益**: 30-60% (150-300万) 债券+银行理财
- **权益类**: 20-50% (100-250万) 公募基金
- **另类投资**: 0-15% (0-75万) 黄金+外汇
- **再平衡阈值**: ±5% 漂移时触发调仓

---

## 功能模块

### 1. 数据层 (data_fetcher.py)

```python
class DataFetcher:
    - get_money_fund_data()      # 货币基金
    - get_bank_product_data()    # 银行理财
    - get_fund_data()            # 公募基金
    - get_bond_data()            # 债券
    - get_gold_data()            # 黄金
    - get_forex_data()           # 外汇
    - get_market_index_data()    # 市场指数
    - get_market_sentiment()     # 市场情绪
    - get_all_asset_data()       # 综合数据
```

**数据源**:
- akshare (真实行情，可选)
- Fallback 默认数据 (网络失败时)

### 2. 优化层 (optimizer.py)

```python
class PortfolioOptimizer:
    - optimize_risk_parity()       # 风险平价
    - optimize_max_sharpe()        # 最大夏普
    - optimize_mpt()               # 现代组合理论
    - optimize_target_allocation() # 目标配置
    - calculate_portfolio_metrics() # 指标计算
```

### 3. 分析层

#### 回测引擎 (backtest.py)
```python
class BacktestEngine:
    - run_backtest(allocation, days=252)  # 运行回测
    - compare_strategies(a, b)             # 策略对比
```

#### 收益追踪 (tracker.py)
```python
class PerformanceTracker:
    - record_daily_value(date, value, allocation)  # 记录净值
    - calculate_returns(days=30)                    # 收益统计
    - get_history(days=30)                          # 历史记录
```

#### 风险预警 (risk_alert.py)
```python
class RiskAlertManager:
    - check_portfolio_risk(metrics, allocation)  # 风险检查
    - get_active_alerts()                        # 活跃预警
```

#### 组合分析 (analytics.py)
```python
class PortfolioAnalytics:
    - calculate_risk_contribution()  # 风险分解
    - calculate_return_attribution()  # 收益归因
    - generate_analysis_report()      # 分析报告
```

### 4. 飞书推送 (feishu_pusher.py)

```python
class FeishuPusher:
    - push_text(text)              # 文本消息
    - push_rich_report()           # 富文本日报
    - push_card_report()           # 卡片日报 (推荐)
    - push_risk_alert(alert)       # 风险预警
    - push_daily_report()          # 推送入口
```

---

## API 接口

### GET /api/portfolio
返回当前最优投资组合

### GET /api/recommendations
返回每日推荐 (操作建议 + 精选推荐 + 市场展望)

### GET /api/assets/{type}
返回指定类型资产数据

### GET /api/market
返回市场情绪指标

### POST /api/refresh
强制刷新所有数据

### POST /api/push
推送当前推荐到飞书

### GET /api/history
获取组合历史表现

### GET /api/backtest
运行回测

### GET /api/analytics
获取组合分析报告

### GET /api/alerts
获取风险预警

---

## 前端界面 (v2.0)

### 设计风格
- 深色主题 + 玻璃态效果 (Glassmorphism)
- 主色调: 深蓝 #0a0f1c, 强调色 #00d4aa
- 字体: Inter + JetBrains Mono (数字)

### 页面布局
```
┌──────────────────────────────────────────────────────────────┐
│ 🌙 Wealth Guide         [市场状态] [更新时间] [刷新] [推送]  │
├──────────────────────────────────────────────────────────────┤
│  总资产 ¥5000万   预期年化 4.05%   夏普比率 1.42   VaR 1.5%  │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────────────────────┐│
│  │   资产配置图     │  │         收益走势图                 ││
│  │   (环形图)      │  │       (折线图)                   ││
│  └──────────────────┘  └──────────────────────────────────┘│
│                                                              │
│  ┌─ 风险 ─┐ ┌─ 波动率 ─┐ ┌─ 回撤 ─┐ ┌─ 流动性 ─┐          │
│  │  中等  │ │   8.2%   │ │ 12%   │ │   优    │          │
│  └────────┘ └──────────┘ └────────┘ └─────────┘          │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐│
│  │   今日操作建议    │  │        精选推荐 TOP 5             ││
│  │   买入基金 50万   │  │   1. 易方达蓝筹 +12%              ││
│  └──────────────────┘  └──────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │   资产明细表格                                           ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │   市场情绪仪表盘                                         ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 组件
- 数字滚动动画 (countUp)
- 环形图绘制动画
- 仪表盘风险可视化
- 卡片悬浮发光效果
- Toast 通知

---

## 飞书推送格式

### 卡片日报
```
┌─────────────────────────────────────┐
│ 📊 每日理财指南 | 2026年5月19日      │
├─────────────────────────────────────┤
│  💰 总资产    📈 预期收益   ⚖️ 夏普   │
│  5000万       4.05%        1.42    │
├─────────────────────────────────────┤
│  📈 资产配置                        │
│  💰货币  🏦银行 📄债券 📈基金 🥇黄金 │
│  20%     35%    15%    20%    5%   │
├─────────────────────────────────────┤
│  💡 今日操作建议                     │
│  📈 买入 公募基金 ¥50万              │
├─────────────────────────────────────┤
│  ⚠️ 本建议仅供参考，投资有风险        │
└─────────────────────────────────────┘
```

---

## 文件结构

```
wealth_guide/
├── SPEC.md
├── README.md
├── config.yaml
├── requirements.txt
├── .env.example
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口 + WebSocket
│   ├── data_fetcher.py      # 数据抓取 (akshare + fallback)
│   ├── optimizer.py         # 组合优化
│   ├── recommender.py       # 推荐引擎
│   ├── models.py            # Pydantic 模型
│   ├── database.py          # SQLite 数据库
│   ├── feishu_pusher.py     # 飞书推送
│   ├── analytics.py         # 组合分析
│   ├── backtest.py          # 回测引擎
│   ├── tracker.py           # 收益追踪
│   └── risk_alert.py        # 风险预警
├── frontend/
│   └── index.html           # Dashboard 页面 (v2.0)
├── scripts/
│   └── daily_push.py        # 每日推送脚本
└── data/
    └── wealth_guide.db      # SQLite 数据库
```

---

## 环境变量

```bash
# .env 文件
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_CHAT_ID=oc_xxx

# 可选
AKSHARE_API_KEY=xxx
LOG_LEVEL=INFO
```

---

## 运行方式

### 1. 安装依赖
```bash
cd ~/workspace/wealth_guide
pip install -r requirements.txt
```

### 2. 配置飞书
```bash
cp .env.example .env
# 编辑 .env 添加 FEISHU_WEBHOOK_URL
```

### 3. 启动后端
```bash
cd ~/workspace/wealth_guide
uvicorn backend.main:app --reload --port 8000
```

### 4. 打开前端
浏览器打开 `frontend/index.html` 或 `http://localhost:8000`

### 5. 配置每日推送
```bash
# 添加到 crontab
crontab -e
# 0 9 * * 1-5 cd ~/workspace/wealth_guide && python scripts/daily_push.py
```

---

## 技术栈

- **后端**: Python 3.11+, FastAPI, Uvicorn
- **数据**: akshare (可选), pandas, numpy
- **优化**: cvxpy, scipy
- **数据库**: SQLite + aiosqlite
- **图表**: Chart.js 4.x (前端)
- **推送**: 飞书 Webhook API
- **HTTP**: httpx (异步)

---

## 开发进度

- [x] SPEC.md v2.0 规划
- [x] 前端 UI v2.0 (玻璃态风格)
- [x] 数据层重构 (akshare + fallback)
- [x] 回测引擎
- [x] 收益追踪
- [x] 风险预警
- [x] 组合分析
- [x] 飞书卡片推送
- [x] 每日推送脚本
- [ ] WebSocket 实时推送
- [ ] Docker 部署
- [ ] 测试验证

---

## License

MIT
