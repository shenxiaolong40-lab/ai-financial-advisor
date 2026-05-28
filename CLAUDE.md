# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 本地开发启动（从项目根目录执行）
python3 -m uvicorn backend.main:app --reload

# Docker 部署
DEEPSEEK_API_KEY=sk-xxx docker compose up -d

# 健康检查
curl http://localhost:8000/api/health
```

## 环境变量（`.env`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `USER_MODE` | `single` | `single` 无需登录；`multi` 启用 JWT 认证 |
| `DEEPSEEK_API_KEY` | 空 | 必须以 `sk-` 开头且长度 > 10 才算有效 |
| `SECRET_KEY` | 内置弱密钥 | 多用户模式必须修改 |
| `DATABASE_URL` | `sqlite:///./finance.db` | 支持 PostgreSQL |

## 架构概览

**产品定位**：财务自由顾问（FIRE 法则）— 核心问题：「我还需要多久才能财务自由？」

**技术栈**：FastAPI + SQLAlchemy 2.0 + SQLite，纯 HTML/CSS/JS 前端（零框架），DeepSeek API（OpenAI 兼容）。

### FIRE 计算核心（`backend/services/fire_service.py`）

- **FIRE 数字** = 月均支出（近3月） × 12 × `fire_multiplier`（默认25，即4%法则）
- **距离年数** = 复利公式：`n = log((FV - PMT/r) / (PV - PMT/r)) / log(1+r) / 12`
- 入口：`calculate_fire_status(db, user_id)` 返回完整状态；`calculate_projection()` 返回30年预测曲线

### 数据模型（`backend/models.py`）

4张表：`User` → `Transaction`（支出/收入记录）、`Category`（预设10类）、`FireProfile`（月收入 + 4类资产 + FIRE 参数）、`AISession`（对话历史）。`Transaction` 上有 `UniqueConstraint("sync_source", "sync_id")` 用于 CSV 导入去重。

### 路由结构（从11个精简为5个）

| 前缀 | 文件 | 主要功能 |
|------|------|---------|
| `/api/fire` | `routers/fire.py` | FIRE 状态/配置/预测曲线 |
| `/api/transactions` | `routers/transactions.py` | 收支记录 CRUD |
| `/api/categories` | `routers/categories.py` | 分类列表（只读） |
| `/api/ai` | `routers/ai.py` | FIRE 顾问对话/报告 |
| `/api/import` | `routers/imports.py` | 支付宝/微信 CSV 导入 |

### 单/多用户模式

`deps.py:get_current_user_id()` — 单用户模式直接返回 `user_id=1`，完全跳过 JWT。

### AI 服务（`backend/services/ai_service.py`）

System prompt 专注 FIRE 顾问角色；每次请求从 `fire_service.calculate_fire_status()` 动态构建上下文（FIRE数字、储蓄率、分类支出）注入 system prompt；保留近5轮历史，超过50条自动清理最早记录。

### 前端结构（3页 SPA）

`frontend/index.html` 包含3个页面 + 2个模态框（FIRE配置、添加交易）。静态文件由 FastAPI 在根路径 `/` 挂载，**必须在所有 API 路由注册之后再挂载**。

| JS 文件 | 职责 |
|---------|------|
| `api.js` | HTTP 请求封装，含 Auth token 管理 |
| `app.js` | 3页导航、toast、模态框、分类缓存 |
| `fire.js` | FIRE 仪表盘：英雄区、进度条、预测曲线、双图、AI 预览 |
| `transactions.js` | 收支列表、CRUD、CSV 导入 |
| `ai.js` | FIRE 顾问对话、一键分析报告 |

### CSV 导入链路

`routers/imports.py` → `services/sync_service.py`（解析支付宝/微信 CSV 为 `ParsedRow` → 按 `CATEGORY_KEYWORDS` 自动归类 → 去重写入）。导入后月均支出自动更新，FIRE 计算随之变化。
