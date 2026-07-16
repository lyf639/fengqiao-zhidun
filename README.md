# 枫桥智盾 · 基层矛盾纠纷智能预警与化解平台

基于国产大模型与智能体技术，面向乡镇（街道）综治中心的一体化矛盾纠纷管理平台。

## 🚀 一键启动

```bash
# 本地开发
pip install -r requirements.txt
python backend/server.py          # API 服务 → http://localhost:5000
python -m http.server 3000 -d web  # 前端    → http://localhost:3000

# Docker 部署
docker-compose up -d               # MySQL + API + 前端 → http://localhost:5000
```

启动后打开：
- **驾驶舱** → http://localhost:5000
- **Swagger 文档** → http://localhost:5000/docs
- **ReDoc 文档** → http://localhost:5000/redoc

## 🧠 核心功能

| 功能 | 说明 |
|------|------|
| Excel 一键导入 | 拖入上游系统导出的 Excel，自动解析 18 列字段并入库 |
| 智能去重 | 四维加权评分 + AI 语义相似度，自动识别重复事件 |
| 风险预警 | 红/橙/黄三级预警，跨渠道关联自动触发钉钉推送 |
| 一人一档 | 重点人员全周期管理，随访到期自动提醒 |
| 分类映射 | 不同系统分类自动统一，8 条映射规则 |
| 案件标签 | 多对多标签体系，风险/人群/区域/时效多维标注 |

## 🏗 技术栈

| 层 | 技术 |
|----|------|
| **前端** | 纯 HTML/CSS/JS + Chart.js + SheetJS（Excel 解析） |
| **后端** | Python · FastAPI · Swagger 自动文档 |
| **ORM** | SQLAlchemy 2.0 · 10 张数据表 · 完整关系映射 |
| **数据库** | MySQL 8.4 · utf8mb4 |
| **缓存** | Redis (fakeredis 开发模式，生产切换 redis-py) |
| **AI** | 四后端插件架构：DeepSeek-v4-pro / Sentence-Transformers / Ollama / 规则引擎 |
| **部署** | Docker + docker-compose 一键编排 |

## 📂 项目结构

```
├── web/index.html          前端驾驶舱 + 四步 Demo
├── backend/
│   ├── server.py           FastAPI 主服务
│   ├── models.py           SQLAlchemy ORM 模型（10 表）
│   └── ai_service.py       AI 语义服务（4 后端自动回退）
├── sql/init.sql            数据库初始化脚本
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example            环境变量模板
```

## 🔧 环境配置

```bash
cp .env.example .env
# 编辑 .env，选择 AI 后端：
AI_BACKEND=deepseek     # 云端 DeepSeek-v4-pro
AI_BACKEND=ollama       # 本地 Ollama（需先安装）
AI_BACKEND=st           # 本地 Sentence-Transformers
AI_BACKEND=mock         # 规则引擎（无需联网）
```

---

**作者：** 刘亦凡 · **仓库：** [github.com/lyf639/fengqiao-zhidun](https://github.com/lyf639/fengqiao-zhidun)
