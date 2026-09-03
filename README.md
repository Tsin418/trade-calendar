# Trade Calendar

面向单用户的动态交易事件日历。项目按 `roadmap/` 的阶段质量门逐步交付。

## 当前状态

- Phase 0：有条件通过，等待用户确认个性化配置。
- Phase 1：已完成，Docker Compose 已实际启动，Playwright 桌面/移动端 E2E 通过。
- Phase 2：已完成，人工事件 CRUD、版本、变更、字段锁和审计可用。
- Phase 3～5：进行中；页面、Adapter/同步、提醒/ICS 核心已经建立。
- 公司财报：50 家美日韩中港台 Watchlist 已建立；Finnhub、JPX、KRX KIND、TWSE
  自动来源已启用；长桥宏观与财报日历均已通过只读 OAuth 接入。
- 默认时区：`Asia/Shanghai`。
- 默认关注市场：美国、日本、韩国、台湾、香港及有限全球事件。

## 目录

```text
apps/web/       Next.js 前端
apps/api/       FastAPI API 与数据模型
apps/worker/    APScheduler Worker
config/         事件、影响规则、数据源与提醒配置
adapters/       外部来源适配器
infrastructure/ Docker Compose、Caddy 与运维脚本
docs/           产品、数据、API 与开发文档
tests/          跨服务集成与 E2E 测试
roadmap/        分阶段计划和完成记录
```

环境、启动和测试方式见 `docs/development.md`（Phase 1 完成时提供）。

当前本地容器入口：Web `http://localhost:3000`，API 文档 `http://localhost:8000/docs`。

Cloudflare 受保护预览：`https://trade-calendar.chenandrew418.workers.dev`。云端前端已监听 GitHub `main`，本地 API 尚未通过 Tunnel 接入，详见 `docs/cloudflare-deployment.md`。
