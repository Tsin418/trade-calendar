# MVP REST API 草案

所有 `/api/v1` 写接口需要会话认证、CSRF Token、限流和 `Idempotency-Key`。错误统一返回 `request_id`、机器可读 `code` 和中文 `message`。

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | API 进程健康 |
| GET | `/ready` | 数据库与依赖就绪 |
| GET/POST | `/api/v1/events` | 查询或人工创建事件 |
| GET/PATCH/DELETE | `/api/v1/events/{id}` | 详情、更新、软删除 |
| GET | `/api/v1/events/{id}/versions` | 版本历史 |
| GET/PUT/DELETE | `/api/v1/events/{id}/locks/{field}` | 字段锁 |
| GET | `/api/v1/changes` | 变更 Feed |
| GET | `/api/v1/sources` | 来源及健康状态 |
| GET | `/api/v1/sources/{id}/runs` | 抓取运行历史 |
| POST | `/api/v1/sources/{id}/sync` | 创建单来源同步任务 |
| POST | `/api/v1/sync` | 创建全量同步任务 |
| GET | `/api/v1/jobs/{id}` | 任务状态 |
| GET/PATCH | `/api/v1/settings` | 用户设置 |
| GET/POST/PATCH/DELETE | `/api/v1/alert-rules` | 提醒规则 |
| POST | `/api/v1/notifications/test` | 测试提醒 |
| GET/POST | `/api/v1/review-queue` | 审核列表/批量操作 |
| GET | `/api/v1/system/status` | 系统状态 |
| GET | `/calendar/{token}.ics` | 私有 ICS Feed |
| POST | `/api/v1/ics-token/rotate` | 轮换订阅 Token |
| POST/DELETE | `/api/v1/session` | 登录/退出 |

列表接口支持 `from`、`to`、`country`、`market`、`category`、`importance`、`status`、`q`、`cursor` 和稳定的 `sort`。

