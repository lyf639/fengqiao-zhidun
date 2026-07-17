"""
枫桥智盾 · 多租户中间件
======================

每个乡镇（街道）是一个独立租户，数据通过 tenant_id 隔离：
  - 超级管理员（tenant_id=NULL）可查看/操作所有乡镇数据
  - 管理员/操作员/观察员 绑定到具体乡镇，只能看到本乡镇数据
  - 所有 API 查询自动注入 tenant_id 过滤，防止跨租户数据泄露

JWT 中携带 tenant_id 和 tenant_code，后端所有 CRUD 操作以此过滤。
"""
from functools import wraps
from fastapi import HTTPException, Request
from models import Tenant, get_session


def get_tenant_context(request: Request) -> dict:
    """从请求中提取租户上下文——由 verify_token 或 check_perm 调用后填充到 request.state"""
    if hasattr(request.state, 'tenant_id'):
        return {
            'tenant_id': request.state.tenant_id,
            'tenant_code': getattr(request.state, 'tenant_code', ''),
            'tenant_name': getattr(request.state, 'tenant_name', ''),
            'is_super': getattr(request.state, 'is_super_admin', False),
        }
    return {'tenant_id': None, 'tenant_code': '', 'tenant_name': '', 'is_super': True}


def set_tenant_context(request: Request, payload: dict):
    """认证后设置租户上下文到 request.state"""
    user_role = payload.get('role', '')
    is_super = (user_role == 'super_admin')
    request.state.is_super_admin = is_super
    request.state.tenant_id = payload.get('tenant_id') if not is_super else None
    request.state.tenant_code = payload.get('tenant_code', '')
    request.state.tenant_name = payload.get('tenant_name', '')


def tenant_filter_for(session, model, tenant_id: int | None):
    """返回带租户过滤的 SQLAlchemy Query。super_admin 不过滤，其他角色仅看本租户。"""
    q = session.query(model)
    if tenant_id is not None and hasattr(model, 'tenant_id'):
        q = q.filter(model.tenant_id == tenant_id)
    return q


def list_tenants(include_inactive: bool = False) -> list:
    """列出所有租户"""
    session = get_session()
    try:
        q = session.query(Tenant)
        if not include_inactive:
            q = q.filter(Tenant.is_active == 1)
        return [{'id': t.id, 'name': t.name, 'code': t.code,
                 'district': t.district, 'is_active': t.is_active}
                for t in q.all()]
    finally:
        session.close()
