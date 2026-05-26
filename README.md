# AI 财务顾问

AI 驱动的个人财务管理工具：自动同步银行/支付宝/微信账单，智能分析消费习惯，根据收入和目标给出改善建议。

## 功能

- 📊 **仪表盘** — 收支总览、趋势图、分类饼图、预算进度
- 📋 **账单管理** — 增删改查、分类筛选、月度统计
- 🎯 **目标预算** — 储蓄目标追踪、分类预算超支预警
- 🤖 **AI 顾问** — 基于真实数据的对话式财务建议（DeepSeek）
- 💙 **账单导入** — 支付宝/微信 CSV 账单一键导入，自动去重归类
- 💳 **账户管理** — 多账户余额汇总

## 快速启动（本地开发）

```bash
# 1. 克隆项目
git clone https://github.com/shenxiaolong40-lab/ai-financial-advisor.git
cd ai-financial-advisor

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 启动后端（单用户模式，无需登录）
python -m uvicorn backend.main:app --reload

# 5. 浏览器打开前端
open frontend/index.html
# 或访问 http://localhost:8000（后端直接提供前端）
```

## Docker 部署

```bash
# 单用户模式（推荐个人使用）
DEEPSEEK_API_KEY=sk-xxx docker compose up -d

# 多用户模式
USER_MODE=multi DEEPSEEK_API_KEY=sk-xxx SECRET_KEY=your-random-secret docker compose up -d
```

访问 `http://your-server:8000`

## 多用户模式

在 `.env` 中设置：
```
USER_MODE=multi
SECRET_KEY=your-random-32-char-secret
```

多用户模式下启用注册/登录，每个用户数据完全隔离。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|------|
| `USER_MODE` | `single` 单用户 / `multi` 多用户 | `single` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 空 |
| `SECRET_KEY` | JWT 签名密钥（多用户必填） | 内置默认值 |
| `DATABASE_URL` | 数据库连接字符串 | `sqlite:///./finance.db` |

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 前端 | 纯 HTML/CSS/JS（零框架）+ Chart.js |
| AI | DeepSeek API（OpenAI 兼容） |
| 认证 | JWT（多用户模式） |
| 部署 | Docker + docker-compose |

## 账单导入说明

### 支付宝
支付宝 App → 我的 → 账单 → 右上角「...」→ 开具交易流水证明 → 邮箱发送 → 下载 CSV

### 微信
微信 → 我 → 服务 → 钱包 → 账单 → 右上角「...」→ 账单下载 → 申请账单

导入的账单自动去重（相同交易单号不重复入库）并按关键词自动归类。
