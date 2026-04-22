"""
股票交易智能体 - SQLite 数据库模块
使用 Python 内置 sqlite3 实现用户管理、自选股和 AI 日志功能

安全特性：
- 密码使用 bcrypt 哈希（自动加盐），兼容旧版 SHA-256 密码（登录时自动迁移）
- 所有数据库操作使用参数化查询，防止 SQL 注入
"""

import sqlite3
import hashlib
import os
import logging

logger = logging.getLogger(__name__)

# 数据库文件路径
DB_DIR = os.environ.get("APP_DATA_DIR", "/root/stock_trading_agent")
DB_PATH = os.path.join(DB_DIR, "data.db")

# bcrypt 哈希前缀标识
_BCRYPT_PREFIX = "$2b$"


def get_connection():
    """获取数据库连接，启用外键约束"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    初始化数据库：创建所有表（如果不存在），并创建默认管理员账户
    """
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
        logger.info("默认管理员账户已创建 (admin/admin123)，请尽快修改密码！")

    conn.commit()
    conn.close()


# ==================== 密码哈希（bcrypt + SHA-256 兼容） ====================

def hash_password(password):
    """
    使用 bcrypt 对密码进行哈希加密（自动加盐）

    参数:
        password: 原始密码字符串

    返回:
        bcrypt 哈希字符串（以 $2b$ 开头）
    """
    import bcrypt
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def _is_bcrypt_hash(hash_val):
    """判断哈希值是否为 bcrypt 格式"""
    return hash_val and hash_val.startswith(_BCRYPT_PREFIX)


def _verify_sha256(password, hash_val):
    """验证旧版 SHA-256 哈希（兼容迁移用）"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == hash_val


def verify_password(password, hash_val):
    """
    验证密码是否匹配

    支持 bcrypt 哈希和旧版 SHA-256 哈希。
    如果检测到旧版 SHA-256 哈希验证成功，会返回一个标记提示调用方进行迁移。

    参数:
        password: 原始密码字符串
        hash_val: 存储的哈希值

    返回:
        (bool, bool): (密码是否正确, 是否需要迁移到bcrypt)
    """
    if _is_bcrypt_hash(hash_val):
        import bcrypt
        try:
            result = bcrypt.checkpw(password.encode("utf-8"), hash_val.encode("utf-8"))
            return (result, False)
        except Exception:
            return (False, False)
    else:
        # 旧版 SHA-256 兼容
        result = _verify_sha256(password, hash_val)
        return (result, result)  # 如果SHA256验证成功，标记需要迁移


def _upgrade_password_hash(user_id, password):
    """
    将用户的密码哈希从 SHA-256 升级为 bcrypt

    参数:
        user_id: 用户 ID
        password: 原始密码（明文）
    """
    new_hash = hash_password(password)
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id),
        )
        conn.commit()
        logger.info(f"用户 {user_id} 的密码哈希已从 SHA-256 迁移到 bcrypt")
    except Exception as e:
        logger.error(f"密码哈希迁移失败 (user_id={user_id}): {e}")
    finally:
        conn.close()


# ==================== 用户管理 ====================

def create_user(username, password):
    """
    创建新用户（密码使用 bcrypt 哈希）

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
        return None
    finally:
        conn.close()


def authenticate(username, password):
    """
    用户登录认证

    支持 bcrypt 和旧版 SHA-256 密码验证。
    如果使用旧版 SHA-256 验证成功，会自动将密码升级为 bcrypt。

    返回:
        认证成功返回用户字典，失败返回 None
    """
    conn = get_connection()
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    conn.close()

    if not user:
        return None

    password_ok, needs_upgrade = verify_password(password, user["password_hash"])
    if not password_ok:
        return None

    # 自动迁移旧版 SHA-256 密码到 bcrypt
    if needs_upgrade:
        _upgrade_password_hash(user["id"], password)

    return dict(user)


def get_user(user_id):
    """根据用户 ID 获取用户信息"""
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
    """获取所有用户列表（管理员功能）"""
    conn = get_connection()
    cursor = conn.cursor()

    users = cursor.execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return [dict(u) for u in users]


# ==================== 自选股管理 ====================

def get_watchlist(user_id):
    """获取用户的自选股列表"""
    conn = get_connection()
    cursor = conn.cursor()

    stocks = cursor.execute(
        "SELECT * FROM watchlist WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()

    conn.close()

    return [dict(s) for s in stocks]


def add_to_watchlist(user_id, ts_code, name):
    """添加股票到自选股"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ts_code, name) VALUES (?, ?, ?)",
            (user_id, ts_code, name),
        )
        conn.commit()
    finally:
        conn.close()


def remove_from_watchlist(user_id, ts_code):
    """从自选股中移除股票"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ts_code = ?",
            (user_id, ts_code),
        )
        conn.commit()
    finally:
        conn.close()


# ==================== AI 用量 ====================

def increment_ai_usage(user_id):
    """增加用户的 AI 使用次数（+1）"""
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
    """记录 AI 使用日志"""
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
