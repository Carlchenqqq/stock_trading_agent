#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易工具模块 - A股交易费用计算
=====================================
提供交易费用计算等基础工具函数，供 hybrid_agent 等实盘模块使用。

注意：完整的A股交易规则引擎请参见 trading_rules.py
"""

import logging

logger = logging.getLogger(__name__)


# ==================== A股交易费用常量 ====================

COMMISSION_RATE = 0.00025    # 佣金费率 万2.5
COMMISSION_MIN = 5.0         # 最低佣金 5元
STAMP_DUTY_RATE = 0.001      # 印花税 千1（仅卖出）
TRANSFER_FEE_RATE = 0.00001  # 过户费 万0.1（买卖均收）


def calculate_trade_fee(price: float, quantity: int, is_sell: bool = False) -> float:
    """
    计算A股交易费用

    Args:
        price: 成交价格
        quantity: 成交数量（股）
        is_sell: 是否为卖出操作

    Returns:
        总费用
    """
    amount = price * quantity
    commission = max(amount * COMMISSION_RATE, COMMISSION_MIN)
    stamp_duty = amount * STAMP_DUTY_RATE if is_sell else 0
    transfer_fee = amount * TRANSFER_FEE_RATE
    return commission + stamp_duty + transfer_fee
