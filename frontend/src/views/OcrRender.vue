<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const docList = ref([])
const selectedDocId = ref('')
const loading = ref(false)
const renderContainer = ref(null)

onMounted(async () => {
  await loadDocList()
})

async function loadDocList() {
  try {
    const response = await api.getDocuments(0, 100)
    docList.value = response.items || response.documents || []
  } catch (error) {
    console.error('Failed to load document list:', error)
    ElMessage.error('加载文档列表失败')
  }
}

// 从 prov 获取坐标（数据库 Docling 格式）
function getBboxFromProv(el) {
  const prov = el.prov
  if (!prov || !prov.length) return null
  const bbox = prov[0].bbox
  if (!bbox) return null
  return {
    l: bbox.l,
    t: bbox.t,
    r: bbox.r,
    b: bbox.b,
    coord_origin: bbox.coord_origin
  }
}

// 从 bounding box 获取坐标（旧格式）
function getBboxFromArray(bbox) {
  if (!bbox || bbox.length < 4) return null
  return { l: bbox[0], t: bbox[1], r: bbox[2], b: bbox[3], coord_origin: 'BOTTOMLEFT' }
}

// 转换坐标到 CSS 坐标系（原点左上角）
function transformCoords(bbox, pageHeight, scale = 1) {
  if (!bbox) return null
  const { l, t, r, b, coord_origin } = bbox

  let cssTop, height
  if (coord_origin === 'BOTTOMLEFT') {
    cssTop = (pageHeight - b) * scale
    height = (b - t) * scale
  } else {
    cssTop = t * scale
    height = (b - t) * scale
  }

  return {
    left: l * scale,
    top: cssTop,
    width: (r - l) * scale,
    height: height
  }
}

// 解析字体大小
function getFontSize(el) {
  if (el['font size']) return el['font size']
  if (el.formatting && el.formatting.length) {
    return el.formatting[0].size || 12
  }
  return 12
}

async function handleRender() {
  if (!selectedDocId.value) {
    ElMessage.warning('请选择文档')
    return
  }

  loading.value = true

  try {
    // 获取 OCR 结果数据（数据库格式）
    const data = await api.getDocumentResult(selectedDocId.value)
    console.log('[OcrRender] Loaded data:', {
      texts: data.document?.json_content?.texts?.length || 0,
      tables: data.document?.json_content?.tables?.length || 0,
      pictures: data.document?.json_content?.pictures?.length || 0,
      keys: Object.keys(data)
    })

    // 直接渲染到容器
    const container = document.querySelector('#render-container')
    if (!container) {
      throw new Error('Render container not found')
    }
    container.innerHTML = ''

    // 检测数据格式并提取元素
    let texts = [], tables = [], pictures = [], pageSizes = {}

    if (data.document && data.document.json_content) {
      // Docling 数据库格式
      const jc = data.document.json_content
      texts = jc.texts || []
      tables = jc.tables || []
      pictures = jc.pictures || []

      // 提取页面尺寸
      const pagesMeta = jc.pages || {}
      for (const [pageNo, pageInfo] of Object.entries(pagesMeta)) {
        const size = pageInfo.size || {}
        pageSizes[pageNo] = {
          width: size.width || 595,
          height: size.height || 842
        }
      }
    } else if (data.texts) {
      // 直接 texts 格式
      texts = data.texts || []
      tables = data.tables || []
      pictures = data.pictures || []
    }

    console.log(`[OcrRender] Rendering ${Object.keys(pageSizes).length || texts.length} pages`)

    // 按页码分组
    const pageMap = new Map()
    const addToPage = (el) => {
      const pageNo = el.prov?.[0]?.page_no || el['page number'] || 1
      if (!pageMap.has(pageNo)) pageMap.set(pageNo, [])
      pageMap.get(pageNo).push(el)
    }

    texts.forEach(addToPage)
    tables.forEach(addToPage)
    pictures.forEach(addToPage)

    // 为每一页创建画布
    for (const [pageNum, pageElements] of pageMap) {
      const pageDiv = document.createElement('div')
      pageDiv.className = 'ocr-page'

      // 使用实际页面尺寸或默认 A4
      const size = pageSizes[pageNum] || { width: 595, height: 842 }
      pageDiv.style.cssText = `
        position: relative;
        width: ${size.width}px;
        height: ${size.height}px;
        background: white;
        border: 1px solid #ccc;
        margin: 20px auto;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        overflow: hidden;
      `

      // 渲染每个元素
      for (const el of pageElements) {
        const elDiv = renderElement(el, size.height)
        if (elDiv) {
          pageDiv.appendChild(elDiv)
        }
      }

      // 添加页码
      const pageNumDiv = document.createElement('div')
      pageNumDiv.className = 'page-num'
      pageNumDiv.textContent = `Page ${pageNum}`
      pageDiv.appendChild(pageNumDiv)

      container.appendChild(pageDiv)
    }

    ElMessage.success('渲染完成')
  } catch (error) {
    console.error('[OcrRender] Render error:', error)
    ElMessage.error('渲染失败: ' + (error.message || error))
  } finally {
    loading.value = false
  }
}

function renderElement(el, pageHeight) {
  const type = el.label || el.type || 'text'
  let bbox = getBboxFromProv(el) || getBboxFromArray(el['bounding box'] || el.bbox)
  const coords = transformCoords(bbox, pageHeight)

  if (!coords || coords.width <= 0 || coords.height <= 0) {
    return null
  }

  const div = document.createElement('div')
  div.className = `ocr-element ocr-${type.toLowerCase()}`
  div.style.cssText = `position:absolute;left:${coords.left}px;top:${coords.top}px;width:${coords.width}px;height:${coords.height}px;`

  const text = el.text || el.content || ''
  const fontSize = getFontSize(el)

  switch (type.toLowerCase()) {
    case 'page_header':
    case 'page_footer':
      div.textContent = text
      div.style.font = `${fontSize}px Arial`
      div.style.color = '#888'
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      break
    case 'heading':
    case 'title':
    case 'section_header':
      div.textContent = text
      div.style.font = `bold ${fontSize}px Arial`
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      break
    case 'text':
    case 'paragraph':
      div.textContent = text
      div.style.font = `${fontSize}px Arial`
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      break
    case 'list_item':
      div.textContent = text
      div.style.font = `${fontSize}px Arial`
      div.style.paddingLeft = '20px'
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      break
    case 'code':
      div.textContent = text
      div.style.font = `${Math.max(fontSize * 0.9, 10)}px monospace`
      div.style.background = '#f5f5f5'
      div.style.padding = '4px'
      div.style.whiteSpace = 'pre-wrap'
      div.style.overflow = 'hidden'
      break
    case 'table':
      div.innerHTML = renderTable(el)
      div.style.background = 'rgba(0,0,0,0.02)'
      break
    case 'picture':
      div.innerHTML = '[Image]'
      div.style.background = '#f0f0f0'
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      div.style.justifyContent = 'center'
      div.style.color = '#666'
      div.style.fontSize = '12px'
      break
    default:
      div.textContent = text || `[${type}]`
      div.style.font = `${fontSize}px Arial`
  }

  return div
}

function renderTable(tableEl) {
  const grid = tableEl.data?.grid
  if (grid && Array.isArray(grid)) {
    let html = '<table style="border-collapse:collapse;width:100%;">'
    for (const row of grid) {
      html += '<tr>'
      for (const cell of row) {
        if (!cell) { html += '<td style="border:1px solid #ccc;padding:4px;"></td>'; continue }
        const colspan = cell.col_span || 1
        const rowspan = cell.row_span || 1
        html += `<td colspan="${colspan}" rowspan="${rowspan}" style="border:1px solid #ccc;padding:4px;">`
        html += cell.text || ''
        html += '</td>'
      }
      html += '</tr>'
    }
    html += '</table>'
    return html
  }

  const html_table = tableEl.html_table || tableEl.table
  if (html_table) return html_table

  const rows = tableEl.rows || []
  if (rows.length === 0) return '<table><tr><td>Empty table</td></tr></table>'

  let html = '<table style="border-collapse:collapse;width:100%;">'
  for (const row of rows) {
    html += '<tr>'
    for (const cell of (row.cells || [])) {
      const colspan = cell.col_span || cell['column span'] || 1
      const rowspan = cell.row_span || cell['row span'] || 1
      html += `<td colspan="${colspan}" rowspan="${rowspan}" style="border:1px solid #ccc;padding:4px;">`
      if (cell.text) html += cell.text
      else if (cell.kids) {
        for (const kid of cell.kids) {
          if (kid.text) html += kid.text
        }
      }
      html += '</td>'
    }
    html += '</tr>'
  }
  html += '</table>'
  return html
}

function isCodeLike(text, el) {
  if (!text) return false

  // 小字体可能是代码（OCR 识别代码时常用较小字体）
  const fontSize = el['font size'] || 12
  if (fontSize <= 9) return true

  // 检测代码特征
  const codePatterns = [
    /[{}\[\]();]/,                          // 代码常见符号
    /\/\/|\/\*|\*\/|#\s/m,                  // 注释
    /["'`].*["'`]\s*:/,                      // 键值对
    /^\s*(import|export|const|let|var|function|class|def |async|await)\s/m,
    /^\s*(if|else|for|while|return|switch|try|catch)\s*[({]/m,
    /[.#]\w+\s*[{:]/,                       // CSS选择器或属性访问
    /<\w+[^>]*>/,                           // HTML/XML标签
    /\w+\s*=\s*['"`]?[\w\d]+['"`]?/,      // 赋值语句
  ]

  // 统计匹配的模式数量
  const matchCount = codePatterns.filter(p => p.test(text)).length

  // 短行且有代码符号
  if (text.length < 100 && matchCount >= 2) return true

  // 多行代码特征
  if (text.length > 50 && matchCount >= 3) return true

  // JSON/配置文件格式
  if (text.includes('":') && text.includes('{')) return true

  return matchCount >= 4
}

function renderList(el) {
  const items = el['list items'] || []
  if (items.length === 0) return '<div>[List]</div>'

  let html = '<div style="padding:4px;">'
  for (const item of items) {
    const itemText = item.content || item.text || ''
    html += `<div style="padding-left:16px;list-style:disc;">${escapeHtml(itemText)}</div>`
  }
  html += '</div>'
  return html
}

function escapeHtml(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function handleDocChange(docId) {
  selectedDocId.value = docId
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="ocr-render-container">
    <header class="header">
      <h1>OCR 结果渲染</h1>
    </header>

    <main class="content">
      <div class="toolbar">
        <div class="file-selector">
          <label>选择文档：</label>
          <select v-model="selectedDocId" @change="handleDocChange(selectedDocId)">
            <option value="">-- 请选择 --</option>
            <option v-for="doc in docList" :key="doc.id" :value="doc.id">
              {{ doc.file_name || doc.id }} ({{ formatDate(doc.created_at) }})
            </option>
          </select>
        </div>
        <el-button type="primary" :loading="loading" :disabled="!selectedDocId" @click="handleRender">
          渲染
        </el-button>
      </div>

      <div v-if="loading" class="loading">加载中...</div>

      <div id="render-container" ref="renderContainer" class="render-container"></div>
    </main>
  </div>
</template>

<style scoped>
.ocr-render-container {
  min-height: 100vh;
  background: #f5f5f5;
}
.header {
  padding: 20px 40px;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.header h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
}
.content {
  padding: 20px 40px;
  max-width: 1400px;
  margin: 0 auto;
}
.toolbar {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.file-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.file-selector label {
  font-weight: 500;
  color: #333;
}
.file-selector select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  max-width: 500px;
}
.loading {
  text-align: center;
  padding: 60px;
  color: #666;
}
.render-container {
  display: flex;
  flex-direction: column;
  gap: 30px;
}
:deep(.ocr-page) {
  position: relative;
  background: white;
  border: 1px solid #ccc;
  margin: 0 auto;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
}
:deep(.ocr-element) {
  position: absolute;
  overflow: hidden;
}
:deep(.ocr-page .page-num) {
  position: absolute;
  bottom: 10px;
  right: 20px;
  font-size: 12px;
  color: #999;
}
:deep(.ocr-code) {
  font-family: monospace !important;
  background: #f5f5f5 !important;
  white-space: pre-wrap !important;
  overflow: hidden !important;
  border-left: 3px solid #409eff;
}
:deep(.ocr-image) {
  background: #f0f0f0;
}
:deep(.ocr-list) {
  background: transparent;
}
:deep(.ocr-table) {
  background: #f0f0f0;
}
</style>
