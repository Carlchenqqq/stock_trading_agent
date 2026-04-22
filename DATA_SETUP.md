# 真实数据接入指南

## 概述

股票交易Agent现在支持两种数据模式：
- **模拟数据**（默认）：用于测试和演示，使用 `main.py`
- **真实数据**：通过AKShare免费数据源获取实时市场数据，使用 `hybrid_agent.py`

## 文件说明

| 文件 | 用途 |
|------|------|
| `agent.py` | 核心Agent类（模拟数据版） |
| `main.py` | 演示程序入口（模拟数据） |
| `hybrid_agent.py` | 混合模式Agent（真实数据版，使用AKShare） |
| `real_data_agent.py` | 纯真实数据Agent（使用NeoData API） |
| `data_adapter.py` | NeoData API数据适配器 |
| `akshare_adapter.py` | AKShare免费数据适配器 |
| `trading_strategies.py` | 交易策略模块 |
| `market_analyzer.py` | 市场分析模块 |
| `models.py` | 统一数据模型层 |

## 快速开始

### 1. 使用模拟数据（无需配置）

```bash
cd stock_trading_agent
python main.py
```

或运行特定演示模块：

```bash
python main.py --demo market    # 市场分析演示
python main.py --demo signals   # 交易信号演示
python main.py --demo position  # 仓位管理演示
python main.py --demo risk      # 风险管理演示
python main.py --demo trapped   # 被套应对演示
python main.py --demo plan      # 每日计划演示
```

### 2. 使用真实数据（AKShare免费数据源）

#### 步骤1：安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：
- `akshare>=1.12.0` - 免费A股数据源
- `pandas>=1.5.0` - 数据处理
- `requests>=2.28.0` - HTTP请求

#### 步骤2：运行Agent

```bash
cd stock_trading_agent
python hybrid_agent.py
```

这将：
1. 使用AKShare获取实时市场数据
2. 分析16只自选股（可修改代码自定义）
3. 生成每日交易报告
4. 运行4种策略分析（动量、均值回归、趋势跟踪、波动率突破）

输出示例：

```
======================================================================
每日交易报告 - 2026-04-21
======================================================================

> 市场情绪
--------------------------------------------------
  上证指数: 3250.00 (+1.20%)
  涨停家数: 45
  跌停家数: 12

> 自选股分析
--------------------------------------------------

  000001.SZ - 平安银行
    当前价: 12.50元
    涨跌幅: +2.50%
    成交额: 50000万
...
```

### 3. 使用NeoData API（需要Token）

#### 步骤1：获取NeoData Token

NeoData token需要通过腾讯云代理服务获取。

#### 步骤2：保存Token

```bash
mkdir -p ~/.workbuddy
echo "YOUR_JWT_TOKEN" > ~/.workbuddy/.neodata_token
chmod 600 ~/.workbuddy/.neodata_token
```

#### 步骤3：运行Agent

```bash
python real_data_agent.py
```

## API支持的数据

### 股票数据
- 日线行情（开盘价、收盘价、最高价、最低价、成交量）
- 实时价格、涨跌幅
- 成交额
- 前收盘价

### 市场数据
- 涨停/跌停家数
- 上证指数、深证成指
- 沪深港通资金流向
- 市场涨跌家数统计

### 指数数据
- 上证指数（000001.SH）
- 深证成指（399001.SZ）
- 创业板指数等

## 在代码中使用

### 使用模拟数据

```python
from agent import StockTradingAgent, MarketSentiment

# 创建Agent
agent = StockTradingAgent(initial_capital=100000)

# 添加自选股
agent.add_to_watch_list("000001.SZ")  # 平安银行
agent.add_to_watch_list("600519.SH")  # 贵州茅台

# 模拟市场数据
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
sentiment = MarketSentiment.NEUTRAL
plan = agent.run_daily_analysis(market_data, sentiment)
print(plan)
```

### 使用真实数据（AKShare）

```python
from hybrid_agent import TradingAgent

# 创建Agent
agent = TradingAgent()

# 添加自选股
agent.add_to_watchlist("000001.SZ", "平安银行")
agent.add_to_watchlist("600519.SH", "贵州茅台")

# 生成每日报告
agent.print_daily_report()

# 运行策略分析
agent.run_strategy_analysis()
```

### 使用真实数据（NeoData）

```python
from real_data_agent import RealDataTradingAgent

# 创建Agent
agent = RealDataTradingAgent()

# 添加自选股
agent.add_to_watchlist("000001.SZ")
agent.add_to_watchlist("600519.SH")

# 生成每日计划
plan = agent.generate_daily_plan()
print(plan)
```

## 数据排序约定

所有 `get_stock_daily` 方法返回的数据均按 **newest first**（最新在前）排序：

```python
data_list = adapter.get_stock_daily("000001.SZ", limit=5)
# data_list[0] 是最新一天的数据
# data_list[-1] 是最旧一天的数据
```

## 扩展数据源

如需接入更多数据源（如Tushare、Wind等），可以：

1. 创建新的数据适配器类，实现统一接口
2. 使用 `models.py` 中定义的 `StockData` 数据类
3. 确保返回数据按 newest first 排序

示例：

```python
from models import StockData

class CustomAdapter:
    def get_stock_daily(self, ts_code: str, limit: int = 30) -> List[StockData]:
        # 获取数据
        raw_data = self._fetch_from_api(ts_code, limit)

        # 转换为 StockData
        result = []
        for item in raw_data:
            result.append(StockData(
                ts_code=item['code'],
                name=item['name'],
                open=item['open'],
                high=item['high'],
                low=item['low'],
                close=item['close'],
                pre_close=item['pre_close'],
                change=item['change'],
                pct_chg=item['pct_chg'],
                vol=item['volume'],
                amount=item['amount'],
                date=item['date']
            ))

        # 确保最新在前
        result.reverse()
        return result
```

## 注意事项

1. **真实数据有延迟**：免费API通常有15-30分钟延迟
2. **调用频率限制**：注意API的调用频率限制，避免被封禁
3. **数据准确性**：生产环境使用前请验证数据准确性
4. **仅供学习研究**：本Agent仅供学习研究，不构成投资建议
5. **交易费用**：模拟数据模式已包含A股交易费用计算（佣金万2.5、印花税千1、过户费万0.1）

## 故障排查

### 问题：提示"未找到token"（NeoData）

**解决方案**：
1. 确认已保存token到 `~/.workbuddy/.neodata_token`
2. 检查文件权限：`ls -la ~/.workbuddy/.neodata_token`
3. 使用AKShare数据源（无需token）：`python hybrid_agent.py`

### 问题：AKShare API调用失败

**解决方案**：
1. 检查网络连接
2. 确认已安装依赖：`pip install -r requirements.txt`
3. 查看日志了解详细错误信息
4. AKShare可能需要绕过代理，代码已自动处理

### 问题：数据返回为空

**解决方案**：
1. 检查股票代码格式（如 000001.SZ）
2. 确认交易日（非交易日可能无数据）
3. 尝试获取历史数据而非当日数据
4. AKShare数据可能需要调整 `start_date` 参数

### 问题：涨跌幅显示异常（如全部+1.01%）

**解决方案**：
此问题已在最新版本中修复。如果仍遇到：
1. 确保使用最新代码
2. 检查 `get_stock_daily` 返回的 `pre_close` 字段是否正确
3. 查看日志中的数据解析警告

## 项目架构优化说明

本次优化对项目架构进行了全面重构：

1. **统一数据模型层**：创建 `models.py`，消除各模块中的重复定义
2. **修复数据准确性问题**：修复了 pre_close 估算错误，确保涨跌幅计算准确
3. **消除重复策略实现**：统一使用 `trading_strategies.py` 中的策略逻辑
4. **修复全局污染**：移除 `hybrid_agent.py` 中的环境变量和 Monkey-patching
5. **添加交易费用**：模拟数据模式包含A股标准交易费用计算
6. **性能优化**：使用并行获取数据，向量化操作替代 iterrows
7. **代码质量提升**：统一日志配置，修复裸 except，添加除零保护

详见优化计划文档。
