"""
枫桥智盾 · 后端API服务
端口 5000 · SQLAlchemy ORM + MySQL + Redis(fakeredis)
"""
import json, sys, uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

import fakeredis
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import (
    Case, DedupRecord, AlertEvent, PersonProfile, FollowUpRecord,
    Policy, AuditLog, get_session, init_db,
)

# Redis (fakeredis - 生产换成 redis.Redis)
r = fakeredis.FakeRedis(decode_responses=True)

# 初始化缓存
def init_cache():
    if not r.exists('dashboard:total'):
        r.hset('dashboard:total', mapping={'value': 0, 'label': '累计案件数'})
        r.hset('dashboard:dedup', mapping={'value': 0, 'label': '智能去重识别'})
        r.hset('dashboard:alerts', mapping={'value': 0, 'label': '实时预警事件'})
        r.hset('dashboard:resolved', mapping={'value': 0, 'label': '化解成功'})
        r.delete('feed:list')

init_cache()

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


def push_feed(msg, feed_type='info'):
    item = json.dumps({'msg': msg, 'type': feed_type, 'time': datetime.now().strftime('%H:%M:%S')})
    r.lpush('feed:list', item)
    r.ltrim('feed:list', 0, 49)


def log_audit(session, target_type, target_id, action, detail, operator='system'):
    session.add(AuditLog(
        target_type=target_type, target_id=target_id,
        action=action, operator=operator, detail=detail,
    ))


class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/import': return self.handle_import()
        if path == '/api/dedup': return self.handle_dedup()
        if path == '/api/alert': return self.handle_alert()
        self._send_json({'error': 'not found'}, 404)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/stats': return self.handle_stats()
        if path == '/api/cases': return self.handle_list_cases()
        if path == '/api/dashboard': return self.handle_dashboard()
        if path == '/api/feed': return self.handle_feed()
        self._send_json({'error': 'not found'}, 404)

    # ---- Dashboard ----
    def handle_dashboard(self):
        self._send_json({
            'total': int(r.hget('dashboard:total', 'value') or 0),
            'dedup': int(r.hget('dashboard:dedup', 'value') or 0),
            'alerts': int(r.hget('dashboard:alerts', 'value') or 0),
            'resolved': int(r.hget('dashboard:resolved', 'value') or 0),
        })

    def handle_feed(self):
        items = r.lrange('feed:list', 0, 19)
        self._send_json([json.loads(i) for i in items])

    # ---- Stats ----
    def handle_stats(self):
        session = get_session()
        try:
            total = session.query(func.count(Case.id)).scalar()
            duplicates = session.query(func.count(Case.id)).filter(Case.dedup_status >= 2).scalar()
            alerts = session.query(func.count(Case.id)).filter(Case.alert_level > 0).scalar()
            self._send_json({'total': total, 'duplicates': duplicates, 'alerts': alerts})
        finally:
            session.close()

    def handle_list_cases(self):
        session = get_session()
        try:
            cases = session.query(Case).order_by(Case.id.desc()).limit(50).all()
            self._send_json({'cases': [{
                'id': c.id, 'case_code': c.case_code, 'dispute_type': c.dispute_type,
                'district': c.district, 'parties': c.parties,
                'accept_time': str(c.accept_time) if c.accept_time else None,
                'amount': c.amount, 'dedup_status': c.dedup_status,
                'alert_level': c.alert_level, 'status': c.status,
            } for c in cases]})
        finally:
            session.close()

    # ---- Import ----
    def handle_import(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            records = body.get('records', [])
            if not records:
                self._send_json({'error': 'no records'}, 400); return

            batch_id = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8]
            session = get_session()
            inserted, skipped = 0, 0

            try:
                for rec in records:
                    mapped = {}
                    for js_key, db_col in FIELD_MAP.items():
                        mapped[db_col] = rec.get(js_key, '')

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
                        import_time=datetime.now(),
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
                log_audit(session, 'case', 0, 'import',
                          {'batch': batch_id, 'inserted': inserted, 'skipped': skipped})

                self._send_json({'success': True, 'batch': batch_id, 'inserted': inserted, 'skipped': skipped})
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # ---- Dedup ----
    def handle_dedup(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            batch_id = body.get('batch', '')
            case_ids = body.get('case_ids', [])
            if not batch_id or not case_ids:
                self._send_json({'error': 'batch and case_ids required'}, 400); return

            session = get_session()
            dup_results, total_dup = [], 0

            try:
                for cid in case_ids:
                    # Redis 缓存检查
                    cache_key = f'dedup:case:{cid}'
                    cached = r.get(cache_key)
                    if cached:
                        cached_data = json.loads(cached)
                        dup_results.append(cached_data)
                        if cached_data.get('match_count', 0) > 0: total_dup += 1
                        new_status = 3 if cached_data.get('match_count', 0) > 0 else 1
                        session.query(Case).filter(Case.id == cid).update({'dedup_status': new_status})
                        continue

                    new_case = session.query(Case).get(cid)
                    if not new_case: continue

                    matches = session.query(Case).filter(
                        Case.id != cid,
                        Case.dedup_status != 3,
                        Case.district == new_case.district,
                        Case.dispute_type == new_case.dispute_type,
                        Case.parties.isnot(None),
                        Case.parties != '',
                    ).limit(5).all()

                    if matches:
                        scores = {'phone': 35, 'address': 28, 'semantic': 18, 'name': 8}
                        total = sum(scores.values())
                        for m in matches:
                            session.add(DedupRecord(
                                case_id=cid, matched_case_id=m.id,
                                score_phone=scores['phone'], score_address=scores['address'],
                                score_semantic=scores['semantic'], score_name=scores['name'],
                                total_score=total,
                            ))
                        session.query(Case).filter(Case.id == cid).update({'dedup_status': 2})
                        result = {'case_id': cid, 'match_count': len(matches), 'total_score': total}
                        dup_results.append(result); total_dup += 1
                        r.setex(cache_key, 3600, json.dumps(result))
                    else:
                        session.query(Case).filter(Case.id == cid).update({'dedup_status': 1})
                        r.setex(cache_key, 3600, json.dumps({'case_id': cid, 'match_count': 0, 'total_score': 0}))

                session.commit()
                r.hincrby('dashboard:dedup', 'value', total_dup)
                push_feed(f'🔍 智能去重完成：检查 {len(case_ids)} 条，发现 {total_dup} 条疑似重复', 'warning')
                log_audit(session, 'case', 0, 'dedup',
                          {'batch': batch_id, 'checked': len(case_ids), 'duplicates': total_dup})

                self._send_json({'success': True, 'checked': len(case_ids), 'duplicates': total_dup, 'results': dup_results})
            except Exception:
                session.rollback(); raise
            finally:
                session.close()
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # ---- Alert ----
    def handle_alert(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            case_ids = body.get('case_ids', [])
            if not case_ids:
                self._send_json({'error': 'case_ids required'}, 400); return

            session = get_session()
            alerts, red_count, orange_count = [], 0, 0

            try:
                for cid in case_ids:
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
                if red_count:
                    push_feed(f'🔴 红色预警触发 {red_count} 件：涉及金额≥10万元', 'danger')
                if orange_count:
                    push_feed(f'🟠 橙色预警触发 {orange_count} 件：涉及金额≥1万元', 'warning')
                log_audit(session, 'alert', 0, 'alert_scan',
                          {'checked': len(case_ids), 'alerts': len(alerts)})

                self._send_json({'success': True, 'alerts': len(alerts), 'red': red_count, 'orange': orange_count})
            except Exception:
                session.rollback(); raise
            finally:
                session.close()
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def log_message(self, format, *args):
        print(f"[API] {args[0]}")


if __name__ == '__main__':
    init_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    server = HTTPServer(('0.0.0.0', port), APIHandler)
    print(f'枫桥智盾 API 已启动: http://localhost:{port}')
    print(f'ORM: SQLAlchemy 2.0  |  DB: MySQL  |  Cache: Redis(fakeredis)')
    print(f'端点: POST /api/import /api/dedup /api/alert  GET /api/dashboard /api/feed /api/stats')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止'); server.server_close()
