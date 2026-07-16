"""
枫桥智盾 · 后台管理 API 逻辑层
=============================

提供 6 大模块的 CRUD 操作：
  1. 案件管理：list / get / create / update / delete
  2. 去重记录：list（只读）
  3. 预警事件：list（只读）
  4. 人员档案：list / create / update / delete
  5. 随访记录：list / create
  6. 审计日志：list（只读）

所有接口在 server.py 中挂载，受 JWT 认证保护（verify_token）
"""
from datetime import datetime, date
from sqlalchemy import func, desc

from models import (
    Case, DedupRecord, AlertEvent, PersonProfile, FollowUpRecord,
    AuditLog, get_session,
)

# ==================== 案件 CRUD ====================

def list_cases(page=1, page_size=20, district='', dispute_type='', keyword=''):
    session = get_session()
    try:
        q = session.query(Case)
        if district: q = q.filter(Case.district.like(f'%{district}%'))
        if dispute_type: q = q.filter(Case.dispute_type.like(f'%{dispute_type}%'))
        if keyword:
            q = q.filter(Case.parties.like(f'%{keyword}%') | Case.description.like(f'%{keyword}%'))
        total = q.count()
        rows = q.order_by(Case.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {
            'total': total, 'page': page, 'page_size': page_size,
            'rows': [_case_to_dict(c) for c in rows],
        }
    finally:
        session.close()


def get_case(case_id: int):
    session = get_session()
    try:
        c = session.query(Case).get(case_id)
        return _case_to_dict(c) if c else None
    finally:
        session.close()


def create_case(data: dict):
    session = get_session()
    try:
        c = Case(
            case_code=data.get('case_code', ''),
            agreement_type=data.get('agreement_type', ''),
            case_source=data.get('case_source', ''),
            mediation_org=data.get('mediation_org', ''),
            studio=data.get('studio', ''),
            handler=data.get('handler', ''),
            description=data.get('description', ''),
            difficulty=data.get('difficulty', ''),
            dispute_type=data.get('dispute_type', ''),
            case_attr=data.get('case_attr', ''),
            special_group=data.get('special_group', ''),
            district=data.get('district', ''),
            has_death=data.get('has_death', ''),
            mediation_result=data.get('mediation_result', ''),
            parties=data.get('parties', ''),
            amount=float(data.get('amount', 0) or 0),
            dedup_status=int(data.get('dedup_status', 0)),
            alert_level=int(data.get('alert_level', 0)),
            status=int(data.get('status', 0)),
        )
        session.add(c)
        session.flush()
        session.commit()
        return {'id': c.id}
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_case(case_id: int, data: dict):
    session = get_session()
    try:
        c = session.query(Case).get(case_id)
        if not c: return None
        updatable = ['case_code','agreement_type','case_source','mediation_org','studio',
                      'handler','description','difficulty','dispute_type','case_attr',
                      'special_group','district','has_death','mediation_result','parties',
                      'dedup_status','alert_level','status']
        for k in updatable:
            if k in data:
                setattr(c, k, data[k])
        if 'amount' in data:
            c.amount = float(data['amount'] or 0)
        session.commit()
        return _case_to_dict(c)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def delete_case(case_id: int):
    session = get_session()
    try:
        session.query(Case).filter(Case.id == case_id).delete()
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def _case_to_dict(c):
    return {
        'id': c.id, 'case_code': c.case_code, 'agreement_type': c.agreement_type,
        'case_source': c.case_source, 'mediation_org': c.mediation_org,
        'studio': c.studio, 'handler': c.handler,
        'accept_time': str(c.accept_time) if c.accept_time else None,
        'description': c.description, 'difficulty': c.difficulty,
        'dispute_type': c.dispute_type, 'case_attr': c.case_attr,
        'special_group': c.special_group, 'district': c.district,
        'has_death': c.has_death, 'mediation_result': c.mediation_result,
        'mediation_time': str(c.mediation_time) if c.mediation_time else None,
        'parties': c.parties, 'amount': float(c.amount or 0),
        'dedup_status': c.dedup_status, 'alert_level': c.alert_level,
        'status': c.status,
        'created_at': str(c.created_at) if c.created_at else None,
    }


# ==================== 去重记录 ====================

def list_dedup_records(page=1, page_size=20):
    session = get_session()
    try:
        total = session.query(func.count(DedupRecord.id)).scalar()
        rows = session.query(DedupRecord).order_by(DedupRecord.id.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {
            'total': total, 'page': page,
            'rows': [{
                'id': r.id, 'case_id': r.case_id, 'matched_case_id': r.matched_case_id,
                'score_phone': r.score_phone, 'score_address': r.score_address,
                'score_semantic': r.score_semantic, 'score_name': r.score_name,
                'total_score': r.total_score, 'is_confirmed': r.is_confirmed,
            } for r in rows],
        }
    finally:
        session.close()


# ==================== 预警事件 ====================

def list_alerts(page=1, page_size=20, level=None):
    session = get_session()
    try:
        q = session.query(AlertEvent)
        if level: q = q.filter(AlertEvent.alert_level == int(level))
        total = q.count()
        rows = q.order_by(AlertEvent.id.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {
            'total': total, 'page': page,
            'rows': [{
                'id': a.id, 'case_id': a.case_id, 'alert_level': a.alert_level,
                'rule_type': a.rule_type, 'channel_count': a.channel_count,
                'channels': a.channels, 'is_pushed': a.is_pushed,
                'created_at': str(a.created_at) if a.created_at else None,
            } for a in rows],
        }
    finally:
        session.close()


# ==================== 人员档案 ====================

def list_persons(page=1, page_size=20, person_type=''):
    session = get_session()
    try:
        q = session.query(PersonProfile)
        if person_type: q = q.filter(PersonProfile.person_type.like(f'%{person_type}%'))
        total = q.count()
        rows = q.order_by(PersonProfile.id.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {
            'total': total, 'page': page,
            'rows': [{
                'id': p.id, 'name': p.name, 'person_type': p.person_type,
                'risk_level': p.risk_level, 'departments': p.departments,
                'district': p.district, 'phone': p.phone, 'status': p.status,
            } for p in rows],
        }
    finally:
        session.close()


def create_person(data: dict):
    session = get_session()
    try:
        p = PersonProfile(
            name=data.get('name',''), person_type=data.get('person_type',''),
            risk_level=int(data.get('risk_level',1)), departments=data.get('departments',''),
            district=data.get('district',''), phone=data.get('phone',''),
            remark=data.get('remark',''),
        )
        session.add(p)
        session.flush()
        session.commit()
        return {'id': p.id}
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_person(pid: int, data: dict):
    session = get_session()
    try:
        p = session.query(PersonProfile).get(pid)
        if not p: return None
        for k in ['name','person_type','risk_level','departments','district','phone','remark','status']:
            if k in data: setattr(p, k, data[k])
        session.commit()
        return {'id': p.id}
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def delete_person(pid: int):
    session = get_session()
    try:
        session.query(FollowUpRecord).filter(FollowUpRecord.person_id == pid).delete()
        session.query(PersonProfile).filter(PersonProfile.id == pid).delete()
        session.commit()
        return True
    except:
        session.rollback()
        raise
    finally:
        session.close()


def get_person(pid: int):
    """获取单个人员档案"""
    session = get_session()
    try:
        p = session.query(PersonProfile).get(pid)
        if not p: return None
        return {'id': p.id, 'name': p.name, 'person_type': p.person_type,
                'risk_level': p.risk_level, 'departments': p.departments,
                'district': p.district, 'phone': p.phone, 'remark': p.remark,
                'status': p.status}
    finally:
        session.close()


# ==================== 随访记录 ====================

def list_followups(person_id=None, page=1, page_size=20):
    session = get_session()
    try:
        q = session.query(FollowUpRecord)
        if person_id: q = q.filter(FollowUpRecord.person_id == int(person_id))
        total = q.count()
        rows = q.order_by(FollowUpRecord.follow_date.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {
            'total': total, 'page': page,
            'rows': [{
                'id': f.id, 'person_id': f.person_id, 'follow_date': str(f.follow_date),
                'content': f.content, 'next_date': str(f.next_date) if f.next_date else None,
                'is_reminded': f.is_reminded, 'recorder': f.recorder,
            } for f in rows],
        }
    finally:
        session.close()


def create_followup(data: dict):
    session = get_session()
    try:
        f = FollowUpRecord(
            person_id=int(data['person_id']),
            follow_date=data.get('follow_date') or date.today(),
            content=data.get('content',''),
            next_date=data.get('next_date') or None,
            recorder=data.get('recorder',''),
        )
        session.add(f)
        session.flush()
        session.commit()
        return {'id': f.id}
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ==================== 审计日志 ====================

def list_audit_logs(page=1, page_size=30):
    session = get_session()
    try:
        total = session.query(func.count(AuditLog.id)).scalar()
        rows = session.query(AuditLog).order_by(AuditLog.id.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {
            'total': total, 'page': page,
            'rows': [{
                'id': l.id, 'target_type': l.target_type, 'target_id': l.target_id,
                'action': l.action, 'operator': l.operator,
                'detail': l.detail, 'created_at': str(l.created_at) if l.created_at else None,
            } for l in rows],
        }
    finally:
        session.close()
