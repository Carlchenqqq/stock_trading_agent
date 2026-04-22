#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据模型层
==============
消除各模块中的重复定义，提供统一的数据类型
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ==================== 枚举类型 ====================

class TradeMode(Enum):
    """交易模式"""
    DAY_TRADING = "day_trading"      # 日内交易
    SWING_TRADING = "swing_trading"  # 波段交易
    POSITION_TRADING = "position"    # 持仓交易


class MarketSentiment(Enum):
    """市场情绪"""
    EXTREME_FEAR = "extreme_fear"    # 极度恐慌 - 贪婪指数 < 20
    FEAR = "fear"                    # 恐慌 - 贪婪指数 20-40
    NEUTRAL = "neutral"              # 中性 - 贪婪指数 40-60
    GREED = "greed"                  # 贪婪 - 贪婪指数 60-80
    EXTREME_GREED = "extreme_greed"  # 极度贪婪 - 贪婪指数 > 80


class SignalType(Enum):
    """交易信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketPhase(Enum):
    """市场阶段"""
    BOTTOM = "bottom"                # 底部区域
    RISING = "rising"                # 上涨阶段
    TOP = "top"                      # 顶部区域
    FALLING = "falling"              # 下跌阶段
    CONSOLIDATION = "consolidation"  # 震荡整理


class PatternType(Enum):
    """交易模式类型"""
    FIRST_LIMIT_UP = "首板模式"          # 首次涨停
    CONSECUTIVE_LIMIT = "连板模式"       # 连续涨停
    ANTI_PACKAGE = "反包模式"            # 断板反包
    PULLBACK_BUY = "低吸模式"            # 回调低吸
    LIMIT_UP_BUY = "打板模式"            # 涨停打板
    END_DAY_SURGE = "尾盘模式"           # 尾盘异动
    OPENING_RUSH = "竞价模式"            # 竞价抢筹


# ==================== 数据类 ====================

@dataclass
class StockData:
    """股票日线数据（统一模型）"""
    ts_code: str
    name: str
    open: float
    high: float
    low: float
    close: float
    pre_close: float
    change: float
    pct_chg: float
    vol: float
    amount: float
    date: str = ""  # 交易日期 YYYYMMDD


@dataclass
class MarketSentimentData:
    """市场情绪数据"""
    date: str
    limit_up_count: int       # 涨停家数
    limit_down_count: int     # 跌停家数
    up_count: int             # 上涨家数
    down_count: int           # 下跌家数
    total_amount: float       # 总成交额
    sentiment_score: float    # 情绪分数 -1~1
    sentiment_label: str      # 情绪标签


@dataclass
class PatternSignal:
    """模式信号"""
    pattern_type: PatternType
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    description: str
    risk_reward_ratio: float


@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    stock_name: str
    entry_price: float
    current_price: float
    quantity: int
    entry_date: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    @property
    def profit_pct(self) -> float:
        """盈亏百分比"""
        return (self.current_price - self.entry_price) / self.entry_price * 100

    @property
    def market_value(self) -> float:
        """市值"""
        return self.current_price * self.quantity


@dataclass
class TradeSignal:
    """交易信号"""
    stock_code: str
    stock_name: str
    signal_type: SignalType  # 使用枚举替代字符串
    confidence: float        # 0-1
    reason: str
    suggested_price: float
    position_size_pct: float  # 建议仓位百分比
    stop_loss: float = 0.0
    take_profit: float = 0.0


@dataclass
class Account:
    """账户信息"""
    total_capital: float
    available_cash: float
    positions: Dict[str, Position] = field(default_factory=dict)

    @property
    def position_value(self) -> float:
        """持仓市值"""
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_value(self) -> float:
        """总资产"""
        return self.available_cash + self.position_value


@dataclass
class MarketContext:
    """市场环境"""
    sentiment: MarketSentiment
    phase: MarketPhase
    index_trend: str  # up, down, sideways
    volume_status: str  # high, normal, low
    leading_sectors: List[str] = field(default_factory=list)
    risk_level: str = "medium"  # low, medium, high


@dataclass
class SectorAnalysis:
    """板块分析"""
    sector_name: str
    trend: str  # strong, moderate, weak
    money_flow: str  # inflow, neutral, outflow
    leading_stocks: List[str] = field(default_factory=list)
    strength_rank: int = 0
