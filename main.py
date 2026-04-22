#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票交易Agent主程序
==================
基于真实数据（AKShare）的智能交易系统

功能：
1. 每日市场报告
2. 策略分析（动量/均值回归/趋势跟踪/波动率突破）
3. 股票推荐（多维度评分排名）
4. 异动股筛选
5. A股交易规则校验
"""

import logging
import argparse

# 配置全局日志（仅在入口文件配置一次）
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from hybrid_agent import TradingAgent


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票交易Agent - 基于真实数据')
    parser.add_argument(
        '--mode',
        choices=['full', 'report', 'strategy', 'recommend', 'rules', 'anomaly'],
        default='full',
        help='运行模式: full=完整分析, report=每日报告, strategy=策略分析, '
             'recommend=股票推荐, rules=交易规则, anomaly=异动筛选'
    )

    args = parser.parse_args()

    agent = TradingAgent()

    # 自选股列表
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

    # 根据模式运行
    if args.mode == 'full':
        agent.print_daily_report()
        print("\n> 策略分析\n" + "-" * 50)
        agent.run_strategy_analysis()
        agent.run_stock_recommendation(top_n=10)
        agent.filter_anomaly_stocks()
        agent.show_trading_rules_info()
        print("\n> 交易校验示例\n" + "-" * 50)
        agent.validate_trade("000001.SZ", "BUY", 12.50, 500, available_cash=100000)
        agent.validate_trade("000001.SZ", "BUY", 12.50, 50, available_cash=100000)

    elif args.mode == 'report':
        agent.print_daily_report()

    elif args.mode == 'strategy':
        agent.run_strategy_analysis()

    elif args.mode == 'recommend':
        agent.run_stock_recommendation(top_n=10)

    elif args.mode == 'rules':
        agent.show_trading_rules_info()

    elif args.mode == 'anomaly':
        agent.filter_anomaly_stocks()


if __name__ == "__main__":
    main()
