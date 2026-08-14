import requests

# 1. gRPC 报告（monthly 带 month）
r = requests.post('http://localhost:5000/api/report/generate', json={'period': 'monthly', 'year': 2026, 'month': 6})
print('report monthly:', r.status_code, 'error' if 'error' in r.text else 'OK')

# 2. gRPC 报告（quarterly 带 quarter）
r2 = requests.post('http://localhost:5000/api/report/generate', json={'period': 'quarterly', 'year': 2026, 'quarter': 2})
print('report quarterly:', r2.status_code, 'error' if 'error' in r2.text else 'OK')

# 3. confirm_dedup 无鉴权应 401
r3 = requests.post('http://localhost:5000/api/dedup/confirm', json={'case_id': 1, 'decision': 'duplicate'})
print('confirm no-auth:', r3.status_code, '(expect 401)')

# 4. 导入租户从 JWT 提取（登录后 tenant 应为 1 且导入成功）
r4 = requests.post('http://localhost:5000/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
t = r4.json()['token']
r5 = requests.post('http://localhost:5000/api/import', json={'records': [{'caseCode': 'TENANT_T1', 'disputeType': '邻里纠纷', 'parties': '测试', 'district': '枸杞乡', 'amount': '100', 'description': 'x'}]},
                   headers={'Authorization': 'Bearer ' + t})
print('import with auth:', r5.status_code, r5.json())
