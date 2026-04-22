#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票交易Agent Web仪表盘 - Flask后端
=====================================
提供API接口，供前端页面调用。
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, jsonify, render_template
import traceback

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 延迟初始化（避免导入时触发akshare）
_agent = None
_ai_analyzer = None


def get_agent():
    global _agent
    if _agent is None:
        from hybrid_agent import TradingAgent
        _agent = TradingAgent()
        # 添加默认自选股
        watchlist = [
            ("000001.SZ", "平安银行"), ("600036.SH", "招商银行"), ("601318.SH", "中国平安"),
            ("000002.SZ", "万科A"), ("600519.SH", "贵州茅台"), ("000858.SZ", "五粮液"),
            ("000568.SZ", "泸州老窖"), ("002594.SZ", "比亚迪"), ("300750.SZ", "宁德时代"),
            ("601012.SH", "隆基绿能"), ("000725.SZ", "京东方A"), ("002415.SZ", "海康威视"),
            ("600570.SH", "恒生电子"), ("600276.SH", "恒瑞医药"), ("000538.SZ", "云南白药"),
            ("601857.SH", "中国石油"), ("601398.SH", "工商银行"),
        ]
        for code, name in watchlist:
            _agent.add_to_watchlist(code, name)
    return _agent


def get_ai_analyzer():
    global _ai_analyzer
    if _ai_analyzer is None:
        from ai_analyzer import AIAnalyzer
        _ai_analyzer = AIAnalyzer()
    return _ai_analyzer


# ==================== 页面路由 ====================

@app.route('/')
def index():
    return render_template('index.html')


# ==================== API接口 ====================

@app.route('/api/market')
def api_market():
    """市场情绪数据"""
    try:
        agent = get_agent()
        sentiment = agent.analyze_market_sentiment()
        return jsonify({"success": True, "data": sentiment})
    except Exception as e:
        logger.error(f"市场数据获取失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/watchlist')
def api_watchlist():
    """自选股分析"""
    try:
        agent = get_agent()
        results = []
        for stock in agent.watchlist:
            info = agent.analyze_stock(stock["code"])
            info["code"] = stock["code"]
            info["name"] = stock["name"]
            results.append(info)
        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.error(f"自选股分析失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/strategy')
def api_strategy():
    """策略分析"""
    try:
        agent = get_agent()
        results = agent.run_strategy_analysis()
        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.error(f"策略分析失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/recommend')
def api_recommend():
    """股票推荐"""
    try:
        agent = get_agent()
        report = agent.run_stock_recommendation(top_n=10)
        stocks = []
        for s in report.recommendations:
            stocks.append({
                "ts_code": s.ts_code,
                "name": s.name,
                "total_score": s.total_score,
                "trend_score": s.trend_score,
                "momentum_score": s.momentum_score,
                "volatility_score": s.volatility_score,
                "volume_score": s.volume_score,
                "pattern_score": s.pattern_score,
                "current_price": s.current_price,
                "change_pct": s.change_pct,
                "recommendation": s.recommendation,
                "risk_level": s.risk_level,
                "signals": s.signals,
            })
        return jsonify({
            "success": True,
            "data": {
                "date": report.date,
                "market_sentiment": report.market_sentiment,
                "warnings": report.warnings,
                "recommendations": stocks,
            }
        })
    except Exception as e:
        logger.error(f"推荐分析失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/anomaly')
def api_anomaly():
    """异动股筛选"""
    try:
        agent = get_agent()
        anomalies = agent.filter_anomaly_stocks()
        stocks = []
        for s in anomalies:
            stocks.append({
                "ts_code": s.ts_code,
                "name": s.name,
                "total_score": s.total_score,
                "change_pct": s.change_pct,
                "signals": s.signals,
            })
        return jsonify({"success": True, "data": stocks})
    except Exception as e:
        logger.error(f"异动筛选失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/rules')
def api_rules():
    """交易规则"""
    try:
        from trading_rules import TradingRules
        rules = {
            "min_lot_size": 100,
            "max_single_order": 1000000,
            "min_price_unit": 0.01,
            "boards": {
                "main": {"name": "主板", "limit_pct": 10.0},
                "kcb": {"name": "科创板", "limit_pct": 20.0},
                "cyb": {"name": "创业板", "limit_pct": 20.0},
                "st": {"name": "ST股", "limit_pct": 5.0},
                "bse": {"name": "北交所", "limit_pct": 30.0},
            },
            "trading_time": {
                "auction": "9:15-9:25",
                "morning": "9:30-11:30",
                "afternoon": "13:00-15:00",
            },
            "fees": {
                "commission": "万2.5（最低5元）",
                "stamp_duty": "千1（仅卖出）",
                "transfer_fee": "万0.1（买卖均收）",
            },
            "t_plus_1": True,
            "limit_price_examples": {},
        }
        for board in ["main", "kcb", "cyb", "st"]:
            up, down = TradingRules.calculate_limit_price(10.0, board)
            rules["limit_price_examples"][board] = {"up": up, "down": down}
        return jsonify({"success": True, "data": rules})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/status')
def api_ai_status():
    """AI分析器状态"""
    try:
        ai = get_ai_analyzer()
        return jsonify({"success": True, "data": ai.get_status()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/market')
def api_ai_market():
    """AI市场分析"""
    try:
        ai = get_ai_analyzer()
        agent = get_agent()
        market_data = agent.analyze_market_sentiment()
        analysis = ai.analyze_market(market_data)
        return jsonify({"success": True, "data": {"analysis": analysis}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/stock/<ts_code>')
def api_ai_stock(ts_code):
    """AI个股分析"""
    try:
        ai = get_ai_analyzer()
        agent = get_agent()
        stock_data = agent.analyze_stock(ts_code)
        analysis = ai.analyze_stock(stock_data)
        return jsonify({"success": True, "data": {"analysis": analysis}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/strategy')
def api_ai_strategy():
    """AI策略分析"""
    try:
        ai = get_ai_analyzer()
        agent = get_agent()
        signals = agent.run_strategy_analysis()
        analysis = ai.analyze_strategy(signals)
        return jsonify({"success": True, "data": {"analysis": analysis}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/recommend')
def api_ai_recommend():
    """AI推荐分析"""
    try:
        ai = get_ai_analyzer()
        agent = get_agent()
        report = agent.run_stock_recommendation(top_n=10)
        analysis = ai.analyze_recommendation([
            {"ts_code": s.ts_code, "name": s.name, "total_score": s.total_score,
             "change_pct": s.change_pct, "signals": s.signals}
            for s in report.recommendations
        ])
        return jsonify({"success": True, "data": {"analysis": analysis}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 全局异常处理：确保所有API始终返回JSON
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"未捕获异常: {e}\n{traceback.format_exc()}")
    return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("\n  股票交易Agent Web仪表盘")
    print("  访问 http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
