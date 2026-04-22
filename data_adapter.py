"""
真实数据适配器 - 接入 NeoData 金融数据 API
使用自然语言查询方式获取数据
"""
import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

from models import StockData, MarketSentimentData

logger = logging.getLogger(__name__)


class FinanceDataAdapter:
    """金融数据适配器 - 使用 NeoData API"""

    DEFAULT_ENDPOINT = "https://copilot.tencent.com/agenttool/v1/neodata"
    TOKEN_FILE = Path.home() / ".workbuddy" / ".neodata_token"

    def __init__(self):
        self.session = requests.Session()
        self.endpoint = os.getenv("NEODATA_ENDPOINT", self.DEFAULT_ENDPOINT)
        self.token = self._read_token()

    def _read_token(self) -> Optional[str]:
        """读取 token"""
        try:
            token = self.TOKEN_FILE.read_text().strip()
            # 设置文件权限为仅所有者可读写
            try:
                self.TOKEN_FILE.chmod(0o600)
            except OSError:
                pass
            return token if token else None
        except (FileNotFoundError, PermissionError):
            return None

    def _call_neodata(self, query: str, data_type: str = "api") -> dict:
        """调用 NeoData API"""
        if not self.token:
            logger.error("未找到 NeoData token，请先配置")
            return {}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        payload = {
            "query": query,
            "channel": "neodata",
            "sub_channel": "workbuddy",
            "data_type": data_type
        }

        try:
            response = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return {}

    def _parse_table_data(self, result: dict) -> List[dict]:
        """解析表格数据"""
        data = result.get("data", {})
        if not data:
            return []

        # 处理 api 返回格式
        if "fields" in data and "items" in data:
            fields = data["fields"]
            items = data["items"]
            return [dict(zip(fields, item)) for item in items]

        # 处理 doc 返回格式
        if isinstance(data, list):
            return data

        return []

    def get_stock_daily(self, ts_code: str, limit: int = 30) -> List[StockData]:
        """
        获取股票日线数据

        Args:
            ts_code: 股票代码（如 000001.SZ）
            limit: 返回条数限制
        """
        query = f"{ts_code} 日线行情 最近{limit}天"
        result = self._call_neodata(query, "api")
        rows = self._parse_table_data(result)

        result_list = []
        for row in rows:
            try:
                stock_data = StockData(
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
                result_list.append(stock_data)
            except (ValueError, TypeError) as e:
                logger.warning(f"解析数据失败: {e}, row={row}")
                continue

        result_list.reverse()
        return result_list

    def get_stock_name(self, ts_code: str) -> str:
        """获取股票名称"""
        query = f"{ts_code} 股票名称"
        result = self._call_neodata(query, "api")
        rows = self._parse_table_data(result)
        if rows:
            return rows[0].get("name", ts_code)
        return ts_code

    def get_limit_list(self, trade_date: str = "") -> Tuple[int, int]:
        """
        获取涨跌停数据

        Returns:
            (涨停家数, 跌停家数)
        """
        if not trade_date:
            trade_date = datetime.now().strftime("%Y%m%d")

        query = f"{trade_date} 涨跌停数据"
        result = self._call_neodata(query, "api")
        rows = self._parse_table_data(result)

        limit_up = 0
        limit_down = 0

        for row in rows:
            limit_type = row.get("limit", "")
            if limit_type == "U":
                limit_up += 1
            elif limit_type == "D":
                limit_down += 1

        return limit_up, limit_down

    def get_moneyflow_hsgt(self, limit: int = 5) -> List[dict]:
        """
        获取沪深港通资金流向
        """
        query = f"沪深港通资金流向 最近{limit}天"
        result = self._call_neodata(query, "api")
        return self._parse_table_data(result)

    def get_index_daily(self, ts_code: str = "000001.SH", limit: int = 30) -> List[dict]:
        """
        获取指数日线数据

        Args:
            ts_code: 指数代码（000001.SH 上证指数，399001.SZ 深证成指）
        """
        query = f"{ts_code} 指数日线 最近{limit}天"
        result = self._call_neodata(query, "api")
        return self._parse_table_data(result)

    def calculate_market_sentiment(self) -> MarketSentimentData:
        """
        计算市场情绪
        """
        trade_date = datetime.now().strftime("%Y%m%d")

        # 获取涨跌停数据
        limit_up, limit_down = self.get_limit_list(trade_date)

        # 获取每日指标数据
        query = f"{trade_date} 每日指标 涨跌幅"
        result = self._call_neodata(query, "api")
        rows = self._parse_table_data(result)

        up_count = 0
        down_count = 0
        total_amount = 0

        for row in rows:
            try:
                pct_chg = float(row.get("pct_chg", 0) or 0)
                amount = float(row.get("amount", 0) or 0)

                if pct_chg > 0:
                    up_count += 1
                elif pct_chg < 0:
                    down_count += 1

                total_amount += amount
            except (ValueError, TypeError):
                continue

        # 计算情绪分数 (-1 ~ 1)
        total = up_count + down_count
        if total > 0:
            sentiment_score = (up_count - down_count) / total
        else:
            sentiment_score = 0

        # 情绪标签
        if sentiment_score > 0.5:
            sentiment_label = "极度贪婪"
        elif sentiment_score > 0.2:
            sentiment_label = "贪婪"
        elif sentiment_score > -0.2:
            sentiment_label = "中性"
        elif sentiment_score > -0.5:
            sentiment_label = "恐慌"
        else:
            sentiment_label = "极度恐慌"

        return MarketSentimentData(
            date=trade_date,
            limit_up_count=limit_up,
            limit_down_count=limit_down,
            up_count=up_count,
            down_count=down_count,
            total_amount=total_amount,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label
        )

    def get_realtime_data(self, ts_codes: List[str]) -> Dict[str, StockData]:
        """
        获取多只股票最新数据
        """
        result = {}

        for ts_code in ts_codes:
            data = self.get_stock_daily(ts_code, limit=1)
            if data:
                result[ts_code] = data[0]

        return result

    def get_stock_list(self, limit: int = 100) -> List[dict]:
        """
        获取股票列表
        """
        query = f"股票列表 前{limit}只"
        result = self._call_neodata(query, "api")
        return self._parse_table_data(result)


# 懒加载单例
_data_adapter_instance = None


def get_data_adapter() -> FinanceDataAdapter:
    """获取 FinanceDataAdapter 单例（懒加载）"""
    global _data_adapter_instance
    if _data_adapter_instance is None:
        _data_adapter_instance = FinanceDataAdapter()
    return _data_adapter_instance


if __name__ == "__main__":
    # 测试
    adapter = FinanceDataAdapter()

    if not adapter.token:
        print("错误: 未找到 NeoData token")
        print(f"请先将 token 保存到: {adapter.TOKEN_FILE}")
        exit(1)

    print("=" * 60)
    print("测试1: 获取股票日线数据")
    print("=" * 60)
    stock_data = adapter.get_stock_daily("000001.SZ", limit=5)
    for d in stock_data:
        print(f"{d.date} {d.ts_code}: 开{d.open} 收{d.close} 涨{d.pct_chg:.2f}%")

    print("\n" + "=" * 60)
    print("测试2: 获取涨跌停数据")
    print("=" * 60)
    limit_up, limit_down = adapter.get_limit_list()
    print(f"涨停: {limit_up}家, 跌停: {limit_down}家")

    print("\n" + "=" * 60)
    print("测试3: 计算市场情绪")
    print("=" * 60)
    sentiment = adapter.calculate_market_sentiment()
    print(f"情绪: {sentiment.sentiment_label}")
    print(f"分数: {sentiment.sentiment_score:.2f}")
    print(f"上涨: {sentiment.up_count}家, 下跌: {sentiment.down_count}家")
    print(f"涨停: {sentiment.limit_up_count}家, 跌停: {sentiment.limit_down_count}家")
