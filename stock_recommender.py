#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票推荐模块
============
基于多维度评分的智能股票推荐系统。

评分维度：
1. 趋势评分 - 均线排列、价格趋势
2. 动量评分 - 涨跌幅、成交量变化
3. 波动率评分 - ATR、波动率突破
4. 资金面评分 - 成交额、量比
5. 技术形态评分 - K线形态、支撑压力位

推荐策略：
- 综合评分排名
- 板块轮动推荐
- 异动股筛选
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from models import StockData

logger = logging.getLogger(__name__)


@dataclass
class StockScore:
    """股票评分结果"""
    ts_code: str
    name: str
    total_score: float          # 综合评分 0-100
    trend_score: float = 0.0    # 趋势评分
    momentum_score: float = 0.0 # 动量评分
    volatility_score: float = 0.0  # 波动率评分
    volume_score: float = 0.0   # 资金面评分
    pattern_score: float = 0.0  # 技术形态评分
    current_price: float = 0.0
    change_pct: float = 0.0
    recommendation: str = ""    # 推荐理由
    risk_level: str = "medium"  # low/medium/high
    signals: List[str] = field(default_factory=list)  # 交易信号标签


@dataclass
class RecommendationReport:
    """推荐报告"""
    date: str
    market_sentiment: str
    recommendations: List[StockScore] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StockRecommender:
    """
    股票推荐引擎

    基于多维度技术指标评分，从候选股票池中筛选出最具交易价值的标的。
    """

    def __init__(self, data_adapter=None):
        """
        Args:
            data_adapter: 数据适配器（AKShareAdapter 实例）
        """
        self.data_adapter = data_adapter

    # ==================== 评分引擎 ====================

    def score_trend(self, closes: List[float]) -> Tuple[float, List[str]]:
        """
        趋势评分（0-100）

        评估维度：
        - 均线多头排列（MA5 > MA10 > MA20）
        - 价格在均线之上
        - 短期趋势方向
        """
        signals = []
        score = 50.0  # 基准分

        if len(closes) < 20:
            return score, signals

        ma5 = sum(closes[:5]) / 5
        ma10 = sum(closes[:10]) / 10
        ma20 = sum(closes[:20]) / 20
        cur = closes[0]

        # 均线多头排列 +20
        if cur > ma5 > ma10 > ma20:
            score += 20
            signals.append("多头排列")
        elif cur < ma5 < ma10 < ma20:
            score -= 20
            signals.append("空头排列")

        # 价格在MA5之上 +10
        if cur > ma5:
            score += 10
            signals.append("站上MA5")
        else:
            score -= 10
            signals.append("跌破MA5")

        # 价格在MA20之上 +10
        if cur > ma20:
            score += 10
            signals.append("站上MA20")

        # 短期趋势（5日）+10
        if len(closes) >= 6:
            short_trend = (closes[0] - closes[5]) / closes[5] * 100
            if short_trend > 3:
                score += 10
                signals.append(f"5日上涨{short_trend:.1f}%")
            elif short_trend < -3:
                score -= 10
                signals.append(f"5日下跌{short_trend:.1f}%")

        return max(0, min(100, score)), signals

    def score_momentum(self, closes: List[float], pct_chg: float) -> Tuple[float, List[str]]:
        """
        动量评分（0-100）

        评估维度：
        - 多周期涨跌幅
        - 动量方向一致性
        - 涨停/跌停状态
        """
        signals = []
        score = 50.0

        if len(closes) < 10:
            return score, signals

        # 5日动量
        m5 = (closes[0] - closes[4]) / closes[4] * 100
        # 10日动量
        m10 = (closes[0] - closes[9]) / closes[9] * 100

        # 动量一致性（短期和中期方向一致）
        if m5 > 0 and m10 > 0:
            score += 15
            signals.append("多周期上涨")
        elif m5 < 0 and m10 < 0:
            score -= 15
            signals.append("多周期下跌")

        # 动量强度
        if m5 > 5:
            score += 15
            signals.append(f"5日强势+{m5:.1f}%")
        elif m5 > 2:
            score += 8
        elif m5 < -5:
            score -= 15
            signals.append(f"5日弱势{m5:.1f}%")
        elif m5 < -2:
            score -= 8

        # 当日涨跌幅
        if pct_chg > 5:
            score += 10
            signals.append(f"当日大涨+{pct_chg:.1f}%")
        elif pct_chg > 2:
            score += 5
        elif pct_chg < -5:
            score -= 10
            signals.append(f"当日大跌{pct_chg:.1f}%")
        elif pct_chg < -2:
            score -= 5

        return max(0, min(100, score)), signals

    def score_volatility(self, data: List[StockData]) -> Tuple[float, List[str]]:
        """
        波动率评分（0-100）

        评估维度：
        - ATR（平均真实波幅）
        - 波动率方向（扩张/收缩）
        - 突破信号
        """
        signals = []
        score = 50.0

        if len(data) < 11:
            return score, signals

        closes = [d.close for d in data]
        highs = [d.high for d in data]
        lows = [d.low for d in data]
        vols = [d.vol for d in data]

        # 计算 ATR
        trs = []
        for i in range(len(highs) - 1):
            hl = highs[i] - lows[i]
            pc = closes[i + 1]  # newest-first, i+1 是前一日
            trs.append(max(hl, abs(highs[i] - pc), abs(lows[i] - pc)))

        if len(trs) < 5:
            return score, signals

        atr = sum(trs) / len(trs)
        avg_vol = sum(vols[1:6]) / 5
        vol_ratio = vols[0] / avg_vol if avg_vol > 0 else 1

        # 波动率突破（价格变动 > 1.5倍ATR）
        price_change = abs(closes[0] - closes[1])
        if price_change > atr * 1.5 and vol_ratio > 1.5:
            direction = "向上突破" if closes[0] > closes[1] else "向下突破"
            if direction == "向上突破":
                score += 20
                signals.append(f"放量突破ATR (量比{vol_ratio:.1f})")
            else:
                score -= 15
                signals.append(f"放量下跌突破ATR")

        # 波动率收缩（蓄势）
        recent_atr = sum(trs[:5]) / 5
        old_atr = sum(trs[5:]) / len(trs[5:]) if len(trs) > 5 else recent_atr
        if old_atr > 0 and recent_atr < old_atr * 0.7:
            score += 10
            signals.append("波动率收缩，蓄势中")

        # 量价配合
        if vol_ratio > 2:
            signals.append(f"放量{vol_ratio:.1f}倍")
            if closes[0] > closes[1]:
                score += 10  # 放量上涨
            else:
                score -= 10  # 放量下跌
        elif vol_ratio < 0.5:
            signals.append("缩量")
            score += 5  # 缩量企稳

        return max(0, min(100, score)), signals

    def score_volume(self, data: List[StockData]) -> Tuple[float, List[str]]:
        """
        资金面评分（0-100）

        评估维度：
        - 成交额水平
        - 量比变化
        - 资金流向趋势
        """
        signals = []
        score = 50.0

        if len(data) < 6:
            return score, signals

        vols = [d.vol for d in data]
        amounts = [d.amount for d in data]

        # 量比（当日/5日均量）
        avg_vol = sum(vols[1:6]) / 5
        vol_ratio = vols[0] / avg_vol if avg_vol > 0 else 1

        if vol_ratio > 2:
            score += 20
            signals.append(f"显著放量 (量比{vol_ratio:.1f})")
        elif vol_ratio > 1.3:
            score += 10
            signals.append(f"温和放量 (量比{vol_ratio:.1f})")
        elif vol_ratio < 0.5:
            score -= 10
            signals.append("极度缩量")
        elif vol_ratio < 0.7:
            score -= 5
            signals.append("缩量")

        # 成交额趋势（资金是否持续流入）
        if len(amounts) >= 5:
            recent_avg = sum(amounts[:5]) / 5
            old_avg = sum(amounts[5:10]) / 5 if len(amounts) >= 10 else recent_avg
            if old_avg > 0 and recent_avg > old_avg * 1.2:
                score += 10
                signals.append("成交额放大趋势")
            elif old_avg > 0 and recent_avg < old_avg * 0.8:
                score -= 10
                signals.append("成交额萎缩趋势")

        return max(0, min(100, score)), signals

    def score_pattern(self, data: List[StockData]) -> Tuple[float, List[str]]:
        """
        技术形态评分（0-100）

        评估维度：
        - K线形态（阳线/阴线/十字星）
        - 上下影线
        - 连续涨跌
        - 缺口
        """
        signals = []
        score = 50.0

        if not data:
            return score, signals

        cur = data[0]
        body = abs(cur.close - cur.open)
        upper_shadow = cur.high - max(cur.close, cur.open)
        lower_shadow = min(cur.close, cur.open) - cur.low
        body_pct = body / cur.close * 100 if cur.close > 0 else 0

        # 大阳线
        if cur.close > cur.open and body_pct > 3:
            score += 15
            signals.append("大阳线")
        # 大阴线
        elif cur.close < cur.open and body_pct > 3:
            score -= 15
            signals.append("大阴线")
        # 十字星（放在小阳/小阴之前，否则会被 elif 阻隔）
        elif body_pct < 0.5:
            score += 5
            signals.append("十字星（变盘信号）")
        # 小阳线
        elif cur.close > cur.open:
            score += 5
            signals.append("小阳线")
        # 小阴线
        elif cur.close < cur.open:
            score -= 5
            signals.append("小阴线")

        # 下影线（支撑）
        if lower_shadow > body * 2 and cur.close > cur.open:
            score += 10
            signals.append("长下影线（强支撑）")

        # 上影线（压力）
        if upper_shadow > body * 2:
            score -= 5
            signals.append("长上影线（上方压力）")

        # 连续涨跌
        if len(data) >= 3:
            consecutive_up = all(data[i].close > data[i].open for i in range(min(3, len(data))))
            consecutive_down = all(data[i].close < data[i].open for i in range(min(3, len(data))))

            if consecutive_up:
                score += 10
                signals.append(f"连续{min(3, len(data))}日阳线")
            elif consecutive_down:
                score -= 10
                signals.append(f"连续{min(3, len(data))}日阴线")

        # 跳空缺口
        if len(data) >= 2:
            gap_up = data[0].low > data[1].high
            gap_down = data[0].high < data[1].low
            if gap_up:
                score += 10
                signals.append("向上跳空缺口")
            elif gap_down:
                score -= 10
                signals.append("向下跳空缺口")

        return max(0, min(100, score)), signals

    # ==================== 综合推荐 ====================

    def score_stock(self, ts_code: str, data: List[StockData]) -> Optional[StockScore]:
        """
        对单只股票进行综合评分

        Args:
            ts_code: 股票代码
            data: 日线数据列表（newest-first）

        Returns:
            StockScore 评分结果
        """
        if not data or len(data) < 5:
            logger.warning(f"{ts_code} 数据不足，无法评分")
            return None

        closes = [d.close for d in data]
        cur = data[0]

        # 各维度评分
        trend_score, trend_signals = self.score_trend(closes)
        momentum_score, momentum_signals = self.score_momentum(closes, cur.pct_chg)
        volatility_score, volatility_signals = self.score_volatility(data)
        volume_score, volume_signals = self.score_volume(data)
        pattern_score, pattern_signals = self.score_pattern(data)

        # 加权综合评分
        total_score = (
            trend_score * 0.25 +
            momentum_score * 0.25 +
            volatility_score * 0.15 +
            volume_score * 0.20 +
            pattern_score * 0.15
        )

        # 汇总信号
        all_signals = trend_signals + momentum_signals + volatility_signals + volume_signals + pattern_signals

        # 风险等级
        if total_score >= 70:
            risk_level = "low"
        elif total_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "high"

        # 推荐理由
        recommendation = self._generate_recommendation(
            total_score, trend_score, momentum_score,
            volume_score, all_signals
        )

        return StockScore(
            ts_code=ts_code,
            name=cur.name,
            total_score=round(total_score, 1),
            trend_score=round(trend_score, 1),
            momentum_score=round(momentum_score, 1),
            volatility_score=round(volatility_score, 1),
            volume_score=round(volume_score, 1),
            pattern_score=round(pattern_score, 1),
            current_price=cur.close,
            change_pct=cur.pct_chg,
            recommendation=recommendation,
            risk_level=risk_level,
            signals=all_signals
        )

    def recommend_from_watchlist(
        self,
        watchlist: List[Dict],
        top_n: int = 10
    ) -> List[StockScore]:
        """
        从自选股中推荐

        Args:
            watchlist: 自选股列表 [{"code": "000001.SZ", "name": "平安银行"}, ...]
            top_n: 返回前N个推荐

        Returns:
            按综合评分排序的推荐列表
        """
        if not self.data_adapter:
            logger.error("未设置数据适配器，无法获取数据")
            return []

        scores = []
        for stock in watchlist:
            ts_code = stock["code"]
            try:
                data = self.data_adapter.get_stock_daily(ts_code, limit=30)
                if data:
                    score = self.score_stock(ts_code, data)
                    if score:
                        scores.append(score)
            except Exception as e:
                logger.warning(f"评分失败 {ts_code}: {e}")

        # 按综合评分排序
        scores.sort(key=lambda x: x.total_score, reverse=True)
        return scores[:top_n]

    def recommend_from_pool(
        self,
        pool_codes: List[str],
        top_n: int = 20
    ) -> List[StockScore]:
        """
        从股票池中推荐（可传入更大范围的股票代码列表）

        Args:
            pool_codes: 股票代码列表
            top_n: 返回前N个推荐

        Returns:
            按综合评分排序的推荐列表
        """
        return self.recommend_from_watchlist(
            [{"code": code, "name": ""} for code in pool_codes],
            top_n
        )

    def filter_anomaly_stocks(
        self,
        watchlist: List[Dict]
    ) -> List[StockScore]:
        """
        筛选异动股

        条件：
        - 涨跌幅超过5%
        - 量比超过2
        - 波动率突破ATR
        """
        if not self.data_adapter:
            return []

        anomalies = []
        for stock in watchlist:
            ts_code = stock["code"]
            try:
                data = self.data_adapter.get_stock_daily(ts_code, limit=20)
                if not data or len(data) < 6:
                    continue

                cur = data[0]
                closes = [d.close for d in data]
                vols = [d.vol for d in data]

                # 涨跌幅异动
                if abs(cur.pct_chg) < 5:
                    continue

                # 量比异动
                avg_vol = sum(vols[1:6]) / 5
                vol_ratio = vols[0] / avg_vol if avg_vol > 0 else 1
                if vol_ratio < 1.5:
                    continue

                score = self.score_stock(ts_code, data)
                if score:
                    score.signals.insert(0, f"异动: 涨跌{cur.pct_chg:+.1f}% 量比{vol_ratio:.1f}")
                    anomalies.append(score)

            except Exception as e:
                logger.warning(f"异动筛选失败 {ts_code}: {e}")

        anomalies.sort(key=lambda x: x.total_score, reverse=True)
        return anomalies

    @staticmethod
    def _generate_recommendation(
        total_score: float,
        trend_score: float,
        momentum_score: float,
        volume_score: float,
        signals: List[str]
    ) -> str:
        """生成推荐理由"""
        parts = []

        if total_score >= 75:
            parts.append("综合评分优秀")
        elif total_score >= 60:
            parts.append("综合评分良好")
        elif total_score >= 40:
            parts.append("综合评分一般")
        else:
            parts.append("综合评分偏低")

        if trend_score >= 70:
            parts.append("趋势向好")
        elif trend_score <= 30:
            parts.append("趋势走弱")

        if momentum_score >= 70:
            parts.append("动量充足")
        elif momentum_score <= 30:
            parts.append("动量不足")

        if volume_score >= 70:
            parts.append("资金活跃")

        # 关键信号
        key_signals = [s for s in signals if any(
            kw in s for kw in ["多头排列", "突破", "放量", "大阳线", "涨停"]
        )]
        if key_signals:
            parts.append(f"关键信号: {', '.join(key_signals[:3])}")

        return "；".join(parts)

    @staticmethod
    def format_recommendation(score: StockScore) -> str:
        """格式化单只股票推荐结果"""
        risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(score.risk_level, "⚪")
        lines = [
            f"{risk_icon} {score.ts_code} - {score.name}",
            f"   综合评分: {score.total_score:.1f}/100",
            f"   当前价: {score.current_price:.2f}元 ({score.change_pct:+.2f}%)",
            f"   评分明细: 趋势{score.trend_score:.0f} | 动量{score.momentum_score:.0f} | "
            f"波动{score.volatility_score:.0f} | 资金{score.volume_score:.0f} | 形态{score.pattern_score:.0f}",
        ]
        if score.signals:
            lines.append(f"   信号: {', '.join(score.signals[:5])}")
        lines.append(f"   建议: {score.recommendation}")
        return "\n".join(lines)

    @staticmethod
    def format_report(report: RecommendationReport) -> str:
        """格式化推荐报告"""
        lines = [
            "\n" + "=" * 70,
            f"  股票推荐报告 - {report.date}",
            f"  市场情绪: {report.market_sentiment}",
            "=" * 70,
        ]

        if report.warnings:
            lines.append("\n⚠️ 风险提示:")
            for w in report.warnings:
                lines.append(f"  - {w}")

        if report.recommendations:
            lines.append(f"\n📊 推荐排名 (共{len(report.recommendations)}只):\n")
            for i, score in enumerate(report.recommendations, 1):
                lines.append(f"  【第{i}名】")
                lines.append(StockRecommender.format_recommendation(score))
                lines.append("")

        else:
            lines.append("\n  当前无推荐标的，建议观望。")

        lines.append("=" * 70)
        return "\n".join(lines)
