"""
股票交易Agent - 基于AKShare免费数据源

功能模块：
1. 每日市场报告
2. 策略分析（动量/均值回归/趋势跟踪/波动率突破）
3. 股票推荐（多维度评分排名）
4. 交易规则校验（A股规则引擎）

使用方法:
  python hybrid_agent.py              # 运行完整分析（默认）
  python hybrid_agent.py > report.txt  # 输出到文件
"""
import os
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

from akshare_adapter import AKShareAdapter, get_akshare_adapter
from trading_rules import TradingRules, TradeCheckResult
from trading_rules import (
    MIN_LOT_SIZE, MAX_SINGLE_ORDER, MIN_PRICE_UNIT,
    COMMISSION_RATE as RULES_COMMISSION_RATE,
    COMMISSION_MIN as RULES_COMMISSION_MIN,
    STAMP_DUTY_RATE, TRANSFER_FEE_RATE
)
from stock_recommender import StockRecommender, RecommendationReport


# ============== 工具方法 ==============

def _create_clean_session():
    """创建一个不受代理环境影响的 requests.Session 实例。"""
    import requests
    session = requests.Session()
    session.trust_env = False
    session.proxies.clear()
    return session


def _clean_env_for_subprocess():
    """返回一份移除了代理变量的环境变量字典，用于 subprocess 调用。"""
    proxy_vars = [
        'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
        'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy',
    ]
    env = os.environ.copy()
    for k in proxy_vars:
        env.pop(k, None)
    return env


# ============== 交易Agent ==============

class TradingAgent:
    """基于真实数据的股票分析Agent"""

    def __init__(self):
        self.data_adapter = get_akshare_adapter()
        self.watchlist = []
        self.trading_rules = TradingRules()
        self.recommender = StockRecommender(data_adapter=self.data_adapter)
        logger.info("Agent初始化完成")

    def add_to_watchlist(self, ts_code: str, name: str = ""):
        """添加自选股（去重）"""
        for item in self.watchlist:
            if item["code"] == ts_code:
                logger.debug(f"自选股已存在，跳过: {ts_code}")
                return
        if not name:
            name = self.data_adapter.get_stock_name(ts_code)
        self.watchlist.append({"code": ts_code, "name": name})
        logger.info(f"添加自选股: {ts_code} - {name}")

    def analyze_stock(self, ts_code: str) -> Dict:
        """分析单只股票基本信息"""
        data_list = self.data_adapter.get_stock_daily(ts_code, limit=5)
        if not data_list:
            return {"error": "无法获取数据"}
        latest = data_list[0]
        return {
            "ts_code": ts_code,
            "name": latest.name or ts_code,
            "current_price": float(latest.close),
            "change_pct": float(latest.pct_chg),
            "volume": float(latest.vol),
            "amount": float(latest.amount),
        }

    def _get_market_overview(self) -> Dict:
        """获取市场涨跌概览"""
        try:
            import akshare as ak
            # 使用 stock_zh_a_spot_em 替代已废弃的 stock_zs_pg
            df = ak.stock_zh_a_spot_em()
            return {
                'up_count': len(df[df['涨跌幅'] > 0]),
                'down_count': len(df[df['涨跌幅'] < 0]),
                'total_count': len(df)
            }
        except Exception as e:
            logger.warning(f"市场概览数据获取失败: {e}")
            return {}

    def analyze_market_sentiment(self) -> Dict:
        """分析市场情绪"""
        limit_up, limit_down = self.data_adapter.get_limit_list()
        overview = self._get_market_overview()

        # 获取三大指数
        indices = {}
        for code, name in [("000001.SH", "sh"), ("399001.SZ", "sz"), ("399006.SZ", "cyb")]:
            data = self.data_adapter.get_index_daily(code, limit=1)
            if data:
                close = float(data[0].get("close", 0))
                pre = float(data[0].get("pre_close", 0))
                chg = ((close - pre) / pre * 100) if pre else 0
                indices[name] = {"close": close, "change": chg}

        result = {
            "limit_up": limit_up, "limit_down": limit_down,
            "sh_index": indices.get("sh", {}).get("close"),
            "sh_change": indices.get("sh", {}).get("change"),
            "sz_index": indices.get("sz", {}).get("close"),
            "sz_change": indices.get("sz", {}).get("change"),
            "cyb_index": indices.get("cyb", {}).get("close"),
            "cyb_change": indices.get("cyb", {}).get("change"),
            "overview": overview,
        }

        if not indices:
            result["index_error"] = True

        return result

    # ==================== 报告输出 ====================

    def print_daily_report(self):
        """打印每日交易报告"""
        plan = self.generate_plan()
        print("\n" + "=" * 70)
        print(f"每日交易报告 - {plan['date']}")
        print("=" * 70)

        sent = plan["market_sentiment"]
        print(f"\n> 市场情绪\n{'-' * 50}")
        if sent.get("index_error"):
            print(f"  上证指数: [数据获取失败]")
        else:
            idx = sent['sh_index']
            c = sent['sh_change']
            print(f"  上证指数: {idx:.2f} ({c:+.2f}%)" if idx else "  上证指数: N/A")
        print(f"  涨停家数: {sent['limit_up']}")
        print(f"  跌停家数: {sent['limit_down']}")

        print(f"\n> 自选股分析\n{'-' * 50}")
        for a in plan["watchlist_analysis"]:
            if "error" in a:
                print(f"\n  {a.get('ts_code', '?')}: {a['error']}")
                continue
            print(f"\n  {a['ts_code']} - {a['name']}")
            print(f"    当前价: {a['current_price']:.2f}元")
            print(f"    涨跌幅: {a['change_pct']:+.2f}%")
            print(f"    成交额: {a['amount']/10000:.0f}万")
        print("\n" + "=" * 70)

    def generate_plan(self) -> Dict:
        """生成每日交易计划"""
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "market_sentiment": self.analyze_market_sentiment(),
            "watchlist_analysis": [self.analyze_stock(s["code"]) for s in self.watchlist],
        }

    # ==================== 策略引擎 ====================

    def run_strategy_analysis(self) -> Dict:
        """运行策略分析"""
        strategies = {
            "动量策略": self._momentum_strategy,
            "均值回归": self._mean_reversion,
            "趋势跟踪": self._trend_following,
            "波动率突破": self._volatility_breakout,
        }
        results = {}
        for name, func in strategies.items():
            try:
                signals = func()
                results[name] = signals
                print(f"\n【{name}】")
                for sig in signals[:3]:
                    code = sig.get('code', '')
                    action = sig.get('action', '-')
                    reason = sig.get('reason', '')[:30]
                    conf = sig.get('confidence', 0)
                    tag = "[BUY]" if "买" in action or "看多" in action else \
                          ("[SELL]" if "卖" in action or "看空" in action else "[WATCH]")
                    print(f"  {tag} {code}: {action} ({conf:.0%}) - {reason}...")
                if len(signals) > 3:
                    print(f"  ... 共{len(signals)}个信号")
            except Exception as e:
                logger.error(f"{name}执行失败: {e}")
        return results

    def _get_closes(self, code, limit=10):
        data = self.data_adapter.get_stock_daily(code, limit=limit)
        return [d.close for d in data] if data else []

    def _momentum_strategy(self) -> List[Dict]:
        """动量策略：追涨杀跌"""
        signals = []
        for stock in self.watchlist:
            closes = self._get_closes(stock["code"], 10)
            if len(closes) < 6:
                continue
            m5 = (closes[0] - closes[4]) / closes[4] * 100
            m10 = (closes[0] - closes[-1]) / closes[-1] * 100
            if m5 > 5 and m10 > 3:
                signals.append({
                    "code": stock["code"], "name": stock["name"],
                    "action": "买入", "confidence": min(abs(m5)/15, 1),
                    "reason": f"5日动量{m5:+.2f}%, 强势上涨",
                })
            elif m5 < -5 and m10 < -3:
                signals.append({
                    "code": stock["code"], "name": stock["name"],
                    "action": "卖出", "confidence": min(abs(m5)/15, 1),
                    "reason": f"5日动量{m5:+.2f}%, 快速下跌",
                })
        return sorted(signals, key=lambda x: abs(x.get("confidence", 0)), reverse=True)

    def _mean_reversion(self) -> List[Dict]:
        """均值回归：超跌买入/超涨卖出"""
        signals = []
        for stock in self.watchlist:
            closes = self._get_closes(stock["code"], 20)
            if len(closes) < 10:
                continue
            ma5 = sum(closes[:5]) / 5
            ma20 = sum(closes) / len(closes)
            cur = closes[0]
            dev5 = (cur - ma5) / ma5 * 100
            if dev5 < -8 and cur < ma20:
                signals.append({
                    "code": stock["code"], "name": stock["name"],
                    "action": "超跌关注", "confidence": min(abs(dev5)/12, 1),
                    "reason": f"偏离MA5 {dev5:+.2f}%, 可能反弹",
                })
            elif dev5 > 8 and cur > ma20:
                signals.append({
                    "code": stock["code"], "name": stock["name"],
                    "action": "获利了结", "confidence": min(abs(dev5)/12, 1),
                    "reason": f"偏离MA5 {dev5:+.2f}%, 注意回调",
                })
        return sorted(signals, key=lambda x: abs(x.get("confidence", 0)), reverse=True)

    def _trend_following(self) -> List[Dict]:
        """趋势跟踪：均线多头/空头排列"""
        signals = []
        for stock in self.watchlist:
            closes = self._get_closes(stock["code"], 30)
            if len(closes) < 21:
                continue
            ma5, ma10, ma20 = sum(closes[:5])/5, sum(closes[:10])/10, sum(closes[:20])/20
            cur = closes[0]
            if cur > ma5 > ma10 > ma20:
                signals.append({"code": stock["code"], "name": stock["name"],
                               "action": "趋势看多", "confidence": 0.75, "reason": "多头排列"})
            elif cur < ma5 < ma10 < ma20:
                signals.append({"code": stock["code"], "name": stock["name"],
                               "action": "趋势看空", "confidence": 0.7, "reason": "空头排列"})
        return sorted(signals, key=lambda x: abs(x.get("confidence", 0)), reverse=True)

    def _volatility_breakout(self) -> List[Dict]:
        """波动率突破：ATR+放量检测"""
        signals = []
        for stock in self.watchlist:
            data = self.data_adapter.get_stock_daily(stock["code"], 20)
            if len(data) < 11:
                continue
            closes = [d.close for d in data]
            highs = [d.high for d in data]
            lows = [d.low for d in data]
            vols = [d.vol for d in data]

            trs = []
            for i in range(len(highs) - 1):
                hl = highs[i] - lows[i]
                pc = closes[i + 1]
                trs.append(max(hl, abs(highs[i] - pc), abs(lows[i] - pc)))

            if len(trs) < 5:
                continue

            atr = sum(trs) / len(trs)
            avg_vol = sum(vols[1:6]) / 5
            vr = vols[0] / avg_vol if avg_vol else 1
            change = abs(closes[0] - closes[1])

            if change > atr * 1.5 and vr > 1.5:
                direction = "向上突破" if closes[0] > closes[1] else "向下突破"
                signals.append({
                    "code": stock["code"], "name": stock["name"],
                    "action": direction, "confidence": min(vr/3, 1),
                    "reason": f"放量{vr:.1f}倍, 波动突破ATR",
                })
        return sorted(signals, key=lambda x: abs(x.get("confidence", 0)), reverse=True)

    # ==================== 股票推荐 ====================

    def run_stock_recommendation(self, top_n: int = 10) -> RecommendationReport:
        """
        运行股票推荐

        Args:
            top_n: 返回前N个推荐

        Returns:
            RecommendationReport 推荐报告
        """
        print(f"\n> 股票推荐 (Top {top_n})\n{'-' * 50}")

        # 获取市场情绪
        sentiment_data = self.data_adapter.calculate_market_sentiment()
        sentiment_label = sentiment_data.sentiment_label

        # 生成推荐
        scores = self.recommender.recommend_from_watchlist(self.watchlist, top_n=top_n)

        # 构建报告
        report = RecommendationReport(
            date=datetime.now().strftime("%Y-%m-%d"),
            market_sentiment=sentiment_label,
            recommendations=scores,
            warnings=[]
        )

        # 风险提示
        if sentiment_label in ("极度贪婪", "贪婪"):
            report.warnings.append("市场情绪过热，注意控制仓位")
        if sentiment_label in ("极度恐慌",):
            report.warnings.append("市场极度恐慌，可适当关注超跌机会")

        # 打印报告
        print(StockRecommender.format_report(report))

        return report

    def filter_anomaly_stocks(self) -> List:
        """筛选异动股"""
        print(f"\n> 异动股筛选\n{'-' * 50}")

        anomalies = self.recommender.filter_anomaly_stocks(self.watchlist)

        if anomalies:
            for i, score in enumerate(anomalies, 1):
                print(f"  【异动{i}】{score.ts_code} - {score.name}")
                print(f"    涨跌幅: {score.change_pct:+.2f}%")
                print(f"    信号: {', '.join(score.signals[:3])}")
                print(f"    评分: {score.total_score:.1f}/100")
        else:
            print("  今日无显著异动")

        return anomalies

    # ==================== 交易规则校验 ====================

    def validate_trade(
        self,
        ts_code: str,
        action: str,
        price: float,
        quantity: int,
        available_cash: float = 0,
        is_st: bool = False
    ) -> TradeCheckResult:
        """
        校验交易是否符合A股规则

        Args:
            ts_code: 股票代码
            action: BUY 或 SELL
            price: 委托价格
            quantity: 委托数量（股）
            available_cash: 可用资金
            is_st: 是否ST股

        Returns:
            TradeCheckResult 校验结果
        """
        # 获取前收盘价
        data = self.data_adapter.get_stock_daily(ts_code, limit=2)
        if not data:
            return TradeCheckResult(passed=False, reason="无法获取股票数据")

        pre_close = data[0].pre_close if data[0].pre_close > 0 else data[0].close

        result = self.trading_rules.validate_trade(
            ts_code=ts_code,
            action=action,
            price=price,
            quantity=quantity,
            pre_close=pre_close,
            available_cash=available_cash,
            is_st=is_st,
            check_time=False  # 程序化交易不检查实时时间
        )

        # 打印校验结果
        print(TradingRules.format_trade_summary(result, ts_code, action))

        return result

    def show_trading_rules_info(self):
        """展示A股交易规则概要"""
        print("\n" + "=" * 70)
        print("  A股交易规则概要")
        print("=" * 70)

        rules = [
            ("最低交易量", f"{MIN_LOT_SIZE}股（1手）"),
            ("单笔最大委托", f"{MAX_SINGLE_ORDER:,}股"),
            ("最小价格变动", f"{MIN_PRICE_UNIT}元"),
            ("主板涨跌停", f"±{TradingRules.get_limit_pct('main')}%"),
            ("科创板涨跌停", f"±{TradingRules.get_limit_pct('kcb')}%"),
            ("创业板涨跌停", f"±{TradingRules.get_limit_pct('cyb')}%"),
            ("ST股涨跌停", f"±{TradingRules.get_limit_pct('st')}%"),
            ("北交所涨跌停", f"±{TradingRules.get_limit_pct('bse')}%"),
            ("交易制度", "T+1（当日买入次日方可卖出）"),
            ("集合竞价", "9:15-9:25"),
            ("上午连续竞价", "9:30-11:30"),
            ("下午连续竞价", "13:00-15:00"),
            ("佣金费率", f"万{RULES_COMMISSION_RATE * 10000:.1f}（最低{RULES_COMMISSION_MIN}元）"),
            ("印花税", f"千{STAMP_DUTY_RATE * 1000:.0f}（仅卖出）"),
            ("过户费", f"万{TRANSFER_FEE_RATE * 10000:.1f}（买卖均收）"),
        ]

        for name, value in rules:
            print(f"  {name:.<20} {value}")

        # 涨跌停价格示例
        print(f"\n  涨跌停价格示例（前收盘10.00元）:")
        for board in ["main", "kcb", "cyb", "st"]:
            up, down = TradingRules.calculate_limit_price(10.0, board)
            name_map = {"main": "主板", "kcb": "科创板", "cyb": "创业板", "st": "ST股"}
            print(f"    {name_map[board]}: 涨停 {up:.2f}元 / 跌停 {down:.2f}元")

        print("=" * 70)


# ============== 主入口 ==============

def main():
    agent = TradingAgent()

    # 自选股
    watchlist = [
        ("000001.SZ", "平安银行"),   ("600036.SH", "招商银行"),   ("601318.SH", "中国平安"),
        ("000002.SZ", "万科A"),
        ("600519.SH", "贵州茅台"),   ("000858.SZ", "五粮液"),     ("000568.SZ", "泸州老窖"),
        ("002594.SZ", "比亚迪"),     ("300750.SZ", "宁德时代"),   ("601012.SH", "隆基绿能"),
        ("000725.SZ", "京东方A"),    ("002415.SZ", "海康威视"),   ("600570.SH", "恒生电子"),
        ("600276.SH", "恒瑞医药"),   ("000538.SZ", "云南白药"),
        ("601857.SH", "中国石油"),   ("601398.SH", "工商银行"),
    ]
    for code, name in watchlist:
        agent.add_to_watchlist(code, name)

    # 1. 每日报告
    agent.print_daily_report()

    # 2. 策略分析
    print("\n> 策略分析\n" + "-" * 50)
    agent.run_strategy_analysis()

    # 3. 股票推荐
    agent.run_stock_recommendation(top_n=10)

    # 4. 异动股筛选
    agent.filter_anomaly_stocks()

    # 5. 交易规则展示
    agent.show_trading_rules_info()

    # 6. 交易校验示例
    print("\n> 交易校验示例\n" + "-" * 50)
    agent.validate_trade("000001.SZ", "BUY", 12.50, 500, available_cash=100000)
    agent.validate_trade("000001.SZ", "BUY", 12.50, 50, available_cash=100000)   # 低于最低交易量
    agent.validate_trade("688001.SH", "BUY", 50.00, 200, available_cash=10000)   # 科创板


if __name__ == "__main__":
    main()
