"""
枫桥智盾 · FastAPI 后端服务
uvicorn server:app --host 0.0.0.0 --port 5000 --reload
"""
import json, uuid, sys, os
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

# ⚠ .env 必须在所有业务模块导入之前加载，override=True 覆盖系统环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

import fakeredis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import (
    Case, DedupRecord, AlertEvent, PersonProfile, FollowUpRecord,
    Policy, AuditLog, CategoryMapping, CaseTag, CaseTagRelation,
    get_session, init_db,
)
from ai_service import semantic_similarity, field_scores
from report_generator import generate_report
from admin_api import (
    list_cases as admin_list_cases, get_case, create_case, update_case, delete_case,
    list_dedup_records, list_alerts, list_persons, create_person, update_person, delete_person,
    list_followups, create_followup, list_audit_logs,
)

# ==================== App ====================
app = FastAPI(
    title="枫桥智盾 API",
    description="基层矛盾纠纷智能预警与化解平台 · 后端服务",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Redis (fakeredis) ====================
r = fakeredis.FakeRedis(decode_responses=True)


def init_cache():
    if not r.exists('dashboard:total'):
        r.hset('dashboard:total', mapping={'value': 0, 'label': '累计案件数'})
        r.hset('dashboard:dedup', mapping={'value': 0, 'label': '智能去重识别'})
        r.hset('dashboard:alerts', mapping={'value': 0, 'label': '实时预警事件'})
        r.hset('dashboard:resolved', mapping={'value': 0, 'label': '化解成功'})
        r.delete('feed:list')


def push_feed(msg: str, feed_type: str = 'info'):
    item = json.dumps({'msg': msg, 'type': feed_type, 'time': datetime.now().strftime('%H:%M:%S')},
                       ensure_ascii=False)
    r.lpush('feed:list', item)
    r.ltrim('feed:list', 0, 49)


def log_audit(session, target_type: str, target_id: int, action: str, detail: dict):
    session.add(AuditLog(target_type=target_type, target_id=target_id, action=action, detail=detail))


# ==================== Schemas ====================
class CaseRecord(BaseModel):
    caseCode: Optional[str] = ''
    agreementType: Optional[str] = ''
    caseSource: Optional[str] = ''
    mediationOrg: Optional[str] = ''
    studio: Optional[str] = ''
    handler: Optional[str] = ''
    acceptTime: Optional[str] = ''
    description: Optional[str] = ''
    difficulty: Optional[str] = ''
    disputeType: Optional[str] = ''
    caseAttr: Optional[str] = ''
    specialGroup: Optional[str] = ''
    district: Optional[str] = ''
    hasDeath: Optional[str] = ''
    result: Optional[str] = ''
    mediationTime: Optional[str] = ''
    parties: Optional[str] = ''
    amount: Optional[str] = ''


class ImportRequest(BaseModel):
    records: list[CaseRecord] = Field(..., min_length=1, description="导入的案件记录列表")


class DedupRequest(BaseModel):
    batch: str = Field(..., description="导入批次号")
    case_ids: list[int] = Field(..., min_length=1)


class AlertRequest(BaseModel):
    case_ids: list[int] = Field(..., min_length=1)


# ==================== Helpers ====================
FIELD_MAP = {
    'caseCode': 'case_code', 'agreementType': 'agreement_type',
    'caseSource': 'case_source', 'mediationOrg': 'mediation_org',
    'studio': 'studio', 'handler': 'handler',
    'acceptTime': 'accept_time', 'description': 'description',
    'difficulty': 'difficulty', 'disputeType': 'dispute_type',
    'caseAttr': 'case_attr', 'specialGroup': 'special_group',
    'district': 'district', 'hasDeath': 'has_death',
    'result': 'mediation_result', 'mediationTime': 'mediation_time',
    'parties': 'parties', 'amount': 'amount',
}


def parse_datetime(val):
    if not val: return None
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d']:
        try: return datetime.strptime(str(val).strip(), fmt)
        except ValueError: continue
    return None


def parse_amount(val):
    if not val or str(val).strip() == '': return 0.0
    try: return float(str(val).replace(',', '').replace('，', ''))
    except ValueError: return 0.0


# ==================== Startup ====================
@app.on_event('startup')
def startup():
    init_db()
    init_cache()
    print('枫桥智盾 FastAPI 已启动')
    print('Swagger 文档: http://localhost:5000/docs')
    print('ReDoc 文档:  http://localhost:5000/redoc')


# ==================== API Routes ====================

@app.get('/api/dashboard', tags=['驾驶舱'])
def get_dashboard():
    """获取驾驶舱实时数据（来自 Redis 缓存）"""
    return {
        'total': int(r.hget('dashboard:total', 'value') or 0),
        'dedup': int(r.hget('dashboard:dedup', 'value') or 0),
        'alerts': int(r.hget('dashboard:alerts', 'value') or 0),
        'resolved': int(r.hget('dashboard:resolved', 'value') or 0),
    }


@app.get('/api/feed', tags=['驾驶舱'])
def get_feed():
    """获取实时动态流（最近 20 条，来自 Redis）"""
    items = r.lrange('feed:list', 0, 19)
    return [json.loads(i) for i in items]


@app.get('/api/stats', tags=['统计'])
def get_stats():
    """全量统计数据"""
    session = get_session()
    try:
        return {
            'total': session.query(func.count(Case.id)).scalar(),
            'duplicates': session.query(func.count(Case.id)).filter(Case.dedup_status >= 2).scalar(),
            'alerts': session.query(func.count(Case.id)).filter(Case.alert_level > 0).scalar(),
        }
    finally:
        session.close()


@app.get('/api/cases', tags=['案件'])
def list_cases(limit: int = 50):
    """获取最近案件列表"""
    session = get_session()
    try:
        cases = session.query(Case).order_by(Case.id.desc()).limit(limit).all()
        return {'cases': [{
            'id': c.id, 'case_code': c.case_code, 'dispute_type': c.dispute_type,
            'district': c.district, 'parties': c.parties,
            'accept_time': str(c.accept_time) if c.accept_time else None,
            'amount': c.amount, 'dedup_status': c.dedup_status,
            'alert_level': c.alert_level, 'status': c.status,
        } for c in cases]}
    finally:
        session.close()


# ==================== Import ====================

@app.post('/api/import', tags=['导入'])
def import_cases(req: ImportRequest):
    """
    Excel 一键导入

    接收前端解析后的案件记录列表，自动映射字段并写入 MySQL，
    同时更新 Redis 缓存计数和实时动态流。
    """
    batch_id = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8]
    session = get_session()
    inserted, skipped = 0, 0

    try:
        for rec in req.records:
            d = rec.model_dump()
            mapped = {FIELD_MAP.get(k, k): v for k, v in d.items()}

            case = Case(
                case_code=mapped.get('case_code') or f'AUTO_{uuid.uuid4().hex[:12].upper()}',
                agreement_type=mapped.get('agreement_type', ''),
                case_source=mapped.get('case_source', ''),
                mediation_org=mapped.get('mediation_org', ''),
                studio=mapped.get('studio', ''),
                handler=mapped.get('handler', ''),
                accept_time=parse_datetime(mapped.get('accept_time')),
                description=mapped.get('description', ''),
                difficulty=mapped.get('difficulty', ''),
                dispute_type=mapped.get('dispute_type', ''),
                case_attr=mapped.get('case_attr', ''),
                special_group=mapped.get('special_group', ''),
                district=mapped.get('district', ''),
                has_death=mapped.get('has_death', ''),
                mediation_result=mapped.get('mediation_result', ''),
                mediation_time=parse_datetime(mapped.get('mediation_time')),
                parties=mapped.get('parties', ''),
                amount=parse_amount(mapped.get('amount')),
                import_batch=batch_id,
            )
            session.add(case)
            try:
                session.flush()
                inserted += 1
            except IntegrityError:
                session.rollback()
                skipped += 1

        session.commit()
        r.hincrby('dashboard:total', 'value', inserted)
        push_feed(f'📥 Excel一键导入 {inserted} 条案件' + (f'，{skipped} 条跳过' if skipped else ''))
        log_audit(session, 'case', 0, 'import', {'batch': batch_id, 'inserted': inserted, 'skipped': skipped})

        return {'success': True, 'batch': batch_id, 'inserted': inserted, 'skipped': skipped}
    except Exception as e:
        session.rollback()
        raise HTTPException(500, str(e))
    finally:
        session.close()


# ==================== Dedup ====================

@app.post('/api/dedup', tags=['去重'])
def run_dedup(req: DedupRequest):
    """
    智能去重

    对导入批次内的案件与存量数据进行多维度比对（电话/地址/语义/姓名），
    综合评分 ≥85 分标记为疑似重复。结果缓存至 Redis（TTL 1小时）。
    """
    session = get_session()
    dup_results, total_dup = [], 0

    try:
        for cid in req.case_ids:
            cache_key = f'dedup:case:{cid}'
            cached = r.get(cache_key)
            if cached:
                data = json.loads(cached)
                dup_results.append(data)
                if data.get('match_count', 0) > 0: total_dup += 1
                new_status = 3 if data.get('match_count', 0) > 0 else 1
                session.query(Case).filter(Case.id == cid).update({'dedup_status': new_status})
                continue

            new_case = session.query(Case).get(cid)
            if not new_case: continue

            matches = session.query(Case).filter(
                Case.id != cid, Case.dedup_status != 3,
                Case.district == new_case.district,
                Case.dispute_type == new_case.dispute_type,
                Case.parties.isnot(None), Case.parties != '',
            ).limit(5).all()

            if matches:
                # 使用 AI 计算语义相似度（自动回退到规则匹配）
                new_dict = {
                    'parties': new_case.parties or '',
                    'district': new_case.district or '',
                    'dispute_type': new_case.dispute_type or '',
                    'description': new_case.description or '',
                }
                for m in matches:
                    match_dict = {
                        'parties': m.parties or '',
                        'district': m.district or '',
                        'dispute_type': m.dispute_type or '',
                        'description': m.description or '',
                    }
                    ai_result = semantic_similarity(new_dict, match_dict)
                    score_semantic = ai_result['score']
                    # 逐字段实际比对 phone/address/name，不再硬编码满分
                    f_scores = field_scores(new_dict, match_dict)
                    scores = {'phone': f_scores['phone'], 'address': f_scores['address'], 'semantic': score_semantic, 'name': f_scores['name']}
                    total = sum(scores.values())
                    session.add(DedupRecord(
                        case_id=cid, matched_case_id=m.id,
                        score_phone=scores['phone'], score_address=scores['address'],
                        score_semantic=score_semantic, score_name=scores['name'],
                        total_score=total,
                    ))
                session.query(Case).filter(Case.id == cid).update({'dedup_status': 2})
                result = {
                    'case_id': cid, 'match_count': len(matches), 'total_score': total,
                    'ai_backend': ai_result.get('backend', 'mock'),
                    'ai_reason': ai_result.get('reason', ''),
                }
                dup_results.append(result); total_dup += 1
                r.setex(cache_key, 3600, json.dumps(result))
            else:
                session.query(Case).filter(Case.id == cid).update({'dedup_status': 1})
                r.setex(cache_key, 3600, json.dumps({'case_id': cid, 'match_count': 0, 'total_score': 0}))

        session.commit()
        r.hincrby('dashboard:dedup', 'value', total_dup)
        push_feed(f'🔍 智能去重完成：检查 {len(req.case_ids)} 条，发现 {total_dup} 条疑似重复', 'warning')
        log_audit(session, 'case', 0, 'dedup',
                  {'batch': req.batch, 'checked': len(req.case_ids), 'duplicates': total_dup})

        return {'success': True, 'checked': len(req.case_ids), 'duplicates': total_dup, 'results': dup_results}
    except Exception as e:
        session.rollback()
        raise HTTPException(500, str(e))
    finally:
        session.close()


# ==================== Alert ====================

@app.post('/api/alert', tags=['预警'])
def run_alert(req: AlertRequest):
    """
    风险预警扫描

    按规则自动判定风险等级：
    - 红色：金额 ≥10万元 或 涉及死亡
    - 橙色：金额 1万~10万元
    - 黄色：难度级别非"简单纠纷"
    """
    session = get_session()
    alerts, red_count, orange_count = [], 0, 0

    try:
        for cid in req.case_ids:
            c = session.query(Case).get(cid)
            if not c: continue

            level, rule = 0, ''
            if c.amount and c.amount >= 100000:
                level, rule = 3, 'high_amount'
            elif c.has_death and c.has_death in ('是', '有', '1'):
                level, rule = 3, 'has_death'
            elif c.amount and c.amount >= 10000:
                level, rule = 2, 'medium_amount'
            elif c.difficulty and c.difficulty not in ('', '简单纠纷'):
                level, rule = 1, 'difficulty_level'

            if level > 0:
                session.add(AlertEvent(
                    case_id=cid, alert_level=level, rule_type=rule,
                    channel_count=1, channels=c.case_source or '',
                    keywords=c.dispute_type or '',
                ))
                c.alert_level = level
                alerts.append({'case_id': cid, 'level': level, 'rule': rule})
                if level == 3: red_count += 1
                elif level == 2: orange_count += 1

        session.commit()
        r.hincrby('dashboard:alerts', 'value', len(alerts))
        if red_count: push_feed(f'🔴 红色预警触发 {red_count} 件', 'danger')
        if orange_count: push_feed(f'🟠 橙色预警触发 {orange_count} 件', 'warning')
        log_audit(session, 'alert', 0, 'alert_scan',
                  {'checked': len(req.case_ids), 'alerts': len(alerts)})

        return {'success': True, 'alerts': len(alerts), 'red': red_count, 'orange': orange_count}
    except Exception as e:
        session.rollback()
        raise HTTPException(500, str(e))
    finally:
        session.close()


# ==================== Report ====================

class ReportRequest(BaseModel):
    period: str = Field(..., description="monthly | quarterly | yearly")
    year: int = Field(..., ge=2020, le=2030)
    month: int | None = Field(None, ge=1, le=12)
    quarter: int | None = Field(None, ge=1, le=4)


@app.post('/api/report/generate', tags=['智能报告'])
def generate_ai_report(req: ReportRequest):
    """
    AI 分析报告生成

    根据选定时间段（月度/季度/年度），自动统计案件数据并调用 DeepSeek 生成专业分析报告，
    包含总体态势、重点分析、工作建议三部分。
    """
    result = generate_report(req.period, req.year, req.month, req.quarter)
    if 'error' in result:
        raise HTTPException(400, result['error'])
    return result


# ==================== Admin API ====================

@app.get('/api/admin/cases', tags=['管理后台'])
def admin_cases(page: int = 1, district: str = '', dispute_type: str = '', keyword: str = ''):
    return admin_list_cases(page, 20, district, dispute_type, keyword)

@app.get('/api/admin/cases/{case_id}', tags=['管理后台'])
def admin_get_case(case_id: int):
    r = get_case(case_id)
    if not r: raise HTTPException(404, 'not found')
    return r

@app.post('/api/admin/cases', tags=['管理后台'])
def admin_create_case(data: dict):
    try: return create_case(data)
    except Exception as e: raise HTTPException(500, str(e))

@app.put('/api/admin/cases/{case_id}', tags=['管理后台'])
def admin_update_case(case_id: int, data: dict):
    r = update_case(case_id, data)
    if not r: raise HTTPException(404, 'not found')
    return r

@app.delete('/api/admin/cases/{case_id}', tags=['管理后台'])
def admin_delete_case(case_id: int):
    delete_case(case_id)
    return {'success': True}

@app.get('/api/admin/dedup', tags=['管理后台'])
def admin_dedup(page: int = 1):
    return list_dedup_records(page, 20)

@app.get('/api/admin/alerts', tags=['管理后台'])
def admin_alerts(page: int = 1, level: int = None):
    return list_alerts(page, 20, level)

@app.get('/api/admin/persons', tags=['管理后台'])
def admin_persons(page: int = 1, person_type: str = ''):
    return list_persons(page, 20, person_type)

@app.post('/api/admin/persons', tags=['管理后台'])
def admin_create_person(data: dict):
    try: return create_person(data)
    except Exception as e: raise HTTPException(500, str(e))

@app.put('/api/admin/persons/{person_id}', tags=['管理后台'])
def admin_update_person(person_id: int, data: dict):
    r = update_person(person_id, data)
    if not r: raise HTTPException(404, 'not found')
    return r

@app.delete('/api/admin/persons/{person_id}', tags=['管理后台'])
def admin_delete_person(person_id: int):
    delete_person(person_id)
    return {'success': True}

@app.get('/api/admin/followups', tags=['管理后台'])
def admin_followups(person_id: int = None, page: int = 1):
    return list_followups(person_id, page, 20)

@app.post('/api/admin/followups', tags=['管理后台'])
def admin_create_followup(data: dict):
    try: return create_followup(data)
    except Exception as e: raise HTTPException(500, str(e))

@app.get('/api/admin/audit', tags=['管理后台'])
def admin_audit(page: int = 1):
    return list_audit_logs(page, 30)


# ==================== Static Frontend ====================
WEB_DIR = os.path.join(os.path.dirname(__file__), '..', 'web')
if os.path.isdir(WEB_DIR):
    app.mount('/static', StaticFiles(directory=WEB_DIR), name='static')

@app.get('/')
def serve_index():
    """托管前端驾驶舱页面"""
    index_path = os.path.join(WEB_DIR, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {'message': '枫桥智盾 API 已启动', 'docs': '/docs'}

@app.get('/admin')
def serve_admin():
    """后台管理页面"""
    admin_path = os.path.join(WEB_DIR, 'admin.html')
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return {'message': '管理页面未找到'}


# ==================== Entry ====================
if __name__ == '__main__':
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    uvicorn.run('server:app', host='0.0.0.0', port=port, reload=False, log_level='info')
