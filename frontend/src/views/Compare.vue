<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCompareStore } from '@/stores/compare'
import { ElMessage } from 'element-plus'
import PDFViewer from '@/components/compare/PDFViewer.vue'
import { ScrollSyncer } from '@/utils/ScrollSyncer'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const compareStore = useCompareStore()

const { docAId, docBId } = route.params
const scale = ref(1.0)
const activeBlockId = ref(null)
const leftPanelRef = ref(null)
const rightPanelRef = ref(null)
const loading = ref(false)
const ocrLoading = ref(false)
const ocrContainerRef = ref(null)
let scrollSyncer = null

// OCR 渲染相关
let ocrData = null
const pageMap = new Map()

const pdfUrlA = computed(() => api.getDocumentFileUrl(docAId))
const pdfUrlB = computed(() => api.getDocumentFileUrl(docBId))

onMounted(async () => {
  compareStore.reset()
  loading.value = true
  try {
    await compareStore.loadDocuments(docAId, docBId)
    await compareStore.loadDiffs(docAId, docBId)
    await loadOcrResult()
  } catch {
    ElMessage.error('加载文档失败')
  } finally {
    loading.value = false
  }
})

watch([leftPanelRef, rightPanelRef], ([lEl, rEl]) => {
  if (lEl && rEl) {
    scrollSyncer?.destroy()
    scrollSyncer = new ScrollSyncer(lEl, rEl)
  }
})

onUnmounted(() => { scrollSyncer?.destroy() })

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

// 判断是否为代码块
function isCodeLike(text, el) {
  if (!text) return false

  const fontSize = el['font size'] || 12
  if (fontSize <= 9) return true

  const codePatterns = [
    /[{}\[\]();]/,
    /\/\/|\/\*|\*\/|#\s/m,
    /["'`].*["'`]\s*:/,
    /^\s*(import|export|const|let|var|function|class|def |async|await)\s/m,
    /^\s*(if|else|for|while|return|switch|try|catch)\s*[({]/m,
    /[.#]\w+\s*[{:]/,
    /<\w+[^>]*>/,
    /\w+\s*=\s*['"`]?[\w\d]+['"`]?/,
  ]

  const matchCount = codePatterns.filter(p => p.test(text)).length
  if (text.length < 100 && matchCount >= 2) return true
  if (text.length > 50 && matchCount >= 3) return true
  if (text.includes('":') && text.includes('{')) return true

  return matchCount >= 4
}

// 解析字体大小
function getFontSize(el) {
  if (el['font size']) return el['font size']
  if (el.formatting && el.formatting.length) {
    return el.formatting[0].size || 12
  }
  return 12
}

// 加载 OCR 结果
async function loadOcrResult() {
  ocrLoading.value = true
  try {
    const data = await api.getDocumentResult(docBId)
    ocrData = data

    // 检测数据格式并提取元素
    let texts = [], tables = [], pictures = [], pageSizes = {}

    if (data.document && data.document.json_content) {
      const jc = data.document.json_content
      texts = jc.texts || []
      tables = jc.tables || []
      pictures = jc.pictures || []

      const pagesMeta = jc.pages || {}
      for (const [pageNo, pageInfo] of Object.entries(pagesMeta)) {
        const size = pageInfo.size || {}
        pageSizes[pageNo] = {
          width: size.width || 595,
          height: size.height || 842
        }
      }
    } else if (data.texts) {
      texts = data.texts || []
      tables = data.tables || []
      pictures = data.pictures || []
    }

    // 按页码分组
    pageMap.clear()
    const addToPage = (el) => {
      const pageNo = el.prov?.[0]?.page_no || el['page number'] || 1
      if (!pageMap.has(pageNo)) pageMap.set(pageNo, [])
      pageMap.get(pageNo).push(el)
    }

    texts.forEach(addToPage)
    tables.forEach(addToPage)
    pictures.forEach(addToPage)

    // 找出与无 source 的 picture 区域重叠的 text/paragraph，标记为表格区域
    const pictureAreas = pictures.filter(p => !p.source && !p.text && !p.content)
    texts.forEach(el => {
      if (!el._tableArea && pictureAreas.length > 0) {
        const bbox = el.prov?.[0]?.bbox || el.bbox || el['bounding box']
        if (bbox) {
          for (const pic of pictureAreas) {
            const picBbox = pic.prov?.[0]?.bbox || pic.bbox || pic['bounding box']
            if (picBbox &&
                bbox.l < picBbox.r && bbox.r > picBbox.l &&
                bbox.t < picBbox.b && bbox.b > picBbox.t) {
              el._tableArea = true
              break
            }
          }
        }
      }
    })

    // 渲染 OCR 结果
    renderOcrResult(pageSizes)
  } catch (error) {
    console.error('[Compare] Load OCR result failed:', error)
  } finally {
    ocrLoading.value = false
  }
}

// 渲染 OCR 结果到容器
function renderOcrResult(pageSizes) {
  const container = ocrContainerRef.value
  if (!container || !ocrData) return

  container.innerHTML = ''

  for (const [pageNum, pageElements] of pageMap) {
    const pageDiv = document.createElement('div')
    pageDiv.className = 'ocr-page'

    const size = pageSizes[pageNum] || { width: 595, height: 842 }
    pageDiv.style.cssText = `
      position: relative;
      width: ${size.width}px;
      height: ${size.height}px;
      background: white;
      border: 1px solid #ccc;
      margin: 10px auto;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      overflow: hidden;
    `

    for (const el of pageElements) {
      const elDiv = renderElement(el, size.height)
      if (elDiv) pageDiv.appendChild(elDiv)
    }

    const pageNumDiv = document.createElement('div')
    pageNumDiv.className = 'page-num'
    pageNumDiv.textContent = `Page ${pageNum}`
    pageDiv.appendChild(pageNumDiv)

    container.appendChild(pageDiv)
  }
}

function renderElement(el, pageHeight) {
  const type = el.label || el.type || 'text'
  let bbox = getBboxFromProv(el) || getBboxFromArray(el['bounding box'] || el.bbox)
  const coords = transformCoords(bbox, pageHeight)

  if (!coords || coords.width <= 0 || coords.height <= 0) {
    return null
  }

  const text = el.text || el.content || ''

  // 检测是否为代码块（根据类型或内容特征）
  const isCode = type === 'code' || isCodeLike(text, el)

  const div = document.createElement('div')
  div.className = `ocr-element ocr-${type.toLowerCase()}${isCode ? ' ocr-code' : ''}`
  div.style.cssText = `position:absolute;left:${coords.left}px;top:${coords.top}px;width:${coords.width}px;height:${coords.height}px;`

  const fontSize = getFontSize(el)

  if (isCode) {
    // 代码块样式：左边框 + monospace 字体 + 浅色背景
    div.textContent = text
    div.style.font = `${Math.max(fontSize * 0.9, 10)}px monospace`
    div.style.background = '#f5f5f5'
    div.style.borderLeft = '3px solid #409eff'
    div.style.padding = '4px'
    div.style.whiteSpace = 'pre-wrap'
    div.style.overflow = 'hidden'
    div.style.display = 'flex'
    div.style.alignItems = 'flex-start'
  } else {
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
        if (el._tableArea) {
          div.style.borderLeft = '3px solid #409eff'
          div.style.paddingLeft = '6px'
          div.style.background = 'rgba(64, 158, 255, 0.05)'
        }
        break
      case 'text':
      case 'paragraph':
        div.textContent = text
        div.style.font = `${fontSize}px Arial`
        div.style.display = 'flex'
        div.style.alignItems = 'center'
        if (el._tableArea) {
          div.style.borderLeft = '3px solid #409eff'
          div.style.paddingLeft = '6px'
          div.style.background = 'rgba(64, 158, 255, 0.05)'
        }
        break
      case 'list_item':
        div.textContent = text
        div.style.font = `${fontSize}px Arial`
        div.style.paddingLeft = '20px'
        div.style.display = 'flex'
        div.style.alignItems = 'center'
        break
      case 'table':
        div.innerHTML = renderTable(el)
        div.style.background = 'rgba(0,0,0,0.02)'
        break
      case 'picture':
        // 有文字就显示文字，没有文字且没有 source 的不渲染
        if (text) {
          div.textContent = text
          div.style.font = `${fontSize}px Arial`
        } else {
          div.style.display = 'none'  // 隐藏无内容的 picture，让同区域的 paragraph 正常显示
        }
        break
      default:
        div.textContent = text || `[${type}]`
        div.style.font = `${fontSize}px Arial`
        div.style.display = 'flex'
        div.style.alignItems = 'center'
    }
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

function handleScaleChange(newScale) {
  scale.value = newScale
}

function handleLeftScroll() {
  scrollSyncer?.handleSourceScroll(activeBlockId.value)
}

function handleBlockClickA(blockId) {
  activeBlockId.value = blockId
  compareStore.setActiveBlock(blockId)
  const diff = compareStore.diffs.find(d => d.block_id_a === blockId)
  if (diff?.block_id_b && rightPanelRef.value) {
    const el = rightPanelRef.value.querySelector(`[data-block-id="${diff.block_id_b}"]`)
    el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
}

function handleBlockClickB(blockId) {
  activeBlockId.value = blockId
  compareStore.setActiveBlock(blockId)
}

function handlePrevDiff() {
  compareStore.goToPrevDiff()
  activeBlockId.value = compareStore.activeBlockId
}

function handleNextDiff() {
  compareStore.goToNextDiff()
  activeBlockId.value = compareStore.activeBlockId
}

function getDiffClass(block) {
  const blockId = block.id || block.block_id
  const diff = compareStore.diffs.find(d => d.block_id_b === blockId)
  if (!diff) return ''
  if (diff.need_review) return 'need_review'
  return diff.diff_type
}

function getDiffLabel(block) {
  const map = { modified: '修改', added: '新增', deleted: '删除', need_review: '需核验' }
  return map[getDiffClass(block)] || ''
}

const diffCount = computed(() => compareStore.diffs.length)
const modifiedCount = computed(() => compareStore.diffs.filter(d => d.diff_type === 'modified').length)
const addedCount = computed(() => compareStore.diffs.filter(d => d.diff_type === 'added').length)
const deletedCount = computed(() => compareStore.diffs.filter(d => d.diff_type === 'deleted').length)
</script>

<template>
  <div class="compare-container" v-loading="loading">
    <header class="header">
      <div class="header-left">
        <el-button @click="router.push('/tasks')">返回</el-button>
        <span class="title">跨文件比对</span>
        <div class="diff-summary">
          <el-tag type="warning" size="small">修改 {{ modifiedCount }}</el-tag>
          <el-tag type="success" size="small">新增 {{ addedCount }}</el-tag>
          <el-tag type="danger" size="small">删除 {{ deletedCount }}</el-tag>
        </div>
      </div>
      <div class="header-center">
        <el-button :disabled="compareStore.currentDiffIndex === 0" @click="handlePrevDiff">上一处差异</el-button>
        <span class="diff-counter">{{ diffCount > 0 ? compareStore.currentDiffIndex + 1 : 0 }} / {{ diffCount }}</span>
        <el-button :disabled="compareStore.currentDiffIndex >= diffCount - 1" @click="handleNextDiff">下一处差异</el-button>
      </div>
      <div class="header-right">
        <span class="file-label">A：{{ compareStore.documentA?.file_name }}</span>
        <span class="file-sep">vs</span>
        <span class="file-label">B：{{ compareStore.documentB?.file_name }}</span>
      </div>
    </header>

    <div class="panel-labels">
      <div class="panel-label-item">PDF 原文（文档 A）</div>
      <div class="panel-label-item">
        OCR 识别结果（文档 B）
        <span v-if="ocrLoading" class="ocr-loading-tip">加载中...</span>
      </div>
    </div>

    <main class="main-content">
      <!-- 左侧：文档 A PDF -->
      <div class="compare-panel left-panel" ref="leftPanelRef">
        <PDFViewer
          :pdf-url="pdfUrlA"
          :scale="scale"
          :highlights="compareStore.highlightsA"
          :active-block-id="activeBlockId"
          @scale-change="handleScaleChange"
          @click-block="handleBlockClickA"
          @scroll="handleLeftScroll"
        />
      </div>

      <!-- 右侧：文档 B OCR 识别结果 -->
      <div class="compare-panel right-panel" ref="rightPanelRef">
        <div v-if="ocrLoading" class="ocr-loading">OCR 结果加载中...</div>
        <div
          v-else-if="pageMap.size > 0"
          ref="ocrContainerRef"
          class="ocr-render-container"
        ></div>
        <div v-else class="structured-wrapper">
          <div
            v-for="block in compareStore.blocksB"
            :key="block.id || block.block_id"
            :data-block-id="block.id || block.block_id"
            :class="['block-item', getDiffClass(block), {
              active: activeBlockId === (block.id || block.block_id)
            }]"
            @click="handleBlockClickB(block.id || block.block_id)"
          >
            <div class="block-content">{{ block.content || block.text || `[${block.type}]` }}</div>
            <div v-if="getDiffLabel(block)" class="diff-badge" :class="getDiffClass(block)">
              {{ getDiffLabel(block) }}
            </div>
          </div>

          <div v-if="!compareStore.blocksB.length && !loading" class="empty-tip">
            暂无识别内容
          </div>
        </div>
      </div>
    </main>

    <footer class="legend">
      <span class="legend-item modified">■ 修改</span>
      <span class="legend-item added">■ 新增</span>
      <span class="legend-item deleted">■ 删除</span>
      <span class="legend-item need_review">■ 需核验</span>
    </footer>
  </div>
</template>

<style scoped>
.compare-container { display: flex; flex-direction: column; height: 100vh; background: #f0f2f5; }
.header { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background: white; border-bottom: 1px solid #e0e0e0; flex-shrink: 0; flex-wrap: wrap; gap: 8px; }
.header-left, .header-center, .header-right { display: flex; align-items: center; gap: 8px; }
.title { font-size: 15px; font-weight: 600; }
.diff-summary { display: flex; gap: 6px; }
.diff-counter { font-size: 14px; color: #555; white-space: nowrap; }
.file-label { font-size: 12px; color: #888; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-sep { font-size: 12px; color: #bbb; }

.panel-labels { display: flex; background: #fafafa; border-bottom: 1px solid #eee; flex-shrink: 0; }
.panel-label-item { flex: 1; padding: 6px 20px; font-size: 12px; color: #666; font-weight: 500; display: flex; align-items: center; gap: 8px; }
.panel-label-item:first-child { border-right: 1px solid #eee; }
.ocr-loading-tip { font-size: 11px; color: #999; }

.main-content { flex: 1; display: flex; overflow: hidden; }
.compare-panel { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.left-panel { border-right: 1px solid #ddd; }

.ocr-render-container { flex: 1; overflow-y: auto; padding: 10px; background: #f5f5f5; }
.ocr-loading { text-align: center; padding: 60px 20px; color: #666; font-size: 14px; }

.structured-wrapper { flex: 1; overflow-y: auto; padding: 20px; background: white; }
.block-item { margin-bottom: 10px; padding: 12px; border-radius: 6px; cursor: pointer; border: 1px solid #e8e8e8; transition: all 0.15s; position: relative; }
.block-item:hover { background: #fafafa; }
.block-item.active { outline: 2px solid #409eff; }
.block-item.modified { background: #FFF9C4; border-color: #f0c040; }
.block-item.added { background: #E8F5E9; border-color: #81c784; }
.block-item.deleted { background: #FFEBEE; border-color: #e57373; }
.block-item.need_review { background: #E3F2FD; border-color: #90caf9; }
.block-content { font-size: 14px; line-height: 1.7; white-space: pre-wrap; word-break: break-all; }
.diff-badge { position: absolute; top: 8px; right: 8px; padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; }
.diff-badge.modified { background: #f0a800; }
.diff-badge.added { background: #4caf50; }
.diff-badge.deleted { background: #f44336; }
.diff-badge.need_review { background: #2196f3; }

.empty-tip { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; }
.legend { display: flex; gap: 20px; padding: 8px 20px; background: white; border-top: 1px solid #eee; font-size: 12px; flex-shrink: 0; }
.legend-item { color: #666; }
.legend-item.modified { color: #f0a800; }
.legend-item.added { color: #4caf50; }
.legend-item.deleted { color: #f44336; }
.legend-item.need_review { color: #2196f3; }
</style>

<style>
/* Global styles for OCR elements inside Compare */
.ocr-page { position: relative; background: white; border: 1px solid #ccc; margin: 10px auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }
.ocr-element { position: absolute; overflow: hidden; }
.ocr-page .page-num { position: absolute; bottom: 10px; right: 20px; font-size: 12px; color: #999; }
.ocr-code {
  font-family: monospace !important;
  background: #f5f5f5 !important;
  white-space: pre-wrap !important;
  overflow: hidden !important;
  border-left: 3px solid #409eff !important;
}
</style>