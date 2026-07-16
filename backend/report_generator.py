"""
枫桥智盾 · AI 分析报告生成器
支持月度/季度/年度报告，统计 + AI 叙事分析（云→本→规则三级降级）
"""
import json, os
from datetime import datetime, timedelta
from collections import Counter

import requests
from sqlalchemy import func

from models import Case, AlertEvent, get_session

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'deepseek-r1:1.5b')


def _call_deepseek(prompt: str) -> str:
    """调用云端 DeepSeek-v4-pro"""
    resp = requests.post(
        f'{DEEPSEEK_BASE_URL}/v1/chat/completions',
        headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'},
        json={
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3, 'max_tokens': 2000,
        },
        timeout=60,
    )
    if resp.status_code == 200:
        return resp.json()['choices'][0]['message']['content']
    raise Exception(f'DeepSeek API error: {resp.status_code}')


def _call_ollama(prompt: str) -> str:
    """调用本地 Ollama 模型"""
    resp = requests.post(
        f'{OLLAMA_HOST}/api/generate',
        json={'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False,
              'options': {'temperature': 0.3, 'num_predict': 1500}},
        timeout=60,
    )
    if resp.status_code == 200:
        return resp.json().get('response', '')
    raise Exception(f'Ollama error: {resp.status_code}')


def _generate_analysis(prompt: str, stats: dict, title: str) -> dict:
    """三级降级：DeepSeek → Ollama → 规则引擎"""
    # 第一级：云端 DeepSeek
    try:
        if DEEPSEEK_API_KEY:
            return {'analysis': _call_deepseek(prompt), 'backend': 'deepseek'}
    except Exception:
        pass

    # 第二级：本地 Ollama
    try:
        return {'analysis': _call_ollama(prompt), 'backend': 'ollama'}
    except Exception:
        pass

    # 第三级：规则引擎兜底
    return {'analysis': _rule_based_analysis(stats, title), 'backend': 'rule'}


def _rule_based_analysis(stats: dict, title: str) -> str:
    """规则引擎生成结构化报告（零依赖）"""
    t = stats
    top_types = ', '.join(f"{x['name']}({x['pct']}%)" for x in t['type_distribution'][:3])
    top_districts = ', '.join(f"{x['name']}({x['count']}件)" for x in t['district_distribution'][:3])
    top_sources = ', '.join(f"{x['name']}" for x in t['source_distribution'][:3])
    resolve_comment = '化解成效显著' if t['resolve_rate'] >= 70 else ('化解工作稳步推进' if t['resolve_rate'] >= 50 else '化解压力较大，需加大力度')
    alert_comment = '需重点关注高风险事件' if t['alert_red'] > 0 else '高风险事件总体可控'
    top_case_text = ''
    for c in t['top_cases'][:2]:
        top_case_text += f"- {c['case_code']}：{c['dispute_type']}，{c['district']}，涉及金额 {c['amount']:,.0f} 元\n"

    return f"""## 一、总体态势

{title}期间，嵊泗县共受理矛盾纠纷 {t['total']} 件，已成功化解 {t['resolved']} 件，化解率 {t['resolve_rate']}%。{resolve_comment}。涉及总金额 {t['total_amount']:,.0f} 元。{alert_comment}，其中红色预警 {t['alert_red']} 件，橙色预警 {t['alert_orange']} 件。

## 二、重点分析

高发纠纷类型集中在：{top_types}。从区域分布看，{top_districts} 为案件高发区域。案件主要来源渠道为 {top_sources}。

高金额案件方面：
{top_case_text}
## 三、工作建议

1. 针对 {t['type_distribution'][0]['name'] if t['type_distribution'] else '重点类型'} 类纠纷占比最高的情况，建议开展专项排查和源头治理。
2. 加强 {t['district_distribution'][0]['name'] if t['district_distribution'] else '重点区域'} 的调解力量配置，提升一线化解能力。
3. 完善跨部门联动机制，对涉及金额较大的案件实行领导包案、限期化解，防止矛盾升级。"""


def generate_report(period: str, year: int, month: int = None, quarter: int = None) -> dict:
    """
    生成分析报告
    period: monthly | quarterly | yearly
    """
    if period == 'monthly' and month:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        title = f'{year}年{month}月'
    elif period == 'quarterly' and quarter:
        start_month = (quarter - 1) * 3 + 1
        start = datetime(year, start_month, 1)
        end_month = start_month + 3
        if end_month > 12:
            end = datetime(year + 1, end_month - 12, 1)
        else:
            end = datetime(year, end_month, 1)
        title = f'{year}年第{quarter}季度'
    elif period == 'yearly':
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)
        title = f'{year}年'
    else:
        return {'error': 'invalid period'}

    session = get_session()
    try:
        # ---- 统计数据 ----
        cases = session.query(Case).filter(
            Case.accept_time >= start, Case.accept_time < end
        ).all()

        total = len(cases)
        resolved = sum(1 for c in cases if c.status == 2 or c.mediation_result == '调解成功')
        alert_red = sum(1 for c in cases if c.alert_level == 3)
        alert_orange = sum(1 for c in cases if c.alert_level == 2)
        total_amount = sum(c.amount or 0 for c in cases)

        # 类型分布
        type_counter = Counter(c.dispute_type for c in cases if c.dispute_type)
        type_dist = [{'name': k, 'count': v, 'pct': round(v / total * 100, 1)} for k, v in type_counter.most_common(8)]

        # 区域分布
        district_counter = Counter(c.district for c in cases if c.district)
        district_dist = [{'name': k, 'count': v} for k, v in district_counter.most_common(6)]

        # 来源分布
        source_counter = Counter(c.case_source for c in cases if c.case_source)
        source_dist = [{'name': k, 'count': v} for k, v in source_counter.most_common(6)]

        # 金额 Top5
        top_amount = sorted([c for c in cases if c.amount], key=lambda x: x.amount, reverse=True)[:5]

        stats = {
            'total': total,
            'resolved': resolved,
            'resolve_rate': round(resolved / total * 100, 1) if total > 0 else 0,
            'alert_red': alert_red,
            'alert_orange': alert_orange,
            'total_amount': round(total_amount, 2),
            'type_distribution': type_dist,
            'district_distribution': district_dist,
            'source_distribution': source_dist,
            'top_cases': [{
                'case_code': c.case_code,
                'dispute_type': c.dispute_type,
                'district': c.district,
                'parties': c.parties,
                'amount': c.amount,
                'description': (c.description or '')[:100],
            } for c in top_amount],
        }

        # ---- AI 生成叙事分析 ----
        ai_prompt = f"""你是嵊泗县综治中心的数据分析专家。请根据以下{title}矛盾纠纷统计数据，撰写一份专业的分析报告。

【数据概览】
- 事件总数：{total} 件
- 已化解：{resolved} 件（化解率 {stats['resolve_rate']}%）
- 红色预警：{alert_red} 件
- 橙色预警：{alert_orange} 件
- 涉及总金额：{total_amount:.2f} 元

【类型分布】
{json.dumps(type_dist, ensure_ascii=False)}

【区域分布】
{json.dumps(district_dist, ensure_ascii=False)}

【来源分布】
{json.dumps(source_dist, ensure_ascii=False)}

【高金额案件】
{json.dumps([{'案件': c['case_code'], '类型': c['dispute_type'], '区域': c['district'], '金额': c['amount']} for c in stats['top_cases']], ensure_ascii=False)}

请按以下结构撰写报告（共三部分，每部分 100-200 字）：

## 一、总体态势
概括{title}期间矛盾纠纷的总体规模、化解情况、与趋势判断。

## 二、重点分析
分析高发类型、重点区域、主要来源渠道，指出需要特别关注的领域。

## 三、工作建议
针对当前形势，提出 3 条具体的下一步工作建议。

请直接返回 Markdown 格式，不要额外说明。"""

        ai_result = _generate_analysis(ai_prompt, stats, title)

        return {
            'success': True,
            'title': f'嵊泗县{title}矛盾纠纷形势分析报告',
            'period': period,
            'year': year,
            'month': month,
            'quarter': quarter,
            'date_range': f'{start.strftime("%Y-%m-%d")} ~ {end.strftime("%Y-%m-%d")}',
            'stats': stats,
            'analysis': ai_result['analysis'],
            'ai_backend': ai_result['backend'],
            'generated_at': datetime.now().isoformat(),
        }
    finally:
        session.close()
