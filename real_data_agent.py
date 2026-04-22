"""
真实数据股票交易Agent
使用 neodata-financial-search skill 获取实时数据
"""
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from trading_strategies import ShortTermPatterns, RiskManagement, TrappedPositionStrategy
from market_analyzer import MarketSentimentAnalyzer
import logging

from models import StockData

logger = logging.getLogger(__name__)


class RealDataAdapter:
    """真实数据适配器 - 使用 neodata-financial-search skill"""

    def __init__(self):
        self.skill_path = os.path.expanduser(
            "~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/"
            "skills/neodata-financial-search/scripts/query.py"
        )
        if not os.path.exists(self.skill_path):
            logger.warning(
                f"neodata-financial-search skill 未安装: {self.skill_path}\n"
                "请先安装 finance-data 插件"
            )
        self.python_cmd = "python"

    def _query(self, query_str: str, data_type: str = "api") -> List[Dict]:
        """执行查询"""
        try:
            cmd = [
                self.python_cmd, self.skill_path,
                "--query", query_str,
                "--data-type", data_type
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"查询失败: {result.stderr}")
                return []

            data = json.loads(result.stdout)

            # 解析数据
            if "data" in data:
                api_data = data["data"]
                if "fields" in api_data and "items" in api_data:
                    fields = api_data["fields"]
                    items = api_data["items"]
                    return [dict(zip(fields, item)) for item in items]

            return []
        except Exception as e:
            logger.error(f"查询异常: {e}")
            return []

    def get_stock_daily(self, ts_code: str, limit: int = 5) -> List[StockData]:
        """获取股票日线数据"""
        query = f"{ts_code} 日线行情 最近{limit}天"
        rows = self._query(query, "api")

        result = []
        for row in rows:
            try:
                data = StockData(
                    ts_code=row.get("ts_code", ts_code),
                    name=row.get("name", ""),
                    open=float(row.get("open", 0) or 0),
                    high=float(row.get("high", 0) or 0),
                    low=float(row.get("low", 0) or 0),
                    close=float(row.get("close", 0) or 0),
                    pre_close=float(row.get("pre_close", 0) or 0),
                    change=float(row.get("change", 0) or 0),
                    pct_chg=float(row.get("pct_chg", 0) or 0),
                    vol=float(row.get("vol", 0) or 0),
                    amount=float(row.get("amount", 0) or 0),
                    date=row.get("trade_date", "")
                )
                result.append(data)
            except (ValueError, TypeError) as e:
                logger.warning(f"解析失败: {e}")
                continue

        result.reverse()
        return result

    def get_stock_name(self, ts_code: str) -> str:
        """获取股票名称"""
        query = f"{ts_code} 股票基本信息"
        rows = self._query(query, "api")
        if rows:
            return rows[0].get("name", ts_code)
        return ts_code

    def get_limit_list(self) -> tuple:
        """获取涨跌停数据"""
        query = "今日涨跌停股票"
        rows = self._query(query, "api")

        limit_up = 0
        limit_down = 0

        for row in rows:
            limit_type = row.get("limit", "")
            if limit_type == "U":
                limit_up += 1
            elif limit_type == "D":
                limit_down += 1

        return limit_up, limit_down

    def get_moneyflow_hsgt(self, limit: int = 3) -> List[Dict]:
        """获取沪深港通资金流向"""
        query = f"沪深港通资金流向 最近{limit}天"
        return self._query(query, "api")

    def get_index_daily(self, ts_code: str = "000001.SH", limit: int = 5) -> List[Dict]:
        """获取指数日线数据"""
        query = f"{ts_code} 指数行情 最近{limit}天"
        return self._query(query, "api")

    def get_market_overview(self) -> Dict:
        """获取市场概览"""
        query = "A股市场概况 涨跌家数 成交额"
        rows = self._query(query, "api")

        if rows:
            return rows[0]
        return {}


class RealDataTradingAgent:
    """真实数据股票交易Agent"""

    def __init__(self):
        self.data_adapter = RealDataAdapter()
        self.pattern_recognizer = ShortTermPatterns()
        self.risk_manager = RiskManagement()
        self.sentiment_analyzer = MarketSentimentAnalyzer()
        self.watchlist = []

    def add_to_watchlist(self, ts_code: str):
        """添加自选股"""
        name = self.data_adapter.get_stock_name(ts_code)
        self.watchlist.append({"code": ts_code, "name": name})
        logger.info(f"添加自选股: {ts_code} - {name}")

    def analyze_stock(self, ts_code: str) -> Dict:
        """分析单只股票"""
        # 获取数据
        data_list = self.data_adapter.get_stock_daily(ts_code, limit=10)

        if not data_list:
            return {"error": "无法获取数据"}

        latest = data_list[0]
        name = latest.name if latest.name else ts_code

        # 构建K线数据
        kline_data = {
            "open": latest.open,
            "high": latest.high,
            "low": latest.low,
            "close": latest.close,
            "pre_close": latest.pre_close,
            "volume": latest.vol,
            "amount": latest.amount
        }

        # 识别交易模式
        from trading_strategies import analyze_all_patterns
        patterns = analyze_all_patterns(kline_data)

        return {
            "ts_code": ts_code,
            "name": name,
            "current_price": latest.close,
            "change_pct": latest.pct_chg,
            "patterns": patterns,
            "volume": latest.vol,
            "amount": latest.amount
        }

    def analyze_market_sentiment(self) -> Dict:
        """分析市场情绪"""
        limit_up, limit_down = self.data_adapter.get_limit_list()
        overview = self.data_adapter.get_market_overview()

        # 获取指数数据
        sh_index = self.data_adapter.get_index_daily("000001.SH", limit=1)
        sz_index = self.data_adapter.get_index_daily("399001.SZ", limit=1)

        sh_close = sh_index[0].get("close", 0) if sh_index else 0
        sh_pre_close = sh_index[0].get("pre_close", 0) if sh_index else 0
        sh_change = ((sh_close - sh_pre_close) / sh_pre_close * 100) if sh_pre_close else 0

        return {
            "limit_up": limit_up,
            "limit_down": limit_down,
            "sh_index": sh_close,
            "sh_change": sh_change,
            "overview": overview
        }

    def generate_daily_plan(self) -> Dict:
        """生成每日交易计划"""
        plan = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "market_sentiment": self.analyze_market_sentiment(),
            "watchlist_analysis": []
        }

        for stock in self.watchlist:
            analysis = self.analyze_stock(stock["code"])
            plan["watchlist_analysis"].append(analysis)

        return plan

    def calculate_position(self, ts_code: str, entry_price: float, stop_loss: float,
                          total_capital: float = 100000) -> Dict:
        """计算建议仓位"""
        shares = RiskManagement.calculate_position_size(
            total_capital, entry_price, stop_loss
        )

        position_value = shares * entry_price
        position_pct = position_value / total_capital
        risk_amount = shares * (entry_price - stop_loss)

        return {
            "ts_code": ts_code,
            "shares": shares,
            "position_value": position_value,
            "position_pct": position_pct,
            "risk_amount": risk_amount,
            "entry_price": entry_price,
            "stop_loss": stop_loss
        }


def demo_real_data():
    """真实数据演示"""
    print("\n" + "=" * 70)
    print("真实数据股票交易Agent演示")
    print("=" * 70)

    agent = RealDataTradingAgent()

    # 添加自选股
    print("\n> 添加自选股")
    print("-" * 50)
    agent.add_to_watchlist("000001.SZ")  # 平安银行
    agent.add_to_watchlist("000002.SZ")  # 万科A
    agent.add_to_watchlist("600519.SH")  # 贵州茅台

    # 分析市场情绪
    print("\n> 市场情绪分析")
    print("-" * 50)
    sentiment = agent.analyze_market_sentiment()
    print(f"  涨停家数: {sentiment['limit_up']}")
    print(f"  跌停家数: {sentiment['limit_down']}")
    print(f"  上证指数: {sentiment['sh_index']:.2f} ({sentiment['sh_change']:+.2f}%)")

    # 分析自选股
    print("\n> 自选股分析")
    print("-" * 50)
    for stock in agent.watchlist:
        print(f"\n  分析: {stock['code']} - {stock['name']}")
        analysis = agent.analyze_stock(stock['code'])

        if "error" in analysis:
            print(f"    错误: {analysis['error']}")
            continue

        print(f"    当前价: {analysis['current_price']:.2f}元")
        print(f"    涨跌幅: {analysis['change_pct']:+.2f}%")
        print(f"    成交额: {analysis['amount']/10000:.0f}万")

        if analysis['patterns']:
            print(f"    识别到 {len(analysis['patterns'])} 个交易模式:")
            for p in analysis['patterns'][:2]:
                print(f"      - {p['pattern']} (置信度: {p['confidence']*100:.0f}%)")
        else:
            print("    无明显交易模式")

    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)


if __name__ == "__main__":
    demo_real_data()
