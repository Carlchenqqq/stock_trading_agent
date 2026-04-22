"""
股票交易智能体 - SQLite 数据库模块
使用 Python 内置 sqlite3 实现用户管理、自选股和 AI 日志功能
"""

import sqlite3
import hashlib
import os

# 数据库文件路径
DB_DIR = "/root/stock_trading_agent"
DB_PATH = os.path.join(DB_DIR, "data.db")


def get_connection():
    """获取数据库连接，启用外键约束"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # 让查询结果可以通过列名访问
    return conn


def init_db():
    """
    初始化数据库：创建所有表（如果不存在），并创建默认管理员账户
    """
    # 确保数据库目录存在
    os.makedirs(DB_DIR, exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor()

    # 创建用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            ai_usage INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建自选股表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ts_code TEXT NOT NULL,
            name TEXT,
            UNIQUE(user_id, ts_code),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # 创建 AI 使用日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            analysis_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # 创建默认管理员账户（如果不存在）
    admin_exists = cursor.execute(
        "SELECT id FROM users WHERE username = ?", ("admin",)
    ).fetchone()

    if not admin_exists:
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", hash_password("admin123"), "admin"),
        )

    conn.commit()
    conn.close()


def hash_password(password):
    """
    使用 SHA-256 对密码进行哈希加密

    参数:
        password: 原始密码字符串

    返回:
        十六进制哈希字符串
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password, hash_val):
    """
    验证密码是否匹配

    参数:
        password: 原始密码字符串
        hash_val: 存储的哈希值

    返回:
        bool: 密码是否正确
    """
    return hash_password(password) == hash_val


def create_user(username, password):
    """
    创建新用户

    参数:
        username: 用户名
        password: 密码（明文，函数内部会哈希）

    返回:
        成功时返回用户字典，用户名已存在时返回 None
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        conn.commit()
        user_id = cursor.lastrowid
        return get_user(user_id)
    except sqlite3.IntegrityError:
        # 用户名已存在
        return None
    finally:
        conn.close()


def authenticate(username, password):
    """
    用户登录认证

    参数:
        username: 用户名
        password: 密码（明文）

    返回:
        认证成功返回用户字典，失败返回 None
    """
    conn = get_connection()
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    conn.close()

    if user and verify_password(password, user["password_hash"]):
        return dict(user)
    return None


def get_user(user_id):
    """
    根据用户 ID 获取用户信息

    参数:
        user_id: 用户 ID

    返回:
        用户字典，不存在时返回 None
    """
    conn = get_connection()
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    conn.close()

    if user:
        return dict(user)
    return None


def get_all_users():
    """
    获取所有用户列表（管理员功能）

    返回:
        用户字典列表
    """
    conn = get_connection()
    cursor = conn.cursor()

    users = cursor.execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return [dict(u) for u in users]


def get_watchlist(user_id):
    """
    获取用户的自选股列表

    参数:
        user_id: 用户 ID

    返回:
        自选股字典列表
    """
    conn = get_connection()
    cursor = conn.cursor()

    stocks = cursor.execute(
        "SELECT * FROM watchlist WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()

    conn.close()

    return [dict(s) for s in stocks]


def add_to_watchlist(user_id, ts_code, name):
    """
    添加股票到自选股

    参数:
        user_id: 用户 ID
        ts_code: 股票代码（如 000001.SZ）
        name: 股票名称
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ts_code, name) VALUES (?, ?, ?)",
            (user_id, ts_code, name),
        )
        conn.commit()
    finally:
        conn.close()


def remove_from_watchlist(user_id, ts_code):
    """
    从自选股中移除股票

    参数:
        user_id: 用户 ID
        ts_code: 股票代码
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ts_code = ?",
            (user_id, ts_code),
        )
        conn.commit()
    finally:
        conn.close()


def increment_ai_usage(user_id):
    """
    增加用户的 AI 使用次数（+1）
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET ai_usage = ai_usage + 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def log_ai_usage(user_id, analysis_type):
    """
    记录 AI 使用日志
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ai_logs (user_id, analysis_type) VALUES (?, ?)",
            (user_id, analysis_type),
        )
        conn.commit()
    finally:
        conn.close()
