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

4张表：`User` → `Transaction`（支出/收入记录，CSV 导入落地）、`Category`（预设10类）、`FireProfile`（FIRE 参数，含总资产/年薪/刚性支出/弹性支出/收益率）、`AISession`（对话历史）。`Transaction` 上有 `UniqueConstraint("sync_source", "sync_id")` 用于 CSV 导入去重。

### 收支数据流（`fire_service.py:calculate_fire_status`）

**优先级：交易记录聚合 > 手动配置 > 空**

- 收入：若 `Transaction` 表近3月有 `type=income` 记录 → 用月均×12 作为 `S`；否则用 `FireProfile.annual_salary`
- 支出：同上逻辑 → 用月均×12 作为 `E`；否则用 `FireProfile.annual_fixed_expense + annual_flex_expense`
- 月均按"实际有交易的日历月"数平均（`active_months`），避免空月份稀释
- 响应包含 `data_source` 字段：`{income: transactions|manual|none, expense: ...}`，前端在"自由说明"页展示
- AI 上下文（`ai_service._build_fire_context`）也注入数据来源标签

**前端无收支列表页** — 交易记录仅通过 CSV 导入 API（`/api/import/{alipay|wechat}`）入库，无 UI 查看；FIRE 配置模态框仅作为交易数据缺失时的降级输入。

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

`frontend/index.html` 包含3个页面（🔥自由之路 / 📖自由说明 / 🤖AI 顾问）+ 2个模态框（FIRE 配置、登录）。**前端无收支列表页** — 收支数据通过 FIRE 配置模态框手动填写年度刚性/弹性支出。静态文件由 FastAPI 在根路径 `/` 挂载，**必须在所有 API 路由注册之后再挂载**。

| JS 文件 | 职责 |
|---------|------|
| `api.js` | HTTP 请求封装，含 Auth token 管理 |
| `app.js` | 3页导航、toast、模态框、分类缓存 |
| `fire.js` | FIRE 仪表盘：英雄区、进度条、预测曲线、敏感性分析、AI 预览 |
| `explain.js` | 财务自由说明页：参数展示、里程碑、敏感性解读 |
| `ai.js` | FIRE 顾问对话、一键分析报告 |

### CSV 导入链路（后端保留，前端未开放）

`routers/imports.py` → `services/sync_service.py`（解析支付宝/微信 CSV 为 `ParsedRow` → 按 `CATEGORY_KEYWORDS` 自动归类 → 去重写入 `Transaction` 表）。导入后 `Transaction` 数据进入 FIRE 计算（见上方"收支数据流"），FIRE 状态随之变化。前端无收支列表页，但交易数据通过 FIRE 计算结果反映在仪表盘和说明页上。
