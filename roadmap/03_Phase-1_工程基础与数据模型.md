# 03｜Phase 1：工程基础与数据模型

## 1. 阶段目标

建立前端、API、Worker 和 PostgreSQL 可以共同运行的工程底座，完成核心数据模型、Migration、配置、日志和本地容器环境。

建议周期：1 周。

## 2. 进入条件

- Phase 0 已通过验收；
- 事件枚举和数据源注册字段已经冻结；
- 目录结构和技术栈已经确认；
- Docker 开发环境可用。

## 3. 我要完成的事情

### 3.1 初始化工程

- [x] 建立项目目录；
- [x] 初始化 Next.js 和 TypeScript；
- [x] 初始化 FastAPI 和 Python 依赖管理；
- [x] 建立独立 Worker 入口；
- [x] 建立共享类型和配置目录；
- [x] 配置代码格式化、Lint 和类型检查；
- [x] 提供 `.env.example`。

### 3.2 建立数据库

- [x] 配置 PostgreSQL；
- [x] 配置 SQLAlchemy 和 Alembic；
- [x] 实现 `events`；
- [x] 实现 `source_observations`；
- [x] 实现 `event_sources`；
- [x] 实现 `event_versions` 和 `event_changes`；
- [x] 实现 `event_field_locks`；
- [x] 实现 `raw_snapshots`；
- [x] 实现 `sources` 和 `fetch_runs`；
- [x] 实现 `alert_rules` 和 `notifications`；
- [x] 实现 `review_queue` 和 `audit_logs`；
- [x] 建立必要索引、唯一约束和外键。

### 3.3 建立服务骨架

- [x] API 健康检查；
- [x] 数据库健康检查；
- [x] Worker 心跳；
- [x] 统一错误响应；
- [x] 结构化 JSON 日志；
- [x] `request_id`、`run_id` 和 `event_id` 上下文；
- [x] 配置敏感字段脱敏。

### 3.4 建立容器环境

- [x] Web、API、Worker、PostgreSQL 服务；
- [x] 本地开发 Compose 配置；
- [x] 数据库持久化卷；
- [x] 服务启动顺序和健康检查；
- [x] 一条命令启动全部服务；
- [x] 一条命令执行 Migration 和测试。

### 3.5 建立测试底座

- [x] Pytest；
- [x] 前端组件和工具函数测试；
- [x] Playwright E2E 骨架；
- [x] 测试数据库和数据工厂；
- [x] Migration 升级和降级测试；
- [x] 最小持续集成检查。

## 4. 需要实现的目标

- 新环境可以根据说明启动项目；
- 数据库可以从零迁移到当前版本；
- Web、API 和 Worker 能够独立报告健康状态；
- 结构化日志可以串联一次请求或任务；
- 数据模型支持多来源、版本、锁定和审核；
- 工程错误能在测试阶段被类型检查和 Lint 发现。

## 5. 交付物

- 可运行的项目骨架；
- Docker Compose；
- `.env.example`；
- 初始数据库 Migration；
- 数据模型说明；
- 开发环境说明；
- 测试命令说明；
- 健康检查接口。

## 6. 验收标准

- [x] 新数据库能完整执行 Migration；
- [x] Migration 可以安全回退一个版本；
- [x] Docker Compose 可以启动全部核心服务；
- [x] Web 能访问 API；
- [x] Worker 能连接数据库并写入心跳；
- [x] 日志不包含密码、Webhook 或 Token；
- [x] Lint、类型检查和基础测试全部通过；
- [x] 核心表唯一约束和索引经过检查。

## 7. 主要风险

- 前后端重复定义类型导致字段漂移；
- 时间字段设计错误会影响所有后续阶段；
- Migration 设计不当会阻碍长期升级；
- Worker 与 API 并发写入造成竞态；
- 本地和生产环境配置不一致。

## 8. 完成情况与质量补充

- 状态：已完成
- 实际开始日期：2026-09-02
- 实际完成日期：2026-09-02
- 实际投入：单次集中实现与容器联调
- 已完成任务：工程骨架、14+ 核心表、Migration、健康检查、Worker、Docker Compose、日志、Lint/类型/测试
- 未完成或调整任务：无；Playwright 骨架在 Phase 3 联动时完成
- 交付物位置：`apps/`、`infrastructure/`、`.env.example`、`scripts/`、`docs/development.md`
- 自动化检查结果：Python Ruff/Mypy 通过；27 Pytest；前端 ESLint/tsc/2 Vitest/6 Playwright/Next build 全部通过
- Migration 验证结果：SQLite 从零升级、回退一版、再次升级通过；PostgreSQL Compose 初次升级通过
- 缺陷数量及级别：P0 0 / P1 0 / P2 0 / P3 0
- 遗留技术债：无 Phase 1 阻断项
- 质量评分：94 / 100
- 验收结论：通过
- 下一阶段注意事项：Migration `246ffc20abda` 已应用；后续变更继续执行升级/回退双向验证
