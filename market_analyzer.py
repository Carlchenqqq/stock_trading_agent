#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场分析模块 - 基于股票高手交易大模型
====================================
包含市场情绪分析、板块轮动分析、资金流向分析
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from models import MarketSentiment, MarketPhase, MarketContext, SectorAnalysis

logger = logging.getLogger(__name__)


class MarketSentimentAnalyzer:
    """
    市场情绪分析器

    分析维度：
    1. 涨跌家数比
    2. 涨停跌停比
    3. 成交量变化
    4. 北向资金流向
    5. 恐慌贪婪指数
    """

    def analyze_sentiment(self, market_data: Dict) -> MarketSentiment:
        """
        分析市场情绪

        Args:
            market_data: 市场数据字典
                - advance_decline_ratio: 涨跌家数比
                - limit_up_down_ratio: 涨跌停比
                - volume_change: 成交量变化
                - northbound_flow: 北向资金流向
                - fear_greed_index: 恐慌贪婪指数
        """
        # 优先使用恐慌贪婪指数
        fear_greed = market_data.get('fear_greed_index', 50)

        if fear_greed < 20:
            return MarketSentiment.EXTREME_FEAR
        elif fear_greed < 40:
            return MarketSentiment.FEAR
        elif fear_greed < 60:
            return MarketSentiment.NEUTRAL
        elif fear_greed < 80:
            return MarketSentiment.GREED
        else:
            return MarketSentiment.EXTREME_GREED

    def get_sentiment_description(self, sentiment: MarketSentiment) -> str:
        """获取情绪描述"""
        descriptions = {
            MarketSentiment.EXTREME_FEAR: "极度恐慌 - 市场恐慌情绪蔓延，可能是抄底机会",
            MarketSentiment.FEAR: "恐慌 - 市场情绪偏空，谨慎操作",
            MarketSentiment.NEUTRAL: "中性 - 市场情绪平衡，结构性机会",
            MarketSentiment.GREED: "贪婪 - 市场情绪偏暖，注意风险",
            MarketSentiment.EXTREME_GREED: "极度贪婪 - 市场过热，警惕回调风险"
        }
        return descriptions.get(sentiment, "未知")

    def get_position_suggestion(self, sentiment: MarketSentiment) -> Dict:
        """
        根据情绪给出仓位建议

        原则：
        - 极度恐慌：重仓（别人恐惧我贪婪）
        - 恐慌：适度加仓
        - 中性：正常仓位
        - 贪婪：减仓
        - 极度贪婪：空仓
        """
        suggestions = {
            MarketSentiment.EXTREME_FEAR: {
                "position_limit": 0.8,
                "action": "积极布局",
                "reason": "市场恐慌，优质资产被错杀"
            },
            MarketSentiment.FEAR: {
                "position_limit": 0.6,
                "action": "逢低吸纳",
                "reason": "市场情绪偏空，但机会渐显"
            },
            MarketSentiment.NEUTRAL: {
                "position_limit": 0.5,
                "action": "均衡配置",
                "reason": "市场情绪平衡，精选个股"
            },
            MarketSentiment.GREED: {
                "position_limit": 0.3,
                "action": "逐步减仓",
                "reason": "市场情绪过热，锁定利润"
            },
            MarketSentiment.EXTREME_GREED: {
                "position_limit": 0.1,
                "action": "空仓观望",
                "reason": "市场极度贪婪，风险大于机会"
            }
        }
        return suggestions.get(sentiment, {"position_limit": 0.5, "action": "观望", "reason": "情绪不明"})


class MarketPhaseAnalyzer:
    """
    市场阶段分析器

    判断市场处于哪个阶段：
    - 底部区域：缩量下跌，估值低位
    - 上涨阶段：量价齐升，趋势向上
    - 顶部区域：放量滞涨，情绪狂热
    - 下跌阶段：量价齐跌，趋势向下
    """

    def analyze_phase(self, market_data: Dict) -> MarketPhase:
        """
        分析市场阶段

        Args:
            market_data: 市场数据
                - index_trend: 指数趋势（ma20方向）
                - volume_trend: 成交量趋势
                - valuation_level: 估值水平
                - market_breadth: 市场宽度
        """
        trend = market_data.get('index_trend', 'sideways')
        volume = market_data.get('volume_trend', 'stable')
        valuation = market_data.get('valuation_level', 'normal')

        # 底部特征：趋势向下+缩量+低估值
        if trend == 'down' and volume == 'shrinking' and valuation == 'low':
            return MarketPhase.BOTTOM

        # 上涨特征：趋势向上+放量
        elif trend == 'up' and volume == 'expanding':
            return MarketPhase.RISING

        # 顶部特征：趋势向上+放量滞涨或缩量
        elif trend == 'up' and volume in ['stable', 'shrinking']:
            return MarketPhase.TOP

        # 下跌特征：趋势向下+放量
        elif trend == 'down' and volume == 'expanding':
            return MarketPhase.FALLING

        else:
            return MarketPhase.CONSOLIDATION

    def get_phase_strategy(self, phase: MarketPhase) -> Dict:
        """获取阶段策略"""
        strategies = {
            MarketPhase.BOTTOM: {
                "strategy": "左侧布局",
                "action": "分批建仓",
                "focus": "价值股、超跌股",
                "risk": "可能继续探底，控制仓位"
            },
            MarketPhase.RISING: {
                "strategy": "顺势而为",
                "action": "持股待涨",
                "focus": "强势股、龙头股",
                "risk": "避免追高，设好止损"
            },
            MarketPhase.TOP: {
                "strategy": "逢高减仓",
                "action": "逐步获利了结",
                "focus": "减仓为主",
                "risk": "警惕突然转向"
            },
            MarketPhase.FALLING: {
                "strategy": "空仓观望",
                "action": "止损离场",
                "focus": "现金为王",
                "risk": "不轻易抄底"
            },
            MarketPhase.CONSOLIDATION: {
                "strategy": "区间操作",
                "action": "高抛低吸",
                "focus": "震荡强势品种",
                "risk": "避免追涨杀跌"
            }
        }
        return strategies.get(phase, {"strategy": "观望", "action": "等待", "focus": "", "risk": ""})


class SectorRotationAnalyzer:
    """
    板块轮动分析器

    分析板块强度和资金流向，识别：
    - 当前热点板块
    - 板块轮动节奏
    - 资金流入流出
    """

    def analyze_sectors(self, sector_data: List[Dict]) -> List[SectorAnalysis]:
        """
        分析板块数据

        Args:
            sector_data: 板块数据列表
                - name: 板块名称
                - change_pct: 涨跌幅
                - volume_ratio: 量比
                - money_flow: 资金流向
        """
        analyses = []

        for data in sector_data:
            change = data.get('change_pct', 0)
            volume = data.get('volume_ratio', 1)
            flow = data.get('money_flow', 0)

            # 判断趋势强度
            if change > 3 and volume > 1.5 and flow > 0:
                trend = 'strong'
            elif change > 0 and flow >= 0:
                trend = 'moderate'
            else:
                trend = 'weak'

            # 判断资金流向
            if flow > 100000000:  # 1亿
                money_flow_status = 'inflow'
            elif flow < -100000000:
                money_flow_status = 'outflow'
            else:
                money_flow_status = 'neutral'

            analysis = SectorAnalysis(
                sector_name=data.get('name', ''),
                trend=trend,
                money_flow=money_flow_status,
                leading_stocks=data.get('leading_stocks', []),
                strength_rank=0  # 后续排序
            )
            analyses.append(analysis)

        # 按强度排序
        analyses.sort(key=lambda x: (x.trend == 'strong', x.money_flow == 'inflow'), reverse=True)
        for i, a in enumerate(analyses):
            a.strength_rank = i + 1

        return analyses

    def identify_hot_sectors(self, analyses: List[SectorAnalysis], top_n: int = 3) -> List[str]:
        """识别热点板块"""
        hot = [a for a in analyses if a.trend == 'strong' and a.money_flow == 'inflow']
        return [a.sector_name for a in hot[:top_n]]

    def get_sector_rotation_advice(self, analyses: List[SectorAnalysis]) -> Dict:
        """获取板块轮动建议"""
        hot_sectors = self.identify_hot_sectors(analyses)

        if len(hot_sectors) >= 3:
            return {
                "market_status": "热点活跃",
                "strategy": "积极参与热点",
                "focus_sectors": hot_sectors,
                "risk": "注意热点切换节奏"
            }
        elif len(hot_sectors) >= 1:
            return {
                "market_status": "结构性行情",
                "strategy": "精选热点板块",
                "focus_sectors": hot_sectors,
                "risk": "避免追高风险"
            }
        else:
            return {
                "market_status": "热点匮乏",
                "strategy": "控制仓位观望",
                "focus_sectors": [],
                "risk": "市场缺乏主线"
            }


class MoneyFlowAnalyzer:
    """
    资金流向分析器

    分析：
    - 北向资金流向
    - 主力资金流向
    - 板块资金流向
    - 个股资金流向
    """

    def analyze_northbound_flow(self, flow_data: Dict) -> Dict:
        """
        分析北向资金流向

        Args:
            flow_data: 北向资金数据
                - daily_net: 当日净流入
                - weekly_net: 本周净流入
                - monthly_net: 本月净流入
                - cumulative: 累计持仓
        """
        daily = flow_data.get('daily_net', 0)
        weekly = flow_data.get('weekly_net', 0)

        # 判断流向趋势
        if daily > 5000000000:  # 50亿
            trend = "大幅流入"
            signal = "强烈看多"
        elif daily > 0:
            trend = "小幅流入"
            signal = "偏多"
        elif daily > -5000000000:
            trend = "小幅流出"
            signal = "偏空"
        else:
            trend = "大幅流出"
            signal = "强烈看空"

        return {
            "daily_flow": daily,
            "weekly_flow": weekly,
            "trend": trend,
            "signal": signal
        }

    def analyze_main_force_flow(self, flow_data: Dict) -> Dict:
        """
        分析主力资金流向

        Args:
            flow_data: 主力资金数据
                - large_order_net: 大单净流入
                - medium_order_net: 中单净流入
                - small_order_net: 小单净流入
        """
        large = flow_data.get('large_order_net', 0)
        medium = flow_data.get('medium_order_net', 0)

        # 主力动向
        if large > 0 and medium > 0:
            main_force = "积极进场"
        elif large > 0:
            main_force = "主力吸筹"
        elif large < 0 and medium < 0:
            main_force = "主力出逃"
        else:
            main_force = "观望"

        return {
            "large_order": large,
            "medium_order": medium,
            "main_force": main_force
        }

    def detect_capital_concentration(self, stock_flows: List[Dict]) -> List[str]:
        """
        检测资金集中度高的个股

        Returns:
            资金大幅流入的股票列表
        """
        concentrated = []
        for stock in stock_flows:
            code = stock.get('code', '')
            net_inflow = stock.get('net_inflow', 0)
            flow_ratio = stock.get('flow_ratio', 0)

            # 资金大幅流入且占比高
            if net_inflow > 100000000 and flow_ratio > 0.1:  # 1亿且占比10%
                concentrated.append(code)

        return concentrated


class MarketAnalyzer:
    """
    市场分析主类

    整合所有分析模块，提供完整的市场分析
    """

    def __init__(self):
        self.sentiment_analyzer = MarketSentimentAnalyzer()
        self.phase_analyzer = MarketPhaseAnalyzer()
        self.sector_analyzer = SectorRotationAnalyzer()
        self.money_flow_analyzer = MoneyFlowAnalyzer()

    def comprehensive_analysis(
        self,
        market_data: Dict,
        sector_data: List[Dict],
        flow_data: Dict
    ) -> MarketContext:
        """
        综合分析市场环境

        Returns:
            MarketContext: 市场环境上下文
        """
        # 情绪分析
        sentiment = self.sentiment_analyzer.analyze_sentiment(market_data)

        # 阶段分析
        phase = self.phase_analyzer.analyze_phase(market_data)

        # 板块分析
        sector_analyses = self.sector_analyzer.analyze_sectors(sector_data)
        leading_sectors = self.sector_analyzer.identify_hot_sectors(sector_analyses)

        # 资金流向
        northbound = self.money_flow_analyzer.analyze_northbound_flow(flow_data)

        # 判断指数趋势
        index_trend = market_data.get('index_trend', 'sideways')
        volume_status = market_data.get('volume_status', 'normal')

        # 风险评估
        risk_level = self._assess_risk(sentiment, phase, northbound)

        return MarketContext(
            sentiment=sentiment,
            phase=phase,
            index_trend=index_trend,
            volume_status=volume_status,
            leading_sectors=leading_sectors,
            risk_level=risk_level
        )

    def _assess_risk(
        self,
        sentiment: MarketSentiment,
        phase: MarketPhase,
        northbound: Dict
    ) -> str:
        """评估风险等级"""
        risk_score = 0

        # 情绪风险
        if sentiment == MarketSentiment.EXTREME_GREED:
            risk_score += 2
        elif sentiment == MarketSentiment.GREED:
            risk_score += 1

        # 阶段风险
        if phase in [MarketPhase.TOP, MarketPhase.FALLING]:
            risk_score += 2
        elif phase == MarketPhase.CONSOLIDATION:
            risk_score += 1

        # 资金流向风险
        if northbound.get('signal') == "强烈看空":
            risk_score += 2
        elif northbound.get('signal') == "偏空":
            risk_score += 1

        if risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"

    def generate_daily_market_report(
        self,
        market_data: Dict,
        sector_data: List[Dict],
        flow_data: Dict
    ) -> Dict:
        """生成每日市场报告"""
        context = self.comprehensive_analysis(market_data, sector_data, flow_data)

        # 情绪建议
        sentiment_suggestion = self.sentiment_analyzer.get_position_suggestion(context.sentiment)

        # 阶段策略
        phase_strategy = self.phase_analyzer.get_phase_strategy(context.phase)

        # 板块建议
        sector_analyses = self.sector_analyzer.analyze_sectors(sector_data)
        sector_advice = self.sector_analyzer.get_sector_rotation_advice(sector_analyses)

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "market_summary": {
                "sentiment": context.sentiment.value,
                "sentiment_desc": self.sentiment_analyzer.get_sentiment_description(context.sentiment),
                "phase": context.phase.value,
                "risk_level": context.risk_level,
                "index_trend": context.index_trend
            },
            "strategy": {
                "position_limit": sentiment_suggestion["position_limit"],
                "action": sentiment_suggestion["action"],
                "phase_strategy": phase_strategy["strategy"],
                "phase_action": phase_strategy["action"]
            },
            "sectors": {
                "leading_sectors": context.leading_sectors,
                "market_status": sector_advice["market_status"],
                "focus_sectors": sector_advice["focus_sectors"]
            },
            "risks": [
                sentiment_suggestion["reason"],
                phase_strategy["risk"],
                sector_advice["risk"]
            ]
        }


# 便捷函数
def quick_market_check(market_data: Dict) -> Dict:
    """快速市场检查"""
    analyzer = MarketAnalyzer()
    sentiment = analyzer.sentiment_analyzer.analyze_sentiment(market_data)
    suggestion = analyzer.sentiment_analyzer.get_position_suggestion(sentiment)

    return {
        "sentiment": sentiment.value,
        "position_limit": suggestion["position_limit"],
        "action": suggestion["action"]
    }
