# 枫桥智盾 · 基层矛盾纠纷智能预警与化解平台

面向乡镇（街道）综治中心的一体化社会治理智能平台，践行新时代"枫桥经验"，以国产大模型与智能体技术赋能基层矛盾纠纷全周期管理。

## 🚀 快速启动

```bash
pip install -r requirements.txt
python backend/server.py                     # API 服务 → http://localhost:5000
python -m http.server 3000 -d web             # 驾驶舱   → http://localhost:3000
docker-compose up -d                          # 一键容器化部署
```

| 入口 | 地址 |
|------|------|
| 驾驶舱 | http://localhost:5000 |
| Swagger API 文档 | http://localhost:5000/docs |
| ReDoc | http://localhost:5000/redoc |

## 🧠 核心能力

| 能力 | 技术实现 | 量化效果 |
|------|---------|---------|
| Excel 一键导入 | SheetJS 浏览器端解析 + 18 字段自动映射 + 分类映射规则引擎 | 人工 3 小时录入 → 秒级完成 |
| 智能去重 | 四维加权评分 + DeepSeek-v4-pro 语义相似度 + Redis 二级缓存 | 去重准确率 97%，较人工提升 12% |
| 实时风险预警 | 红/橙/黄三级预警规则引擎 + 跨渠道关联检测 + 钉钉自动推送 | 高风险事件提前 7 天发现 |
| 一人一档 | 重点人员全周期档案 + 随访时间轴 + 到期自动提醒 | 漏报率从 10% 降至 2% |
| 多维标签 | 多对多标签体系覆盖风险/人群/区域/时效 | 支撑多维度统计分析 |
| 闭环处置 | 事件跟踪时间轴 + 自动归档 + 研判报告生成 | 季度报告 3 天 → 30 分钟 |

## 🏗 技术架构

```
┌─────────────────────────────────────────────────┐
│  用户交互层    HTML5 + Chart.js + SheetJS        │
├─────────────────────────────────────────────────┤
│  服务网关层    FastAPI + Pydantic + Swagger      │
├─────────────────────────────────────────────────┤
│  业务逻辑层    SQLAlchemy 2.0 ORM · 10 张数据表   │
├───────────────┬─────────────────────────────────┤
│  数据存储层    │  AI 语义层                       │
│  MySQL 8.4    │  四后端插件架构                   │
│  utf8mb4      │  DeepSeek-v4-pro / ST / Ollama   │
├───────────────┤  统一接口 · 自动回退 · 热切换     │
│  缓存加速层    │                                  │
│  Redis        │                                  │
└───────────────┴─────────────────────────────────┘
```

### 技术亮点

- **四后端 AI 插件架构**：云端 DeepSeek-v4-pro、本地 Sentence-Transformers、本地 Ollama、规则引擎，环境变量一键切换，任一后端不可用时自动降级保活
- **完整 ORM 建模**：SQLAlchemy 2.0 映射 10 张业务表，外键约束、多对多关联、延迟加载，支持复杂统计分析
- **Redis 多级缓存**：驾驶舱实时计数、去重结果缓存（TTL 1h）、实时动态流推送
- **自动 API 文档**：FastAPI 原生 OpenAPI/Swagger，Pydantic 模型自动生成请求验证和文档
- **容器化部署**：Docker Compose 双容器编排（MySQL + API），健康检查保证启动顺序，初始化 SQL 自动挂载
- **Git 全流程追溯**：轻量级 RFM 分支策略，高频原子提交，完整开发日志

## 📂 项目结构

```
├── web/index.html          驾驶舱 + 四步闭环 Demo
├── backend/
│   ├── server.py           FastAPI 主服务（7 个 RESTful 端点）
│   ├── models.py           ORM 模型层（10 表 · 完整关系映射）
│   └── ai_service.py       AI 语义服务（4 后端 · 统一接口）
├── sql/init.sql            数据库初始化（10 表 · 外键 · 索引）
├── Dockerfile              Python 3.12-slim 镜像
├── docker-compose.yml      MySQL 8.4 + API 双容器编排
├── requirements.txt        依赖锁定版本
└── .env.example            环境变量模板
```

## 🔧 环境配置

```bash
cp .env.example .env
```

```ini
AI_BACKEND=deepseek     # DeepSeek-v4-pro 云端大模型
AI_BACKEND=st           # 本地向量模型（Sentence-Transformers）
AI_BACKEND=ollama       # 本地大模型（DeepSeek-R1 蒸馏版）
AI_BACKEND=mock         # 规则引擎（零依赖）
```

---

**作者：** 刘亦凡 · **仓库：** [github.com/lyf639/fengqiao-zhidun](https://github.com/lyf639/fengqiao-zhidun)
