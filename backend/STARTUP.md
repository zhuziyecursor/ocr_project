# 后端开发启动文档

本文档说明如何使用 docker-compose 启动后端服务进行本地开发。

---

## 一、环境要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Docker | 24.0+ | |
| Docker Compose | 2.0+ | |
| Python | 3.11+ | 仅本地运行测试用 |
| Node.js | 18+ | 仅前端开发用 |

---

## 二、服务架构

```
┌─────────────────────────────────────────────────────────┐
│                    开发环境                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │ postgres │    │  redis   │    │  minio    │         │
│  │   5432   │    │   6379   │    │ 9000/9001│         │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘         │
│       │               │               │                │
│       └───────────────┼───────────────┘                │
│                       │                                 │
│               ┌───────▼───────┐                        │
│               │  backend      │  :8000                 │
│               │  (uvicorn)    │                        │
│               └───────┬───────┘                        │
│                       │                                 │
│               ┌───────▼───────┐                        │
│               │ celery_worker │                        │
│               │               │                        │
│               └───────────────┘                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 三、启动步骤

### 3.1 启动基础设施和后端服务

```bash
# 在项目根目录执行
docker compose up -d postgres redis minio backend celery_worker
```

**启动顺序说明：**
1. `postgres` → `redis` → `minio` 是基础设施，先启动
2. `backend` 依赖基础设施，必须等健康检查通过后才启动
3. `celery_worker` 依赖 `backend` 启动后再启动

### 3.2 验证服务状态

```bash
# 查看所有服务状态
docker compose ps

# 预期输出
NAME                IMAGE               COMMAND                  SERVICE             CREATED             STATUS              PORTS
ocr_postgres        postgres:15-alpine  "docker-entrypoint.s…"   postgres            5 seconds ago       Up 4 seconds        0.0.0.0:5432->5432/tcp
ocr_redis           redis:7-alpine      "docker-entrypoint.s…"   redis               5 seconds ago       Up 4 seconds        0.0.0.0:6379->6379/tcp
ocr_minio           minio/minio:latest  "minio server /data…"    minio               5 seconds ago       Up 3 seconds        0.0.0.0:9000->9000/tcp, 0.0.0.0:9001->9001/tcp
ocr_backend         ocr-backend         "uvicorn main:app --…"    backend             3 seconds ago       Up 2 seconds        0.0.0.0:8000->8000/tcp
ocr_celery          ocr-backend         "celery -A tasks.doc…"    celery_worker       2 seconds ago       Up 1 seconds
```

### 3.3 验证服务是否正常

```bash
# 1. 验证后端 API
curl http://localhost:8000/health
# 预期返回：{"status":"healthy"}

# 2. 验证 Redis
docker compose exec redis redis-cli ping
# 预期返回：PONG

# 3. 验证 Postgres
docker compose exec postgres pg_isready -U postgres
# 预期返回：accepting connections
```

---

## 四、查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f celery_worker

# 查看最近 100 行日志
docker compose logs --tail=100 backend
```

---

## 五、关闭服务

```bash
# 停止所有服务（保留数据卷）
docker compose stop

# 停止并删除容器（保留数据卷）
docker compose down

# 停止并删除容器和数据卷（清空所有数据）
docker compose down -v
```

---

## 六、常见问题

### 6.1 后端启动失败：could not connect to server

**原因**：postgres 或 redis 还未就绪时 backend 就启动了

**解决**：
```bash
# 等待基础设施就绪后重启 backend
docker compose up -d --wait backend
```

### 6.2 Celery Worker 启动失败：could not connect to redis

**原因**：同 6.1，Redis 未就绪

**解决**：
```bash
docker compose up -d --wait celery_worker
```

### 6.3 数据库连接被拒绝

**检查**：
```bash
docker compose exec postgres pg_isready -U postgres
```

### 6.4 修改代码后服务没有更新

**说明**：当前配置是挂载源码的，但如果使用 reload 模式，需要等待 uvicorn 自动重载。

**强制重启**：
```bash
docker compose restart backend
```

---

## 七、开发调试

### 7.1 进入后端容器

```bash
docker compose exec backend bash
```

### 7.2 进入 Celery Worker 容器

```bash
docker compose exec celery_worker bash
```

### 7.3 查看 Celery 任务队列

```bash
# 在容器内执行
celery -A tasks.document_tasks inspect active
```

---

## 八、前端开发

前端开发需要单独启动（热更新需求）：

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器通过 vite.config.js 中的 proxy 访问后端 API：
- 前端：http://localhost:3000
- 后端 API：http://localhost:3000/api → 代理到 http://localhost:8000/api

---

## 九、快速命令汇总

```bash
# 启动全部服务
docker compose up -d postgres redis minio backend celery_worker

# 检查状态
docker compose ps

# 验证后端
curl http://localhost:8000/health

# 查看日志
docker compose logs -f backend

# 重启后端（代码更新后）
docker compose restart backend

# 关闭全部服务
docker compose stop

# 完全清理（删除容器和数据）
docker compose down -v
```

---

## 十、重要提醒

1. **每次修改 docker-compose.yml 后**，确认是否需要同步更新本文档
2. **如果修改了环境变量**（.env），需要重新创建容器：docker compose up -d
3. **Celery Worker 必须与后端一起启动**，否则异步任务会失败
4. **数据持久化**：postgres 和 redis 的数据存储在 docker volume 中，删除容器不会丢失数据

---

## 十一、已知问题与解决方案（2026-04-15 更新）

### 问题1：删除文档接口报错 500

**原因**：删除 Document 记录时未先删除关联的 RecognitionResult 记录，违反外键约束

**解决方案**：已在 `document_service.py` 中修复，删除前会先清理关联记录

### 问题2：跨文件比对接口不可用

**原因**：`compare_documents` 函数缺少 `@router.post` 装饰器，未注册到路由

**解决方案**：已在 `documents.py` 中添加装饰器

### 问题3：文件存储方式

**当前状态**：使用本地存储（`/tmp/ocr_project`），MinIO 配置已预留但未启用

**说明**：MVP 阶段使用本地存储简化部署，MinIO 扩展点已预留，后续需要时可快速切换

### 问题4：数据库初始化

**当前状态**：后端启动时自动创建所有表（通过 FastAPI lifespan 事件）

**说明**：无需手动执行迁移，首次启动时自动创建 `documents`、`recognition_results`、`review_records`、`users` 表

### 问题5：OpenDataLoader 依赖

**当前状态**：已在 `requirements.txt` 中添加本地路径安装

**说明**：容器构建时会自动安装 `opendataloader-pdf` 包

---

## 十二、本次 Session 修复记录（2026-04-15）

### 12.1 后端修复

| # | 问题 | 修复方式 | 涉及文件 |
|---|------|---------|---------|
| 1 | ModuleNotFoundError: No module named 'backend' | 批量替换 `from backend.` 导入为直接模块路径（core/api/models/services/tasks） | 13 个文件 |
| 2 | 删除接口 500 错误 | document_service.py 的 delete_document 先删 RecognitionResult 再删 Document | document_service.py |
| 3 | passlib+bcrypt 5.0.0 兼容性问题 | auth_service.py 的 CryptContext 从 `bcrypt` 改为 `sha256_crypt` | auth_service.py |
| 4 | compare_documents API 未注册 | 添加 `@router.post` 装饰器 | documents.py |
| 5 | celery_worker command 路径 | `backend.tasks.document_tasks` → `tasks.document_tasks`（volume 挂载后 PYTHONPATH=/app） | docker-compose.yml |
| 6 | Dockerfile CMD 和 volume 配置 | volume `./backend:/app`，PYTHONPATH=/app，CMD `uvicorn main:app` | Dockerfile, docker-compose.yml |

### 12.2 OpenDataLoader 部署

| # | 任务 | 关键配置 |
|---|------|---------|
| 7 | Hybrid Server 构建 | Java Maven 项目，手动下载 `parser-1.31.13.jar` 并 install 到本地仓库 |
| 8 | Hybrid Server 部署 | 启动命令：`opendataloader-pdf-hybrid --port 5002 --force-ocr --ocr-lang "zh,en"` |
| 9 | wrapper.py endpoint | `/convert` → `/v1/convert/file`，参数名 `files`（非 `file`） |
| 10 | wrapper.py host | `localhost` → `host.docker.internal`（容器内访问宿主机） |
| 11 | wrapper.py timeout | 300s → 3600s |

**启动命令**：
```bash
opendataloader-pdf-hybrid --port 5002 --force-ocr --ocr-lang "zh,en"
```

### 12.3 前端 MVP 功能补全

| 组件 | 状态 | 说明 |
|------|------|------|
| TextBlock.vue | 新增 | 文本块渲染组件 |
| TableBlock.vue | 新增 | 表格块渲染组件 |
| ImageBlock.vue | 新增 | 图片块渲染组件 |
| ChartPlaceholder.vue | 新增 | 图表占位组件 |
| StructuredViewer.vue | 更新 | 动态路由到子组件 |
| Review.vue | 更新 | 历史抽屉 + 编辑模式优化 |

### 12.4 系统验证结果

| 验证项 | 状态 |
|--------|------|
| health check | 通过 |
| register/login | 通过 |
| documents CRUD | 通过 |
| OCR 端到端 | 通过（上传→Celery→Hybrid Server→结果存储→API返回，status: DONE） |
| 前端所有 MVP 页面 | 通过 |

### 12.5 docker-compose 启动命令（确认）

```bash
docker compose up -d postgres redis minio backend celery_worker
```

**注意**：
- `celery_worker` 的 command 使用 `tasks.document_tasks`（不是 `backend.tasks.document_tasks`）
- 容器内 PYTHONPATH 已设置为 `/app`，与 volume 挂载 `./backend:/app` 配套
- backend 的 CMD 为 `uvicorn main:app`，working_dir 默认为 `/app`
