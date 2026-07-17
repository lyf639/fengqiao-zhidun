"""
枫桥智盾 · RBAC 权限模块
======================

角色-权限体系：
  super_admin → 全部权限（最高权限，不可删除）
  admin       → 除用户管理外的管理权限
  operator    → 日常操作（读写案件/人员、生成报告）
  viewer      → 只读全部

权限码格式: resource:action
  cases:read/write/delete
  persons:read/write/delete
  alerts:read/manage
  dedup:read/manage
  audit:read
  report:generate
  admin:access
  users:manage
"""
from functools import wraps
from fastapi import HTTPException, Request
from models import Role, Permission, User, get_session
from auth import verify_token


# === 角色定义 ===
ROLES = {
    'super_admin': {
        'label': '超级管理员',
        'description': '系统最高权限，可管理用户和全部数据',
    },
    'admin': {
        'label': '管理员',
        'description': '可管理案件、人员、预警等全部业务数据',
    },
    'operator': {
        'label': '操作员',
        'description': '可新增/编辑案件和人员，查看分析结果',
    },
    'viewer': {
        'label': '观察员',
        'description': '只读查看全部数据',
    },
}

# === 权限定义 ===
PERMISSIONS = [
    # 案件管理
    {'code': 'cases:read',   'name': '查看案件', 'resource': 'cases',   'action': 'read'},
    {'code': 'cases:write',  'name': '编辑案件', 'resource': 'cases',   'action': 'write'},
    {'code': 'cases:delete', 'name': '删除案件', 'resource': 'cases',   'action': 'delete'},
    # 人员管理
    {'code': 'persons:read',   'name': '查看人员', 'resource': 'persons',   'action': 'read'},
    {'code': 'persons:write',  'name': '编辑人员', 'resource': 'persons',   'action': 'write'},
    {'code': 'persons:delete', 'name': '删除人员', 'resource': 'persons',   'action': 'delete'},
    # 预警管理
    {'code': 'alerts:read',   'name': '查看预警', 'resource': 'alerts',   'action': 'read'},
    {'code': 'alerts:manage', 'name': '管理预警', 'resource': 'alerts',   'action': 'manage'},
    # 去重管理
    {'code': 'dedup:read',   'name': '查看去重', 'resource': 'dedup',   'action': 'read'},
    {'code': 'dedup:manage', 'name': '管理去重', 'resource': 'dedup',   'action': 'manage'},
    # 审计日志
    {'code': 'audit:read',   'name': '查看审计', 'resource': 'audit',   'action': 'read'},
    # 报告
    {'code': 'report:generate', 'name': '生成报告', 'resource': 'report', 'action': 'generate'},
    # 后台管理
    {'code': 'admin:access', 'name': '访问后台', 'resource': 'admin',   'action': 'access'},
    # 用户管理（仅超级管理员）
    {'code': 'users:manage', 'name': '管理用户', 'resource': 'users',   'action': 'manage'},
]

# === 角色-权限映射 ===
ROLE_PERMISSIONS = {
    'super_admin': [p['code'] for p in PERMISSIONS],  # 全部权限
    'admin': [
        'cases:read', 'cases:write', 'cases:delete',
        'persons:read', 'persons:write', 'persons:delete',
        'alerts:read', 'alerts:manage',
        'dedup:read', 'dedup:manage',
        'audit:read',
        'report:generate',
        'admin:access',
    ],
    'operator': [
        'cases:read', 'cases:write',
        'persons:read', 'persons:write',
        'alerts:read',
        'dedup:read',
        'report:generate',
        'admin:access',
    ],
    'viewer': [
        'cases:read', 'persons:read',
        'alerts:read', 'dedup:read',
        'audit:read',
        'admin:access',
    ],
}


def seed_rbac():
    """初始化 RBAC 表（仅插入不存在的记录）"""
    session = get_session()
    try:
        # 插入角色
        for role_name, role_info in ROLES.items():
            if not session.query(Role).filter(Role.name == role_name).first():
                session.add(Role(name=role_name, label=role_info['label'],
                                 description=role_info['description'], is_system=1))

        # 插入权限
        for perm in PERMISSIONS:
            if not session.query(Permission).filter(Permission.code == perm['code']).first():
                session.add(Permission(**perm))

        session.flush()

        # 建立角色-权限关联
        for role_name, perm_codes in ROLE_PERMISSIONS.items():
            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                continue
            for code in perm_codes:
                perm = session.query(Permission).filter(Permission.code == code).first()
                if not perm:
                    continue
                from models import RolePermission
                exists = session.query(RolePermission).filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id
                ).first()
                if not exists:
                    session.add(RolePermission(role_id=role.id, permission_id=perm.id))

        session.commit()
        print('RBAC 权限体系初始化完成')
    except Exception as e:
        session.rollback()
        print(f'RBAC 初始化失败: {e}')
    finally:
        session.close()


def get_user_permissions(username: str) -> set[str]:
    """获取用户的所有权限码集合"""
    session = get_session()
    try:
        user = session.query(User).filter(User.username == username, User.is_active == 1).first()
        if not user:
            return set()
        return set(ROLE_PERMISSIONS.get(user.role, []))
    finally:
        session.close()


def check_perm(request: Request, permission: str):
    """行内权限检查：验证 Token 并检查权限，同时注入租户上下文，无权限直接抛 403"""
    payload = verify_token(request)
    user_role = payload.get('role', '')
    user_perms = ROLE_PERMISSIONS.get(user_role, [])
    if permission not in user_perms:
        raise HTTPException(403, f'权限不足，需要: {permission}')
    # 注入租户上下文
    from tenant import set_tenant_context
    set_tenant_context(request, payload)
    return payload


def require_perm(permission: str):
    """权限检查装饰器（同步版本，适用于 FastAPI 路由）"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get('request')
            if not request:
                raise HTTPException(500, '无法获取请求上下文')
            check_perm(request, permission)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: str):
    """角色检查装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get('request')
            if not request:
                raise HTTPException(500, '无法获取请求上下文')
            payload = verify_token(request)
            user_role = payload.get('role', '')
            if user_role not in roles:
                raise HTTPException(403, '权限不足，需要以下角色之一: ' + ', '.join(roles))
            return func(*args, **kwargs)
        return wrapper
    return decorator
