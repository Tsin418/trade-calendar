# Agnes 日历翻译

非中文/英文的韩语与日语文本通过 Agnes `agnes-2.5-flash` 翻译为简体中文。
官方文档当前标示该模型输入、输出均免费；使用个人免费密钥，不自动切换付费模型。
参考：https://agnes-ai.com/zh-Hans/docs/agnes-25-flash

## 后端配置

在被 Git 忽略的根目录 `.env` 中设置 `CALENDAR_AGNES_API_KEY` 和
`CALENDAR_AGNES_MODEL=agnes-2.5-flash`。密钥只提供给 API/Worker，前端不接触密钥。
在设置页选择“自动翻译（Agnes 免费模型）”并保存。

Worker 每 5 分钟发现待翻译的外部来源事件标题、机构、原始时间说明、来源标题
和标题变更摘要，每 30 秒处理最多 10 条。私人备注和人工事件不发送到翻译服务。
缓存以原文内容和目标语言的 SHA-256 为键；同一原文只翻译一次，源内容改变后
生成新缓存。多个消费者可共用译文。

译文存入 `text_translations`，保留模型、状态、尝试次数和错误码。原始事件、
来源证据和审计值不被改写，API 通过 `display_*` 字段提供展示文本。
API 请求只查数据库，不等待模型。未完成的译文显示“翻译中”。

## 首次部署与补译

先备份 PostgreSQL，再构建 API、Worker、migrate、web 镜像，执行
`alembic upgrade head`。依照 `cloudflare-deployment.md` 同时重建 API 与 Tunnel，
保持其共享网络空间。完成后可执行一次批量补译：

```powershell
docker compose -f infrastructure/docker-compose.yml --env-file .env exec -T api python -m trade_calendar.translations
```

补译只处理到达重试时间的任务；每次请求后等待 4 秒。429、网络错误、无效 JSON、
未完成的回复、残留韩文/假名或数字变化会保留失败状态，并延迟重试。整批失败后
按单条重试以隔离问题文本。失败任务不会被标记为译完，错误日志不保存密钥或
供应商返回的原始错误正文。

事件列表、详情、来源和变更页面都使用展示字段；源语言的原标题保留在后端，
前端编辑时通过隐藏字段原样回传，避免误把译文或“翻译中”写回原始证据。
