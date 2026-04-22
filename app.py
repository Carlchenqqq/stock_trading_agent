#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票交易Agent Web仪表盘 - Flask后端
=====================================
安全特性：
- HMAC-SHA256 签名 Token 认证（非裸用户ID）
- 异常信息脱敏，不向客户端泄露内部实现细节
- 参数化查询防 SQL 注入（db.py 层面）
"""

import os
import sys
import json
import time
import hmac
import hashlib
import secrets
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

# ==================== 修复: 东方财富TLS指纹拦截 ====================
# Python requests 被东方财富反爬拦截，用 curl_cffi 模拟浏览器TLS指纹
try:
    from curl_cffi import requests as cffi_requests
    import akshare.utils.request as _ak_request
    import akshare.utils.func as _ak_func
    import inspect
    _orig_retry = _ak_request.request_with_retry
    _orig_sig = inspect.signature(_orig_retry)
    def _patched_request_with_retry(*args, **kwargs):
        try:
            session = cffi_requests.Session(impersonate="chrome")
            url = args[0] if args else kwargs.get('url', '')
            params = kwargs.get('params')
            headers = kwargs.get('headers')
            timeout = kwargs.get('timeout', 15)
            r = session.get(url, params=params, headers=headers, timeout=timeout)
            return r
        except Exception:
            return _orig_retry(*args, **kwargs)
    # 必须同时 patch 两个模块的引用（func.py 在 import 时创建了本地副本）
    _ak_request.request_with_retry = _patched_request_with_retry
    _ak_func.request_with_retry = _patched_request_with_retry
    print("[补丁] 已启用 curl_cffi TLS指纹补丁，绕过东方财富反爬")
except ImportError:
    print("[警告] curl_cffi 未安装，使用默认 requests（可能被东方财富拦截）")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
# 安全：SECRET_KEY 持久化到文件，避免重启后 Token 失效
_SECRET_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secret_key')
def _load_or_create_secret_key():
    if os.path.exists(_SECRET_KEY_FILE):
        with open(_SECRET_KEY_FILE, 'r') as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(_SECRET_KEY_FILE, 'w') as f:
        f.write(key)
    # 确保文件权限仅限当前用户
    os.chmod(_SECRET_KEY_FILE, 0o600)
    return key

SECRET_KEY = os.environ.get('SECRET_KEY', _load_or_create_secret_key())
app.secret_key = SECRET_KEY

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


# ==================== HMAC Token 认证 ====================

def generate_token(user_id):
    """
    生成 HMAC-SHA256 签名 Token

    Token 格式: {user_id}.{timestamp}.{signature}
    - user_id: 用户ID
    - timestamp: 签发时间戳（用于过期检查）
    - signature: HMAC-SHA256(user_id.timestamp, SECRET_KEY)

    有效期: 7天
    """
    ts = str(int(time.time()))
    msg = f"{user_id}.{ts}"
    sig = hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{msg}.{sig}"


def verify_token(token_str):
    """
    验证 HMAC Token，返回 user_id 或 None

    安全检查:
    1. Token 格式正确（3段，用.分隔）
    2. HMAC 签名验证通过
    3. 未过期（7天有效期）
    """
    if not token_str:
        return None
    try:
        parts = token_str.split('.')
        if len(parts) != 3:
            return None
        user_id_str, ts_str, sig = parts

        # 验证签名
        msg = f"{user_id_str}.{ts_str}"
        expected_sig = hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected_sig):
            logger.warning(f"无效的 Token 签名 (user_id={user_id_str})")
            return None

        # 验证过期（7天）
        ts = int(ts_str)
        if (time.time() - ts) > 7 * 24 * 3600:
            logger.info(f"Token 已过期 (user_id={user_id_str}, issued={ts})")
            return None

        return int(user_id_str)
    except (ValueError, TypeError):
        return None


def get_current_user():
    """从请求头获取当前用户（HMAC Token 方案）"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    if not token:
        return None
    user_id = verify_token(token)
    if not user_id:
        return None
    return _db.get_user(user_id)


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


# ==================== 延迟初始化（线程安全） ====================
_agent = None
_ai_analyzer = None
_agent_lock = threading.Lock()
_ai_lock = threading.Lock()


def get_agent():
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                from hybrid_agent import TradingAgent
                _agent = TradingAgent()
    return _agent


def get_ai_analyzer():
    global _ai_analyzer
    if _ai_analyzer is None:
        with _ai_lock:
            if _ai_analyzer is None:
                from ai_analyzer import AIAnalyzer
                _ai_analyzer = AIAnalyzer()
    return _ai_analyzer


# ==================== 安全辅助 ====================

def safe_error(message="操作失败，请稍后重试"):
    """返回脱敏的错误信息，不泄露内部细节"""
    return jsonify({"success": False, "error": message})


# ==================== 页面路由 ====================

@app.route('/')
def index():
    return render_template('index.html')


# ==================== 用户认证API ====================

@app.route('/api/register', methods=['POST'])
@admin_required
def api_register():
    """管理员创建新用户"""
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
        logger.error(f"创建用户失败: {e}")
        return safe_error("创建用户失败，请稍后重试")


@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        user = _db.authenticate(username, password)
        if not user:
            return jsonify({"success": False, "error": "用户名或密码错误"})
        # 生成签名 Token
        token = generate_token(user['id'])
        return jsonify({"success": True, "data": {"id": user['id'], "username": user['username'], "role": user['role'], "token": token}})
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return safe_error("登录失败，请稍后重试")


@app.route('/api/user/info')
@login_required
def api_user_info():
    user = request.current_user
    return jsonify({"success": True, "data": {"id": user['id'], "username": user['username'], "role": user['role'], "ai_usage": user['ai_usage']}})


@app.route('/api/user/change-password', methods=['POST'])
@login_required
def api_change_password():
    """用户修改自己的密码"""
    try:
        user = request.current_user
        data = request.get_json()
        old_password = (data.get('old_password') or '').strip()
        new_password = (data.get('new_password') or '').strip()
        if not old_password or not new_password:
            return jsonify({"success": False, "error": "请输入旧密码和新密码"})
        if len(new_password) < 4:
            return jsonify({"success": False, "error": "新密码至少4位"})
        # 验证旧密码
        password_ok, _ = _db.verify_password(old_password, user['password_hash'])
        if not password_ok:
            return jsonify({"success": False, "error": "旧密码错误"})
        # 更新密码
        new_hash = _db.hash_password(new_password)
        conn = _db.get_connection()
        try:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return safe_error("修改密码失败")


# ==================== 自选股API（用户级） ====================

@app.route('/api/watchlist')
@login_required
def api_watchlist():
    try:
        user = request.current_user
        stocks = _db.get_watchlist(user['id'])
        if not stocks:
            return jsonify({"success": True, "data": []})
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
        return safe_error("自选股数据加载失败")


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
        logger.error(f"添加自选股失败: {e}")
        return safe_error("添加失败")


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
        logger.error(f"移除自选股失败: {e}")
        return safe_error("移除失败")


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
        mask = df['代码'].str.contains(keyword, na=False) | df['名称'].str.contains(keyword, na=False)
        matched = df[mask].head(20)
        results = []
        for _, row in matched.iterrows():
            results.append({"ts_code": row['代码'], "name": row['名称'], "price": float(row['最新价']) if row['最新价'] else 0})
        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.error(f"股票搜索失败: {e}")
        return safe_error("搜索失败，请稍后重试")


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
        return safe_error("行业数据加载失败")


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
        return safe_error("市场数据加载失败")


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
        return safe_error("策略数据加载失败")


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
        return safe_error("推荐数据加载失败")


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
        return safe_error("异动数据加载失败")


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
        logger.error(f"交易规则加载失败: {e}")
        return safe_error("规则数据加载失败")


# ==================== AI分析API ====================

@app.route('/api/ai/status')
def api_ai_status():
    try:
        ai = get_ai_analyzer()
        return jsonify({"success": True, "data": ai.get_status()})
    except Exception as e:
        logger.error(f"AI状态获取失败: {e}")
        return safe_error("AI状态获取失败")


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
        logger.error(f"AI市场分析失败: {e}")
        return safe_error("AI分析失败，请稍后重试")


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
        logger.error(f"AI个股分析失败: {e}")
        return safe_error("AI分析失败，请稍后重试")


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
        logger.error(f"AI策略分析失败: {e}")
        return safe_error("AI分析失败，请稍后重试")


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
        logger.error(f"AI推荐分析失败: {e}")
        return safe_error("AI分析失败，请稍后重试")


# ==================== 管理员API ====================

@app.route('/api/admin/users')
@admin_required
def api_admin_users():
    try:
        users = _db.get_all_users()
        for u in users:
            u.pop('password_hash', None)
        return jsonify({"success": True, "data": users})
    except Exception as e:
        logger.error(f"管理员查询用户失败: {e}")
        return safe_error("查询失败")


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
        logger.error(f"管理员查询AI用量失败: {e}")
        return safe_error("查询失败")


@app.route('/api/admin/reset-password', methods=['POST'])
@admin_required
def api_admin_reset_password():
    """管理员重置指定用户的密码"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_password = (data.get('new_password') or '').strip()
        if not user_id or not new_password:
            return jsonify({"success": False, "error": "参数不完整"})
        if len(new_password) < 4:
            return jsonify({"success": False, "error": "密码至少4位"})
        target = _db.get_user(user_id)
        if not target:
            return jsonify({"success": False, "error": "用户不存在"})
        new_hash = _db.hash_password(new_password)
        conn = _db.get_connection()
        try:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"重置密码失败: {e}")
        return safe_error("重置密码失败")


@app.route('/api/admin/delete-user', methods=['POST'])
@admin_required
def api_admin_delete_user():
    """管理员删除用户（不能删除自己）"""
    try:
        admin = request.current_user
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "参数不完整"})
        if user_id == admin['id']:
            return jsonify({"success": False, "error": "不能删除自己"})
        target = _db.get_user(user_id)
        if not target:
            return jsonify({"success": False, "error": "用户不存在"})
        conn = _db.get_connection()
        try:
            conn.execute("DELETE FROM watchlist WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM ai_logs WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        return safe_error("删除用户失败")


# ==================== 全局异常处理（脱敏） ====================

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"未捕获异常: {e}\n{traceback.format_exc()}")
    return jsonify({"success": False, "error": "服务器内部错误，请稍后重试"}), 500


if __name__ == '__main__':
    print("\n  股票交易Agent Web仪表盘")
    print("  访问 http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
