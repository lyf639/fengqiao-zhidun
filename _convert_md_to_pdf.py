import os, markdown
from weasyprint import HTML

md_path = os.path.join(os.path.dirname(__file__), '项目介绍.md')
pdf_path = os.path.join(os.path.dirname(__file__), '项目介绍.pdf')

with open(md_path, 'r', encoding='utf-8') as f:
    md_text = f.read()

html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'toc'])

html_full = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: "Microsoft YaHei", "SimSun", sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.8; }}
  h1 {{ text-align: center; font-size: 24px; border-bottom: 2px solid #1a3a5c; padding-bottom: 10px; }}
  h2 {{ font-size: 20px; border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-top: 30px; }}
  h3 {{ font-size: 16px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
  th {{ background: #f0f4f8; }}
  pre {{ background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }}
  code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }}
  blockquote {{ border-left: 4px solid #1a3a5c; margin: 12px 0; padding: 8px 16px; background: #f8f9fa; }}
  hr {{ border: none; border-top: 1px solid #eee; margin: 30px 0; }}
  strong {{ color: #1a3a5c; }}
  img {{ max-width: 100%; }}
</style>
</head>
<body>
{html_body}
</body>
</html>'''

HTML(string=html_full).write_pdf(pdf_path)
print(f'PDF created: {pdf_path} ({os.path.getsize(pdf_path)} bytes)')
