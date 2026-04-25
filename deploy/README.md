# 生产环境部署指南

本文档说明如何在服务器上使用 Docker 部署 OCR 审计文档处理系统。

## 一、服务器要求

| 要求 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 50 GB | 100 GB+ |
| 系统 | Ubuntu 20.04+ / CentOS 8+ | Ubuntu 22.04 LTS |
| Docker | 20.10+ | 24.0+ |
| Docker Compose | 2.0+ | 2.20+ |

## 二、部署架构

```
                    ┌─────────────────────────────────────────┐
                    │              Nginx (80/443)             │
                    │         反向代理 + SSL 终结             │
                    └──────────────────┬────────────────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
        ┌───────▼───────┐    ┌─────────▼─────────┐   ┌───────▼───────┐
        │   Frontend    │    │    Backend       │   │  Celery Worker│
        │   (Vue SPA)   │    │   (FastAPI)      │   │              │
        │   :3200      │    │   :8200         │   │              │
        └──────────────┘    └──────────────────┘   └──────────────┘
                                 │                      │
                ┌───────────────┼──────────────────────┘
                │               │
        ┌───────▼───────┐ ┌────▼────────┐ ┌──────────┐
        │  PostgreSQL   │ │    Redis    │ │  MinIO   │
        │    :15432    │ │    :6380   │ │ :19000   │
        └──────────────┘ └────────────┘ └──────────┘
        └──────────────┘ └────────────┘ └──────────┘
```

## 三、快速部署

```bash
# 1. 进入部署目录
cd /opt/ocr-project

# 2. 配置环境变量
cp deploy/production.env.example deploy/production.env
vim deploy/production.env  # 修改密码和密钥

# 3. 一键部署
./deploy/deploy.sh

# 4. 查看状态
./deploy/manage.sh status
```

## 四、服务管理

```bash
# 启动服务
./deploy/manage.sh start

# 停止服务
./deploy/manage.sh stop

# 重启服务
./deploy/manage.sh restart

# 查看日志
./deploy/manage.sh logs

# 查看状态
./deploy/manage.sh status

# 重新构建
./deploy/manage.sh rebuild

# 备份数据
./deploy/manage.sh backup
```

## 五、数据备份

```bash
# 执行备份
./deploy/backup.sh

# 备份会保存在 /data/ocr_project/backups/
```

## 六、故障排查

```bash
# 查看所有服务日志
docker compose -f deploy/production.yml logs -f

# 查看特定服务日志
docker compose -f deploy/production.yml logs -f backend

# 健康检查
curl http://localhost:8000/health
```

---

**注意**：部署前请务必编辑 `deploy/production.env` 配置生产环境参数！
