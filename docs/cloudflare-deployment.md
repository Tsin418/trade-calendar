# Cloudflare Workers 部署记录

日期：2026-09-02

## 已完成

- GitHub 私有仓库：`https://github.com/Tsin418/trade-calendar`；
- Cloudflare Worker：`trade-calendar`；
- 正式地址：`https://trade-calendar.chenandrew418.workers.dev`；
- Git 集成：监听 `main`，新提交自动构建部署；
- 构建命令：`cd apps/web && npm ci && npm run cf:build`；OpenNext 配置使用非自动探测文件 `open-next.cloudflare.config.ts`；
- 部署命令：`cd apps/web && npx wrangler deploy`；
- 运行时：OpenNext Cloudflare Adapter 1.20.5、Next.js 16；
- Access：Production 与 Preview 全流量保护；
- Access 策略：仅当前 Cloudflare 账户成员允许，Session 24 小时；
- Observability：Worker Logs 已启用。

`CALENDAR_API` 的 Wrangler 配置显式使用 `"remote": false`，实际发布时仍由 `service_id` 绑定到生产 Worker。OpenNext 1.20.5 的部署封装会在发布前调用 Wrangler 平台代理；VPC binding 会令该代理尝试连接受 Access 保护的远程 Worker，非交互 CI 因缺少 Access Service Token 而失败。本项目未使用 OpenNext R2 缓存填充或 skew mapping，因此构建完成后由原始 `wrangler deploy` 直接发布 `.open-next/worker.js`，避免不必要的平台代理连接。

## 当前架构边界

Cloudflare Worker 只部署 Next.js Web。FastAPI、PostgreSQL 和 APScheduler Worker 仍在本机 Docker Compose 中运行；Worker 通过 `CALENDAR_API` VPC Service binding 访问 Tunnel 后方的 FastAPI。

所有页面都以真实 API 为唯一事实来源。VPC Service、Tunnel 或 FastAPI 不可用时，页面会明确显示连接失败，不再回退到静态演示事件，也不会宣称来源健康。`INTERNAL_API_URL` 仅作为没有 VPC binding 时的受保护 HTTPS 回退；配置成 Web Worker 自身地址会被拒绝，避免代理递归。不得把本机 PostgreSQL 端口直接暴露到公网。

生产可用性仍依赖本机 Tunnel、API、Worker 和数据库持续在线；长期方案是把后端迁移到高可用服务器。日常本地开发使用 `http://localhost:3000`，Next.js 开发环境会跳过远程 VPC binding 并代理到本地 `INTERNAL_API_URL`。

## 安全注意

- GitHub 仓库保持 Private；
- `.env`、数据库、备份、Token、Webhook 和本地缓存均被 Git 忽略；
- Cloudflare Access 不应关闭；
- Cloudflare 构建变量不得写入仓库；
- 飞书 Webhook 当前未配置。
