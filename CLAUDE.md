# 审计文档处理系统

PDF 审计文档 OCR 识别、分屏比对、人工核验、Markdown 导出系统。

## 项目结构

```
backend/          # FastAPI + Celery
  ocr/wrapper.py  # OpenDataLoader 唯一调用入口（禁止绕过）
frontend/         # Vue 3 + Vite
  utils/CoordinateMapper.js  # PDF坐标转换（禁止手动计算坐标）
  utils/ScrollSyncer.js      # 滚动同步（禁止用百分比同步）
opendataloader-pdf-main/     # 第三方引擎（禁止修改）
doc/              # 详细文档
```

## 技术栈

- 后端：Python 3.11 + FastAPI + Celery + PostgreSQL + MinIO
- 前端：Vue 3 + Vite + Pinia + Element Plus + TailwindCSS

## 启动命令

```bash
# OCR 引擎
opendataloader-pdf-hybrid --port 5002 --force-ocr --ocr-lang "zh,en"
# 后端
cd backend && uvicorn main:app --reload --port 8082
# Celery Worker
PYTHONPATH=backend python3 -m celery -A backend.tasks.document_tasks:celery_app worker --loglevel=info
# 前端
cd frontend && npm run dev
```

## 核心约束（每次开发必读）

1. 禁止修改 `opendataloader-pdf-main/`，调用必须经过 `backend/ocr/wrapper.py`
2. 禁止在前端直接计算 PDF 坐标，必须用 `CoordinateMapper.js`
3. 禁止跳过 `need_review` 标记，导出前必须人工确认
4. 禁止在 API 层写业务逻辑，业务全部在 `services/`
5. 数字比对必须先经过 `NumberNormalizer.normalize()`

## 详细文档

- 开发规范：[doc/dev-guide.md](doc/dev-guide.md)
- 踩坑清单：[doc/pitfalls.md](doc/pitfalls.md)
- 排查思路：[doc/重难点问题排查思路.md](doc/重难点问题排查思路.md)
- AI Coding 过程日志：[doc/ai-coding-log.md](doc/ai-coding-log.md)
- MVP 手册：[MVP手册.md](MVP手册.md)
- 技术方案：[技术方案手册.md](技术方案手册.md)
