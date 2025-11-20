# nju_rag_system

南京大学 RAG 系统的统一代码仓库，包含：

- `NRS_backend`：FastAPI 服务，聚合爬虫、向量库、RAG 问答接口。
- `NRS_frontend`：Vue3 + Vite 前端，构建后生成 `dist/` 静态资源。
- `NRS_data` / `NRS_rag` / `NRS_vector`：历史模块，核心功能已合并进统一后端。

## 仓库结构速览

```
nju_rag_system/
├─ README.md               # 当前文档
├─ .env                    # 根级环境变量（被后端读取）
├─ NRS_backend/            # FastAPI 应用，详见子目录 README
├─ NRS_frontend/           # Vue 前端，构建产物在 dist/
├─ NRS_data, NRS_rag ...   # 历史目录（可参考实现细节）
└─ NRS_vector/             # 老的向量服务实现
```

## 阿里云 ECS 部署教程（前后端分离 + Nginx 反向代理）

以下说明假定你已经在本地完成开发，并准备将 `NRS_backend` 与 `NRS_frontend/dist` 部署到一台运行 Ubuntu 22.04 的阿里云 ECS。若你的环境不同，可按需调整命令。示例中所有命令前的注释都用 `#` 解释用途，执行时不要输入注释内容。

### 1. 部署前准备

1. **ECS 基础信息**：确认公网 IP、开放端口（至少 80/443/8000），以及可通过 SSH 登录（`ssh root@<ECS_IP>`）。
2. **域名与 DNS**（可选）：如需通过域名访问，提前在 DNS 指向 ECS 公网 IP。
3. **模型/依赖缓存**：若后端需要离线 Hugging Face 模型（例：`BAAI/bge-small-zh-v1.5`），在本地或其他机器提前下载，准备通过 `scp` 上传至 `NRS_backend/models/`。
4. **环境变量**：整理 `.env`，确认向量模型路径、LLM 配置、数据库目录等参数，并准备一份用于服务器的副本。

### 2. 本地构建与打包

```powershell
# 进入前端目录并安装依赖（仅首次）
cd NRS_frontend
npm install

# 构建生产包，输出在 NRS_frontend/dist
npm run build

# 返回仓库根目录，收集需要上传的文件
cd ..
Compress-Archive -Path NRS_frontend/dist -DestinationPath frontend_dist.zip -Force
Compress-Archive -Path NRS_backend -DestinationPath backend_src.zip -Force
```

> 若已在仓库中缓存本地模型，可将 `NRS_backend/models` 一并打包，或单独压缩后上传。

### 3. 将构建产物上传到 ECS

在本地终端执行（替换 `<ECS_IP>` 为服务器地址）：

```powershell
scp frontend_dist.zip root@<ECS_IP>:/opt/nrs
scp backend_src.zip root@<ECS_IP>:/opt/nrs
# 如有离线模型：
scp bge-small-zh-v1.5.zip root@<ECS_IP>:/opt/nrs
```

### 4. 初始化 ECS 环境

SSH 登录 ECS，执行以下命令安装必要组件：

```bash
ssh root@<ECS_IP>

# 1) 更新系统并安装依赖
apt update && apt upgrade -y
apt install -y python3.11 python3.11-venv python3-pip nginx unzip git

# 2) 创建部署目录
mkdir -p /opt/nrs/{backend,frontend,models}
cd /opt/nrs

# 3) 解压前后端资源
unzip -o backend_src.zip -d backend
unzip -o frontend_dist.zip -d frontend

# 4) 若有模型包，解压到后端 models 目录
unzip -o bge-small-zh-v1.5.zip -d backend/NRS_backend/models
```

> 如系统缺失 Python 3.11，可使用 `apt install software-properties-common` 后再添加 `ppa:deadsnakes/ppa` 获取更高版本。

### 5. 后端部署（FastAPI + Uvicorn + Systemd）

```bash
cd /opt/nrs/backend/NRS_backend

# 1) 创建专用用户（可选，增强安全性）
useradd -r -d /opt/nrs -s /usr/sbin/nologin nrs
chown -R nrs:nrs /opt/nrs

# 2) 创建虚拟环境并安装依赖
sudo -u nrs python3.11 -m venv .venv
sudo -u nrs /opt/nrs/backend/NRS_backend/.venv/bin/pip install -r requirements.txt

# 3) 配置环境变量
cp /path/to/local/.env /opt/nrs/backend/.env
chown nrs:nrs /opt/nrs/backend/.env
```

创建 systemd 服务 `/etc/systemd/system/nrs-backend.service`：

```ini
[Unit]
Description=NRS FastAPI Backend
After=network.target

[Service]
User=nrs
Group=nrs
WorkingDirectory=/opt/nrs/backend/NRS_backend
EnvironmentFile=/opt/nrs/backend/.env
ExecStart=/opt/nrs/backend/NRS_backend/.venv/bin/uvicorn NRS_backend.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
systemctl daemon-reload
systemctl enable --now nrs-backend.service
systemctl status nrs-backend.service
```

如需查看日志：`journalctl -u nrs-backend -f`。

### 6. 前端部署（Nginx 静态托管）

```bash
# 解压后的前端 dist 已放在 /opt/nrs/frontend/dist
mkdir -p /var/www/nrs_frontend
cp -r /opt/nrs/frontend/dist/* /var/www/nrs_frontend/
chown -R www-data:www-data /var/www/nrs_frontend
```

创建 `/etc/nginx/sites-available/nrs.conf`：

```nginx
server {
	listen 80;
	server_name _;  # 如有域名，替换成 example.com

	root /var/www/nrs_frontend;
	index index.html;

	# 前端 SPA：所有前端路由回退到 index.html
	location / {
		try_files $uri $uri/ /index.html;
	}

	# 反向代理到 FastAPI（默认 8000）
	location /api/ {
		proxy_pass         http://127.0.0.1:8000/api/;
		proxy_set_header   Host $host;
		proxy_set_header   X-Real-IP $remote_addr;
		proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header   X-Forwarded-Proto $scheme;
	}

	# 反向代理 vector 路由（若前端直接访问）
	location /vectors/ {
		proxy_pass http://127.0.0.1:8000/vectors/;
		proxy_set_header Host $host;
	}
}
```

启用站点并重启 Nginx：

```bash
ln -s /etc/nginx/sites-available/nrs.conf /etc/nginx/sites-enabled/
nginx -t  # 确认配置无误
systemctl reload nginx
```

> 如需 HTTPS，可在域名解析完成后安装 `certbot` 并运行 `certbot --nginx -d example.com`；完成后 Nginx 会生成 443 端口配置。

### 7. 验证部署

1. 浏览器访问 `http://<ECS_IP>`（或域名）应能打开前端页面。
2. 前端发起问题时，应命中 `http://<ECS_IP>/api/rag` 并得到响应。
3. 通过 `curl http://127.0.0.1:8000/health` 检查后端状态；`curl http://127.0.0.1:8000/docs` 可打开 Swagger 文档。
4. 若后端依赖本地模型，确认 `/opt/nrs/backend/NRS_backend/models/<model>` 下文件完整，且 `.env` 中 `VECTOR_embedding_model` 指向该路径（例如 `./NRS_backend/models/bge-small-zh-v1.5`）。

### 8. 运维建议

- **日志轮转**：可将 `journalctl` 输出管道到文件，或在 Nginx 中启用 `logrotate`，防止磁盘占满。
- **自动重启**：systemd 已配置 `Restart=on-failure`，若需定时平滑重启可使用 `systemctl restart nrs-backend` 结合 `cron`。
- **模型/数据库备份**：定期备份 `/opt/nrs/backend/chroma_db`、`crawler.db` 以及 `models/`，以便迁移或灾备。
- **安全**：关闭未使用端口、禁用 root SSH 登录、启用防火墙（`ufw allow 80`, `ufw allow 443`, `ufw allow 22`）。

按以上步骤即可在阿里云 ECS 上完成 `NRS_backend` 与 `NRS_frontend` 的生产化部署。若需要拓展到多台机器，可在 Nginx 层加上负载均衡，或将后端容器化为 Docker 镜像进一步简化上线流程。