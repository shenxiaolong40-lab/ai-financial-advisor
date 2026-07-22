# AI 财务自由顾问

> 核心问题：**我还需要多久才能财务自由？**

基于 FIRE 法则（Financial Independence, Retire Early）的个人财务自由规划工具。输入你的资产、收入、支出，AI 顾问实时告诉你距离财务自由还有多远，并给出针对性建议。

## 功能

- **FIRE 仪表盘** — 财务自由数字、资产达成进度、预计年数、30年资产预测曲线
- **收支数据流** — 导入支付宝/微信 CSV 后，近3月真实交易记录年化为收入/支出，参与 FIRE 计算（手动配置作为降级数据源）
- **AI 顾问** — 基于你真实 FIRE 状态的对话式建议（DeepSeek），一键生成分析报告
- **资产配置** — 当前总资产 + 年化理财收益率，复利递推预测

## FIRE 计算原理

**财务自由定义**：被动收入（资产 × 年化收益率）≥ 年度总支出

```
逐年资产递推：
  A(n) = A(n-1) × (1+r) + S×(1+g_s)^n - E×(1+i)^n

  A₀  当前总资产        r   年化理财收益率
  S   税后年工资        g_s 年工资增长率
  E   年总支出          i   通胀率（内置 2.5%）

达标条件：
  A(n) × r ≥ E × (1+i)^n   （被动收入覆盖当年通胀后支出）
```

工资是资产积累的引擎，不是被动收入。模型内置 2.5% 通胀，支出每年自然增长，确保财务自由的真实购买力。

## 快速启动

```bash
git clone https://github.com/shenxiaolong40-lab/ai-financial-advisor.git
cd ai-financial-advisor

pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

python -m uvicorn backend.main:app --reload
# 访问 http://localhost:8000
```

## Docker 部署

```bash
# 单用户（推荐个人使用）
DEEPSEEK_API_KEY=sk-xxx docker compose up -d

# 多用户
USER_MODE=multi DEEPSEEK_API_KEY=sk-xxx SECRET_KEY=your-random-secret docker compose up -d
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 空（AI功能不可用） |
| `USER_MODE` | `single` 单用户 / `multi` 多用户 | `single` |
| `SECRET_KEY` | JWT 签名密钥（多用户必填） | 内置弱密钥 |
| `DATABASE_URL` | 数据库连接 | `sqlite:///./finance.db` |

## 账单导入（后端 API）

后端保留 `/api/import/{alipay|wechat}` 接口，可解析支付宝/微信 CSV 账单并去重入库 `Transaction` 表。**导入后交易记录会自动年化进入 FIRE 计算**（近3月月均×12，优先于手动配置）。

数据优先级：**交易记录 > 手动配置**。若导入的交易记录存在，FIRE 仪表盘用真实交易数据算；若未导入，则用 FIRE 配置模态框中手动填写的年工资/年支出。前端无收支列表页（可通过 API 或数据库直接查看）。

前端"自由说明"页会展示当前数据来源徽章（`来自近3月交易记录` / `来自手动配置`）。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + SQLAlchemy 2.0 + SQLite |
| 前端 | 纯 HTML/CSS/JS + Chart.js（零框架） |
| AI | DeepSeek API（OpenAI 兼容） |
| 认证 | JWT（多用户模式） |
| 部署 | Docker + docker-compose / PWA |
