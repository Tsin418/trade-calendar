# Cloudflare Workers 部署记录

日期：2026-09-02

## 已完成

- GitHub 私有仓库：`https://github.com/Tsin418/trade-calendar`；
- Cloudflare Worker：`trade-calendar`；
- 正式地址：`https://trade-calendar.chenandrew418.workers.dev`；
- Git 集成：监听 `main`，新提交自动构建部署；
- 构建命令：`cd apps/web && npm ci && npm run cf:build`；
- 部署命令：`cd apps/web && npx wrangler deploy`；
- 运行时：OpenNext Cloudflare Adapter 1.20.5、Next.js 16；
- Access：Production 与 Preview 全流量保护；
- Access 策略：仅当前 Cloudflare 账户成员允许，Session 24 小时；
- Observability：Worker Logs 已启用。

## 当前架构边界

Cloudflare Worker 只部署 Next.js Web。FastAPI、PostgreSQL 和 APScheduler Worker 仍在本机 Docker Compose 中运行。

云端 Next.js 的 `/api/*` 代理尚未设置可访问的 `INTERNAL_API_URL`，因此 Dashboard 静态内容可用，但依赖真实 API 的 Today、Tomorrow、Week、Month 和编辑功能会显示数据连接错误。不得把本机 PostgreSQL 端口直接暴露到公网。

下一步应建立受保护的 Cloudflare Tunnel 到本机 Web/API 入口，或迁移后端到长期在线服务器，然后将 Cloudflare Worker 的 `INTERNAL_API_URL` 设置为该 HTTPS 地址。Tunnel 完成前，日常使用仍以 `http://localhost:3000` 为准。

## 安全注意

- GitHub 仓库保持 Private；
- `.env`、数据库、备份、Token、Webhook 和本地缓存均被 Git 忽略；
- Cloudflare Access 不应关闭；
- Cloudflare 构建变量不得写入仓库；
- 飞书 Webhook 当前未配置。

