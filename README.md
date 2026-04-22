# 股票交易Agent - 基于股票高手交易大模型

## 项目概述

本项目是一个基于股票高手交易大模型的智能股票交易Agent系统，从腾讯ima知识库中的"股票交易高手大模型"知识库提取核心交易理念和策略，构建完整的交易体系。

### 核心理念

> **你来股市不是为了娱乐，而是稳定盈利。**

### 交易原则

1. **不预测，只应对** - 跟随市场，不主观臆断
2. **截断亏损，让利润奔跑** - 严格止损，放大盈利
3. **仓位管理是生存的关键** - 控制风险，保住本金

## 系统架构

```
stock_trading_agent/
├── agent.py              # 核心Agent类
├── trading_strategies.py # 交易策略模块（7种武器模式）
├── market_analyzer.py    # 市场分析模块
├── main.py              # 主程序入口
└── README.md            # 项目说明
```

## 核心功能

### 1. 交易体系框架

- **交易模式识别**：7种短线交易武器模式
- **仓位管理**：基于风险管理的动态仓位计算
- **风险控制**：多层次止损止盈机制
- **被套应对**：系统化解套策略

### 2. 7种短线交易武器模式

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| 首板模式 | 首次涨停，封板坚决 | 新热点启动 |
| 连板模式 | 连续2+个涨停 | 龙头接力 |
| 反包模式 | 断板后强势反包 | 资金回流 |
| 低吸模式 | 强势股回调5-15% | 趋势延续 |
| 打板模式 | 涨停瞬间买入 | 确定性追板 |
| 尾盘模式 | 尾盘30分钟异动 | 次日溢价 |
| 竞价模式 | 集合竞价抢筹 | 开盘强势 |

### 3. 仓位管理策略

- **单笔风险限制**：不超过总资金的2%
- **市场环境调整**：
  - 极度恐慌：80%仓位
  - 恐慌：60%仓位
  - 中性：50%仓位
  - 贪婪：30%仓位
  - 极度贪婪：10%仓位

### 4. 风险管理

- **止损设置**：
  - 短线：-5%
  - 波段：-8%
  - 持仓：-10%
- **移动止损**：从最高点回落10%触发
- **组合风险**：集中度、最大回撤监控

### 5. 市场分析

- **情绪分析**：恐慌贪婪指数
- **阶段判断**：底部/上涨/顶部/下跌/震荡
- **板块轮动**：热点识别、资金流向
- **资金分析**：北向资金、主力资金

## 快速开始

### 安装依赖

```bash
# 本项目使用Python标准库，无需额外安装
python >= 3.7
```

### 运行演示

```bash
# 运行所有演示
python main.py --demo all

# 运行特定模块演示
python main.py --demo market    # 市场分析
python main.py --demo signals   # 交易信号
python main.py --demo position  # 仓位管理
python main.py --demo risk      # 风险管理
python main.py --demo trapped   # 被套应对
python main.py --demo plan      # 每日计划
```

### 使用Agent

```python
from agent import StockTradingAgent, MarketSentiment

# 初始化Agent
agent = StockTradingAgent(initial_capital=100000)

# 添加自选股
agent.add_to_watch_list("000001.SZ")
agent.add_to_watch_list("000002.SZ")

# 准备市场数据
market_data = {
    "000001.SZ": {
        "name": "平安银行",
        "current_price": 12.50,
        "is_limit_up": True,
        "limit_up_days": 1,
        "trend": "strong"
    }
}

# 运行每日分析
plan = agent.run_daily_analysis(market_data, MarketSentiment.NEUTRAL)
print(plan)
```

## API文档

### StockTradingAgent

主Agent类，整合所有功能模块。

```python
class StockTradingAgent:
    def __init__(self, initial_capital: float = 100000)
    def add_to_watch_list(self, stock_code: str)
    def analyze_stock(self, stock_code: str, stock_data: Dict) -> Dict
    def execute_trade(self, stock_code: str, action: str, price: float, quantity: int) -> Dict
    def get_portfolio_summary(self) -> Dict
    def run_daily_analysis(self, market_data: Dict, market_sentiment: MarketSentiment) -> Dict
```

### TradingSystem

交易体系核心类。

```python
class TradingSystem:
    def calculate_position_size(self, stock_code: str, entry_price: float, stop_loss: float, risk_pct: float = 0.02) -> int
    def get_market_position_limit(self, sentiment: MarketSentiment) -> float
    def analyze_short_term_patterns(self, stock_data: Dict) -> List[Dict]
    def generate_trade_signal(self, stock_code: str, stock_data: Dict, market_sentiment: MarketSentiment) -> Optional[TradeSignal]
    def generate_daily_plan(self, watch_list: List[str], market_sentiment: MarketSentiment) -> Dict
```

### MarketAnalyzer

市场分析器。

```python
class MarketAnalyzer:
    def comprehensive_analysis(self, market_data: Dict, sector_data: List[Dict], flow_data: Dict) -> MarketContext
    def generate_daily_market_report(self, market_data: Dict, sector_data: List[Dict], flow_data: Dict) -> Dict
```

## 交易策略详解

### 首板模式

**特征**：
- 当日首次涨停
- 封板坚决（封单质量>80%）
- 成交量适中（量比1.5-5）

**买点**：次日开盘观察，强势可追
**止损**：-5%
**止盈**：+15%

### 连板模式

**特征**：
- 连续2个及以上涨停
- 市场龙头或板块龙头
- 换手充分

**买点**：分歧转一致时
**止损**：断板即走
**止盈**：+20%

### 低吸模式

**特征**：
- 强势股回调5-15%
- 缩量回调
- 未破关键支撑

**买点**：缩量企稳时
**止损**：跌破支撑位
**止盈**：+10%

## 风险管理规则

### 止损原则

1. **短线交易**：-5%止损
2. **波段交易**：-8%止损
3. **持仓交易**：-10%止损

### 被套应对

| 浮亏程度 | 状态 | 应对策略 |
|---------|------|----------|
| < 3% | 轻度浮亏 | 观察等待 |
| 3-7% | 中度浮亏 | 减仓或止损 |
| 7-15% | 深度套牢 | 制定解套计划 |
| > 15% | 严重套牢 | 果断止损 |

## 免责声明

**本系统仅供学习和研究使用，不构成任何投资建议。**

**股市有风险，投资需谨慎！**

使用本系统进行交易决策前，请充分了解相关风险，并根据自身情况做出独立判断。

## 知识库来源

本项目交易策略基于腾讯ima知识库 **"股票交易高手大模型"** 的核心内容构建，包含：
- 交易体系框架
- 稳定盈利训练手册
- 7种短线交易武器模式
- 仓位管理策略
- 被套应对方法
- 交易纪律与心态

## 许可证

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
