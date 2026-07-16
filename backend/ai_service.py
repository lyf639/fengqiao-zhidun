"""
枫桥智盾 · AI 语义服务
支持：本地 ST (sentence-transformers) / Ollama (deepseek-r1) / 云端 DeepSeek-v4-pro / 模拟回退
切换方式：环境变量 AI_BACKEND=st|ollama|deepseek|mock
"""
import os, json, requests

AI_BACKEND = os.getenv('AI_BACKEND', 'st')              # st | ollama | deepseek | mock
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'deepseek-r1:1.5b')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
ST_MODEL_NAME = os.getenv('ST_MODEL', 'paraphrase-multilingual-MiniLM-L12-v2')

_st_model = None


def extract_digits(s: str) -> str:
    """提取字符串中的数字，用于电话号码模糊比对"""
    return ''.join(c for c in s if c.isdigit())


def normalize_address(s: str) -> str:
    """地址标准化：去空格、统一符号"""
    return s.replace(' ', '').replace('　', '').replace('-', '').replace('，', ',').replace('、', ',')


def field_scores(case_a: dict, case_b: dict) -> dict:
    """
    逐字段比对两个案件的 phone / address / name，返回实际得分
    """
    # 电话匹配 (0-40)
    phone_a = extract_digits(case_a.get('parties', '') + case_a.get('description', ''))
    phone_b = extract_digits(case_b.get('parties', '') + case_b.get('description', ''))
    if phone_a and phone_b and len(phone_a) >= 11 and len(phone_b) >= 11:
        # 比较后 8 位（排除区号和格式差异）
        if phone_a[-8:] == phone_b[-8:]:
            score_phone = 40
        elif phone_a[-6:] == phone_b[-6:]:
            score_phone = 30
        elif phone_a[-4:] == phone_b[-4:]:
            score_phone = 15
        else:
            score_phone = 0
    else:
        # 无足够数字信息时，检查 parties 字段重叠度
        parties_a = set(c.split(',')[0].strip() for c in case_a.get('parties', '').split(','))
        parties_b = set(c.split(',')[0].strip() for c in case_b.get('parties', '').split(','))
        overlap = len(parties_a & parties_b)
        score_phone = min(overlap * 15, 40) if overlap > 0 else 0

    # 地址匹配 (0-30)
    addr_a = normalize_address(case_a.get('district', ''))
    addr_b = normalize_address(case_b.get('district', ''))
    if addr_a and addr_b and addr_a == addr_b:
        score_address = 30
    elif addr_a and addr_b:
        # 部分匹配：乡镇级别相同
        chunk_a = addr_a[:2] if len(addr_a) >= 2 else addr_a
        chunk_b = addr_b[:2] if len(addr_b) >= 2 else addr_b
        score_address = 15 if chunk_a == chunk_b else 5
    else:
        score_address = 0

    # 姓名匹配 (0-10)
    names_a = set(c.split(',')[0].strip() for c in case_a.get('parties', '').split(','))
    names_b = set(c.split(',')[0].strip() for c in case_b.get('parties', '').split(','))
    overlap = len(names_a & names_b)
    score_name = min(overlap * 10, 10) if overlap > 0 else 0

    return {'phone': score_phone, 'address': score_address, 'name': score_name}

def _get_st_model():
    """延迟加载 sentence-transformers 模型"""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(ST_MODEL_NAME)
    return _st_model


def semantic_similarity(case_a: dict, case_b: dict) -> dict:
    """
    计算两条案件描述的语义相似度
    返回: {'score': 0-20, 'reason': '...', 'backend': 'st'|'ollama'|'deepseek'|'mock'}
    """
    if AI_BACKEND == 'deepseek' and DEEPSEEK_API_KEY:
        return _deepseek_similarity(case_a, case_b)
    elif AI_BACKEND == 'ollama':
        return _ollama_similarity(case_a, case_b)
    elif AI_BACKEND == 'st':
        return _st_similarity(case_a, case_b)
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


def _st_similarity(a: dict, b: dict) -> dict:
    """本地 Sentence-Transformers 语义相似度"""
    try:
        model = _get_st_model()
        text_a = f"{a.get('dispute_type','')} {a.get('description','')[:300]}"
        text_b = f"{b.get('dispute_type','')} {b.get('description','')[:300]}"
        embeddings = model.encode([text_a, text_b], convert_to_tensor=True)
        from sentence_transformers.util import cos_sim
        similarity = float(cos_sim(embeddings[0], embeddings[1])[0][0])
        return {
            'score': round(similarity * 20, 1),
            'reason': f'向量余弦相似度 {similarity:.2%}',
            'backend': 'st',
        }
    except Exception as e:
        return _mock_similarity(a, b, f'st_error:{str(e)[:30]}')


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
