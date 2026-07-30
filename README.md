# HomeHub

HomeHub 是一个面向家庭 Linux 服务器的轻量、只读、安全仪表盘。前端基于 [pure-admin-thin](https://github.com/pure-admin/pure-admin-thin)，后端使用 FastAPI；宿主机状态由独立 systemd 采集器写入有限的 JSON 快照，Web 容器没有 Docker Socket、root 权限或系统控制能力。

## v1 功能

- CPU、内存、磁盘、负载、温度和运行时间；
- SSH、NetworkManager、Docker、containerd、Mihomo、订阅定时器状态；
- Mihomo 本地 API 版本检查；
- HomeHub 部署版本和 Commit；
- 家庭应用与开发资源快捷入口；
- 快照延迟和过期提示；
- Mac、iPad、手机响应式页面和暗色模式；
- `/api/health`、`/api/ready`、`/api/version`、`/api/dashboard`；
- GitHub Actions CI 和 GHCR 镜像发布。

## 安全边界

- v1 没有写操作和应用登录，只允许家庭局域网访问；
- 容器以 UID 10001 运行，根文件系统只读，移除全部 capabilities；
- 不挂载 `/var/run/docker.sock`；
- 浏览器请求不会触发 shell 或 systemd 命令；
- 采集器不读取密码、Token、订阅 URL、环境变量或日志正文；
- 加入控制功能之前，必须先实现认证、授权和审计。

## 架构

```text
systemd timer -> collector -> /var/lib/homehub/status.json
                                      |
                                      | read-only
                                      v
browser -> HomeHub container (Vue static + FastAPI)
```

## 本地测试

后端：

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
ruff check . ../collector
pytest --cov=app
```

前端：

```bash
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm typecheck
pnpm lint:check
pnpm build
```

运行开发 API 时，可设置状态和配置路径：

```bash
HOMEHUB_STATUS_FILE=/tmp/status.json \
HOMEHUB_CONFIG_FILE=../deploy/config/homehub.yaml \
uvicorn app.main:app --reload
```

## 服务器安装规划

1. 安装采集器到 `/usr/local/lib/homehub/homehub_collector.py`；
2. 安装并启用 `homehub-collector.service/.timer`；
3. 将 `deploy/` 放到 `/srv/apps/homehub/`；
4. 使用精确 GHCR SHA 镜像启动 Compose；
5. UFW 只允许 `192.168.0.0/24` 通过 `wlp8s0b1` 访问 TCP 8088；
6. 验证容器健康、快照新鲜度和服务器重启恢复。

当前仓库先完成、测试并发布软件；服务器正式部署在 GHCR 镜像产生后执行。

## License

HomeHub 使用 MIT License。前端基础项目的归属信息见 [NOTICE](NOTICE) 和 [frontend/LICENSE](frontend/LICENSE)。
