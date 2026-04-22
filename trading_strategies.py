#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票交易策略模块 - 基于股票高手交易大模型
========================================
包含7种短线交易武器模式及配套策略
"""

from typing import Dict, List, Optional, Tuple
import logging

from models import PatternType, PatternSignal

logger = logging.getLogger(__name__)


class ShortTermPatterns:
    """
    短线交易7种武器模式分析器

    核心理念：
    - 只做确定性高的交易
    - 严格止损，让利润奔跑
    - 顺势而为，不逆势操作
    """

    @staticmethod
    def analyze_first_limit_up(stock_data: Dict) -> Optional[PatternSignal]:
        """
        首板模式分析

        特征：
        - 当日首次涨停
        - 封板坚决，成交量适中
        - 题材热点加持

        买点：次日开盘观察，强势可追
        止损：-5%
        """
        if not stock_data.get('is_limit_up', False):
            return None

        if stock_data.get('limit_up_days', 0) != 1:
            return None

        # 封板质量评估
        seal_quality = stock_data.get('seal_quality', 0)
        volume_ratio = stock_data.get('volume_ratio', 1)

        # 封板坚决且成交量合理
        if seal_quality >= 0.8 and 1.5 <= volume_ratio <= 5:
            confidence = 0.75
        elif seal_quality >= 0.6:
            confidence = 0.65
        else:
            confidence = 0.5

        current_price = stock_data.get('current_price', 0)

        return PatternSignal(
            pattern_type=PatternType.FIRST_LIMIT_UP,
            confidence=confidence,
            entry_price=current_price * 1.02,  # 次日高开2%
            stop_loss=current_price * 0.95,
            take_profit=current_price * 1.15,
            description="首板涨停，封板坚决，关注次日溢价机会",
            risk_reward_ratio=2.5
        )

    @staticmethod
    def analyze_consecutive_limit(stock_data: Dict) -> Optional[PatternSignal]:
        """
        连板模式分析

        特征：
        - 连续2个及以上涨停
        - 市场龙头或板块龙头
        - 换手充分，不缩量加速

        买点：分歧转一致时
        止损：断板即走
        """
        limit_days = stock_data.get('limit_up_days', 0)

        if limit_days < 2:
            return None

        current_price = stock_data.get('current_price', 0)

        # 根据连板天数调整置信度
        if limit_days >= 5:
            confidence = 0.6  # 高位风险大
        elif limit_days >= 3:
            confidence = 0.75
        else:
            confidence = 0.8

        return PatternSignal(
            pattern_type=PatternType.CONSECUTIVE_LIMIT,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=current_price * 0.93,  # 断板即走
            take_profit=current_price * 1.20,
            description=f"连续{limit_days}个涨停，龙头特征明显",
            risk_reward_ratio=2.0
        )

    @staticmethod
    def analyze_anti_package(stock_data: Dict) -> Optional[PatternSignal]:
        """
        反包模式分析

        特征：
        - 前一日断板或下跌
        - 次日强势反包涨停
        - 量能配合，资金回流

        买点：反包确认时
        止损：反包失败
        """
        if not stock_data.get('is_limit_up', False):
            return None

        prev_day_change = stock_data.get('previous_day_change', 0)

        # 前一日下跌或断板
        if prev_day_change > -3:
            return None

        current_price = stock_data.get('current_price', 0)
        volume_surge = stock_data.get('volume_surge', False)

        confidence = 0.75 if volume_surge else 0.65

        return PatternSignal(
            pattern_type=PatternType.ANTI_PACKAGE,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=current_price * 0.95,
            take_profit=current_price * 1.12,
            description="断板后强势反包，资金回流明显",
            risk_reward_ratio=2.0
        )

    @staticmethod
    def analyze_pullback_buy(stock_data: Dict) -> Optional[PatternSignal]:
        """
        低吸模式分析

        特征：
        - 强势股回调5-15%
        - 缩量回调，未破关键支撑
        - 趋势仍然向上

        买点：缩量企稳时
        止损：跌破支撑位
        """
        pullback = stock_data.get('pullback_pct', 0)
        trend = stock_data.get('trend', '')
        volume_shrink = stock_data.get('volume_shrink', False)

        # 回调幅度检查
        if not (5 <= pullback <= 15):
            return None

        # 趋势检查
        if trend != 'strong':
            return None

        current_price = stock_data.get('current_price', 0)
        support_price = stock_data.get('support_price', current_price * 0.9)

        confidence = 0.7 if volume_shrink else 0.6

        return PatternSignal(
            pattern_type=PatternType.PULLBACK_BUY,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=support_price * 0.98,  # 支撑位下方2%
            take_profit=current_price * 1.10,
            description=f"强势股回调{pullback:.1f}%，缩量企稳可低吸",
            risk_reward_ratio=1.8
        )

    @staticmethod
    def analyze_limit_up_buy(stock_data: Dict) -> Optional[PatternSignal]:
        """
        打板模式分析

        特征：
        - 涨停瞬间买入
        - 封单坚决，排板买入
        - 板块效应明显

        买点：涨停瞬间
        止损：开板回落
        """
        if not stock_data.get('is_limit_up', False):
            return None

        # 已经在涨停板上，无法买入时跳过
        if not stock_data.get('can_buy', True):
            return None

        current_price = stock_data.get('current_price', 0)
        sector_effect = stock_data.get('sector_effect', False)

        confidence = 0.7 if sector_effect else 0.6

        return PatternSignal(
            pattern_type=PatternType.LIMIT_UP_BUY,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=current_price * 0.97,  # 开板即走
            take_profit=current_price * 1.10,
            description="涨停打板，板块效应明显",
            risk_reward_ratio=1.5
        )

    @staticmethod
    def analyze_end_day_surge(stock_data: Dict) -> Optional[PatternSignal]:
        """
        尾盘模式分析

        特征：
        - 尾盘30分钟快速拉升
        - 成交量放大
        - 资金抢筹迹象

        买点：尾盘确认拉升
        止损：次日低开
        """
        end_day_change = stock_data.get('end_day_change', 0)
        end_day_volume = stock_data.get('end_day_volume_surge', False)

        # 尾盘涨幅检查
        if end_day_change < 3:
            return None

        if not end_day_volume:
            return None

        current_price = stock_data.get('current_price', 0)

        return PatternSignal(
            pattern_type=PatternType.END_DAY_SURGE,
            confidence=0.65,
            entry_price=current_price,
            stop_loss=current_price * 0.96,
            take_profit=current_price * 1.08,
            description="尾盘资金抢筹，关注次日高开",
            risk_reward_ratio=1.5
        )

    @staticmethod
    def analyze_opening_rush(stock_data: Dict) -> Optional[PatternSignal]:
        """
        竞价模式分析

        特征：
        - 集合竞价大幅高开
        - 竞价成交量放大
        - 隔夜单或抢筹迹象

        买点：竞价确认强势
        止损：开盘回落
        """
        auction_change = stock_data.get('auction_change', 0)
        auction_volume = stock_data.get('auction_volume_ratio', 0)

        # 竞价高开检查
        if auction_change < 5:
            return None

        # 竞价成交量检查
        if auction_volume < 2:
            return None

        current_price = stock_data.get('current_price', 0)

        confidence = 0.7 if auction_change >= 7 else 0.6

        return PatternSignal(
            pattern_type=PatternType.OPENING_RUSH,
            confidence=confidence,
            entry_price=current_price * (1 + auction_change/100),
            stop_loss=current_price * 0.95,
            take_profit=current_price * 1.15,
            description=f"竞价高开{auction_change:.1f}%，资金抢筹明显",
            risk_reward_ratio=2.0
        )


class PositionManagement:
    """
    仓位管理策略

    核心原则：
    1. 单笔风险不超过总资金的2%
    2. 根据市场环境调整总仓位
    3. 分散投资，避免过度集中
    """

    @staticmethod
    def calculate_position_size(
        total_capital: float,
        entry_price: float,
        stop_loss: float,
        risk_pct: float = 0.02
    ) -> int:
        """
        计算仓位大小

        Args:
            total_capital: 总资金
            entry_price: 入场价格
            stop_loss: 止损价格
            risk_pct: 单笔风险比例

        Returns:
            建议买入股数
        """
        risk_amount = total_capital * risk_pct
        price_risk = abs(entry_price - stop_loss)

        if price_risk <= 0:
            return 0

        shares = int(risk_amount / price_risk)

        # 确保100股整数倍（A股）
        shares = (shares // 100) * 100

        if shares < 100:
            logger.warning("计算仓位小于100股，建议放弃该交易")
            return 0

        return shares

    @staticmethod
    def get_sector_position_limit(sector_count: int) -> float:
        """
        根据板块数量确定单板块仓位上限

        原则：分散投资，单板块不超过总仓位的30%
        """
        if sector_count <= 2:
            return 0.5  # 最多50%
        elif sector_count <= 4:
            return 0.3  # 最多30%
        else:
            return 0.2  # 最多20%

    @staticmethod
    def pyramid_position(
        base_position: int,
        current_price: float,
        avg_cost: float,
        profit_pct: float
    ) -> int:
        """
        金字塔加仓策略

        原则：
        - 盈利后才加仓
        - 每次加仓量递减
        - 加仓后止损位上移
        """
        if profit_pct < 5:
            return 0  # 盈利不足5%不加仓

        # 加仓量为上次的一半
        add_position = base_position // 2
        add_position = (add_position // 100) * 100

        return add_position


class RiskManagement:
    """
    风险管理模块

    核心原则：
    1. 活着最重要
    2. 截断亏损，让利润奔跑
    3. 绝不补仓摊低成本（除非有明确计划）
    """

    STOP_LOSS_PCT = {
        'day_trading': 0.05,      # 短线5%
        'swing_trading': 0.08,    # 波段8%
        'position_trading': 0.10  # 持仓10%
    }

    TAKE_PROFIT_PCT = {
        'day_trading': 0.10,      # 短线10%
        'swing_trading': 0.15,    # 波段15%
        'position_trading': 0.25  # 持仓25%
    }

    @classmethod
    def get_stop_loss_price(
        cls,
        entry_price: float,
        trade_type: str = 'day_trading'
    ) -> float:
        """获取止损价格"""
        stop_pct = cls.STOP_LOSS_PCT.get(trade_type, 0.05)
        return entry_price * (1 - stop_pct)

    @classmethod
    def get_take_profit_price(
        cls,
        entry_price: float,
        trade_type: str = 'day_trading'
    ) -> float:
        """获取止盈价格"""
        profit_pct = cls.TAKE_PROFIT_PCT.get(trade_type, 0.10)
        return entry_price * (1 + profit_pct)

    @staticmethod
    def trailing_stop(
        highest_price: float,
        current_price: float,
        trailing_pct: float = 0.10
    ) -> bool:
        """
        移动止损

        当股价从最高点回落超过trailing_pct时触发
        """
        if highest_price <= 0:
            return False

        drawdown = (highest_price - current_price) / highest_price
        return drawdown >= trailing_pct

    @staticmethod
    def calculate_portfolio_risk(
        positions: Dict,
        total_capital: float
    ) -> Dict:
        """计算组合风险"""
        if not positions:
            return {
                'total_risk': 0,
                'max_drawdown': 0,
                'concentration_risk': 0
            }

        total_risk = 0
        position_values = []

        for code, pos in positions.items():
            position_value = pos.get('market_value', 0)
            position_values.append(position_value)

            # 计算单个头寸风险
            stop_loss = pos.get('stop_loss', 0)
            entry_price = pos.get('entry_price', 0)
            quantity = pos.get('quantity', 0)

            if stop_loss > 0 and entry_price > 0:
                risk_per_share = entry_price - stop_loss
                position_risk = risk_per_share * quantity
                total_risk += position_risk

        # 集中度风险（最大头寸占比）
        max_position = max(position_values) if position_values else 0
        concentration_risk = max_position / total_capital if total_capital > 0 else 0

        return {
            'total_risk': total_risk,
            'total_risk_pct': total_risk / total_capital if total_capital > 0 else 0,
            'max_drawdown': 0,  # 需要历史数据计算
            'concentration_risk': concentration_risk
        }


class TrappedPositionStrategy:
    """
    被套应对策略

    核心原则：
    1. 区分主动被套和被动被套
    2. 趋势坏了必须止损
    3. 时间换空间要有计划
    """

    @staticmethod
    def analyze_trapped_situation(
        entry_price: float,
        current_price: float,
        holding_days: int,
        trend_status: str
    ) -> Dict:
        """
        分析被套情况

        Returns:
            应对策略建议
        """
        loss_pct = (current_price - entry_price) / entry_price * 100

        # 轻度浮亏
        if loss_pct > -3:
            return {
                'status': 'mild_loss',
                'action': 'hold',
                'reason': '浮亏在可接受范围，观察等待',
                'plan': ['设置止损位', '观察3天内能否反弹']
            }

        # 中度浮亏
        elif loss_pct > -7:
            return {
                'status': 'moderate_loss',
                'action': 'reduce',
                'reason': '触及短线止损线，需要减仓',
                'plan': ['减仓50%', '剩余设置更严格止损']
            }

        # 深度被套
        elif loss_pct > -15:
            # 判断趋势
            if trend_status == 'deteriorating':
                return {
                    'status': 'deep_loss_bad_trend',
                    'action': 'stop_loss',
                    'reason': '趋势恶化，必须止损',
                    'plan': ['果断止损', '避免更大损失']
                }
            else:
                return {
                    'status': 'deep_loss_good_trend',
                    'action': 'plan',
                    'reason': '深度套牢但趋势尚可，制定解套计划',
                    'plan': [
                        '1. 停止继续买入',
                        '2. 分析被套原因',
                        '3. 制定分批补仓计划（如适用）',
                        '4. 设置新的止损位',
                        '5. 设定解套目标和时间'
                    ]
                }

        # 严重套牢
        else:
            return {
                'status': 'severe_loss',
                'action': 'emergency',
                'reason': '亏损超过15%，必须采取行动',
                'plan': ['立即止损', '保留本金', '总结教训']
            }

    @staticmethod
    def calculate_average_down_plan(
        current_price: float,
        current_shares: int,
        avg_cost: float,
        available_cash: float,
        target_cost_reduction: float = 0.1
    ) -> Optional[Dict]:
        """
        计算补仓摊低成本计划

        警告：补仓是双刃剑，仅在以下情况使用：
        1. 基本面没有恶化
        2. 有明确止跌信号
        3. 有充足资金计划
        """
        current_cost = avg_cost * current_shares
        target_avg_cost = avg_cost * (1 - target_cost_reduction)

        # 计算需要买入的股数
        # (current_cost + new_cost) / (current_shares + new_shares) = target_avg_cost
        # 假设以current_price买入

        if current_price >= avg_cost:
            return None  # 不追高补仓

        # 简化计算
        max_new_shares = int(available_cash / current_price / 100) * 100

        if max_new_shares < 100:
            return None

        new_cost = current_price * max_new_shares
        total_shares = current_shares + max_new_shares
        new_avg_cost = (current_cost + new_cost) / total_shares

        cost_reduction = (avg_cost - new_avg_cost) / avg_cost

        return {
            'buy_shares': max_new_shares,
            'buy_price': current_price,
            'new_avg_cost': new_avg_cost,
            'cost_reduction_pct': cost_reduction * 100,
            'total_investment': current_cost + new_cost,
            'warning': '补仓有风险，请确保基本面良好'
        }


# 便捷函数
def analyze_all_patterns(stock_data: Dict) -> List[PatternSignal]:
    """分析所有模式，返回所有匹配的信号"""
    analyzer = ShortTermPatterns()
    signals = []

    methods = [
        analyzer.analyze_first_limit_up,
        analyzer.analyze_consecutive_limit,
        analyzer.analyze_anti_package,
        analyzer.analyze_pullback_buy,
        analyzer.analyze_limit_up_buy,
        analyzer.analyze_end_day_surge,
        analyzer.analyze_opening_rush
    ]

    for method in methods:
        signal = method(stock_data)
        if signal:
            signals.append(signal)

    # 按置信度排序
    signals.sort(key=lambda x: x.confidence, reverse=True)
    return signals
