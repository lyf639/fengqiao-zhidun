"""
枫桥智盾 · SQLAlchemy ORM 模型层
==================================

本文件定义了项目全部 11 张数据库表的 ORM 映射，包括：
  1. Case（案件）           - 核心业务表，Excel导入的目标
  2. DedupRecord（去重记录）  - 记录每次比对的四维得分
  3. AlertEvent（预警事件）   - 触发规则、等级、推送状态
  4. PersonProfile（人员档案） - 重点人员一人一档
  5. FollowUpRecord（随访）   - 关联人员的随访时间轴
  6. Policy（政策库）         - 政策匹配数据源
  7. AuditLog（审计日志）     - 全操作链路记录
  8. User（系统用户）         - 后台登录账号
  9. CategoryMapping（分类映射）- 上游系统分类名→标准分类
 10. CaseTag（案件标签）      - 多维标签体系
 11. CaseTagRelation（关联表） - 多对多中间表

数据表关系：
  Case 1──N DedupRecord（case_id, matched_case_id 双外键）
  Case 1──N AlertEvent
  PersonProfile 1──N FollowUpRecord
  Case M──N CaseTag（通过 CaseTagRelation）

连接配置：环境变量 DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME
生产切换：修改 DATABASE_URL 即可（如切换到 PostgreSQL）
"""
from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, DateTime, Date,
    Float, JSON, ForeignKey, UniqueConstraint, Index, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ============================================================
# 0. 多租户 - 乡镇/街道 (tenants)
# ============================================================
class Tenant(Base):
    __tablename__ = 'tenants'

    id               = mapped_column(Integer, primary_key=True, autoincrement=True)
    name             = mapped_column(String(50), nullable=False, unique=True, comment='乡镇名称')
    code             = mapped_column(String(20), nullable=False, unique=True, comment='租户编码: gouqi')
    district         = mapped_column(String(50), default='', comment='所属区县')
    is_active        = mapped_column(Integer, default=1, comment='是否启用')
    created_at       = mapped_column(DateTime, default=datetime.now)

    users            = relationship('User', back_populates='tenant', lazy='dynamic')
    cases            = relationship('Case', back_populates='tenant', lazy='dynamic')
    person_profiles  = relationship('PersonProfile', back_populates='tenant', lazy='dynamic')


# ============================================================
# 1. 矛盾纠纷案件
# ============================================================
class Case(Base):
    __tablename__ = 'cases'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id        = mapped_column(Integer, ForeignKey('tenants.id'), nullable=False, index=True, comment='所属乡镇')
    case_code        = mapped_column(String(50), nullable=False, unique=True, comment='案件编码')
    agreement_type   = mapped_column(String(20), default='', comment='协议类型')
    case_source      = mapped_column(String(60), default='', comment='案件来源')
    mediation_org    = mapped_column(String(120), default='', comment='调解组织')
    studio           = mapped_column(String(120), default='', comment='工作室')
    handler          = mapped_column(String(50), default='', comment='受理人姓名')
    accept_time      = mapped_column(DateTime, nullable=True, comment='受理时间')
    description      = mapped_column(Text, default='', comment='纠纷简要情况')
    difficulty       = mapped_column(String(20), default='', comment='案件难度级别')
    dispute_type     = mapped_column(String(30), default='', index=True, comment='纠纷类别')
    case_attr        = mapped_column(String(30), default='', comment='案件属性')
    special_group    = mapped_column(String(30), default='', comment='涉及特殊群体')
    district         = mapped_column(String(50), default='', index=True, comment='乡镇/街道')
    has_death        = mapped_column(String(4), default='', comment='有无死亡')
    mediation_result = mapped_column(String(20), default='', comment='调解结果')
    mediation_time   = mapped_column(DateTime, nullable=True, comment='调解时间')
    parties          = mapped_column(String(500), default='', comment='当事人')
    amount           = mapped_column(Float, default=0.0, comment='涉及金额')

    # 系统扩展字段
    import_batch     = mapped_column(String(32), default='', comment='导入批次号')
    import_time      = mapped_column(DateTime, default=datetime.now, comment='导入时间')
    dedup_status     = mapped_column(Integer, default=0, index=True, comment='去重状态 0未检测 1唯一 2疑似 3确认重复')
    alert_level      = mapped_column(Integer, default=0, index=True, comment='预警等级 0无 1黄 2橙 3红')
    status           = mapped_column(Integer, default=0, comment='处置状态 0待处置 1处置中 2已化解 3已归档')
    created_at       = mapped_column(DateTime, default=datetime.now)
    updated_at       = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    tenant           = relationship('Tenant', back_populates='cases')
    # 关联
    dedup_matches    = relationship('DedupRecord', foreign_keys='DedupRecord.case_id',
                                     back_populates='case', lazy='dynamic', cascade='all, delete-orphan')
    alert_events     = relationship('AlertEvent', back_populates='case',
                                     lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_accept_time', 'accept_time'),
        Index('idx_status', 'status'),
    )


# ============================================================
# 2. 去重比对记录
# ============================================================
class DedupRecord(Base):
    __tablename__ = 'dedup_records'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id          = mapped_column(BigInteger, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True)
    matched_case_id  = mapped_column(BigInteger, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True)
    score_phone      = mapped_column(Integer, default=0, comment='电话匹配得分 满分40')
    score_address    = mapped_column(Integer, default=0, comment='地址匹配得分 满分30')
    score_semantic   = mapped_column(Integer, default=0, comment='语义相似度得分 满分20')
    score_name       = mapped_column(Integer, default=0, comment='姓名匹配得分 满分10')
    total_score      = mapped_column(Integer, default=0, index=True, comment='综合评分')
    is_confirmed     = mapped_column(Integer, default=0, comment='0未确认 1确认重复 2判定独立')
    confirmed_by     = mapped_column(String(50), default='')
    confirmed_at     = mapped_column(DateTime, nullable=True)
    created_at       = mapped_column(DateTime, default=datetime.now)

    # 双向关联
    case             = relationship('Case', foreign_keys=[case_id], back_populates='dedup_matches')
    matched_case     = relationship('Case', foreign_keys=[matched_case_id])


# ============================================================
# 3. 预警事件
# ============================================================
class AlertEvent(Base):
    __tablename__ = 'alert_events'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id          = mapped_column(BigInteger, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True)
    alert_level      = mapped_column(Integer, nullable=False, index=True, comment='1黄 2橙 3红')
    rule_type        = mapped_column(String(50), default='', comment='触发规则类型')
    channel_count    = mapped_column(Integer, default=0, comment='跨渠道数量')
    channels         = mapped_column(String(200), default='')
    keywords         = mapped_column(String(300), default='')
    is_pushed        = mapped_column(Integer, default=0, index=True, comment='0未推送 1已推送')
    pushed_at        = mapped_column(DateTime, nullable=True)
    push_channel     = mapped_column(String(30), default='dingtalk')
    handler_dept     = mapped_column(String(120), default='')
    handler_person   = mapped_column(String(50), default='')
    resolve_deadline = mapped_column(Date, nullable=True)
    resolved_at      = mapped_column(DateTime, nullable=True)
    created_at       = mapped_column(DateTime, default=datetime.now)

    case             = relationship('Case', back_populates='alert_events')


# ============================================================
# 4. 重点人员档案
# ============================================================
class PersonProfile(Base):
    __tablename__ = 'person_profiles'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id        = mapped_column(Integer, ForeignKey('tenants.id'), nullable=False, index=True, comment='所属乡镇')
    name             = mapped_column(String(50), nullable=False, index=True)
    id_card          = mapped_column(String(200), default='', comment='身份证号 加密存储')
    person_type      = mapped_column(String(50), nullable=False, index=True, comment='精神障碍/刑满释放/社区矫正等')
    risk_level       = mapped_column(Integer, default=1, index=True, comment='1低 2中 3高')
    departments      = mapped_column(String(200), default='')
    district         = mapped_column(String(50), default='', index=True)
    phone            = mapped_column(String(20), default='')
    remark           = mapped_column(Text, default='')
    status           = mapped_column(Integer, default=1, comment='1在管 2已解管')
    created_at       = mapped_column(DateTime, default=datetime.now)
    updated_at       = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    follow_ups       = relationship('FollowUpRecord', back_populates='person',
                                     lazy='dynamic', cascade='all, delete-orphan')
    tenant           = relationship('Tenant', back_populates='person_profiles')


# ============================================================
# 5. 随访记录
# ============================================================
class FollowUpRecord(Base):
    __tablename__ = 'follow_up_records'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    person_id        = mapped_column(BigInteger, ForeignKey('person_profiles.id', ondelete='CASCADE'),
                                      nullable=False, index=True)
    follow_date      = mapped_column(Date, nullable=False)
    content          = mapped_column(Text, default='')
    next_date        = mapped_column(Date, nullable=True, index=True)
    is_reminded      = mapped_column(Integer, default=0, index=True)
    recorder         = mapped_column(String(50), default='')
    created_at       = mapped_column(DateTime, default=datetime.now)

    person           = relationship('PersonProfile', back_populates='follow_ups')


# ============================================================
# 6. 政策法规库
# ============================================================
class Policy(Base):
    __tablename__ = 'policy_library'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    policy_name      = mapped_column(String(200), nullable=False)
    dept             = mapped_column(String(60), default='', index=True)
    category         = mapped_column(String(50), default='', index=True)
    target_group     = mapped_column(String(200), default='')
    conditions       = mapped_column(Text, default='')
    benefit_standard = mapped_column(String(300), default='')
    procedure_desc   = mapped_column(Text, default='')
    keywords         = mapped_column(String(300), default='')
    is_active        = mapped_column(Integer, default=1, index=True)
    created_at       = mapped_column(DateTime, default=datetime.now)
    updated_at       = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============================================================
# 7. 操作审计日志
# ============================================================
class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target_type      = mapped_column(String(30), nullable=False, index=True)
    target_id        = mapped_column(BigInteger, default=0)
    action           = mapped_column(String(30), nullable=False, index=True)
    operator         = mapped_column(String(50), default='')
    detail           = mapped_column(JSON, nullable=True)
    ip_address       = mapped_column(String(45), default='')
    created_at       = mapped_column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index('idx_target', 'target_type', 'target_id'),
    )


# ============================================================
# 8. 系统用户表 (users)
# ============================================================
class User(Base):
    __tablename__ = 'users'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id        = mapped_column(Integer, ForeignKey('tenants.id'), nullable=True, index=True, comment='所属乡镇; NULL=超级管理员')
    username         = mapped_column(String(50), nullable=False, unique=True, index=True, comment='用户名')
    password_hash    = mapped_column(String(200), nullable=False, comment='bcrypt 密码哈希')
    display_name     = mapped_column(String(50), default='', comment='显示名称')
    role             = mapped_column(String(20), default='admin', comment='角色: admin/operator/viewer')
    is_active        = mapped_column(Integer, default=1, comment='是否启用')
    last_login       = mapped_column(DateTime, nullable=True)
    created_at       = mapped_column(DateTime, default=datetime.now)

    tenant           = relationship('Tenant', back_populates='users')


# ============================================================
# 8b. RBAC 角色表 (roles)
# ============================================================
class Role(Base):
    __tablename__ = 'roles'

    id               = mapped_column(Integer, primary_key=True, autoincrement=True)
    name             = mapped_column(String(30), nullable=False, unique=True, comment='角色标识: super_admin/admin/operator/viewer')
    label            = mapped_column(String(50), nullable=False, comment='显示名称')
    description      = mapped_column(String(200), default='')
    is_system        = mapped_column(Integer, default=1, comment='系统内置角色不可删除')
    created_at       = mapped_column(DateTime, default=datetime.now)

    permissions = relationship('Permission', secondary='role_permissions', back_populates='roles')


# ============================================================
# 8c. 权限表 (permissions)
# ============================================================
class Permission(Base):
    __tablename__ = 'permissions'

    id               = mapped_column(Integer, primary_key=True, autoincrement=True)
    code             = mapped_column(String(50), nullable=False, unique=True, comment='权限码: cases:read')
    name             = mapped_column(String(50), nullable=False, comment='权限名称')
    resource         = mapped_column(String(30), nullable=False, comment='资源: cases/persons/alerts...')
    action           = mapped_column(String(20), nullable=False, comment='操作: read/write/delete/manage')

    roles = relationship('Role', secondary='role_permissions', back_populates='permissions')


# ============================================================
# 8d. 角色-权限关联表 (role_permissions)
# ============================================================
class RolePermission(Base):
    __tablename__ = 'role_permissions'

    role_id          = mapped_column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    permission_id    = mapped_column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)


# ============================================================
# 9. 分类映射表 (category_mappings)
# 不同上游系统的分类叫法不同 → 统一映射到标准分类
# ============================================================
class CategoryMapping(Base):
    __tablename__ = 'category_mappings'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_system    = mapped_column(String(60), nullable=False, index=True, comment='来源系统 如12345热线/公安接警')
    source_category  = mapped_column(String(60), nullable=False, comment='源系统分类名 如邻里矛盾')
    target_category  = mapped_column(String(60), nullable=False, index=True, comment='统一标准分类 如邻里纠纷')
    confidence       = mapped_column(Float, default=1.0, comment='映射置信度 0~1')
    is_auto          = mapped_column(Integer, default=1, comment='0人工标注 1自动匹配')
    created_at       = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('source_system', 'source_category', name='uq_source_category'),
    )


# ============================================================
# 9. 案件标签表 (case_tags)
# 灵活的多维标签体系，比固定 dispute_type 更丰富
# ============================================================
class CaseTag(Base):
    __tablename__ = 'case_tags'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name             = mapped_column(String(30), nullable=False, unique=True, comment='标签名')
    color            = mapped_column(String(7), default='#2A5290', comment='标签颜色 #HEX')
    tag_category     = mapped_column(String(30), default='', index=True, comment='标签分类: 风险/类型/人群/区域/时效')
    description      = mapped_column(String(100), default='')
    created_at       = mapped_column(DateTime, default=datetime.now)

    cases            = relationship('Case', secondary='case_tag_relations', back_populates='tags')


# ============================================================
# 10. 案件-标签关联表 (case_tag_relations)
# 多对多中间表
# ============================================================
class CaseTagRelation(Base):
    __tablename__ = 'case_tag_relations'

    id               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_id          = mapped_column(BigInteger, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True, comment='关联案件')
    tag_id           = mapped_column(BigInteger, ForeignKey('case_tags.id', ondelete='CASCADE'), nullable=False, index=True, comment='关联标签')
    created_at       = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('case_id', 'tag_id', name='uq_case_tag'),
        {'mysql_engine': 'InnoDB'},
    )


# 更新 Case 模型 —— 添加 tags 反向关联
Case.tags = relationship('CaseTag', secondary='case_tag_relations', back_populates='cases')


# ============================================================
# 数据库连接工厂
# ============================================================
import os
from urllib.parse import quote_plus

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'FengQiao@2026')
DB_NAME = os.getenv('DB_NAME', 'fengqiao_zhidun')

DATABASE_URL = f'mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session():
    """获取数据库会话"""
    return SessionLocal()


def init_db():
    """建表（仅首次运行，表已存在则跳过）"""
    Base.metadata.create_all(engine)
