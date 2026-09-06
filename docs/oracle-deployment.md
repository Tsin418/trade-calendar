# Oracle Cloud Always Free 部署

本方案保留 Cloudflare Worker 前端，将 FastAPI、PostgreSQL 和定时 Worker 迁移到
Oracle Cloud Ampere A1。`cloudflared` 安装为 OCI 主机服务，API 只监听主机回环地址。

## 需要用户亲自完成的操作

- Oracle 注册中的信用卡、账单地址、CAPTCHA 和 MFA；
- 保存 OCI SSH 私钥；
- 在 GitHub 添加服务器的只读 Deploy Key；
- 在 Cloudflare 控制台确认 Tunnel 和 VPC Service；
- 长桥 OAuth 登录授权。

不要把信用卡、密码、MFA、Tunnel Token、OAuth Token 或 `.env` 内容发送到聊天。

## 1. 创建免费 OCI 实例

创建 `VM.Standard.A1.Flex` 实例，使用 Ubuntu ARM64、2 OCPU、4 GB 内存和约 50 GB
启动盘。创建前确认控制台显示 `Always Free eligible`。Home Region 一旦选定不能更改，
Always Free Compute 必须创建在 Home Region。

实例使用公共子网和临时公网 IP 便于 SSH，但安全列表只允许用户当前公网 IP 访问
TCP 22。不要开放 3000、5432 或 8000，也不要创建负载均衡器或 NAT Gateway。

## 2. 安装基础软件

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git curl
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu
```

退出 SSH 并重新登录，然后确认 `docker version` 和 `docker compose version` 可用。

## 3. 拉取私有仓库

在服务器生成专用 SSH 密钥，将公钥添加为 GitHub 仓库的只读 Deploy Key。然后：

```bash
git clone git@github.com:Tsin418/trade-calendar.git
cd trade-calendar
cp infrastructure/oci.env.example .env
chmod 600 .env
```

编辑 `.env`，替换所有 `replace-with-...` 值，并填写所需的可选服务密钥。可使用
`openssl rand -hex 32` 为数据库、Session 和 ICS 生成不同的随机值。

## 4. 首次部署

```bash
chmod +x scripts/deploy-oci.sh
./scripts/deploy-oci.sh
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

部署脚本在已有数据库运行时会先把自定义格式的 PostgreSQL 备份写入 `backups/`，
再构建镜像、执行 Alembic migration、启动 API 和 Worker，并检查 readiness。

## 5. 安装 Cloudflare Tunnel

在 Cloudflare Workers VPC 的 Tunnels 页面选择现有 Tunnel 或创建生产 Tunnel，按
Linux ARM64 指令在 OCI 主机安装 `cloudflared`。VPC Service 使用：

- 类型：HTTP；
- Host：`localhost`；
- HTTP port：`8000`；
- Tunnel：OCI 主机上正在运行的 Tunnel。

Workers VPC 要求 Tunnel 使用 `auto` 或 `quic`，OCI 出站防火墙必须允许 UDP 7844。
如果新建了 VPC Service，将新 `service_id` 写入 `apps/web/wrangler.jsonc` 的
`CALENDAR_API` binding 后重新部署前端；复用原 Service ID 时不需要修改前端。

验证：

```bash
sudo systemctl status cloudflared --no-pager
docker compose -f infrastructure/docker-compose.yml ps
docker compose -f infrastructure/docker-compose.yml logs --tail=100 api worker
```

最后在受 Cloudflare Access 保护的生产网址访问 `/api/v1/events?limit=1`，确认返回
JSON 且日历不再显示 503。

## 6. 长桥授权与数据迁移

Worker 的长桥 Token 位于 Docker volume `longbridge_auth`。在 OCI 上通过带该 volume
的临时容器执行 `longbridge auth login`，将输出的授权地址复制到自己的浏览器完成
OAuth。授权后执行 `longbridge check`。

现有本地事件需要保留时，应先从本地 PostgreSQL 导出自定义格式备份，再安全传到
OCI，并在首次启动 Worker 前恢复。不要通过聊天传送数据库备份或 Token。

## 7. 更新与恢复

正常更新：

```bash
cd ~/trade-calendar
git pull --ff-only
./scripts/deploy-oci.sh
```

Oracle 可能回收长期低利用率的 Always Free 实例。至少保留异机数据库备份，并记录
实例、Tunnel、VPC Service 和环境变量的恢复步骤。
