"""
枫桥智盾 · AI 语义服务
=====================

四后端插件架构：
  1. deepseek   —— 云端 DeepSeek-v4-pro（需 API Key）
  2. ollama     —— 本地 Ollama 运行 deepseek-r1 蒸馏模型
  3. st         —— 本地 Sentence-Transformers 向量模型
  4. mock       —— 规则引擎兜底（关键词+类型+区域）

降级策略（field_scores 内部）：
  AI_BACKEND=deepseek 不可用 → ollama 不可用 → st 不可用 → mock 兜底

核心函数：
  semantic_similarity(a, b)  → {'score': 0-20, 'reason': '...', 'backend': '...'}
  field_scores(a, b)          → {'phone': 0-40, 'address': 0-30, 'name': 0-10}
  parse_case_text(text)       → {'fields': {...}, 'confidence': 0-1, 'backend': '...'}

使用示例：
  result = semantic_similarity(case_a, case_b)
  print(result['score'])   # 18.5（满分 20）
  print(result['backend']) # 'deepseek'
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
    
    评分规则（总分 80 = phone 40 + address 30 + name 10）：
    - 电话：提取数字，后8位全匹配=40分，后6位=30分，后4位=15分，无关=0分
    - 地址：乡镇完全相同=30分，前2字相同=15分，不同=5分
    - 姓名：当事人交集数量 × 10 分（上限10分）
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
    b_district = b.get('district', '')

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


# ============================================================
# 文字解析 - 结构化字段提取（三级降级）
# ============================================================

PARSE_PROMPT = """你是基层矛盾纠纷调解系统的智能助手。请从以下文字中提取纠纷案件的关键信息，只返回 JSON。

文字内容：{text}

返回格式（只返回 JSON，不要说别的话）：
{{
  "case_code": "",
  "dispute_type": "",
  "parties": "",
  "district": "",
  "amount": 0,
  "description": "",
  "difficulty": "简单纠纷",
  "case_source": "",
  "special_group": "",
  "has_death": "否"
}}

要求：
- parties 填写"申请人姓名 vs 被申请人姓名"
- dispute_type 从以下选：损害赔偿纠纷、邻里纠纷、婚姻家庭纠纷、合同纠纷、劳动争议、土地纠纷、物业纠纷、医疗纠纷、交通事故纠纷、其他纠纷
- district 填写乡镇/街道名称
- amount 为涉及金额（数字），没有则填 0
- description 为纠纷摘要（200 字以内）
- difficulty 为 简单纠纷/一般纠纷/复杂纠纷
"""


def parse_case_text(text: str) -> dict:
    """
    将一段自然语言文字解析为结构化案件字段。
    三级降级：deepseek → ollama → regex_parse
    返回: {'fields': {...}, 'confidence': 0-1, 'backend': '...'}
    """
    text = text.strip()
    if not text:
        return {'fields': {}, 'confidence': 0, 'backend': 'empty', 'error': '输入为空'}

    if AI_BACKEND == 'deepseek' and DEEPSEEK_API_KEY:
        return _deepseek_parse(text)
    elif AI_BACKEND == 'ollama':
        return _ollama_parse(text)
    else:
        return _regex_parse(text)


def _deepseek_parse(text: str) -> dict:
    """DeepSeek API 解析"""
    try:
        resp = requests.post(
            f'{DEEPSEEK_BASE_URL}/chat/completions',
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'deepseek-chat', 'messages': [{'role': 'user', 'content': PARSE_PROMPT.format(text=text)}],
                  'temperature': 0.1, 'max_tokens': 500},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            raw = data['choices'][0]['message']['content'].strip()
            start, end = raw.find('{'), raw.rfind('}') + 1
            if start >= 0 and end > start:
                return {'fields': json.loads(raw[start:end]), 'confidence': 0.9, 'backend': 'deepseek'}
        return _ollama_parse(text) if OLLAMA_HOST else _regex_parse(text)
    except Exception:
        return _ollama_parse(text) if OLLAMA_HOST else _regex_parse(text)


def _ollama_parse(text: str) -> dict:
    """Ollama 本地模型解析"""
    try:
        resp = requests.post(
            f'{OLLAMA_HOST}/api/generate',
            json={'model': OLLAMA_MODEL, 'prompt': PARSE_PROMPT.format(text=text), 'stream': False,
                  'options': {'temperature': 0.1, 'num_predict': 500}},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get('response', '').strip()
            start, end = raw.find('{'), raw.rfind('}') + 1
            if start >= 0 and end > start:
                return {'fields': json.loads(raw[start:end]), 'confidence': 0.7, 'backend': 'ollama'}
        return _regex_parse(text)
    except Exception:
        return _regex_parse(text)


def _regex_parse(text: str) -> dict:
    """规则兜底：正则 + 关键词提取"""
    import re
    fields = {'case_code': '', 'dispute_type': '其他纠纷', 'parties': '', 'district': '',
              'amount': 0, 'description': text[:200], 'difficulty': '简单纠纷',
              'case_source': '', 'special_group': '', 'has_death': '否'}

    # 提取金额
    m = re.search(r'(\d+[\.\d]*)\s*万', text)
    if m: fields['amount'] = float(m.group(1)) * 10000
    else:
        m = re.search(r'(\d+[\.\d]*)\s*元', text)
        if m: fields['amount'] = float(m.group(1))

    # 提取当事人（"XX vs XX" 或 "XX与XX" 或 "XX和XX"）
    # 用更精确的模式：找"人名+连接词+人名"，限制名字长度
    m = re.search(r'([\u4e00-\u9fa5]{2,4})\s*(?:vs|VS|和|与|同|对|跟)\s*([\u4e00-\u9fa5]{2,4})', text)
    if m: fields['parties'] = f"{m.group(1)} vs {m.group(2)}"

    # 提取区域
    dist_keywords = ['乡', '镇', '街道', '村', '社区']
    for kw in dist_keywords:
        m = re.search(rf'([\u4e00-\u9fa5]{{2,4}}{kw})', text)
        if m:
            fields['district'] = m.group(1)
            break

    # 提取纠纷类型
    types = {'损害赔偿纠纷': ['赔偿', '损伤', '伤害', '受伤', '损害'],
             '邻里纠纷': ['邻居', '邻里', '漏水', '噪音', '楼道'],
             '婚姻家庭纠纷': ['离婚', '抚养', '赡养', '继承', '婚姻'],
             '土地纠纷': ['土地', '宅基地', '拆迁', '征地'],
             '合同纠纷': ['合同', '违约', '欠款', '拖欠'],
             '劳动争议': ['工资', '劳动', '工伤', '社保'],
             '物业纠纷': ['物业', '小区', '停车', '电梯'],
             '交通事故纠纷': ['交通', '车祸', '撞', '剐蹭']}
    for t, kws in types.items():
        if any(kw in text for kw in kws):
            fields['dispute_type'] = t
            break

    # 提取难度
    if any(kw in text for kw in ['死亡', '重伤', '命案', '重大']):
        fields['difficulty'] = '复杂纠纷'
        fields['has_death'] = '是' if any(k in text for k in ['死亡', '死', '命案']) else '否'
    elif any(kw in text for kw in ['争议', '多次', '上访', '报警']):
        fields['difficulty'] = '一般纠纷'

    return {'fields': fields, 'confidence': 0.4, 'backend': 'regex'}
