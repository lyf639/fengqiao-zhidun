# -*- coding: utf-8 -*-
"""
枫桥智盾 · 项目介绍.md → 项目介绍.pdf
纯 Python 生成方案（reportlab + 系统中文字体），不依赖 weasyprint/浏览器。

用法: python _gen_pdf_reportlab.py
"""
import os
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Preformatted, HRFlowable, ListFlowable, ListItem,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

BASE = os.path.dirname(os.path.abspath(__file__))
MD_PATH = os.path.join(BASE, '项目介绍.md')
PDF_PATH = os.path.join(BASE, '项目介绍.pdf')

# ---------------------------------------------------------------------------
# 字体
# ---------------------------------------------------------------------------
def setup_fonts():
    body = 'STSong-Light'
    bold = None
    if os.path.exists('C:/Windows/Fonts/msyh.ttc'):
        try:
            pdfmetrics.registerFont(TTFont('MSYH', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
            body = 'MSYH'
            if os.path.exists('C:/Windows/Fonts/msyhbd.ttc'):
                try:
                    pdfmetrics.registerFont(TTFont('MSYHBD', 'C:/Windows/Fonts/msyhbd.ttc', subfontIndex=0))
                    bold = 'MSYHBD'
                except Exception:
                    bold = None
            pdfmetrics.registerFontFamily('MSYH', normal='MSYH',
                                          bold=bold or 'MSYH', italic='MSYH',
                                          boldItalic=bold or 'MSYH')
        except Exception as e:
            print('[font] MSYH 注册失败，回退 STSong-Light:', e)
            body = 'STSong-Light'
    else:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    return body, bold

BODY, BOLD = setup_fonts()
CODE_FONT = BODY  # 代码块用 CJK 字体以保证中文/制表符可见

# ---------------------------------------------------------------------------
# 样式
# ---------------------------------------------------------------------------
NAVY = colors.HexColor('#1a3a5c')
GRAY = colors.HexColor('#555555')
LIGHT = colors.HexColor('#f0f4f8')
LINE = colors.HexColor('#cccccc')

def S(name, **kw):
    base = dict(fontName=BODY, fontSize=10, leading=15.5, textColor=colors.black)
    base.update(kw)
    return ParagraphStyle(name, **base)

st_title = S('title', fontName=BOLD or BODY, fontSize=20, leading=26, alignment=1,
             textColor=NAVY, spaceAfter=4)
st_subtitle = S('subtitle', fontSize=9.5, alignment=1, textColor=GRAY, spaceAfter=6)
st_h2 = S('h2', fontName=BOLD or BODY, fontSize=14.5, leading=19, textColor=NAVY,
          spaceBefore=14, spaceAfter=5)
st_h3 = S('h3', fontName=BOLD or BODY, fontSize=11.5, leading=15, textColor=NAVY,
          spaceBefore=9, spaceAfter=3)
st_body = S('body', spaceBefore=2, spaceAfter=4)
st_bullet = S('bullet', leftIndent=4, spaceAfter=2)
st_quote = S('quote', leftIndent=12, textColor=GRAY, spaceBefore=3, spaceAfter=5)
st_code = S('code', fontName=CODE_FONT, fontSize=7.5, leading=9.5,
            backColor=colors.HexColor('#f5f5f5'), textColor=colors.HexColor('#333333'),
            borderColor=LINE, borderWidth=0.5, borderPadding=5,
            spaceBefore=4, spaceAfter=6)
st_th = S('th', fontName=BOLD or BODY, fontSize=8.6, leading=11.5,
          backColor=LIGHT, textColor=NAVY)
st_td = S('td', fontSize=8.4, leading=11.5)

ALIGN = {'LEFT': 0, 'CENTER': 1, 'RIGHT': 2}

# ---------------------------------------------------------------------------
# markdown 行内与文本处理
# ---------------------------------------------------------------------------
def sanitize(text):
    """清理 emoji，替换为 CJK 字体可渲染的安全字符。"""
    text = (text.replace('🔴', '●').replace('🟠', '●').replace('🟡', '●')
                .replace('⭐', '★').replace('⚡', ''))
    # 去除补充平面 emoji、变体选择符、零宽连接符
    text = re.sub(r'[\U0001F000-\U0001FAFF\uFE0F\u200D]', '', text)
    return text

def inline(text):
    """转义 + 应用行内标记（**bold**、`code`、[text](url)）。"""
    text = sanitize(text)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'`([^`]+)`', lambda m: f'<font face="Courier" size="7.5">{m.group(1)}</font>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text

# ---------------------------------------------------------------------------
# 表格
# ---------------------------------------------------------------------------
SEP_RE = re.compile(r'^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$')

def is_sep(line):
    return bool(SEP_RE.match(line))

def is_table_start(lines, i):
    return '|' in lines[i] and i + 1 < len(lines) and is_sep(lines[i + 1])

def split_row(line):
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [c.strip() for c in line.split('|')]

def make_table(rows):
    header = split_row(rows[0])
    aligns = []
    for p in rows[1].strip().strip('|').split('|'):
        p = p.strip()
        if p.startswith(':') and p.endswith(':'):
            aligns.append('CENTER')
        elif p.endswith(':'):
            aligns.append('RIGHT')
        else:
            aligns.append('LEFT')
    data = [split_row(r) for r in rows[2:]]

    def cells(row, style):
        out = []
        for idx, c in enumerate(row):
            p = Paragraph(inline(c), style)
            p.style.alignment = ALIGN.get(aligns[idx] if idx < len(aligns) else 'LEFT', 0)
            out.append(p)
        return out

    header_cells = cells(header, st_th)
    body_cells = [cells(r, st_td) for r in data]
    col_n = max(len(header), max((len(r) for r in data), default=0))
    while len(header_cells) < col_n:
        header_cells.append(Paragraph('', st_th))
    for r in body_cells:
        while len(r) < col_n:
            r.append(Paragraph('', st_td))

    t = Table([header_cells] + body_cells, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafbfd')]),
    ]))
    return t

# ---------------------------------------------------------------------------
# 代码块
# ---------------------------------------------------------------------------
def code_block(text):
    text = text.rstrip('\n')
    return Preformatted(text, st_code)

# ---------------------------------------------------------------------------
# 主解析
# ---------------------------------------------------------------------------
def heading(text, level):
    text = sanitize(text).strip()
    text = re.sub(r'\s+#+\s*$', '', text)
    if level == 1:
        return Paragraph(inline(text), st_title)
    if level == 2:
        return Paragraph(inline(text), st_h2)
    if level == 3:
        return Paragraph(inline(text), st_h3)
    return Paragraph(inline(text), st_body)

def starts_block(lines, i):
    s = lines[i].strip()
    if not s:
        return True
    if s.startswith('```'):
        return True
    if s == '---':
        return True
    if re.match(r'^#{1,6}\s', lines[i]):
        return True
    if re.match(r'^\s*[-*+]\s+', lines[i]):
        return True
    if s.startswith('>'):
        return True
    if is_table_start(lines, i):
        return True
    return False

def build_story(lines):
    story = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        # 代码块
        if s.startswith('```'):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            story.append(code_block('\n'.join(buf)))
            continue
        # 分隔线
        if s == '---':
            story.append(HRFlowable(width='100%', thickness=0.8, color=LINE,
                                    spaceBefore=8, spaceAfter=8))
            i += 1
            continue
        # 标题
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m:
            story.append(heading(m.group(2), len(m.group(1))))
            i += 1
            continue
        # 表格
        if is_table_start(lines, i):
            tbl = []
            while i < n:
                cur = lines[i].strip()
                if not cur:
                    break
                if cur.startswith('```') or re.match(r'^#{1,6}\s', lines[i]):
                    break
                if '|' not in cur:
                    break
                tbl.append(lines[i])
                i += 1
            story.append(make_table(tbl))
            continue
        # 列表
        if re.match(r'^\s*[-*+]\s+', line):
            items = []
            while i < n and re.match(r'^\s*[-*+]\s+', lines[i]):
                item_text = re.sub(r'^\s*[-*+]\s+', '', lines[i].strip())
                items.append(ListItem(Paragraph(inline(item_text), st_bullet)))
                i += 1
            story.append(ListFlowable(items, bulletType='bullet', start='•',
                                      leftIndent=10, spaceBefore=3, spaceAfter=5))
            continue
        # 引用
        if s.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i].strip()))
                i += 1
            story.append(Paragraph(inline('<br/>'.join(buf)), st_quote))
            continue
        # 段落（合并连续文本行）
        para = [s]
        i += 1
        while i < n and not starts_block(lines, i):
            para.append(lines[i].strip())
            i += 1
        story.append(Paragraph(inline(' '.join(para)), st_body))
    return story

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY, 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 12 * mm, '枫桥智盾 · 基层矛盾纠纷智能预警与化解平台')
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f'第 {doc.page} 页')
    canvas.restoreState()

def main():
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        md = f.read()
    lines = md.splitlines()

    doc = SimpleDocTemplate(
        PDF_PATH, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title='枫桥智盾 · 项目介绍',
        author='嵊泗县委政法委',
    )
    story = build_story(lines)
    # 标题下分隔线
    story.insert(1, HRFlowable(width='100%', thickness=1.2, color=NAVY,
                               spaceBefore=4, spaceAfter=8))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f'PDF created: {PDF_PATH} ({os.path.getsize(PDF_PATH)} bytes)')

if __name__ == '__main__':
    main()
