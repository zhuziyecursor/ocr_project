# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 审计文档处理系统

PDF 审计文档 OCR 识别、分屏比对、人工核验、Markdown 导出系统。

## 项目结构

```
OCR_PROJECT/
├── backend/                    # FastAPI + Celery
│   ├── main.py                 # 应用入口，路由注册
│   ├── api/                    # API 路由层
│   ├── services/               # 所有业务逻辑（API 层禁止写业务）
│   ├── models/                 # 数据库模型
│   ├── ocr/
│   │   ├── wrapper.py          # OpenDataLoader 唯一调用入口
│   │   └── audit_enhancer.py   # 审计增强层
│   ├── tasks/
│   │   └── document_tasks.py  # Celery 异步任务（OCR 识别流程）
│   └── core/                   # 核心配置
├── frontend/src/              # Vue 3 前端
│   ├── views/Review.vue        # 核验页面（右侧 OCR 结果渲染）
│   └── utils/                 # 工具函数
├── ocr_res/                    # OCR 识别结果本地存储
│   └── {document_id}/          # 每个文档的识别结果
│       ├── result.json        # kids 格式识别结果
│       └── images/            # 提取的图片
└── doc/                        # 详细文档
```

## 技术栈

- 后端：Python 3.11 + FastAPI + Celery + PostgreSQL + MinIO
- 前端：Vue 3 + Vite + Pinia + Element Plus + TailwindCSS

## 启动命令

```bash
# 后端（端口 8200）
cd backend && python3 -m uvicorn main:app --reload --port 8200

# Celery Worker（必须在 backend 目录内执行）
cd backend && python3 -m celery -A tasks.document_tasks:celery_app worker --loglevel=info

# 前端（端口 3200）
cd frontend && npm run dev
```

服务端口：
- Frontend: 3200
- Backend API: 8200
- PostgreSQL: 15432
- Redis: 6380
- MinIO: 19000/19001

**注意：** OCR 引擎通过 `opendataloader_pdf.convert()` 直接调用 Java CLI，不再依赖 HTTP 服务。

## 数据格式约定（必读）

系统使用 **kids 格式**存储 OCR 结果：

```json
{
  "kids": [...],
  "number of pages": 75,
  "file name": "xxx.pdf"
}
```

**kids 格式特征：**
- `kids` 数组包含所有识别元素（paragraph、heading、image、table 等）
- 每个元素有 `page number`、`bounding box`、`content` 等字段

**识别结果存储：**
1. **数据库**：`recognition_results.result_json` (JSONB)
2. **本地文件**：`ocr_res/{document_id}/result.json` + `images/`

## 核心约束（每次开发必读）

1. OCR 调用必须经过 `backend/ocr/wrapper.py`
2. 禁止在前端直接计算 PDF 坐标，必须用 `CoordinateMapper.js`（坐标系是 BOTTOMLEFT，手动计算方向必错）
3. 禁止跳过 `need_review` 标记，导出前必须人工确认（审计合规要求）
4. 禁止在 API 层写业务逻辑，业务全部在 `services/`
5. 数字比对必须先经过 `NumberNormalizer.normalize()`
6. 识别结果同时存储到数据库和本地 `ocr_res/{document_id}/` 目录

## 核心功能修改规范（铁律）

**修改 bug 或添加新功能时，严禁修改核心功能。**

核心功能包括但不限于：
- `process_document_task` 的主流程（OCR 调用链路）
- `OpenDataLoaderWrapper.convert()` / `convert_with_images()` 的调用方式
- 数据的存储结构（result_json、kids 格式）
- API 的核心返回格式

如果必须修改核心功能，必须：
1. 先向用户说明修改内容和原因
2. 获得用户明确确认后才能执行
3. 修改后立即验证不影响现有功能

**违反此规范的修改，即使代码能运行，也必须回退。**

## 已知限制

- `services/compare_service.py`：kids 格式下比对功能可能返回空结果
- `services/export_service.py`：kids 格式下导出内容可能为空

如需修改以上两个文件，需同时支持 kids 格式和 Docling 格式：
```python
if result_json.get("kids"):
    # kids 格式处理
else:
    # Docling 格式处理
```

## 详细文档

- 开发规范：[doc/dev-guide.md](doc/dev-guide.md)
- 踩坑清单：[doc/pitfalls.md](doc/pitfalls.md)
- 排查思路：[doc/重难点问题排查思路.md](doc/重难点问题排查思路.md)
- AI Coding 过程日志：[doc/ai-coding-log.md](doc/ai-coding-log.md)
- MVP 手册：[MVP手册.md](MVP手册.md)
- 技术方案：[技术方案手册.md](技术方案手册.md)

## Karpathy Guidelines

行为准则，减少 LLM 编程错误。**权衡：** 偏向谨慎而非速度，简单任务自行判断。

### 1. Think Before Coding

**不要假设，不要隐藏困惑，暴露权衡。**

实现前：
- 明确陈述假设，不确定时提问
- 存在多种解释时，列出它们而不是默默选择
- 存在更简单方案时说出来，该反驳时反驳
- 有不清楚的地方就停下来，指出困惑所在并提问

### 2. Simplicity First

**最少代码解决问题，不做投机性代码。**

- 不添加需求之外的功能
- 不为一次性代码创建抽象
- 不添加未请求的"灵活性"或"可配置性"
- 不为不可能的场景添加错误处理
- 如果 200 行可以写成 50 行，重写

自问："高级工程师会说这过度复杂吗？"如果是，简化。

### 3. Surgical Changes

**只触碰必须改的，只清理自己的烂摊子。**

编辑现有代码时：
- 不"改进"相邻代码、注释或格式
- 不重构没坏的部分
- 匹配现有风格，即使你会有不同做法
- 发现无关死代码时提及，但不删除

你的修改造成孤儿代码时：
- 移除你修改造成的未使用导入/变量/函数
- 不移除已有的死代码，除非被要求

检验标准：每行修改都应该直接追溯到用户请求。

### 4. Goal-Driven Execution

**定义成功标准，循环验证直到完成。**

将任务转化为可验证目标：
- "添加验证" → "为无效输入写测试，然后让它们通过"
- "修复 bug" → "写一个复现它的测试，然后让测试通过"
- "重构 X" → "确保测试前后都通过"

多步任务时，列出简要计划：
```
1. [步骤] → 验证: [检查项]
2. [步骤] → 验证: [检查项]
3. [步骤] → 验证: [检查项]
```

强成功标准让你能独立循环，弱标准（"让它工作"）需要不断澄清。

---

## 项目特定架构知识（从踩坑实践中沉淀）

### 图片渲染链路（重要）

```
OpenDataLoader 输出 image kids（仅含 id、bbox，无 data）
     ↓ convert_with_images() 复制图片到 ocr_res/{doc_id}/images/
     ↓
save_to_local() 为每个 image kid 写入 source 字段
     ↓ source 格式: "images/imageFile1.png"
     ↓
前端 getImageUrl(source) → /api/documents/{id}/images/{name}
     ↓
backend get_document_image() → 读 ocr_res/{id}/images/{name}
```

**关键陷阱：OpenDataLoader 的 kid.id 与 imageFileN.png 中的 N 不匹配**
- kid.id 是全局唯一标识符（如 10、67、943）
- imageFileN.png 的 N 只是文件序号（1, 2, 3...）
- 不要尝试通过 id 匹配来建立关联，这行不通
- `save_to_local()` 的兜底逻辑：所有 image kid 共享 `images/imageFile1.png`

**OpenDataLoader 的 image kid 分类质量差**：系统会把装饰分隔线、页码小图标等非图片元素也标记为 `type=image`，这是 OCR 引擎行为，非代码 bug。

### kids 格式 vs Docling 格式（双轨制）

系统从 OpenDataLoader 切换到 kids 格式后，部分存量数据仍是 Docling 格式。

| 格式 | 结构 | 处理状态 |
|------|------|---------|
| kids 格式 | `kids[]` 数组，含 paragraph/heading/image/table | 当前主力格式 |
| Docling 格式 | `document.json_content {texts, tables, pictures}` | 旧格式，已废弃 |

**判断方法：**
```python
if result.get("kids"):
    # kids 格式
else:
    # Docling 格式
```

**compare_service.py 和 export_service.py 必须同时支持两种格式**。

### PDF 坐标与 Vue 响应式陷阱

PDF 使用 BOTTOMLEFT 坐标系（原点左下，Y轴向上），Canvas 使用 TOPLEFT 坐标系。

**坐标转换必须用 CoordinateMapper.js，禁止手动计算。**

**PDF.js 对象禁止用 ref() 深度代理**：pdfjs 内部使用 `#pagePromises` 等私有字段，被 Vue `ref()` 深度代理后私有字段访问会抛出 `Cannot read private member`。修复：使用 `shallowRef()` 而非 `ref()`。

### 数据流反向追溯法（排查问题时用）

界面现象 → 前端 API 响应 → Service 层 → 数据库/Redis → 写入代码

遇到 Bug 时，先打印/查数据库验证数据是否到位，再看渲染代码。

### Celery Worker 与代码更新

Celery Worker 加载的是启动时的代码快照。修改 `document_tasks.py` 后**必须重启 Worker**：
```bash
pkill -f "celery.*document_tasks"
cd backend && python3 -m celery -A tasks.document_tasks:celery_app worker --loglevel=info
```
