"""
AKShare 免费数据源适配器
无需Token，直接获取A股实时数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import StockData, MarketSentimentData

logger = logging.getLogger(__name__)


class AKShareAdapter:
    """AKShare 数据适配器 - 免费数据源"""

    def __init__(self):
        self.stock_name_cache = {}
        self._stock_list_loaded = False
        self._full_stock_list = None

    def _to_ts_code(self, symbol: str) -> str:
        """转换为统一代码格式"""
        if '.' in symbol:
            return symbol
        # 6位数字代码
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"

    def _from_ts_code(self, ts_code: str) -> str:
        """从统一代码格式转换"""
        if '.' in ts_code:
            return ts_code.split('.')[0]
        return ts_code

    def get_stock_daily(self, ts_code: str, limit: int = 30) -> List[StockData]:
        """
        获取股票日线数据

        Args:
            ts_code: 股票代码（如 000001.SZ 或 000001）
            limit: 返回条数限制

        Returns:
            按日期从新到旧排列的 StockData 列表（newest first）
        """
        try:
            symbol = self._from_ts_code(ts_code)
            # AKShare 格式：sz000001 或 sh600000
            if symbol.startswith('6'):
                ak_symbol = f"sh{symbol}"
            else:
                ak_symbol = f"sz{symbol}"

            # 动态计算 start_date，按 limit*3 天回溯以覆盖周末/节假日
            start_date = (datetime.now() - timedelta(days=limit * 3)).strftime("%Y%m%d")

            # 多取一行，确保第一条数据有准确的前一日收盘价
            df = ak.stock_zh_a_daily(symbol=ak_symbol, start_date=start_date)

            if df.empty:
                logger.warning(f"未获取到数据: {ts_code}")
                return []

            # 取 limit+1 条，从第二条开始遍历，用前一条的 close 作为 pre_close
            df = df.tail(limit + 1).reset_index(drop=True)

            # 获取股票名称
            name = self.get_stock_name(ts_code)

            records = df.to_dict('records')
            result = []
            for idx, row in enumerate(records):
                try:
                    # 跳过第一条（仅作为 pre_close 的来源）
                    if idx == 0:
                        continue

                    pre_close = float(records[idx - 1]['close'])
                    close = float(row['close'])
                    change = close - pre_close
                    pct_chg = (change / pre_close) * 100 if pre_close > 0 else 0

                    stock_data = StockData(
                        ts_code=self._to_ts_code(symbol),
                        name=name,
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=close,
                        pre_close=pre_close,
                        change=change,
                        pct_chg=pct_chg,
                        vol=float(row['volume']),
                        amount=float(row.get('amount', 0)),
                        date=str(row['date']).replace('-', '')
                    )
                    result.append(stock_data)
                except Exception as e:
                    logger.warning(f"解析数据失败: {e}")
                    continue

            # 返回数据按日期从新到旧排列（newest first）
            result.reverse()
            return result

        except Exception as e:
            logger.error(f"获取股票数据失败 {ts_code}: {e}")
            return []

    def get_stock_name(self, ts_code: str) -> str:
        """获取股票名称（首次调用时预加载全量股票列表并缓存）"""
        try:
            symbol = self._from_ts_code(ts_code)

            # 检查缓存
            if symbol in self.stock_name_cache:
                return self.stock_name_cache[symbol]

            # 首次调用时加载全量股票列表
            if not self._stock_list_loaded:
                try:
                    df = ak.stock_info_a_code_name()
                    self._full_stock_list = df
                    # 预填充缓存
                    for _, row in df.iterrows():
                        code = str(row['code'])
                        self.stock_name_cache[code] = row['name']
                    self._stock_list_loaded = True
                    logger.info(f"预加载股票列表完成，共 {len(df)} 只")
                except Exception as e:
                    logger.error(f"预加载股票列表失败: {e}")
                    return ts_code

            return self.stock_name_cache.get(symbol, symbol)

        except Exception as e:
            logger.error(f"获取股票名称失败: {e}")
            return ts_code

    def get_limit_list(self) -> Tuple[int, int]:
        """
        获取涨跌停数据

        Returns:
            (涨停家数, 跌停家数)
        """
        try:
            # 获取当日涨停数据
            df_limit_up = ak.stock_zt_pool_em(date=datetime.now().strftime("%Y%m%d"))
            limit_up = len(df_limit_up)

            # 获取当日跌停数据
            df_limit_down = ak.stock_zt_pool_dtgc_em(date=datetime.now().strftime("%Y%m%d"))
            limit_down = len(df_limit_down)

            return limit_up, limit_down

        except Exception as e:
            logger.error(f"获取涨跌停数据失败: {e}")
            # 备用方案：从涨跌分布估算
            try:
                df = ak.stock_zs_pg(symbol="全部股票")
                limit_up = len(df[df['涨跌幅'] >= 9.9])
                limit_down = len(df[df['涨跌幅'] <= -9.9])
                return limit_up, limit_down
            except Exception:
                return 0, 0

    def get_index_daily(self, ts_code: str = "000001.SH", limit: int = 30) -> List[dict]:
        """
        获取指数日线数据

        优先使用 ak.index_zh_a_hist，失败时降级到新浪实时接口。
        """
        try:
            # 中文列名映射为英文
            COLUMN_MAP = {
                '日期': 'trade_date', '开盘': 'open', '最高': 'high',
                '最低': 'low', '收盘': 'close', '涨跌额': 'change',
                '涨跌幅': 'pct_chg', '成交量': 'vol', '成交额': 'amount'
            }

            if "SH" in ts_code or ts_code == "000001":
                df = ak.index_zh_a_hist(symbol="000001", period="daily", start_date="20240101")
            elif "SZ" in ts_code or ts_code == "399001":
                df = ak.index_zh_a_hist(symbol="399001", period="daily", start_date="20240101")
            else:
                return []

            df = df.rename(columns=COLUMN_MAP)
            df = df.tail(limit).reset_index(drop=True)

            result = []
            for _, row in df.iterrows():
                result.append({
                    'ts_code': ts_code,
                    'trade_date': str(row['trade_date']).replace('-', ''),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'change': float(row['change']),
                    'pct_chg': float(row['pct_chg']),
                    'vol': float(row['vol']),
                    'amount': float(row['amount'])
                })

            return result

        except Exception as e:
            logger.warning(f"ak.index_zh_a_hist 失败，尝试新浪接口: {e}")
            # 降级：使用新浪实时接口获取当日指数数据
            return self._get_index_daily_sina(ts_code, limit)

    def _get_index_daily_sina(self, ts_code: str, limit: int = 1) -> List[dict]:
        """通过新浪财经接口获取指数数据（降级方案）"""
        try:
            import requests
            # 新浪指数代码映射
            sina_map = {
                "000001.SH": "sh000001",
                "399001.SZ": "sz399001",
                "399006.SZ": "sz399006",
            }
            sina_sym = sina_map.get(ts_code, "")
            if not sina_sym:
                return []

            session = requests.Session()
            session.trust_env = False
            session.proxies.clear()

            url = f"http://hq.sinajs.cn/list={sina_sym}"
            headers = {"Referer": "https://finance.sina.com.cn"}
            resp = session.get(url, headers=headers, timeout=10)
            resp.encoding = "gbk"
            text = resp.text.strip()

            if not text or "=" not in text:
                return []

            # 解析新浪数据格式
            data_str = text.split("=")[1].strip('"; \n')
            if not data_str:
                return []

            fields = data_str.split(",")
            # 新浪指数字段: 名称,开盘,昨收,当前,最高,最低,买1,卖1,成交量,成交额...
            if len(fields) < 10:
                return []

            open_price = float(fields[1])
            pre_close = float(fields[2])
            close = float(fields[3])
            high = float(fields[4])
            low = float(fields[5])
            vol = float(fields[8])
            amount = float(fields[9])
            change = close - pre_close
            pct_chg = (change / pre_close * 100) if pre_close else 0

            return [{
                'ts_code': ts_code,
                'trade_date': datetime.now().strftime("%Y%m%d"),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'change': change,
                'pct_chg': pct_chg,
                'vol': vol,
                'amount': amount,
            }]

        except Exception as e:
            logger.error(f"新浪指数接口也失败: {e}")
            return []

    def calculate_market_sentiment(self) -> MarketSentimentData:
        """
        计算市场情绪
        """
        try:
            # 使用 stock_zh_a_spot_em 获取全市场实时行情（替代已废弃的 stock_zs_pg）
            df = ak.stock_zh_a_spot_em()

            up_count = len(df[df['涨跌幅'] > 0])
            down_count = len(df[df['涨跌幅'] < 0])
            limit_up = len(df[df['涨跌幅'] >= 9.9])
            limit_down = len(df[df['涨跌幅'] <= -9.9])

            # 计算情绪分数
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
                date=datetime.now().strftime("%Y%m%d"),
                limit_up_count=limit_up,
                limit_down_count=limit_down,
                up_count=up_count,
                down_count=down_count,
                total_amount=0,  # AKShare不直接提供
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label
            )

        except Exception as e:
            logger.error(f"计算市场情绪失败: {e}")
            return MarketSentimentData(
                date=datetime.now().strftime("%Y%m%d"),
                limit_up_count=0,
                limit_down_count=0,
                up_count=0,
                down_count=0,
                total_amount=0,
                sentiment_score=0,
                sentiment_label="未知"
            )

    def get_realtime_data(self, ts_codes: List[str]) -> Dict[str, StockData]:
        """
        获取多只股票最新数据（并行获取）
        """
        result = {}

        def _fetch_one(code: str) -> Optional[Tuple[str, StockData]]:
            data = self.get_stock_daily(code, limit=1)
            if data:
                return (code, data[0])
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_code = {
                executor.submit(_fetch_one, ts_code): ts_code
                for ts_code in ts_codes
            }
            for future in as_completed(future_to_code):
                try:
                    item = future.result()
                    if item:
                        result[item[0]] = item[1]
                except Exception as e:
                    logger.warning(f"并行获取实时数据失败: {e}")

        return result

    def get_stock_list(self, limit: int = 100) -> List[dict]:
        """
        获取股票列表
        """
        try:
            df = ak.stock_info_a_code_name()
            df = df.head(limit)

            result = []
            for _, row in df.iterrows():
                code = row['code']
                ts_code = self._to_ts_code(code)
                result.append({
                    'ts_code': ts_code,
                    'name': row['name'],
                    'code': code
                })

            return result

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []

    def get_moneyflow_hsgt(self, limit: int = 5) -> List[dict]:
        """
        获取沪深港通资金流向
        """
        try:
            df = ak.stock_hsgt_hist_em(symbol="北上资金")
            df = df.tail(limit).reset_index(drop=True)

            result = []
            for _, row in df.iterrows():
                result.append({
                    'trade_date': str(row['日期']).replace('-', ''),
                    'ggt_ss': float(row.get('港股通上海', 0)),
                    'ggt_sz': float(row.get('港股通深圳', 0)),
                    'hgt': float(row.get('沪股通', 0)),
                    'sgt': float(row.get('深股通', 0)),
                    'north_money': float(row.get('北向资金', 0))
                })

            return result

        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return []


# ==================== 懒加载单例 ====================

_akshare_adapter_instance = None


def get_akshare_adapter() -> AKShareAdapter:
    """获取 AKShareAdapter 懒加载单例"""
    global _akshare_adapter_instance
    if _akshare_adapter_instance is None:
        _akshare_adapter_instance = AKShareAdapter()
    return _akshare_adapter_instance


if __name__ == "__main__":
    # 测试
    adapter = AKShareAdapter()

    print("=" * 60)
    print("AKShare 数据源测试")
    print("=" * 60)

    print("\n测试1: 获取股票日线数据")
    stock_data = adapter.get_stock_daily("000001.SZ", limit=5)
    for d in stock_data:
        print(f"{d.date} {d.ts_code} {d.name}: 开{d.open} 收{d.close} 涨{d.pct_chg:.2f}%")

    print("\n测试2: 获取涨跌停数据")
    limit_up, limit_down = adapter.get_limit_list()
    print(f"涨停: {limit_up}家, 跌停: {limit_down}家")

    print("\n测试3: 计算市场情绪")
    sentiment = adapter.calculate_market_sentiment()
    print(f"情绪: {sentiment.sentiment_label}")
    print(f"分数: {sentiment.sentiment_score:.2f}")
    print(f"上涨: {sentiment.up_count}家, 下跌: {sentiment.down_count}家")

    print("\n测试4: 获取指数数据")
    index_data = adapter.get_index_daily("000001.SH", limit=3)
    for d in index_data:
        print(f"{d['trade_date']} 上证指数: {d['close']} ({d['pct_chg']:+.2f}%)")
