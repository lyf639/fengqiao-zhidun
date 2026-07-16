"""
枫桥智盾 · 认证模块
==================

JWT Token 签发/验证 + bcrypt 密码哈希

认证流程：
  1. 前端 POST /api/auth/login {username, password}
  2. 后端验证 bcrypt 哈希 → 签发 JWT（24h 过期）
  3. 前端存 token 到 localStorage
  4. 后续请求带 Authorization: Bearer <token>
  5. 后端 verify_token() 验证 → 通过/401

默认管理员：admin / admin123（首次启动自动创建）
环境变量：JWT_SECRET（密钥）、JWT_EXPIRE_HOURS（过期时间）
"""
import os, jwt, bcrypt
from datetime import datetime, timedelta
from functools import wraps
from fastapi import HTTPException, Request
from models import User, get_session

JWT_SECRET = os.getenv('JWT_SECRET', 'fengqiao-zhidun-secret-key-2026')
JWT_EXPIRE_HOURS = int(os.getenv('JWT_EXPIRE_HOURS', '24'))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_token(request: Request) -> dict:
    """从请求头提取并验证 JWT Token，返回 payload 或抛 401"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        raise HTTPException(401, '未提供认证令牌')
    token = auth[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, '令牌无效或已过期')
    return payload


def login(username: str, password: str) -> dict:
    """验证用户名密码，返回 token"""
    session = get_session()
    try:
        user = session.query(User).filter(
            User.username == username, User.is_active == 1
        ).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(401, '用户名或密码错误')
        user.last_login = datetime.now()
        session.commit()
        token = create_token(user.id, user.username, user.role)
        return {
            'token': token,
            'username': user.username,
            'display_name': user.display_name or user.username,
            'role': user.role,
        }
    finally:
        session.close()


def seed_default_user():
    """创建默认管理员账号（仅当不存在时）"""
    session = get_session()
    try:
        existing = session.query(User).filter(User.username == 'admin').first()
        if not existing:
            user = User(
                username='admin',
                password_hash=hash_password('admin123'),
                display_name='系统管理员',
                role='admin',
                is_active=1,
            )
            session.add(user)
            session.commit()
            print('已创建默认管理员：admin / admin123')
    except Exception:
        session.rollback()
    finally:
        session.close()
