# 审计文档处理系统

PDF 审计文档 OCR 识别、分屏比对、人工核验、Markdown 导出系统。

---

## 一、项目基本信息

| 项目属性 | 值 |
|---------|-----|
| 项目类型 | Full-Stack Web Application |
| 后端技术 | Python 3.11 + FastAPI + Celery + PostgreSQL + Redis |
| 前端技术 | Vue 3 + Vite + Pinia + Element Plus + TailwindCSS |
| OCR 引擎 | OpenDataLoader (通过 `opendataloader_pdf.convert()` 调用 Java CLI) |
| 数据库 | PostgreSQL |
| 文件存储 | MinIO (S3 兼容) + 本地文件 |

---

## 二、启动命令

### 启动顺序

```bash
# 1. Redis（Celery 依赖）
redis-server

# 2. 后端 API 服务
cd backend && uvicorn main:app --reload --port 8082

# 3. Celery Worker（必须在 backend 目录内执行）
cd backend && python3 -m celery -A tasks.document_tasks:celery_app worker --loglevel=info

# 4. 前端开发服务器
cd frontend && npm run dev
```

**注意：** OCR 引擎通过 `opendataloader_pdf.convert()` 直接调用 Java CLI，不再需要启动独立的 HTTP 服务。

### OCR 引擎配置

`backend/core/config.py` 中的 `OPENDATALOADER_HYBRID` 参数控制文档识别模式：

| 配置值 | 说明 | 特点 |
|--------|------|------|
| `docling-fast`（默认） | 混合模式，文档发送给 docling-fast 服务器处理 | AI 识别能力强，支持表格结构、图表描述增强 |
| `off` | 纯 Java 模式（veraPDF） | 纯本地处理，无需网络；某些扫描页面可能检测到更多图片 |

**修改方式：** 编辑 `backend/core/config.py`，修改 `OPENDATALOADER_HYBRID` 的值。

**注意：** 切换 `hybrid` 配置后需重启 Celery Worker 使其生效。

### 默认管理员账号

```
用户名: admin
密码: admin123
```

---

## 三、项目结构

```
OCR_PROJECT/
├── backend/                           # FastAPI 后端
│   ├── main.py                       # 应用入口，路由注册
│   ├── api/                          # API 路由层
│   │   ├── auth.py                   # 认证相关 API (/auth)
│   │   ├── documents.py              # 文档管理 API (/documents)
│   │   ├── reviews.py                # 审核记录 API (/reviews)
│   │   └── ocr_files.py             # OCR 结果文件 API (/ocr-files)
│   ├── services/                     # 业务逻辑层
│   │   ├── auth_service.py           # 认证服务
│   │   ├── document_service.py       # 文档服务
│   │   ├── compare_service.py        # 跨文件比对服务
│   │   ├── export_service.py         # Markdown 导出服务
│   │   └── review_service.py         # 审核记录服务
│   ├── models/                       # 数据库模型
│   ├── schemas/                      # Pydantic 数据模型
│   ├── ocr/                          # OCR 相关
│   │   ├── wrapper.py                # OpenDataLoader 封装（唯一入口）
│   │   ├── audit_enhancer.py         # 审计增强层
│   │   ├── number_normalizer.py      # 数字规范化
│   │   └── table_merger.py           # 表格合并
│   ├── tasks/                        # Celery 异步任务
│   │   └── document_tasks.py         # 文档处理任务
│   └── core/                         # 核心配置
│
├── frontend/src/                      # Vue 3 前端
│   ├── main.js                       # 前端入口
│   ├── App.vue                       # 根组件
│   ├── router/index.js               # 路由配置
│   ├── views/                        # 页面组件
│   │   ├── Login.vue                 # 登录页
│   │   ├── TaskList.vue              # 任务列表页
│   │   ├── Upload.vue                # 文档上传页
│   │   ├── Review.vue                # 单文档人工核验页
│   │   ├── Compare.vue               # 双文档分屏比对页
│   │   └── OcrRender.vue             # OCR 渲染测试页
│   ├── components/                   # 公共组件
│   │   └── compare/                  # 比对相关组件
│   │       ├── PDFViewer.vue         # PDF 查看器
│   │       ├── TextBlock.vue         # 文本块组件
│   │       ├── TableBlock.vue        # 表格块组件
│   │       ├── ImageBlock.vue        # 图片块组件
│   │       └── ChartPlaceholder.vue  # 图表占位组件
│   ├── stores/                       # Pinia 状态管理
│   │   ├── auth.js                   # 认证状态
│   │   ├── documents.js              # 文档状态
│   │   └── compare.js                # 比对状态
│   ├── utils/                        # 工具函数
│   │   ├── CoordinateMapper.js       # PDF 坐标转换
│   │   ├── ScrollSyncer.js           # 滚动同步器
│   │   └── OCRResultRenderer.js       # OCR 结果渲染
│   └── api/index.js                  # API 调用封装
│
├── opendataloader-pdf-main/          # 第三方 OCR 引擎（禁止修改）
├── ocr_res/                           # OCR 识别结果本地存储
│   └── {document_id}/                # 每个文档的识别结果
│       ├── result.json               # kids 格式识别结果
│       └── images/                    # 提取的图片
├── doc/                              # 文档目录
├── ccr_result/                       # OCR 结果本地缓存
├── files/                            # 文件存储
└── CLAUDE.md                         # 项目约束文档
```

---

## 四、功能列表

```
审计文档处理系统
├── 1. 认证模块
│   ├── 用户注册 (/api/auth/register)
│   ├── 用户登录 (/api/auth/login)
│   └── JWT Token 认证
│
├── 2. 文档管理模块
│   ├── 文档上传 (/api/documents/upload)
│   ├── 文档列表查询 (/api/documents/)
│   ├── 文档详情获取 (/api/documents/{doc_id})
│   ├── 文档状态查询 (/api/documents/{doc_id}/status)
│   ├── 文档删除 (/api/documents/{doc_id})
│   ├── 文档原始文件获取 (/api/documents/{doc_id}/file)
│   └── 识别结果获取 (/api/documents/{doc_id}/result)
│
├── 3. OCR 识别模块
│   ├── OpenDataLoader 封装调用 (backend/ocr/wrapper.py)
│   ├── 审计增强层 (backend/ocr/audit_enhancer.py)
│   │   ├── 置信度计算 (confidence)
│   │   ├── need_review 标记
│   │   └── review_reason 原因记录
│   └── 本地 OCR 结果文件 API (/api/ocr-files/)
│
├── 4. 跨文件比对模块
│   ├── 文档比对 (/api/documents/compare)
│   ├── 文本相似度计算 (权重 0.7)
│   ├── 位置相似度计算 (权重 0.3)
│   └── diff 类型: added / deleted / modified
│
├── 5. 人工核验模块
│   ├── 创建审核记录 (/api/reviews/)
│   ├── 查询文档审核记录 (/api/reviews/document/{doc_id})
│   ├── 更新审核记录 (/api/reviews/{record_id})
│   └── need_review 标记追踪
│
├── 6. Markdown 导出模块
│   ├── 文档导出 (/api/documents/{doc_id}/export)
│   ├── 未核验内容警告标注
│   ├── 核验记录汇总
│   └── 表格渲染
│
└── 7. 前端页面
    ├── /login                          # 登录页
    ├── /tasks                          # 任务列表页
    ├── /upload                         # 文档上传页
    ├── /review/:docId                  # 单文档核验页
    ├── /compare/:docAId/:docBId        # 双文档比对页
    └── /ocr-render                     # OCR 渲染测试页
```

---

## 五、主要功能对应文件

| 功能 | 文件路径 |
|------|----------|
| **后端入口/路由注册** | `backend/main.py` |
| **用户认证 API** | `backend/api/auth.py` |
| **文档管理 API** | `backend/api/documents.py` |
| **审核记录 API** | `backend/api/reviews.py` |
| **OCR 文件 API** | `backend/api/ocr_files.py` |
| **文档服务** | `backend/services/document_service.py` |
| **比对服务** | `backend/services/compare_service.py` |
| **导出服务** | `backend/services/export_service.py` |
| **审核服务** | `backend/services/review_service.py` |
| **OpenDataLoader 封装** | `backend/ocr/wrapper.py` |
| **审计增强** | `backend/ocr/audit_enhancer.py` |
| **Celery 异步任务** | `backend/tasks/document_tasks.py` |
| **用户模型** | `backend/models/user.py` |
| **文档模型** | `backend/models/document.py` |
| **审核记录模型** | `backend/models/review_record.py` |
| **前端路由** | `frontend/src/router/index.js` |
| **登录页** | `frontend/src/views/Login.vue` |
| **任务列表页** | `frontend/src/views/TaskList.vue` |
| **上传页** | `frontend/src/views/Upload.vue` |
| **核验页** | `frontend/src/views/Review.vue` |
| **比对页** | `frontend/src/views/Compare.vue` |
| **PDF 查看器** | `frontend/src/components/compare/PDFViewer.vue` |
| **坐标转换** | `frontend/src/utils/CoordinateMapper.js` |
| **滚动同步** | `frontend/src/utils/ScrollSyncer.js` |
| **OCR 渲染** | `frontend/src/utils/OCRResultRenderer.js` |
| **认证状态** | `frontend/src/stores/auth.js` |
| **文档状态** | `frontend/src/stores/documents.js` |
| **比对状态** | `frontend/src/stores/compare.js` |

---

## 六、API 路由

### 认证模块 (`/api/auth`)

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/auth/register` | 用户注册 |
| POST | `/auth/login` | 用户登录 (返回 JWT Token) |

### 文档模块 (`/api/documents`)

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/documents/upload` | 上传文档 |
| GET | `/documents/` | 获取文档列表 |
| GET | `/documents/{document_id}` | 获取文档详情 |
| GET | `/documents/{document_id}/status` | 获取文档处理状态 |
| DELETE | `/documents/{document_id}` | 删除文档 |
| GET | `/documents/{document_id}/result` | 获取识别结果 |
| GET | `/documents/{document_id}/export` | 导出为 Markdown |
| GET | `/documents/{document_id}/file` | 获取原始 PDF 文件 |
| POST | `/documents/compare` | 跨文件比对 |

### 审核模块 (`/api/reviews`)

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/reviews/` | 创建审核记录 |
| GET | `/reviews/document/{document_id}` | 获取文档审核记录 |
| PUT | `/reviews/{record_id}` | 更新审核记录 |

### OCR 文件模块 (`/api/ocr-files`)

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/ocr-files/` | 列出 OCR 结果文件 |
| GET | `/ocr-files/{filename}` | 获取 OCR 结果 JSON |
| GET | `/ocr-files/{filename}/images/{image_name}` | 获取 OCR 结果中的图片 |

### 系统

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | 根路径，API 信息 |
| GET | `/health` | 健康检查 |

---

## 七、代码流程图

### 7.1 文档上传与 OCR 识别流程

```
用户上传 PDF
     ↓
DocumentService.upload_document()
     ↓
保存文件到 /tmp/ocr_project/{uuid}/
     ↓
创建 Document 记录 (status=PENDING)
     ↓
触发 Celery Task: process_document_task
     ↓
┌─────────────────────────────────────┐
│ Celery Worker 处理 (异步)            │
│                                     │
│ 1. 更新状态为 PROCESSING            │
│ 2. 调用 OpenDataLoader Wrapper      │
│    → 调用 opendataloader-pdf-hybrid  │
│    → 5002 端口 REST API             │
│ 3. AuditEnhancer.enhance()          │
│    → 添加 confidence 字段           │
│    → 标记 need_review               │
│ 4. 存储 RecognitionResult           │
│ 5. 更新状态为 DONE                  │
└─────────────────────────────────────┘
```

### 7.2 跨文件比对流程

```
用户选择两个文档 A 和 B
     ↓
POST /api/documents/compare {doc_a_id, doc_b_id}
     ↓
CompareService.compare()
     ↓
提取两个文档的 blocks (展平)
     ↓
双重循环匹配:
  - 文本相似度 (weight=0.7)
  - 位置相似度 (weight=0.3)
  - 阈值 score > 0.75
     ↓
生成 diffs 列表:
  - diff_type: "added" / "deleted" / "modified"
  - 包含 bbox, page, original_content, modified_content
```

### 7.3 人工核验流程

```
用户在 Review.vue 查看 need_review=True 的 blocks
     ↓
用户逐个核验内容
     ↓
点击确认 → 创建 ReviewRecord
     ↓
API: POST /api/reviews/
     ↓
ReviewService.create_review_record()
     ↓
更新 need_review 状态
```

### 7.4 Markdown 导出流程

```
用户请求导出文档
     ↓
GET /api/documents/{doc_id}/export
     ↓
ExportService.export_markdown()
     ↓
检查 unreviewed blocks:
  - 有未核验内容 → 文件头添加 ⚠️ 警告
     ↓
生成 Markdown:
  - 文件头 (文件名、时间、状态)
  - 警告信息 (如有必要)
  - 核验记录汇总
  - 按页展示识别内容
     ↓
StreamingResponse 返回文件下载
```

---

## 八、数据格式说明

### kids 格式（有效格式）

```json
{
  "kids": [...],
  "number of pages": 75,
  "file name": "xxx.pdf"
}
```

### Docling 格式（无效格式）

```json
{
  "status": "success",
  "document": {
    "json_content": {
      "texts": [...],
      "tables": [...],
      "pictures": [...]
    }
  }
}
```

---

## 九、核心约束

1. 禁止修改 `opendataloader-pdf-main/`，调用必须经过 `backend/ocr/wrapper.py`
2. 禁止在前端直接计算 PDF 坐标，必须用 `CoordinateMapper.js`
3. 禁止跳过 `need_review` 标记，导出前必须人工确认
4. 禁止在 API 层写业务逻辑，业务全部在 `services/`
5. 数字比对必须先经过 `NumberNormalizer.normalize()`
6. 禁止在 Review.vue 或其他组件中重新实现 OCR 渲染逻辑，必须复用 `OCRResultRenderer.js`
7. 修改 `compare_service.py` 或 `export_service.py` 时，必须同时支持 kids 格式和 Docling 格式

---

## 十、已知限制

1. `compare_service.py` 的 `_extract_blocks()` 只处理 Docling 格式，kids 格式下比对功能返回空结果
2. `export_service.py` 同样存在上述问题，kids 格式下导出内容为空

---

## 十一、详细文档

- 开发规范：[doc/dev-guide.md](doc/dev-guide.md)
- 踩坑清单：[doc/pitfalls.md](doc/pitfalls.md)
- 排查思路：[doc/重难点问题排查思路.md](doc/重难点问题排查思路.md)
- AI Coding 日志：[doc/ai-coding-log.md](doc/ai-coding-log.md)
- 项目约束：[CLAUDE.md](CLAUDE.md)
