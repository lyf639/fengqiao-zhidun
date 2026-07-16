"""
枫桥智盾 · AI 语义服务
支持：本地 Ollama (deepseek-r1) / 云端 DeepSeek-v4-pro / 模拟回退
切换方式：环境变量 AI_BACKEND=ollama|deepseek|mock
"""
import os, json, requests

AI_BACKEND = os.getenv('AI_BACKEND', 'ollama')       # ollama | deepseek | mock
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'deepseek-r1:1.5b')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')


def semantic_similarity(case_a: dict, case_b: dict) -> dict:
    """
    计算两条案件描述的语义相似度
    返回: {'score': 0-20, 'reason': '...', 'backend': 'ollama'|'deepseek'|'mock'}
    """
    if AI_BACKEND == 'deepseek' and DEEPSEEK_API_KEY:
        return _deepseek_similarity(case_a, case_b)
    elif AI_BACKEND == 'ollama':
        return _ollama_similarity(case_a, case_b)
    else:
        return _mock_similarity(case_a, case_b)


def _ollama_similarity(a: dict, b: dict) -> dict:
    """调用本地 Ollama 模型"""
    prompt = f"""请判断以下两条矛盾纠纷记录是否为同一事件，仅返回 JSON。

记录 A：
- 当事人：{a.get('parties','')}
- 地址：{a.get('district','')}
- 类型：{a.get('dispute_type','')}
- 描述：{a.get('description','')[:200]}

记录 B：
- 当事人：{b.get('parties','')}
- 地址：{b.get('district','')}
- 类型：{b.get('dispute_type','')}
- 描述：{b.get('description','')[:200]}

返回格式：{{"similarity": 0.85, "reason": "简要理由"}}
similarity 范围 0~1，其中 1 表示完全一致。
"""

    try:
        resp = requests.post(
            f'{OLLAMA_HOST}/api/generate',
            json={'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False,
                  'options': {'temperature': 0.1, 'num_predict': 150}},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get('response', '').strip()
            # 提取 JSON
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
                return {
                    'score': round(parsed.get('similarity', 0.5) * 20, 1),
                    'reason': parsed.get('reason', ''),
                    'backend': 'ollama',
                }
        return _mock_similarity(a, b, 'ollama_unavailable')
    except Exception:
        return _mock_similarity(a, b, 'ollama_error')


def _deepseek_similarity(a: dict, b: dict) -> dict:
    """调用云端 DeepSeek-v4-pro API"""
    prompt = f"""请判断以下两条矛盾纠纷记录是否为同一事件。

记录 A：当事人={a.get('parties','')}，地址={a.get('district','')}，类型={a.get('dispute_type','')}，描述={a.get('description','')[:200]}
记录 B：当事人={b.get('parties','')}，地址={b.get('district','')}，类型={b.get('dispute_type','')}，描述={b.get('description','')[:200]}

仅返回 JSON：{{"similarity": 0.85, "reason": "简要理由"}}"""

    try:
        resp = requests.post(
            f'{DEEPSEEK_BASE_URL}/v1/chat/completions',
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1, 'max_tokens': 150,
                'response_format': {'type': 'json_object'},
            },
            timeout=30,
        )
        if resp.status_code == 200:
            parsed = resp.json()['choices'][0]['message']['content']
            data = json.loads(parsed) if isinstance(parsed, str) else parsed
            return {
                'score': round(data.get('similarity', 0.5) * 20, 1),
                'reason': data.get('reason', ''),
                'backend': 'deepseek',
            }
        return _mock_similarity(a, b, 'deepseek_api_error')
    except Exception:
        return _mock_similarity(a, b, 'deepseek_error')


def _mock_similarity(a: dict, b: dict, backend='mock') -> dict:
    """
    模拟回退：基于规则计算相似度
    当 Ollama 未安装或 DeepSeek API 不可用时自动启用
    """
    score = 0
    reasons = []
    a_type = a.get('dispute_type', '')
    b_type = b.get('dispute_type', '')
    a_district = a.get('district', '')
    b_district = a.get('district', '')

    # 类型一致 +10
    if a_type and a_type == b_type:
        score += 10
        reasons.append(f'类型一致({a_type})')
    elif a_type and b_type:
        score += 3

    # 同区域 +6
    if a_district and a_district == b_district:
        score += 6
        reasons.append(f'同区域({a_district})')
    elif a_district and b_district:
        score += 2

    # 关键词重叠
    desc_a = a.get('description', '')
    desc_b = b.get('description', '')
    kw = ['漏水', '噪音', '装修', '赔偿', '打架', '土地', '拆迁', '物业', '工资', '借贷']
    a_kws = {k for k in kw if k in desc_a}
    b_kws = {k for k in kw if k in desc_b}
    overlap = len(a_kws & b_kws)
    if overlap:
        score += min(overlap * 2, 4)
        reasons.append(f'关键词重叠({overlap}个)')

    return {
        'score': min(score, 20),
        'reason': '；'.join(reasons) if reasons else f'规则匹配 ({backend})',
        'backend': backend.split('_')[0],
    }
