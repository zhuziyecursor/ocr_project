# 开发规范手册

> 从 CLAUDE.md 分离的详细规范，开发前按需查阅。

---

## 一、绝对禁止事项

1. **禁止修改 `opendataloader-pdf-main/`** — 所有调用通过 `backend/ocr/wrapper.py`
2. **禁止前端直接操作 PDF 坐标** — 只用 `CoordinateMapper.js`，手动 `* scale` 是错误信号
3. **禁止用滚动百分比做同步** — 两侧高度不一致会错位，用 `ScrollSyncer.js` 锚点策略
4. **禁止跳过 `need_review`** — 导出前必须人工确认，是审计核心约束
5. **禁止在 API 层写业务逻辑** — 路由层只做参数校验和转发
6. **禁止直接比较数字字符串** — 必须先 `NumberNormalizer.normalize()`

---

## 二、PDF 坐标系

OpenDataLoader 输出 bbox 使用 **PDF 内部坐标系**（原点左下角，Y 轴向上），PDF.js 是 Canvas 坐标系（原点左上角，Y 轴向下）。

**正确转换（CoordinateMapper.js）：**
```javascript
pdfToCanvas(bbox, pageHeight, scale) {
    const [x1, y1, x2, y2] = bbox;
    return {
        left:   x1 * scale,
        top:    (pageHeight - y2) * scale,  // 取 y2，不是 y1
        width:  (x2 - x1) * scale,
        height: (y2 - y1) * scale
    };
}
```

- `pageHeight` 从 `pdfPage.view[3]` 取，每页可能不同
- 缩放变化时必须重新计算，不能缓存旧坐标

---

## 三、后端规范

### 3.1 OpenDataLoader 调用

```python
result = convert(
    input_path,           # 注意参数名是 input_path，不是 pdf_path
    format="json",
    hybrid="docling-fast",
    sanitize=True,        # 安全要求，不得关闭
    table_method="cluster",
    image_output="embedded"
)
```

JVM 启动开销约 1-2 秒/次，50页分块时可忽略，不要过度拆分 chunk。

### 3.2 置信度规则（MVP 三条，不得增加）

| 规则 | 处理 |
|------|------|
| `hidden_text` 字段存在（OCR层） | `confidence *= 0.88` |
| 稀有字体/手写特征 | 强制 `need_review: true` |
| 类型为印章 | 强制 `need_review: true` |

`confidence < 0.85` 自动设置 `need_review: true`

### 3.3 Celery 任务规范

- 参数只接受可序列化类型（字符串/数字/列表），禁止传 ORM 对象
- 大文件分块固定 **50页**，每块完成立即推送进度
- 任务失败必须更新 `status = 'FAILED'`，最多重试 3 次

### 3.4 WebSocket 消息格式（字段不得增减）

```json
{
    "task_id": "string",
    "status": "PENDING | PROCESSING | DONE | FAILED",
    "current_page": 15,
    "total_pages": 45,
    "message": "正在识别第15页...",
    "document_id": "uuid（仅 status=DONE 时存在）"
}
```

### 3.5 数据库规范

- 主键全部 UUID（`gen_random_uuid()`）
- 识别结果整体存 `recognition_results.result_json`（JSONB），不拆表
- 人工修改只 INSERT `review_records`，不 UPDATE 覆盖
- 迁移用 Alembic，禁止直接执行 DDL

### 3.6 文件存储

- 原始文件存 MinIO：`documents/{document_id}/{original_filename}`
- `documents.file_path` 只存 MinIO 路径，不存本地绝对路径
- 临时文件处理完后必须清理

### 3.7 识别结果存储（可配置）

```yaml
storage:
  recognition_results:
    type: "local"   # 默认 local，可改 "minio"
    local:
      path: "/data/recognition_results"
```

---

## 四、前端规范

### 4.1 技术约束

- 组件写法：Composition API + `<script setup>`，禁止 Options API
- 状态：Pinia，禁止 Vuex 或跨层 emit
- 样式：TailwindCSS（布局）+ Element Plus（UI），不混用其他框架
- HTTP：全部封装在 `src/api/`，组件内禁止直接 fetch/axios

### 4.2 分屏比对组件树（结构固定，不得拆合）

```
CompareViewer.vue       ← 协调左右
├── PDFViewer.vue       ← PDF 渲染 + 高亮
└── StructuredViewer.vue ← 结构化内容
    ├── TextBlock.vue
    ├── TableBlock.vue
    ├── ImageBlock.vue
    └── ChartPlaceholder.vue
```

PDFViewer ↔ StructuredViewer 不直接通信，通过 `CompareViewer` 或 `activeBlockId` store 联动。
所有 block 元素必须有 `data-block-id` 属性。

### 4.3 图片渲染

```javascript
width  = (bbox[2] - bbox[0]) * scale
height = (bbox[3] - bbox[1]) * scale
```
禁止写固定尺寸，禁止 `max-width: 100%` 自动缩放。

### 4.4 差异高亮颜色（语义固定，不得更改）

| 类型 | 颜色 | 含义 |
|------|------|------|
| `modified` | `#FFF9C4`（黄） | 内容有差异 |
| `added` | `#E8F5E9`（绿） | 新增 |
| `deleted` | `#FFEBEE`（红） | 删除 |
| `need_review` | `#E3F2FD`（蓝） | 需人工核验 |

### 4.5 编辑模式

双击进入 → Enter 保存 → Escape 取消。保存必须调后端 API，成功后清除对应差异高亮。取消必须恢复原内容。

---

## 五、跨文件比对约定

- 无公共坐标系，只能通过语义相似度建立 `block_id` 映射
- 匹配阈值：`score > 0.75`，低于此值不强行配对
- 相似度权重：文本 **0.7** + 位置 **0.3**
- A/B 文档各自在自己坐标系独立高亮，不做跨文档坐标换算

---

## 六、同步/异步处理边界

| 条件 | 处理方式 | 前端行为 |
|------|---------|---------|
| ≤5MB 且 ≤10页 | 同步，最长 30秒 | 直接跳转核验界面 |
| >5MB 或 >10页 | 异步 Celery | 跳转任务列表，WebSocket 监听 |

判断逻辑在**后端**，前端只根据响应决定跳转目标。

---

## 七、安全规范

- 私有化部署，数据禁止上传任何外部服务
- 接口必须校验 JWT，`/login` 和 `/health` 除外
- 用户只能访问自己的文档（`uploaded_by` 过滤）
- 所有人工操作记录操作人 + 时间戳

---

## 八、验收自检清单

| 检查项 | 标准 |
|--------|------|
| 小文件处理 | ≤10页 PDF 30秒内完成并跳转 |
| 坐标高亮 | 高亮框与 PDF 原文位置吻合，无偏移 |
| 滚动联动 | 滚动任一侧，另一侧对应内容在视口中央 |
| 点击联动 | 响应 < 200ms |
| 修改保存 | 刷新后仍存在，历史记录可查 |
| 未核验导出 | 必须有明确警告 |
| 任务失败 | 状态变 FAILED，有重试入口 |

---

## 九、已知技术限制（交付时告知客户）

1. 图表：只显示 AI 文字描述，无法还原图表本身
2. 手写：识别准确率未验证，全部强制 `need_review`
3. 印章：只提取文字，不做真伪鉴定
4. 并发：MVP ~10人，生产目标 100人
5. 跨文件比对：准确率受大模型语义匹配质量影响
