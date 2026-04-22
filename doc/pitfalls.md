# 改码踩坑清单

记录实际遇到的问题及其根因，避免重复踩坑。

---

## 问题一：前端页面空白（blank page）

**发生时间**：2026-04-15
**项目**：OCR_PROJECT 前端（Vue 3 + Vite）

### 背景

前端使用 Vue 3 + Vite + Element Plus + TailwindCSS v4 技术栈。用户反馈访问 http://localhost:3000 时页面空白。

### 排查过程

#### 第一轮：误判 TailwindCSS v4

- **假设**：TailwindCSS v4 的 @tailwindcss/vite 插件导致空白
- **验证**：注释掉 `@import "tailwindcss"`，使用 Python 静态服务器访问 dist 目录，页面正常显示
- **结论**：构建产物正常，问题在开发服务器
- **教训**：构建版本正常不代表开发版本正常，需要在 dev server 上验证

#### 第二轮：换 PostCSS 方案

- **假设**：@tailwindcss/vite 插件与 Vite 开发服务器不兼容
- **操作**：移除 vite.config.js 中的 tailwindcss() 插件，安装 @tailwindcss/postcss，新建 postcss.config.js
- **验证**：dev server 启动 200 响应，但页面仍空白
- **教训**：换方案没换思路，是画圈不是闭环

#### 第三轮：回到 RCA，搜索空白页常见原因

- **搜索**：`element-plus icons-vue blank page` — 图标导入方式问题，不会导致空白
- **重新读取 main.js 源码**（od -c 逐字节读取）
- **发现**：main.js 文件只有 8 行，仅有 import 语句，**缺少 createApp / app.use / app.mount**

### 根因

main.js 文件不完整，只有 import 语句，Vue app 从未挂载到 `#app`：

```javascript
// 错误：只有 import，没有挂载
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './style.css'
// 缺失：const app = createApp(App)
// 缺失：app.use(pinia) / app.use(router) / app.use(ElementPlus)
// 缺失：app.mount('#app')
```

### 修复

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
```

### 经验总结

1. **空白页排查顺序**：先验证 JS 是否执行（console.log / network），再看 Vue 是否挂载，最后查 CSS
2. **Vue app 必须有 createApp + mount**：没有 mount 就是空白，这是 Vue 入门级错误，但容易被忽略
3. **构建产物正常 ≠ 开发服务器正常**：两类问题的排查方法不同
4. **搜索替代不了源码**：网络搜索 element-plus 图标问题花了时间，而 main.js 只有 8 行，od -c 直接读字节就能发现

---

## 问题二：TailwindCSS v4 插件兼容性（相关）

**发生时间**：2026-04-15

### 现象

@tailwindcss/vite 插件在 Vite 开发服务器模式下可能导致页面空白。构建（npm run build）正常。

### 解决方案

使用 PostCSS 方式替代 Vite 插件方式：

1. `npm install @tailwindcss/postcss --save-dev`
2. 移除 vite.config.js 中的 `tailwindcss()` 插件
3. 新建 `postcss.config.js`：
   ```javascript
   export default {
     plugins: {
       '@tailwindcss/postcss': {}
     }
   }
   ```
4. 保留 style.css 中的 `@import "tailwindcss"`

### 教训

TailwindCSS v4 有两种引入方式：Vite 插件 和 PostCSS。后者在开发模式下更稳定。

---

## 问题三：端口冲突处理

**发生时间**：2026-04-15

### 现象

npm run dev 时端口 3000 已被占用。

### 处理规则

遇到端口占用时，**必须先询问用户**，不得直接切换端口。

```
端口 3000 被占用（PID XXXXX），如何处理？
1. 终止旧进程，释放端口
2. 切换到其他端口
```

### 已记录到用户记忆

路径：`/Users/apple/.claude/memory/端口冲突处理.md`

---

## 问题四：上传接口 Internal Server Error

**发生时间**：2026-04-15
**项目**：OCR_PROJECT 后端（FastAPI + Celery）

### 现象

调用 `POST /api/documents/upload` 返回 500 Internal Server Error。

### 排查过程

1. 检查后端：8082 端口 health 正常
2. 检查 Redis：6379 端口正常
3. 检查 Celery Worker：**未运行**
4. 启动 Worker 后任务执行失败
5. 错误日志：`TypeError: convert() got an unexpected keyword argument 'pdf_path'`
6. 检查 wrapper.py：参数名错误，`pdf_path` 应为 `input_path`

### 根因

| 问题 | 根因 | 阶段 |
|------|------|------|
| Celery Worker 未运行 | 没有开发启动文档说明需要同时启动哪些服务 | 开发阶段 |
| 参数名错误 | 调用第三方库（OpenDataLoader）没有测试验证 | 开发阶段 + 测试缺失 |

### 修复

1. 安装并启动 Celery Worker：
   ```bash
   pip3 install celery
   PYTHONPATH=backend python3 -m celery -A backend.tasks.document_tasks:celery_app worker --loglevel=info
   ```

2. 修复 `backend/ocr/wrapper.py` 第 85 行：
   ```python
   # 错误
   params = {"pdf_path": file_path, ...}
   # 正确
   params = {"input_path": file_path, ...}
   ```

### 经验总结

#### 关于"能跑通就不管"

这个问题是绝对不能出现的。代码写完必须验证，不能因为"异步任务不会同步报错"就以为没问题。

**具体规则：**
- 所有封装的外部依赖调用（如 `wrapper.py`），写完必须实际调用一次验证
- 不能只看代码逻辑正确就认为正确，必须有运行时验证
- 异步任务也要有错误处理和日志，失败不能静默

#### 关于文档与代码的一致性

发现文档和代码有出入时，必须和用户确认，不能擅作主张。

**具体规则：**
- `docker-compose.yml` 定义了服务 = 必须同步写清楚怎么启动
- 任何代码改动影响依赖或启动方式 = 必须更新相关文档并确认
- 不确定时宁愿先问，不要默认"用户应该知道"

#### 关于引入外部依赖

即使你没有说单元测试，在引入外部依赖时我也必须主动考虑测试。

**具体规则：**
- 封装第三方库（OpenDataLoader、MiniIO 等）的代码必须有基础测试
- 测试重点：参数名、返回值结构、异常处理
- 没有测试的外部依赖封装 = 禁止提交

### 预防措施

| 措施 | 优先级 | 状态 |
|------|--------|------|
| 添加 `backend/tests/` 单元测试（wrapper.py） | P0 | 待做 |
| 添加 `backend/STARTUP.md` 开发启动文档 | P0 | 待做 |
| 使用 docker-compose 启动全量服务 | P1 | 可选 |

---

## 问题五：Python 模块导入路径错误（Celery Worker 找不到 backend 模块）

**发生时间**：2026-04-22

### 现象

Celery Worker 启动正常，能识别 tasks，但执行 `process_document_task` 时报错：
```
ModuleNotFoundError: No module named 'backend'
```

### 根因

Celery Worker 在 `backend/` 目录内启动时（`cd backend && python -m celery ...`），当前工作目录是 `backend/`。

此时 `from core.config import settings` 可以正常工作（因为 `core` 是 `backend/` 下的子目录）。

但如果写成 `from backend.core.config import settings`，Python 会把 `backend` 当作顶级模块，从项目根目录开始搜索。但项目根目录没有 `backend` 这个名字的目录在 Python 路径中。

### 修复

在 `backend/ocr/wrapper.py` 中使用 `sys.path` 修改：

```python
import os
import sys

# Add parent directory to path so 'backend' can be imported as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.core.config import settings
```

### 经验总结

Celery Worker 在 `backend/` 目录内启动时，若该模块需要 import `backend.xxx`，必须先修改 `sys.path` 把项目根目录加进去。

---

## 问题六：docling-fast 模式检测不到图片（hybrid off 模式差异）

**发生时间**：2026-04-22

### 现象

文档第 75 页有一张大图，用 `hybrid="docling-fast"` 模式处理时没有检测到图片。但同一个 PDF 用 GitHub 原版（默认 `hybrid="off"`）能检测到。

### 排查过程

1. 调用 docling-fast API 检查原始输出：`curl -X POST http://localhost:5002/v1/convert/file -F "files=@doc.pdf" -F "page_ranges=75-75"`
2. docling API 只返回 3 张极小的图片（10x10, 26x27 pts），都小于 50x50 过滤阈值
3. 文档 75 页的大图在 docling 输出中完全不存在

### 根因

| 模式 | 默认配置 | 行为 |
|------|----------|------|
| `hybrid="docling-fast"` | AI 混合模式 | docling 模型检测图片，某些扫描页背景图可能分类为"背景"而非独立图片 |
| `hybrid="off"` | 纯 Java (veraPDF) | 纯本地处理，无需网络，某些扫描页可能检测到更多图片 |

docling 模型对扫描页面背景图的检测能力弱于纯 Java veraPDF 处理。

### 解决方案

通过 `backend/core/config.py` 中的 `OPENDATALOADER_HYBRID` 配置切换模式：
- `docling-fast`：AI 能力强，支持表格结构、图表描述增强
- `off`：纯本地，某些扫描页检测更好

修改后需重启 Celery Worker。

---

## 问题七：EnrichedImageChunk 使用错误的 bounding box 导致图片提取不完整

**发生时间**：2026-04-22

### 现象

docling 检测到的 SemanticPicture 有正确的大 bbox，但最终提取的图片只是一个小 fragment。

### 根因

1. `filterTinyImages` 先过滤掉了小于 50x50 的 Java ImageChunk
2. `enrichBackendResults` 尝试将 docling 的 SemanticPicture 与 Java ImageChunk 匹配
3. `EnrichedImageChunk(source, description)` 构造函数使用 `source.getBoundingBox()` — 即被过滤后的 Java ImageChunk 的小 bbox
4. `ImagesUtils.writeImage()` 用这个 tiny bbox 提取图片，只提取了一小块

### 修复

EnrichedImageChunk 新增 3 参数构造函数，允许传入正确的 extraction bbox：

```java
public EnrichedImageChunk(ImageChunk source, BoundingBox extractionBbox, String description) {
    super(extractionBbox);  // 使用传入的正确 bbox
    // ...
}
```

调用处改为：
```java
enriched.add(new EnrichedImageChunk(matched, picture.getBoundingBox(), picture.getDescription()));
```

### 经验总结

匹配 Backend 结果时，如果 backend 的 bbox 与 Java 的不一致，必须使用 backend 的 bbox 进行图片提取，而非 Java 侧的 bbox。

---
