# 美股投研

纯美股研究 Web 应用：自选行情、K 线、价格回撤、多源资讯与 DeepSeek 四维分析。行情来自本机 **FutuOpenD**（`futu-api`），**不做下单**，**不覆盖港股**。

未启动 OpenD 时，后端健康检查失败，前端顶部横幅提示「请启动 FutuOpenD」，**不会用假数据填充行情**。资讯仍会尝试 Yahoo Finance、Google 新闻、新浪财经等公开源。

## 你需要提前准备

1. 安装并登录 [FutuOpenD](https://www.futunn.com/download/OpenAPI)，默认监听 `127.0.0.1:11111`
2. 富途账号具备 **美股行情权限**（无权限时页面会展示接口返回的错误原文）
3. DeepSeek API Key（写入根目录 `.env`，不要提交到 git）
4. Python 3.11+、Node.js 18+

## 启动（两个进程，不用 Docker）

```powershell
# 1) 环境变量
copy .env.example .env
# 编辑 .env，至少填写 DEEPSEEK_API_KEY（仅生成报告时需要）

# 2) 后端
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3) 前端（另开终端）
cd frontend
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`。前端把 `/api` 代理到 `http://127.0.0.1:8000`。

## 环境变量

见 `.env.example`：

| 变量 | 说明 |
| --- | --- |
| `FUTU_HOST` | OpenD 地址，默认 `127.0.0.1` |
| `FUTU_PORT` | OpenD 端口，默认 `11111` |
| `DEEPSEEK_API_KEY` | DeepSeek 密钥，不入库 |
| `DEEPSEEK_BASE_URL` | 默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 默认 `deepseek-chat` |

## 页面

- **总览**：美股交易时段（纽约时间）、自选快照（含盘前/盘后）、领涨领跌与热议
- **自选**：本地 SQLite 保存；搜索加入美股代码，如 `AAPL` / `US.NVDA`
- **个股**：快照、K 线（5m/15m/60m/日/周）、回撤水下图、多源资讯、板块/资金流向/简介（可选失败）、四维分析与 AI 解读
- **设置**：OpenD host/port、美股时段、DeepSeek 是否已配置

默认自选：`US.AAPL` `US.NVDA` `US.MSFT` `US.AMZN` `US.GOOGL` `US.META` `US.TSLA` `US.SPY` `US.QQQ`

## 实现要点

- 只接受美股代码；港股、A 股等会返回 400
- OpenD 调用串行加锁，历史 K 线分页 `max_count=1000`，前复权
- SQLite 缓存 K 线、资讯、AI 报告（同标的报告 6 小时复用）
- 资讯并行聚合 Yahoo Finance、Google 新闻、新浪财经与富途，去重后展示来源
- 资金流向 / 公司简介 / 榜单：失败只隐藏对应块，不打断页面

## 目录

```
backend/app/          FastAPI、Futu 客户端、回撤/报告/资讯服务
frontend/src/         Vite + React + TypeScript + lightweight-charts
```
