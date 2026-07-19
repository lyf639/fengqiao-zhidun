import os, markdown

md_path = os.path.join(os.path.dirname(__file__), '项目介绍.md')
html_path = os.path.join(os.path.dirname(__file__), '项目介绍.html')

with open(md_path, 'r', encoding='utf-8') as f:
    md = f.read()

html = markdown.markdown(md, extensions=['tables', 'fenced_code', 'toc'])

body = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8">
<style>
body{{font-family:"Microsoft YaHei",sans-serif;max-width:900px;margin:0 auto;padding:40px;color:#333;line-height:1.8}}
h1{{text-align:center;font-size:26px;border-bottom:2px solid #1a3a5c;padding-bottom:10px}}
h2{{font-size:20px;border-bottom:1px solid #ddd;padding-bottom:6px;margin-top:36px}}
h3{{font-size:16px}}
table{{border-collapse:collapse;width:100%;margin:14px 0}}
th,td{{border:1px solid #ccc;padding:8px 12px;text-align:left}}
th{{background:#f0f4f8}}
pre{{background:#f5f5f5;padding:14px;border-radius:4px;overflow-x:auto;font-size:13px}}
code{{background:#f0f0f0;padding:2px 6px;border-radius:3px}}
blockquote{{border-left:4px solid #1a3a5c;margin:14px 0;padding:10px 18px;background:#f8f9fa}}
hr{{border:none;border-top:1px solid #eee;margin:40px 0}}
strong{{color:#1a3a5c}}
</style></head><body>{html}</body></html>'''

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(body)

print('HTML ready')
