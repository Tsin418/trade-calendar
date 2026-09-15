# 开发环境与验证

## 前置条件

- Docker Desktop（Compose v2）；
- Node.js 24（仅前端本地开发需要）；
- Python 3.12（仅 API 本地开发需要）。

复制 `.env.example` 为 `.env` 并至少替换数据库密码、Session Secret 和 ICS Token。开发默认值只允许用于本机。

## 一条命令启动

在仓库根目录运行：

```powershell
.\scripts\dev.ps1
```

服务启动后：Web `http://localhost:3000`，API 文档 `http://localhost:8000/docs`，API 健康检查 `http://localhost:8000/health`。PostgreSQL 仅绑定本机回环地址。

## Migration

Compose 启动时由一次性 `migrate` 服务执行 `alembic upgrade head`。本地 API 环境可使用：

```powershell
cd apps/api
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe downgrade -1
```

发布顺序固定为：备份数据库 → 构建镜像 → 执行 Migration → 启动 API/Worker/Web → 健康检查。Migration 失败时不得启动新版本应用。

## 自动化检查

```powershell
.\scripts\check.ps1
```

它依次执行 Python Lint 与测试、前端 Lint、TypeScript、组件测试和生产构建。

## 时间与数据规则

- 所有带时间事件写入 API 时必须包含 UTC offset；数据库存 UTC。
- 仅日期事件写 `local_date`，可选写入成对的 `date_range_start/date_range_end`，不得填写 `starts_at`。
- `date_precision=window` 必须同时有 `starts_at` 与 `ends_at`。
- 人工创建通过内建 `manual` 来源建立来源关系；正式事件不能成为无来源记录。
- 重复写入使用 `idempotency_key`，同一内容不会产生重复版本。

## 停机与休眠后的采集恢复

Worker 启动时及运行期间每分钟检查一次数据库中的最近采集记录。若该次运行结束后
已错过来源的 UTC cron 计划，自动排入一次 `catchup` 任务；从未运行的来源排入
`initial` 任务。多天漏跑合并为一次最新抓取，不逐次重放历史计划。

补抓和正常定时任务共用来源行锁及每分钟唯一键。已有 `pending` 或 `running` 任务时
不重复排队；一次失败结束后等到下一次正常计划再重试，避免每分钟重复请求故障来源。
API 的 `/health`、`/ready` 只说明 API 和数据库在线，来源新鲜度还需检查
`/api/v1/sources` 的最近运行、成功时间和健康状态。

台湾央行来源从新闻索引第一页顺序查找当年会议日程，最多检查 20 页，同时保留已发现的
下一年日程；不再依赖公告所在的固定页码。找不到当年日程时仍报告解析故障。
