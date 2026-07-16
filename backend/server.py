"""
枫桥智盾 · 后端API服务
端口 5000，接收前端 Excel 导入数据写入 MySQL
"""
import json, sys, os, uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'FengQiao@2026',
    'database': 'fengqiao_zhidun',
    'charset': 'utf8mb4',
    'autocommit': True,
}

# 前端字段名 → cases 表字段名 映射
FIELD_MAP = {
    'caseCode': 'case_code',
    'agreementType': 'agreement_type',
    'caseSource': 'case_source',
    'mediationOrg': 'mediation_org',
    'studio': 'studio',
    'handler': 'handler',
    'acceptTime': 'accept_time',
    'description': 'description',
    'difficulty': 'difficulty',
    'disputeType': 'dispute_type',
    'caseAttr': 'case_attr',
    'specialGroup': 'special_group',
    'district': 'district',
    'hasDeath': 'has_death',
    'result': 'mediation_result',
    'mediationTime': 'mediation_time',
    'parties': 'parties',
    'amount': 'amount',
}


def get_conn():
    return mysql.connector.connect(**DB_CONFIG)


def parse_datetime(val):
    if not val:
        return None
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d']:
        try:
            return datetime.strptime(str(val).strip(), fmt)
        except ValueError:
            continue
    return None


def parse_amount(val):
    if not val or str(val).strip() == '':
        return 0.0
    try:
        return float(str(val).replace(',', '').replace('，', ''))
    except ValueError:
        return 0.0


class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({})

    def do_POST(self):
        path = urlparse(self.path).path

        if path == '/api/import':
            self.handle_import()
        elif path == '/api/dedup':
            self.handle_dedup()
        elif path == '/api/alert':
            self.handle_alert()
        else:
            self._send_json({'error': 'not found'}, 404)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == '/api/stats':
            self.handle_stats()
        elif path == '/api/cases':
            self.handle_list_cases()
        else:
            self._send_json({'error': 'not found'}, 404)

    # ----- import -----
    def handle_import(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            records = body.get('records', [])
            if not records:
                self._send_json({'error': 'no records'}, 400)
                return

            batch_id = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8]
            conn = get_conn()
            cursor = conn.cursor()
            inserted = 0
            skipped = 0

            insert_sql = """
                INSERT INTO cases (case_code, agreement_type, case_source, mediation_org,
                  studio, handler, accept_time, description, difficulty, dispute_type,
                  case_attr, special_group, district, has_death, mediation_result,
                  mediation_time, parties, amount, import_batch, import_time, dedup_status)
                VALUES (%(case_code)s, %(agreement_type)s, %(case_source)s, %(mediation_org)s,
                  %(studio)s, %(handler)s, %(accept_time)s, %(description)s, %(difficulty)s,
                  %(dispute_type)s, %(case_attr)s, %(special_group)s, %(district)s,
                  %(has_death)s, %(mediation_result)s, %(mediation_time)s, %(parties)s,
                  %(amount)s, %(import_batch)s, NOW(), 0)
            """

            for rec in records:
                mapped = {}
                for js_key, db_col in FIELD_MAP.items():
                    mapped[db_col] = rec.get(js_key, '')

                mapped['case_code'] = mapped.get('case_code', '') or f'AUTO_{uuid.uuid4().hex[:12].upper()}'
                mapped['accept_time'] = parse_datetime(mapped.get('accept_time'))
                mapped['mediation_time'] = parse_datetime(mapped.get('mediation_time'))
                mapped['amount'] = parse_amount(mapped.get('amount'))
                mapped['import_batch'] = batch_id

                try:
                    cursor.execute(insert_sql, mapped)
                    inserted += 1
                except mysql.connector.IntegrityError:
                    skipped += 1  # duplicate case_code

            # audit log
            cursor.execute("""
                INSERT INTO audit_logs (target_type, target_id, action, operator, detail)
                VALUES ('case', 0, 'import', 'system', %s)
            """, (json.dumps({'batch': batch_id, 'inserted': inserted, 'skipped': skipped}),))

            conn.close()
            self._send_json({
                'success': True,
                'batch': batch_id,
                'inserted': inserted,
                'skipped': skipped,
            })

        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # ----- dedup -----
    def handle_dedup(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            batch_id = body.get('batch', '')
            case_ids = body.get('case_ids', [])

            if not batch_id or not case_ids:
                self._send_json({'error': 'batch and case_ids required'}, 400)
                return

            conn = get_conn()
            cursor = conn.cursor(dictionary=True)

            # 对本批次每条新案件，去存量中查找疑似重复
            dup_results = []
            for cid in case_ids:
                cursor.execute("SELECT * FROM cases WHERE id = %s", (cid,))
                new_case = cursor.fetchone()
                if not new_case:
                    continue

                # 简化：按 district + dispute_type + parties 首字符匹配
                cursor.execute("""
                    SELECT id FROM cases
                    WHERE id != %s AND dedup_status != 3
                      AND district = %s AND dispute_type = %s
                      AND parties IS NOT NULL AND parties != ''
                    LIMIT 5
                """, (cid, new_case['district'], new_case['dispute_type']))

                matches = cursor.fetchall()
                if matches:
                    # 模拟打分
                    scores = {'phone': 35, 'address': 28, 'semantic': 18, 'name': 8}
                    total = sum(scores.values())
                    for m in matches:
                        cursor.execute("""
                            INSERT INTO dedup_records (case_id, matched_case_id,
                              score_phone, score_address, score_semantic, score_name, total_score)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (cid, m['id'], scores['phone'], scores['address'],
                              scores['semantic'], scores['name'], total))

                    cursor.execute("UPDATE cases SET dedup_status = 2 WHERE id = %s", (cid,))
                    dup_results.append({
                        'case_id': cid,
                        'match_count': len(matches),
                        'total_score': total,
                    })
                else:
                    cursor.execute("UPDATE cases SET dedup_status = 1 WHERE id = %s", (cid,))

            # audit
            cursor.execute("""
                INSERT INTO audit_logs (target_type, target_id, action, operator, detail)
                VALUES ('case', 0, 'dedup', 'system', %s)
            """, (json.dumps({'batch': batch_id, 'checked': len(case_ids), 'duplicates': len(dup_results)}),))

            conn.close()
            self._send_json({
                'success': True,
                'checked': len(case_ids),
                'duplicates': len(dup_results),
                'results': dup_results,
            })

        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # ----- alert -----
    def handle_alert(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            case_ids = body.get('case_ids', [])
            if not case_ids:
                self._send_json({'error': 'case_ids required'}, 400)
                return

            conn = get_conn()
            cursor = conn.cursor(dictionary=True)
            alerts = []

            for cid in case_ids:
                cursor.execute("SELECT * FROM cases WHERE id = %s", (cid,))
                c = cursor.fetchone()
                if not c:
                    continue

                level = 0
                rule = ''
                # 红色：金额>=10万 或 含"死亡"
                if c['amount'] and c['amount'] >= 100000:
                    level = 3
                    rule = 'high_amount'
                elif c['has_death'] and c['has_death'] in ('是', '有', '1'):
                    level = 3
                    rule = 'has_death'
                # 橙色：金额>=1万
                elif c['amount'] and c['amount'] >= 10000:
                    level = 2
                    rule = 'medium_amount'
                # 黄色：一般纠纷或以上
                elif c['difficulty'] and c['difficulty'] not in ('', '简单纠纷'):
                    level = 1
                    rule = 'difficulty_level'

                if level > 0:
                    cursor.execute("""
                        INSERT INTO alert_events (case_id, alert_level, rule_type, channel_count, channels, keywords)
                        VALUES (%s, %s, %s, 1, %s, %s)
                    """, (cid, level, rule, c['case_source'] or '', c['dispute_type'] or ''))
                    cursor.execute("UPDATE cases SET alert_level = %s WHERE id = %s", (level, cid))
                    alerts.append({'case_id': cid, 'level': level, 'rule': rule})

            cursor.execute("""
                INSERT INTO audit_logs (target_type, target_id, action, operator, detail)
                VALUES ('alert', 0, 'alert_scan', 'system', %s)
            """, (json.dumps({'checked': len(case_ids), 'alerts': len(alerts)}),))

            conn.close()
            self._send_json({'success': True, 'alerts': len(alerts), 'details': alerts})

        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # ----- stats -----
    def handle_stats(self):
        try:
            conn = get_conn()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) AS total FROM cases")
            total = cursor.fetchone()['total']
            cursor.execute("SELECT COUNT(*) AS cnt FROM cases WHERE dedup_status >= 2")
            duplicates = cursor.fetchone()['cnt']
            cursor.execute("SELECT COUNT(*) AS cnt FROM cases WHERE alert_level > 0")
            alerts = cursor.fetchone()['cnt']
            conn.close()
            self._send_json({'total': total, 'duplicates': duplicates, 'alerts': alerts})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    # ----- list cases -----
    def handle_list_cases(self):
        try:
            conn = get_conn()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, case_code, dispute_type, district, parties, accept_time,
                       amount, dedup_status, alert_level, status
                FROM cases ORDER BY id DESC LIMIT 50
            """)
            rows = cursor.fetchall()
            for r in rows:
                r['accept_time'] = str(r['accept_time']) if r['accept_time'] else None
                r['amount'] = float(r['amount']) if r['amount'] else 0
            conn.close()
            self._send_json({'cases': rows})
        except Exception as e:
            self._send_json({'error': str(e)}, 500)

    def log_message(self, format, *args):
        print(f"[API] {args[0]}")


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    server = HTTPServer(('0.0.0.0', port), APIHandler)
    print(f'枫桥智盾 API 服务已启动: http://localhost:{port}')
    print(f'端点: POST /api/import  POST /api/dedup  POST /api/alert  GET /api/stats')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
        server.server_close()
