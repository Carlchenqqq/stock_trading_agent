#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票交易Agent Web仪表盘 - Flask后端
=====================================
提供API接口，供前端页面调用。
"""

import os
import sys
import json
import time
import logging
import threading
from functools import wraps
from datetime import datetime
from flask import Flask, jsonify, render_template, request
import traceback

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_dotenv(_env_path)
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'stock-agent-secret-key-2024')

# ==================== 数据库初始化 ====================
import db as _db
_db.init_db()

# ==================== 数据缓存 ====================
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 300  # 缓存5分钟


def get_cached(key):
    with _cache_lock:
        item = _cache.get(key)
        if item and (time.time() - item['time']) < CACHE_TTL:
            return item['data']
    return None


def set_cached(key, data):
    with _cache_lock:
        _cache[key] = {'data': data, 'time': time.time()}


# ==================== 登录辅助 ====================
def get_current_user():
    """从请求头获取当前用户（简单token方案）"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return None
    try:
        user_id = int(token)
        return _db.get_user(user_id)
    except (ValueError, TypeError):
        return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "请先登录"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user.get('role') != 'admin':
            return jsonify({"success": False, "error": "需要管理员权限"}), 403
        request.current_user = user
        return f(*args, **kwargs)
    return decorated


# ==================== 延迟初始化 ====================
_agent = None
_ai_analyzer = None


def get_agent():
    global _agent
    if _agent is None:
        from hybrid_agent import TradingAgent
        _agent = TradingAgent()
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


# ==================== 用户认证API ====================

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        if len(username) < 2 or len(password) < 4:
            return jsonify({"success": False, "error": "用户名至少2位，密码至少4位"})
        user = _db.create_user(username, password)
        if not user:
            return jsonify({"success": False, "error": "用户名已存在"})
        return jsonify({"success": True, "data": {"id": user['id'], "username": user['username']}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        user = _db.authenticate(username, password)
        if not user:
            return jsonify({"success": False, "error": "用户名或密码错误"})
        return jsonify({"success": True, "data": {"id": user['id'], "username": user['username'], "role": user['role']}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/user/info')
@login_required
def api_user_info():
    user = request.current_user
    return jsonify({"success": True, "data": {"id": user['id'], "username": user['username'], "role": user['role'], "ai_usage": user['ai_usage']}})


# ==================== 自选股API（用户级） ====================

@app.route('/api/watchlist')
@login_required
def api_watchlist():
    try:
        user = request.current_user
        stocks = _db.get_watchlist(user['id'])
        if not stocks:
            return jsonify({"success": True, "data": []})
        # 获取实时行情
        agent = get_agent()
        results = []
        for s in stocks:
            try:
                info = agent.analyze_stock(s['ts_code'])
                info["code"] = s['ts_code']
                info["name"] = s['name']
                results.append(info)
            except Exception:
                results.append({"code": s['ts_code'], "name": s['name'], "error": "数据获取失败"})
        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.error(f"自选股分析失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/watchlist/add', methods=['POST'])
@login_required
def api_watchlist_add():
    try:
        user = request.current_user
        data = request.get_json()
        ts_code = (data.get('ts_code') or '').strip()
        name = (data.get('name') or '').strip()
        if not ts_code or not name:
            return jsonify({"success": False, "error": "股票代码和名称不能为空"})
        _db.add_to_watchlist(user['id'], ts_code, name)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/watchlist/remove', methods=['POST'])
@login_required
def api_watchlist_remove():
    try:
        user = request.current_user
        data = request.get_json()
        ts_code = (data.get('ts_code') or '').strip()
        if not ts_code:
            return jsonify({"success": False, "error": "股票代码不能为空"})
        _db.remove_from_watchlist(user['id'], ts_code)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/watchlist/search')
@login_required
def api_watchlist_search():
    """搜索股票（用于添加自选股）"""
    try:
        keyword = request.args.get('q', '').strip()
        if not keyword:
            return jsonify({"success": False, "error": "请输入搜索关键词"})
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        # 按代码或名称搜索
        mask = df['代码'].str.contains(keyword, na=False) | df['名称'].str.contains(keyword, na=False)
        matched = df[mask].head(20)
        results = []
        for _, row in matched.iterrows():
            results.append({"ts_code": row['代码'], "name": row['名称'], "price": float(row['最新价']) if row['最新价'] else 0})
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== 行业筛选API ====================

@app.route('/api/industry')
def api_industry():
    """热门行业及成分股（带缓存）"""
    try:
        cached = get_cached('industry')
        if cached:
            return jsonify({"success": True, "data": cached, "cached": True})
        from industry_screener import screen_all
        data = screen_all(top_n=10, stocks_per_industry=10)
        set_cached('industry', data)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error(f"行业筛选失败: {e}")
        return jsonify({"success": False, "error": str(e)})


# ==================== 市场数据API ====================

@app.route('/api/market')
def api_market():
    try:
        cached = get_cached('market')
        if cached:
            return jsonify({"success": True, "data": cached, "cached": True})
        agent = get_agent()
        sentiment = agent.analyze_market_sentiment()
        set_cached('market', sentiment)
        return jsonify({"success": True, "data": sentiment})
    except Exception as e:
        logger.error(f"市场数据获取失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/strategy')
def api_strategy():
    try:
        cached = get_cached('strategy')
        if cached:
            return jsonify({"success": True, "data": cached, "cached": True})
        agent = get_agent()
        results = agent.run_strategy_analysis()
        set_cached('strategy', results)
        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.error(f"策略分析失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/recommend')
def api_recommend():
    try:
        cached = get_cached('recommend')
        if cached:
            return jsonify({"success": True, "data": cached, "cached": True})
        agent = get_agent()
        report = agent.run_stock_recommendation(top_n=10)
        stocks = []
        for s in report.recommendations:
            stocks.append({
                "ts_code": s.ts_code, "name": s.name,
                "total_score": s.total_score, "trend_score": s.trend_score,
                "momentum_score": s.momentum_score, "volatility_score": s.volatility_score,
                "volume_score": s.volume_score, "pattern_score": s.pattern_score,
                "current_price": s.current_price, "change_pct": s.change_pct,
                "recommendation": s.recommendation, "risk_level": s.risk_level,
                "signals": s.signals,
            })
        data = {
            "date": report.date, "market_sentiment": report.market_sentiment,
            "warnings": report.warnings, "recommendations": stocks,
        }
        set_cached('recommend', data)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error(f"推荐分析失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/anomaly')
def api_anomaly():
    try:
        cached = get_cached('anomaly')
        if cached:
            return jsonify({"success": True, "data": cached, "cached": True})
        agent = get_agent()
        anomalies = agent.filter_anomaly_stocks()
        stocks = []
        for s in anomalies:
            stocks.append({
                "ts_code": s.ts_code, "name": s.name,
                "total_score": s.total_score, "change_pct": s.change_pct,
                "signals": s.signals,
            })
        set_cached('anomaly', stocks)
        return jsonify({"success": True, "data": stocks})
    except Exception as e:
        logger.error(f"异动筛选失败: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/rules')
def api_rules():
    try:
        from trading_rules import TradingRules
        rules = {
            "min_lot_size": 100, "max_single_order": 1000000, "min_price_unit": 0.01,
            "boards": {
                "main": {"name": "主板", "limit_pct": 10.0},
                "kcb": {"name": "科创板", "limit_pct": 20.0},
                "cyb": {"name": "创业板", "limit_pct": 20.0},
                "st": {"name": "ST股", "limit_pct": 5.0},
                "bse": {"name": "北交所", "limit_pct": 30.0},
            },
            "trading_time": {"auction": "9:15-9:25", "morning": "9:30-11:30", "afternoon": "13:00-15:00"},
            "fees": {"commission": "万2.5（最低5元）", "stamp_duty": "千1（仅卖出）", "transfer_fee": "万0.1（买卖均收）"},
            "t_plus_1": True, "limit_price_examples": {},
        }
        for board in ["main", "kcb", "cyb", "st"]:
            up, down = TradingRules.calculate_limit_price(10.0, board)
            rules["limit_price_examples"][board] = {"up": up, "down": down}
        return jsonify({"success": True, "data": rules})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== AI分析API ====================

@app.route('/api/ai/status')
def api_ai_status():
    try:
        ai = get_ai_analyzer()
        return jsonify({"success": True, "data": ai.get_status()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/market')
@login_required
def api_ai_market():
    try:
        user = request.current_user
        ai = get_ai_analyzer()
        agent = get_agent()
        market_data = agent.analyze_market_sentiment()
        analysis = ai.analyze_market(market_data)
        _db.increment_ai_usage(user['id'])
        _db.log_ai_usage(user['id'], 'market')
        return jsonify({"success": True, "data": {"analysis": analysis}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/stock/<ts_code>')
@login_required
def api_ai_stock(ts_code):
    try:
        user = request.current_user
        ai = get_ai_analyzer()
        agent = get_agent()
        stock_data = agent.analyze_stock(ts_code)
        analysis = ai.analyze_stock(stock_data)
        _db.increment_ai_usage(user['id'])
        _db.log_ai_usage(user['id'], f'stock_{ts_code}')
        return jsonify({"success": True, "data": {"analysis": analysis}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/strategy')
@login_required
def api_ai_strategy():
    try:
        user = request.current_user
        ai = get_ai_analyzer()
        agent = get_agent()
        signals = agent.run_strategy_analysis()
        analysis = ai.analyze_strategy(signals)
        _db.increment_ai_usage(user['id'])
        _db.log_ai_usage(user['id'], 'strategy')
        return jsonify({"success": True, "data": {"analysis": analysis}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/ai/recommend')
@login_required
def api_ai_recommend():
    try:
        user = request.current_user
        ai = get_ai_analyzer()
        agent = get_agent()
        report = agent.run_stock_recommendation(top_n=10)
        analysis = ai.analyze_recommendation([
            {"ts_code": s.ts_code, "name": s.name, "total_score": s.total_score,
             "change_pct": s.change_pct, "signals": s.signals}
            for s in report.recommendations
        ])
        _db.increment_ai_usage(user['id'])
        _db.log_ai_usage(user['id'], 'recommend')
        return jsonify({"success": True, "data": {"analysis": analysis}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== 管理员API ====================

@app.route('/api/admin/users')
@admin_required
def api_admin_users():
    try:
        users = _db.get_all_users()
        # 隐藏密码
        for u in users:
            u.pop('password_hash', None)
        return jsonify({"success": True, "data": users})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/admin/ai-usage')
@admin_required
def api_admin_ai_usage():
    try:
        conn = _db.get_connection()
        conn.row_factory = _db.sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username, u.ai_usage, COUNT(l.id) as log_count,
                   MAX(l.created_at) as last_used
            FROM users u
            LEFT JOIN ai_logs l ON u.id = l.user_id
            GROUP BY u.id
            ORDER BY u.ai_usage DESC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "data": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 全局异常处理
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"未捕获异常: {e}\n{traceback.format_exc()}")
    return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("\n  股票交易Agent Web仪表盘")
    print("  访问 http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
