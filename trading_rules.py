#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股交易规则模块
==============
实现A股市场的交易规则校验，确保交易指令符合交易所规定。

规则覆盖：
1. 最低交易量（1手=100股）
2. 涨跌停限制（主板±10%，科创板/创业板±20%，ST股±5%，北交所±30%）
3. T+1 交易制度（当日买入次日方可卖出）
4. 最小价格变动单位（主板0.01元，科创板0.01元）
5. 委托数量限制（单笔最大100万股）
6. 新股申购规则
7. 交易时间校验
8. 融资融券限制
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ==================== A股交易常量 ====================

# 交易时间
MORNING_START = time(9, 30)
MORNING_END = time(11, 30)
AFTERNOON_START = time(13, 0)
AFTERNOON_END = time(15, 0)

# 集合竞价时间
AUCTION_START = time(9, 15)
AUCTION_END = time(9, 25)

# 数量限制
MIN_LOT_SIZE = 100           # 最小交易单位：1手 = 100股
MAX_SINGLE_ORDER = 1000000   # 单笔委托最大数量：100万股
MIN_PRICE_UNIT = 0.01        # 最小价格变动单位（元）

# 涨跌停限制
LIMIT_PCT = {
    "main": 10.0,       # 主板 ±10%
    "kcb": 20.0,        # 科创板 ±20%
    "cyb": 20.0,        # 创业板 ±20%
    "st": 5.0,          # ST/*ST ±5%
    "bse": 30.0,        # 北交所 ±30%
    "new_stock": {
        "main": 44.0,   # 主板新股首日 ±44%（前5个交易日无涨跌停）
        "kcb": 20.0,    # 科创板新股前5日无涨跌停，之后 ±20%
        "cyb": 20.0,    # 创业板新股前5日无涨跌停，之后 ±20%
    }
}

# 费率
COMMISSION_RATE = 0.00025    # 佣金 万2.5
COMMISSION_MIN = 5.0         # 最低佣金 5元
STAMP_DUTY_RATE = 0.001      # 印花税 千1（仅卖出）
TRANSFER_FEE_RATE = 0.00001  # 过户费 万0.1


@dataclass
class TradeCheckResult:
    """交易校验结果"""
    passed: bool
    reason: str
    adjusted_quantity: int = 0
    adjusted_price: float = 0.0
    fee: float = 0.0
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class TradingRules:
    """
    A股交易规则引擎

    提供交易前的规则校验，确保每笔交易符合交易所规定。
    """

    def __init__(self):
        self._today_bought: Dict[str, datetime] = {}  # 当日买入记录 {code: buy_time}

    @staticmethod
    def get_board_type(ts_code: str) -> str:
        """
        判断股票所属板块

        Args:
            ts_code: 股票代码（如 000001.SZ, 688001.SH, 300001.SZ）

        Returns:
            板块类型: main/kcb/cyb/bse/st
        """
        code = ts_code.split('.')[0]

        # ST 股（需要结合名称判断，此处仅通过代码前缀做基础判断）
        # 实际使用时应结合股票名称中的 ST 标识

        # 北交所：8 开头
        if code.startswith('8') or code.startswith('4'):
            return "bse"

        # 科创板：688 开头
        if code.startswith('688'):
            return "kcb"

        # 创业板：300 开头
        if code.startswith('300') or code.startswith('301'):
            return "cyb"

        # 主板：60/00 开头
        return "main"

    @staticmethod
    def get_limit_pct(board_type: str, is_st: bool = False) -> float:
        """
        获取涨跌停幅度

        Args:
            board_type: 板块类型
            is_st: 是否为ST股

        Returns:
            涨跌停幅度（百分比）
        """
        if is_st:
            return LIMIT_PCT["st"]
        return LIMIT_PCT.get(board_type, LIMIT_PCT["main"])

    @staticmethod
    def calculate_limit_price(
        pre_close: float,
        board_type: str,
        is_st: bool = False
    ) -> Tuple[float, float]:
        """
        计算涨跌停价格

        Args:
            pre_close: 前收盘价
            board_type: 板块类型
            is_st: 是否为ST股

        Returns:
            (涨停价, 跌停价)
        """
        limit_pct = TradingRules.get_limit_pct(board_type, is_st)

        # A股涨跌停价格计算：四舍五入到分
        limit_up = round(pre_close * (1 + limit_pct / 100), 2)
        limit_down = round(pre_close * (1 - limit_pct / 100), 2)

        return limit_up, limit_down

    def check_quantity(self, quantity: int) -> TradeCheckResult:
        """
        校验交易数量

        规则：
        - 最低交易量：100股（1手）
        - 单笔最大：100万股
        - 必须是100的整数倍
        """
        warnings = []

        if quantity <= 0:
            return TradeCheckResult(
                passed=False,
                reason=f"交易数量必须大于0，当前: {quantity}"
            )

        if quantity < MIN_LOT_SIZE:
            return TradeCheckResult(
                passed=False,
                reason=f"低于最低交易量 {MIN_LOT_SIZE}股（1手），当前: {quantity}股"
            )

        if quantity > MAX_SINGLE_ORDER:
            return TradeCheckResult(
                passed=False,
                reason=f"超过单笔最大委托量 {MAX_SINGLE_ORDER}股，当前: {quantity}股"
            )

        if quantity % MIN_LOT_SIZE != 0:
            adjusted = (quantity // MIN_LOT_SIZE) * MIN_LOT_SIZE
            warnings.append(
                f"交易数量调整为 {MIN_LOT_SIZE} 的整数倍: {quantity} -> {adjusted}股"
            )
            return TradeCheckResult(
                passed=True,
                reason="数量已调整为100股整数倍",
                adjusted_quantity=adjusted,
                warnings=warnings
            )

        return TradeCheckResult(
            passed=True,
            reason="交易数量合规",
            adjusted_quantity=quantity
        )

    def check_price(
        self,
        price: float,
        pre_close: float,
        board_type: str,
        is_st: bool = False,
        action: str = "BUY"
    ) -> TradeCheckResult:
        """
        校验委托价格

        规则：
        - 不能超过涨跌停价格
        - 最小价格变动单位：0.01元
        - 不能为负数或零
        """
        warnings = []

        if price <= 0:
            return TradeCheckResult(
                passed=False,
                reason=f"委托价格必须大于0，当前: {price}"
            )

        # 最小价格单位检查
        if round(price, 2) != price:
            adjusted = round(price, 2)
            warnings.append(f"价格调整为最小变动单位: {price} -> {adjusted}元")
            price = adjusted

        # 涨跌停价格检查
        limit_up, limit_down = self.calculate_limit_price(pre_close, board_type, is_st)

        if action == "BUY" and price > limit_up:
            return TradeCheckResult(
                passed=False,
                reason=f"买入价 {price}元 超过涨停价 {limit_up}元"
            )

        if action == "SELL" and price < limit_down:
            return TradeCheckResult(
                passed=False,
                reason=f"卖出价 {price}元 低于跌停价 {limit_down}元"
            )

        return TradeCheckResult(
            passed=True,
            reason="委托价格合规",
            adjusted_price=price,
            warnings=warnings
        )

    def check_t_plus_1(
        self,
        ts_code: str,
        action: str
    ) -> TradeCheckResult:
        """
        T+1 交易规则校验

        规则：当日买入的股票，当日不能卖出
        """
        if action != "SELL":
            return TradeCheckResult(passed=True, reason="买入不受T+1限制")

        if ts_code in self._today_bought:
            buy_time = self._today_bought[ts_code]
            return TradeCheckResult(
                passed=False,
                reason=f"T+1限制: {ts_code} 于 {buy_time.strftime('%H:%M:%S')} 买入，当日不可卖出"
            )

        return TradeCheckResult(passed=True, reason="T+1校验通过")

    def check_trading_time(self) -> TradeCheckResult:
        """
        校验是否在交易时间内

        交易时间：
        - 集合竞价：9:15-9:25
        - 连续竞价（上午）：9:30-11:30
        - 连续竞价（下午）：13:00-15:00
        """
        now = datetime.now().time()

        # 集合竞价
        if AUCTION_START <= now <= AUCTION_END:
            return TradeCheckResult(
                passed=True,
                reason="当前处于集合竞价时段 (9:15-9:25)"
            )

        # 上午连续竞价
        if MORNING_START <= now <= MORNING_END:
            return TradeCheckResult(
                passed=True,
                reason="当前处于上午交易时段 (9:30-11:30)"
            )

        # 下午连续竞价
        if AFTERNOON_START <= now <= AFTERNOON_END:
            return TradeCheckResult(
                passed=True,
                reason="当前处于下午交易时段 (13:00-15:00)"
            )

        return TradeCheckResult(
            passed=False,
            reason=f"当前时间 {now.strftime('%H:%M')} 不在交易时段内"
        )

    def check_is_trading_day(self) -> TradeCheckResult:
        """
        校验是否为交易日（简单判断周末，不含节假日）

        注意：精确的交易日判断需要交易日历数据
        """
        today = datetime.now()
        weekday = today.weekday()

        if weekday >= 5:  # 5=周六, 6=周日
            return TradeCheckResult(
                passed=False,
                reason=f"今天是{'周六' if weekday == 5 else '周日'}，非交易日"
            )

        return TradeCheckResult(
            passed=True,
            reason="今天是交易日（周末判断，不含节假日）"
        )

    def check_capital(
        self,
        price: float,
        quantity: int,
        available_cash: float,
        action: str = "BUY"
    ) -> TradeCheckResult:
        """
        校验资金是否充足

        包含交易费用计算
        """
        if action != "BUY":
            return TradeCheckResult(passed=True, reason="卖出不需要资金校验")

        amount = price * quantity
        fee = self.calculate_fee(price, quantity, is_sell=False)
        total_cost = amount + fee

        if total_cost > available_cash:
            shortage = total_cost - available_cash
            return TradeCheckResult(
                passed=False,
                reason=f"资金不足: 需要 {total_cost:.2f}元（含费用{fee:.2f}元），可用 {available_cash:.2f}元，缺口 {shortage:.2f}元"
            )

        return TradeCheckResult(
            passed=True,
            reason=f"资金充足: 需要 {total_cost:.2f}元，可用 {available_cash:.2f}元",
            fee=fee
        )

    @staticmethod
    def calculate_fee(
        price: float,
        quantity: int,
        is_sell: bool = False
    ) -> float:
        """
        计算交易费用

        A股费用结构：
        - 佣金：万2.5（最低5元）
        - 印花税：千1（仅卖出时收取）
        - 过户费：万0.1（买卖均收）
        """
        amount = price * quantity
        commission = max(amount * COMMISSION_RATE, COMMISSION_MIN)
        stamp_duty = amount * STAMP_DUTY_RATE if is_sell else 0
        transfer_fee = amount * TRANSFER_FEE_RATE
        return commission + stamp_duty + transfer_fee

    def validate_trade(
        self,
        ts_code: str,
        action: str,
        price: float,
        quantity: int,
        pre_close: float,
        available_cash: float = 0,
        is_st: bool = False,
        check_time: bool = True
    ) -> TradeCheckResult:
        """
        综合交易校验（一站式检查）

        Args:
            ts_code: 股票代码
            action: 操作类型 BUY/SELL
            price: 委托价格
            quantity: 委托数量
            pre_close: 前收盘价
            available_cash: 可用资金（买入时必填）
            is_st: 是否ST股
            check_time: 是否检查交易时间

        Returns:
            TradeCheckResult 包含校验结果和调整后的参数
        """
        board_type = self.get_board_type(ts_code)
        all_warnings = []
        adjusted_price = price
        adjusted_quantity = quantity
        total_fee = 0

        # 1. 交易时间校验
        if check_time:
            time_result = self.check_trading_time()
            if not time_result.passed:
                return time_result
            all_warnings.extend(time_result.warnings)

        # 2. 交易数量校验
        qty_result = self.check_quantity(quantity)
        if not qty_result.passed:
            return qty_result
        all_warnings.extend(qty_result.warnings)
        adjusted_quantity = qty_result.adjusted_quantity or quantity

        # 3. 委托价格校验
        price_result = self.check_price(price, pre_close, board_type, is_st, action)
        if not price_result.passed:
            return price_result
        all_warnings.extend(price_result.warnings)
        adjusted_price = price_result.adjusted_price or price

        # 4. T+1 校验（卖出时）
        t1_result = self.check_t_plus_1(ts_code, action)
        if not t1_result.passed:
            return t1_result
        all_warnings.extend(t1_result.warnings)

        # 5. 资金校验（买入时）
        if action == "BUY":
            capital_result = self.check_capital(
                adjusted_price, adjusted_quantity, available_cash, action
            )
            if not capital_result.passed:
                return capital_result
            total_fee = capital_result.fee
        else:
            # 卖出时也计算费用
            total_fee = self.calculate_fee(adjusted_price, adjusted_quantity, is_sell=True)

        # 涨跌停信息
        limit_up, limit_down = self.calculate_limit_price(pre_close, board_type, is_st)

        return TradeCheckResult(
            passed=True,
            reason="交易校验全部通过",
            adjusted_price=adjusted_price,
            adjusted_quantity=adjusted_quantity,
            fee=total_fee,
            warnings=all_warnings
        )

    def record_buy(self, ts_code: str):
        """记录当日买入（用于T+1校验）"""
        self._today_bought[ts_code] = datetime.now()
        logger.info(f"记录买入: {ts_code} (T+1锁定)")

    def clear_today_records(self):
        """清除当日买入记录（每个交易日开始时调用）"""
        self._today_bought.clear()

    @staticmethod
    def format_trade_summary(result: TradeCheckResult, ts_code: str, action: str) -> str:
        """格式化交易校验结果摘要"""
        status = "✅ 通过" if result.passed else "❌ 未通过"
        lines = [
            f"交易校验 {status}: {ts_code} {action}",
            f"  原因: {result.reason}",
        ]
        if result.adjusted_quantity:
            lines.append(f"  数量: {result.adjusted_quantity}股")
        if result.adjusted_price:
            lines.append(f"  价格: {result.adjusted_price:.2f}元")
        if result.fee:
            lines.append(f"  费用: {result.fee:.2f}元")
        if result.warnings:
            for w in result.warnings:
                lines.append(f"  ⚠️ {w}")
        return "\n".join(lines)
