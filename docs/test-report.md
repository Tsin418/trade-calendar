# 自动化与联调记录

日期：2026-09-02

## 自动化检查

| 范围 | 命令 | 结果 |
|---|---|---|
| Python Lint | `ruff check --no-cache trade_calendar tests ../worker` | 通过 |
| Python 类型 | `mypy trade_calendar ../worker` | 通过，34 个源码文件无错误 |
| Python 测试 | `pytest -q` | 27 个测试通过 |
| 前端 Lint | `npm run lint` | 通过 |
| 前端类型 | `npm run typecheck` | 通过 |
| 前端组件 | `npm run test` | 2 个测试通过 |
| 前端 E2E | `npm run test:e2e` | 桌面 Chrome + Pixel 7，共 6 个场景通过 |
| 前端生产构建 | `npm run build` | 9 个静态路由构建通过 |
| Migration | Alembic upgrade → downgrade -1 → upgrade | SQLite 三轮通过；PostgreSQL 已升级到 `246ffc20abda` |
| Compose | build + up + health checks | Web/API/DB/Worker 全部启动，API/DB healthy |

## 核心场景证据

- 仅日期事件生成 `local_date`；可选日期范围在 API 中保留，并在 ICS 中生成跨日全天范围，不伪造午夜时间；
- TBA 补充具体时间产生 `time_confirmed` 变更；
- 改期保留旧版本，ICS UID 不变、`SEQUENCE` 增加；
- 相同人工写入、相同 Adapter Fixture 重跑不增加事件或版本；
- 周期性同标题但不同日期的 FOMC 会议保持为独立事件；
- 人工字段锁阻止来源覆盖，未锁字段仍可同步；
- 单次空结果与 HTML 结构变化形成失败运行，不删除历史事件；
- Critical 生成 120/60/15 分钟提醒，TBA/日期事件不生成分钟提醒；
- ICS Token 轮换后旧地址失效；
- 日志脱敏，API 容器关闭 access log，避免私有 ICS Token 出现在访问日志。

## 真实来源联调

- Federal Reserve 官方 FOMC HTML：HTTP 200，解析 57 条；当前 57 个事件、57 个版本、57 个来源链接；重复运行新增 0、更新 0；
- U.S. BLS 官方 ICS/HTML：容器请求均为 HTTP 403；先由 TradingView 降级恢复，现已
  切换到 Longbridge 宏观日历 Adapter 3.0.0；容器 OAuth 仅保留基础市场数据权限，
  真实同步解析 14 条，连续失败归零；CPI、PPI、就业报告、JOLTS、实际工资及生产率
  初值/修正值分别建模，重复运行新增 0、更新 0；
- 第三次唯一约束 Migration 已获授权并应用；精确清理 1 条重复链接，迁移后重复组和重复链接均为 0。

## 尚未执行

- Playwright E2E；
- 5,000 条 Month 性能测试；
- 飞书真实 Webhook 发送与重试；
- Google/Apple/Outlook ICS 兼容性检查；
- 生产登录、安全扫描、备份恢复和 30 天稳定性观察。

## 2026-09-03 公司财报来源增量

- Python Ruff：通过；Mypy：45 个源码文件无错误；Pytest：52 项通过。
- 前端 ESLint、TypeScript、Vitest（15 项）、Playwright 桌面/移动端（10 项）及
  Next.js 生产构建通过。
- Watchlist：US 10、JP/KR/CN/HK/TW 各 8，共 50 家。
- Finnhub：逐公司真实同步解析 55 条并成功创建 52 条；未来至 2027-01-01 共 37 条。
- JPX：官方 XLSX 真实同步解析 7 条 Watchlist 财报记录。
- KRX KIND / TWSE：当前窗口无目标公司季度说明会，按允许空窗口成功记录健康运行。
- 来源优先级：官方确认来源可接管第三方预计事件；后续低优先级重跑不会覆盖官方日期和状态。

## 2026-09-03 BLS 日程降级与长桥接入

- Python Pytest：52 项通过；Ruff 全量检查通过。
- 真实同步：解析 15 条；修复历史错误关联后新增 3 条，随后重跑新增 0、更新 0。
- 数据质量：同一发布下的多个指标行会合并；不同发布族即使机构、类别和参考期相同也不会误合并。
- Longbridge CLI：主机与 Worker 容器均安装 0.28.4；Linux 包使用固定版本及 SHA-256 校验。
- OAuth：Worker 使用独立 `longbridge_auth` Docker 卷，仅授权 General / Basic data access；
  Watchlist、账户与持仓、订单查询和交易执行均未授权。
- 当前状态：`Longbridge U.S. BLS Macro Calendar` 健康，连续失败 0；解析 14 条，首次迁移
  新增 2、更新 1，重复运行新增 0、更新 0，未来窗口 8 条且重复组为 0。

## 2026-09-03 全来源恢复与跨来源去重

- Python Pytest：58 项通过；Ruff 全量检查通过；Mypy 46 个源码文件无错误。
- 前端 Vitest：15 项通过；ESLint、TypeScript 与 Next.js 生产构建通过。
- 真实来源：16 个外部来源全部启用、均已注册 Adapter，真实同步后 16/16 健康。
- 韩国国家数据处全年发布计划首次同步解析 260 条；香港 C&SD 日程解析 117 条；
  长桥 Watchlist 财报解析 33 条。
- 长桥财报与 Finnhub/交易所来源按股票代码、事件类型和兼容财报期合并；本轮仅新增
  1 个标准事件、更新 8 个既有事件，其余作为来源证据关联。
- 数据库验收：754 个有效标准事件、905 条来源关系、21 个多来源事件；按“标准标题＋日期”
  和“股票代码＋事件类型＋财报期”检查，重复组均为 0。
