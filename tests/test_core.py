"""
枫桥智盾 · 基础自动化测试
=========================

覆盖核心业务逻辑：
  1. 去重字段评分（field_scores）
  2. 文字解析（parse_case_text 正则兜底）
  3. 限流令牌桶（check_rate_limit）
  4. 缓存防护（cache_get_or_set）

运行：python -m pytest tests/ -v 或 python tests/test_core.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ai_service import field_scores, parse_case_text
from rate_limiter import check_rate_limit
from cache_guard import cache_get_or_set, invalidate


def test_field_scores_phone_full_match():
    """电话后8位全匹配应得40分"""
    a = {'parties': '张三,13812345678', 'district': '枸杞乡', 'dispute_type': '邻里纠纷'}
    b = {'parties': '李四,13912345678', 'district': '枸杞乡', 'dispute_type': '邻里纠纷'}
    scores = field_scores(a, b)
    assert scores['phone'] == 40, f"期望40分，实际{scores['phone']}"


def test_field_scores_district_match():
    """乡镇完全一致应得30分"""
    a = {'parties': '张三', 'district': '枸杞乡', 'dispute_type': '邻里纠纷'}
    b = {'parties': '李四', 'district': '枸杞乡', 'dispute_type': '邻里纠纷'}
    scores = field_scores(a, b)
    assert scores['address'] == 30, f"期望30分，实际{scores['address']}"


def test_parse_text_regex_fallback():
    """正则兜底应能提取金额和类型"""
    text = "2025年6月，枸杞乡村民张阿义与邻居李四因宅基地界限争执，涉及赔偿金额2.5万元。"
    result = parse_case_text(text)
    assert result['backend'] == 'regex'
    assert abs(result['fields'].get('amount', 0) - 25000) < 1, f"金额应25000，实际{result['fields'].get('amount')}"
    assert '损害赔偿' in result['fields'].get('dispute_type', '')


def test_rate_limit_token_bucket():
    """令牌桶应在第31次拒绝（30/分钟）"""
    blocked = 0
    for _ in range(35):
        ok, remaining, retry = check_rate_limit('test_bucket', 30, 60)
        if not ok:
            blocked += 1
            assert retry > 0
    assert blocked >= 3, f"应拦截至少3次，实际{blocked}"


def test_cache_guard_null_protection():
    """空值缓存防穿透：None 结果应缓存"""
    key = 'test_null_key'
    invalidate(key)
    calls = {'n': 0}

    def fetch():
        calls['n'] += 1
        return None

    r1 = cache_get_or_set(key, ttl=60, fetch_fn=fetch)
    r2 = cache_get_or_set(key, ttl=60, fetch_fn=fetch)
    assert r1 is None and r2 is None
    assert calls['n'] == 1, f"应只调用一次 fetch，实际{calls['n']}次"


def test_cache_guard_value_cache():
    """正常值缓存命中"""
    key = 'test_value_key'
    invalidate(key)
    calls = {'n': 0}

    def fetch():
        calls['n'] += 1
        return {'data': 'hello'}

    r1 = cache_get_or_set(key, ttl=60, fetch_fn=fetch)
    r2 = cache_get_or_set(key, ttl=60, fetch_fn=fetch)
    assert r1 == {'data': 'hello'} and r2 == {'data': 'hello'}
    assert calls['n'] == 1


if __name__ == '__main__':
    passed = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print(f'[PASS] {name}')
                passed += 1
            except AssertionError as e:
                print(f'[FAIL] {name}: {e}')
    print(f'\n{passed} tests passed')
