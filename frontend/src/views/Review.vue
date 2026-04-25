<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDocumentStore } from '@/stores/documents'
import { useCompareStore } from '@/stores/compare'
import { ElMessage, ElMessageBox } from 'element-plus'
import PDFViewer from '@/components/compare/PDFViewer.vue'
import { ScrollSyncer } from '@/utils/ScrollSyncer'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const documentStore = useDocumentStore()
const compareStore = useCompareStore()

const docId = route.params.docId
const scale = ref(1.5)
const activeBlockId = ref(null)
const pdfPanelRef = ref(null)
const ocrPanelRef = ref(null)
const ocrContainerRef = ref(null)
let scrollSyncer = null

// OCR 渲染相关
const ocrLoading = ref(false)

// 编辑模式
const editingBlock = ref(null)
const editContent = ref('')

// 历史记录
const historyVisible = ref(false)
const historyList = ref([])
const historyLoading = ref(false)

// AI 优化排版
const optimizeLoading = ref(false)
const optimizedContent = ref('')
const optimizedVisible = ref(false)

const pdfUrl = computed(() => api.getDocumentFileUrl(docId))

// 根据 source 字段获取图片 URL
function getImageUrl(source) {
  if (!source) return null
  // source 格式: "images/xxx.png"
  const imageName = source.replace('images/', '')
  return `/api/documents/${docId}/images/${imageName}`
}

onMounted(async () => {
  compareStore.reset()
  try {
    await documentStore.fetchDocument(docId)
    await compareStore.loadDocument(docId)
    // 等待 DOM 更新后再渲染
    await nextTick()
    renderOcrResult()
  } catch {
    ElMessage.error('加载文档失败')
  }
})

// 在 DOM 渲染后初始化滚动同步器
watch([pdfPanelRef, ocrPanelRef], ([pdfEl, ocrEl]) => {
  if (pdfEl && ocrEl) {
    scrollSyncer?.destroy()
    scrollSyncer = new ScrollSyncer(pdfEl, ocrEl)
  }
})

onUnmounted(() => { scrollSyncer?.destroy() })

// ========== OCR 渲染相关（参考 ocr-local-test.html）==========

// 从 bounding box 获取坐标
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
    // BOTTOMLEFT 坐标系：y 从下往上增大
    // Docling 格式：t > b（t 是顶部到底边的距离，更大）
    // 旧格式 kids：t < b（t 是 y 较小值，b 是 y 较大值）
    // 统一用较大值计算 cssTop（代表元素顶部到页面顶部的 CSS 距离）
    const top_y = Math.max(t, b)
    cssTop = (pageHeight - top_y) * scale
    height = Math.abs(t - b) * scale
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

function getFontSize(el) {
  if (el['font size']) return el['font size']
  if (el.formatting && el.formatting.length) {
    return el.formatting[0].size || 12
  }
  return 12
}

function renderElement(el, pageHeight, scale = 1) {
  const type = el.type || el.label || 'text'

  // Docling 格式从 prov 获取 bbox
  let bbox = null
  if (el.prov && el.prov.length > 0 && el.prov[0].bbox) {
    bbox = {
      l: el.prov[0].bbox.l,
      t: el.prov[0].bbox.t,
      r: el.prov[0].bbox.r,
      b: el.prov[0].bbox.b,
      coord_origin: el.prov[0].bbox.coord_origin
    }
  } else if (el.bbox) {
    bbox = getBboxFromArray(el.bbox)
  } else if (el['bounding box']) {
    bbox = getBboxFromArray(el['bounding box'])
  }

  const coords = transformCoords(bbox, pageHeight, scale)

  if (!coords || coords.width <= 0 || coords.height <= 0) {
    return null
  }

  const div = document.createElement('div')
  div.className = `ocr-element ocr-${type.toLowerCase()}`
  div.style.cssText = `position:absolute;left:${coords.left}px;top:${coords.top}px;width:${coords.width}px;height:${coords.height}px;`

  const text = el.text || el.content || ''
  const fontSize = getFontSize(el) * scale

  switch (type.toLowerCase()) {
    case 'heading':
    case 'title':
    case 'section_header':
      div.textContent = text
      div.style.fontSize = `${fontSize}px`
      div.style.fontFamily = '"PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif'
      div.style.fontWeight = 'bold'
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      // 表格区域的 heading 添加特殊样式
      if (el._tableArea) {
        div.style.borderLeft = '3px solid #409eff'
        div.style.paddingLeft = '6px'
        div.style.background = 'rgba(64, 158, 255, 0.05)'
      }
      break
    case 'image':
    case 'picture':
      // 有 source 的 image 才渲染图片
      if (el.source) {
        const img = document.createElement('img')
        img.src = getImageUrl(el.source)
        img.style.maxWidth = '100%'
        img.style.maxHeight = '100%'
        img.style.objectFit = 'contain'
        div.appendChild(img)
        div.style.background = 'transparent'
      } else {
        // 没有 source 的 image 不渲染（可能是 OpenDataLoader 误判表格为 image）
        // 让同区域的 paragraph 内容正常显示
        div.style.display = 'none'  // 隐藏元素但不删除，保持坐标计算正确
      }
      break
    case 'table':
      // 渲染表格内容
      div.style.background = 'rgba(0,0,0,0.02)'
      div.style.display = 'block'
      div.style.overflow = 'hidden'
      div.style.fontSize = `${fontSize}px`
      div.innerHTML = renderTableContent(el, pageHeight, scale)
      break
    default:
      div.textContent = text
      div.style.fontSize = `${fontSize}px`
      div.style.fontFamily = '"PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif'
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      // 表格区域的内容添加轻微背景和左边框
      if (el._tableArea) {
        div.style.borderLeft = '3px solid #409eff'
        div.style.paddingLeft = '6px'
        div.style.background = 'rgba(64, 158, 255, 0.05)'
      }
  }

  return div
}

/**
 * 渲染表格内容（递归渲染 rows/cells 中的文本）
 */
function renderTableContent(tableEl, pageHeight, scale) {
  const rows = tableEl.rows || []
  if (!rows.length) return '[Table]'

  let html = '<table style="width:100%;border-collapse:collapse;font-size:inherit;">'

  for (const row of rows) {
    const cells = row.cells || []
    html += '<tr>'
    for (const cell of cells) {
      const cellBbox = cell['bounding box'] || cell.bbox
      const rowSpan = cell.row_span || 1
      const colSpan = cell.column_span || 1
      let cellWidth = 'auto'
      if (cellBbox && cellBbox.length >= 4) {
        // 计算单元格宽度
        const cellW = (cellBbox[2] - cellBbox[0]) * scale
        cellWidth = `${cellW}px`
      }
      // 递归获取单元格内的文本内容
      const cellText = extractCellText(cell)
      html += `<td rowspan="${rowSpan}" colspan="${colSpan}" style="border:1px solid #ddd;padding:4px 6px;vertical-align:top;width:${cellWidth};box-sizing:border-box;">${cellText}</td>`
    }
    html += '</tr>'
  }

  html += '</table>'
  return html
}

/**
 * 递归提取单元格内的文本内容
 */
function extractCellText(cell) {
  // 如果有嵌套的 kids，遍历获取文本
  const kids = cell.kids || []
  if (kids.length > 0) {
    const texts = []
    for (const kid of kids) {
      if (kid.type === 'paragraph' || kid.type === 'heading') {
        const text = kid.text || kid.content || ''
        if (text.trim()) texts.push(text.trim())
      } else if (kid.type === 'table row') {
        // 嵌套的 table row
        texts.push(extractCellText(kid))
      }
    }
    return texts.join('<br>')
  }
  // 直接文本
  const text = cell.text || cell.content || ''
  return text.trim()
}

function renderOcrResult() {
  const container = ocrContainerRef.value
  if (!container) return

  container.innerHTML = ''

  // 只使用从数据库获取的数据
  const result = compareStore.resultA
  if (!result) return
  renderFromResult(result, container)
}

function renderFromData(data, container) {
  // OpenDataLoader 旧格式
  const kids = data.kids || []

  // 找出与无 source 的 image 区域重叠的 paragraph，标记为表格区域
  // 只比较同一 page 内的元素
  const pageImages = new Map()
  for (const img of kids.filter(k => k.type === 'image' && !k.source)) {
    const pageNo = img['page number']
    if (!pageImages.has(pageNo)) pageImages.set(pageNo, [])
    pageImages.get(pageNo).push(img)
  }

  const markTableArea = (el) => {
    if (el._tableArea) return
    const pageNo = el['page number']
    if (!pageNo) return
    const imagesOnPage = pageImages.get(pageNo) || []
    if (imagesOnPage.length === 0) return

    const bbox = el['bounding box'] || el.bbox
    if (!bbox) return

    for (const img of imagesOnPage) {
      const imgBbox = img['bounding box'] || img.bbox
      if (!imgBbox) continue

      // X 方向重叠
      const xOverlap = !(bbox[2] <= imgBbox[0] || bbox[0] >= imgBbox[2])
      // Y 方向重叠：BOTTOMLEFT 坐标系
      const textTop_y = Math.max(bbox[1], bbox[3])
      const textBottom_y = Math.min(bbox[1], bbox[3])
      const imgTop_y = Math.max(imgBbox[1], imgBbox[3])
      const imgBottom_y = Math.min(imgBbox[1], imgBbox[3])
      const yOverlap = !(textBottom_y > imgTop_y || textTop_y < imgBottom_y)

      if (xOverlap && yOverlap) {
        el._tableArea = true
        break
      }
    }
  }
  kids.filter(k => k.type === 'paragraph' || k.type === 'heading').forEach(markTableArea)

  // 按页码分组
  const pageMap = new Map()

  const addToPage = (el) => {
    const pageNo = el['page number'] || 1
    if (!pageMap.has(pageNo)) pageMap.set(pageNo, [])
    pageMap.get(pageNo).push(el)
  }

  kids.forEach(addToPage)

  // 默认页面尺寸 A4
  const defaultWidth = 595
  const defaultHeight = 842

  // 渲染每一页
  for (const [pageNum, elements] of pageMap) {
    const pageDiv = document.createElement('div')
    pageDiv.className = 'ocr-page'
    pageDiv.style.width = `${defaultWidth}px`
    pageDiv.style.height = `${defaultHeight}px`

    for (const el of elements) {
      const elDiv = renderElementFromOldFormat(el, defaultHeight)
      if (elDiv) pageDiv.appendChild(elDiv)
    }

    const pageNumDiv = document.createElement('div')
    pageNumDiv.className = 'page-num'
    pageNumDiv.textContent = `Page ${pageNum}`
    pageDiv.appendChild(pageNumDiv)

    container.appendChild(pageDiv)
  }
}

function renderFromResult(result, container) {
  // 检测数据格式
  let texts = [], tables = [], pictures = []

  if (result.document && result.document.json_content) {
    // Docling 格式
    const jc = result.document.json_content
    texts = jc.texts || []
    tables = jc.tables || []
    pictures = jc.pictures || []
  } else if (result.kids) {
    // OpenDataLoader 旧格式
    texts = result.kids.filter(k => k.type === 'paragraph' || k.type === 'heading')
    tables = result.kids.filter(k => k.type === 'table')
    pictures = result.kids.filter(k => k.type === 'image')
  } else if (result.texts) {
    texts = result.texts || []
    tables = result.tables || []
    pictures = result.pictures || []
  }

  // 找出与无 source 的 image 区域重叠的 paragraph，标记为表格区域
  // 只比较同一 page 内的元素
  const pageImages = new Map()
  for (const img of (result.kids || []).filter(k => k.type === 'image' && !k.source)) {
    const pageNo = img['page number']
    if (!pageImages.has(pageNo)) pageImages.set(pageNo, [])
    pageImages.get(pageNo).push(img)
  }

  const markTableArea = (el) => {
    if (el._tableArea) return
    const pageNo = el.prov?.[0]?.page_no || el['page number']
    if (!pageNo) return
    const imagesOnPage = pageImages.get(pageNo) || []
    if (imagesOnPage.length === 0) return

    const bbox = el.bbox || el['bounding box'] || el.prov?.[0]?.bbox
    if (!bbox) return

    for (const img of imagesOnPage) {
      const imgBbox = img.bbox || img['bounding box']
      if (!imgBbox) continue

      // X 方向重叠（直接比较）
      const xOverlap = !(bbox[2] <= imgBbox[0] || bbox[0] >= imgBbox[2])
      // Y 方向重叠：BOTTOMLEFT 坐标系
      const textTop_y = Math.max(bbox[1], bbox[3])
      const textBottom_y = Math.min(bbox[1], bbox[3])
      const imgTop_y = Math.max(imgBbox[1], imgBbox[3])
      const imgBottom_y = Math.min(imgBbox[1], imgBbox[3])
      const yOverlap = !(textBottom_y > imgTop_y || textTop_y < imgBottom_y)

      if (xOverlap && yOverlap) {
        el._tableArea = true
        break
      }
    }
  }
  texts.forEach(markTableArea)

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

  // 默认页面尺寸 A4
  const defaultWidth = 595
  const defaultHeight = 842

  // 渲染每一页
  for (const [pageNum, elements] of pageMap) {
    const pageDiv = document.createElement('div')
    pageDiv.className = 'ocr-page'
    pageDiv.style.width = `${defaultWidth}px`
    pageDiv.style.height = `${defaultHeight}px`

    for (const el of elements) {
      const elDiv = renderElement(el, defaultHeight)
      if (elDiv) pageDiv.appendChild(elDiv)
    }

    const pageNumDiv = document.createElement('div')
    pageNumDiv.className = 'page-num'
    pageNumDiv.textContent = `Page ${pageNum}`
    pageDiv.appendChild(pageNumDiv)

    container.appendChild(pageDiv)
  }
}

function renderElementFromOldFormat(el, pageHeight, scale = 1) {
  const type = el.type || 'text'
  const bbox = getBboxFromArray(el['bounding box'] || el.bbox)
  const coords = transformCoords(bbox, pageHeight, scale)

  if (!coords || coords.width <= 0 || coords.height <= 0) {
    return null
  }

  const div = document.createElement('div')
  div.className = `ocr-element ocr-${type.toLowerCase()}`
  div.style.cssText = `position:absolute;left:${coords.left}px;top:${coords.top}px;width:${coords.width}px;height:${coords.height}px;`

  const text = el.content || el.text || ''
  const fontSize = (el['font size'] || 12) * scale

  switch (type.toLowerCase()) {
    case 'heading':
      div.textContent = text
      div.style.fontSize = `${fontSize}px`
      div.style.fontFamily = '"PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif'
      div.style.fontWeight = 'bold'
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      if (el._tableArea) {
        div.style.borderLeft = '3px solid #409eff'
        div.style.paddingLeft = '6px'
        div.style.background = 'rgba(64, 158, 255, 0.05)'
      }
      break
    case 'image':
      // 有 source 的 image 才渲染图片
      if (el.source) {
        const img = document.createElement('img')
        img.src = getImageUrl(el.source)
        img.style.maxWidth = '100%'
        img.style.maxHeight = '100%'
        img.style.objectFit = 'contain'
        div.appendChild(img)
        div.style.background = 'transparent'
      } else {
        // 没有 source 的 image 不渲染（可能是 OpenDataLoader 误判表格为 image）
        // 让同区域的 paragraph 内容正常显示
        div.style.display = 'none'  // 隐藏元素但不删除，保持坐标计算正确
      }
      break
    case 'table':
      div.innerHTML = '[Table]'
      div.style.background = 'rgba(0,0,0,0.02)'
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      div.style.justifyContent = 'center'
      break
    default:
      div.textContent = text
      div.style.fontSize = `${fontSize}px`
      div.style.fontFamily = '"PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif'
      div.style.display = 'flex'
      div.style.alignItems = 'center'
      if (el._tableArea) {
        div.style.borderLeft = '3px solid #409eff'
        div.style.paddingLeft = '6px'
        div.style.background = 'rgba(64, 158, 255, 0.05)'
      }
  }

  return div
}

function handleScaleChange(newScale) {
  scale.value = newScale
}

function handlePdfScroll() {
  scrollSyncer?.handleSourceScroll(activeBlockId.value)
}

function handleBlockClick(blockId) {
  activeBlockId.value = blockId
  compareStore.setActiveBlock(blockId)
}

function handlePdfBlockClick(blockId) {
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

// 双击进入编辑模式
function handleDblClick(block) {
  editingBlock.value = {
    id: block.id || block.block_id,
    originalContent: block.content || block.text || '',
    pageNo: block._page,
  }
  editContent.value = editingBlock.value.originalContent
}

async function handleEditKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    await saveEdit()
  } else if (e.key === 'Escape') {
    cancelEdit()
  }
}

async function saveEdit() {
  if (!editingBlock.value) return
  const { id, originalContent, pageNo } = editingBlock.value
  try {
    await compareStore.markReviewed(id, originalContent, editContent.value, pageNo)
    const block = compareStore.blocksA.find(b => (b.id || b.block_id) === id)
    if (block) {
      block.content = editContent.value
      block.text = editContent.value
    }
    editingBlock.value = null
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败')
  }
}

function cancelEdit() {
  editingBlock.value = null
  editContent.value = ''
}

// 导出 Markdown
async function handleExport() {
  const unreviewedCount = compareStore.blocksA.filter(b => b.need_review).length
  if (unreviewedCount > 0) {
    try {
      await ElMessageBox.confirm(
        `当前有 ${unreviewedCount} 处内容未核验，导出文件头部将包含警告。确认导出？`,
        '未核验内容提醒',
        { type: 'warning', confirmButtonText: '确认导出', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
  }
  try {
    const blob = await api.exportDocument(docId)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const docName = documentStore.currentDocument?.file_name?.replace(/\.[^.]+$/, '') || 'export'
    a.download = `${docName}_识别结果.md`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

// 查看历史记录
async function showHistory() {
  historyVisible.value = true
  historyLoading.value = true
  try {
    const data = await api.getDocumentReviews(docId)
    historyList.value = data.items || data || []
  } catch {
    ElMessage.error('获取历史记录失败')
    historyList.value = []
  } finally {
    historyLoading.value = false
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}

// AI 优化排版
async function handleOptimize() {
  const result = compareStore.resultA
  console.log('resultA:', result)
  if (!result) {
    ElMessage.warning('无识别结果')
    return
  }

  // 提取所有文本内容
  let ocrText = ''
  if (result.kids) {
    // kids 格式
    ocrText = result.kids
      .filter(k => k.type === 'paragraph' || k.type === 'heading')
      .map(k => k.content || k.text || '')
      .filter(t => t.trim())
      .join('\n\n')
  } else if (result.document?.json_content?.texts) {
    // Docling 格式
    ocrText = result.document.json_content.texts
      .map(t => t.text || '')
      .filter(t => t.trim())
      .join('\n\n')
  }

  console.log('ocrText length:', ocrText.length, 'content:', ocrText.substring(0, 200))

  if (!ocrText.trim()) {
    ElMessage.warning('无文本内容可优化')
    return
  }

  optimizeLoading.value = true
  try {
    const res = await api.optimizeLayout(ocrText)
    console.log('optimize result:', res)
    if (res.success) {
      optimizedContent.value = res.optimized_content
      optimizedVisible.value = true
      ElMessage.success('优化完成')
    } else {
      ElMessage.error('优化失败: ' + res.error)
    }
  } catch (e) {
    console.error('optimize error:', e)
    ElMessage.error('调用优化接口失败')
  } finally {
    optimizeLoading.value = false
  }
}

const diffCount = computed(() => compareStore.highlightsReview.length)
const reviewedCount = computed(() => compareStore.reviewedDiffs.length)
</script>

<template>
  <div class="review-container">
    <header class="header">
      <div class="header-left">
        <el-button @click="router.push('/tasks')">返回</el-button>
        <span class="doc-name">{{ documentStore.currentDocument?.file_name }}</span>
      </div>
      <div class="header-center">
        <el-button :disabled="compareStore.currentDiffIndex === 0" @click="handlePrevDiff">上一处</el-button>
        <span class="diff-counter">需核验: {{ diffCount }} &nbsp;已核: {{ reviewedCount }}</span>
        <el-button :disabled="compareStore.currentDiffIndex >= diffCount - 1" @click="handleNextDiff">下一处</el-button>
      </div>
      <div class="header-right">
        <el-button @click="showHistory">历史记录</el-button>
        <el-button type="primary" @click="handleExport">导出 Markdown</el-button>
      </div>
    </header>

    <main class="main-content">
      <!-- 左侧：PDF 原文 -->
      <div class="compare-panel left-panel" ref="pdfPanelRef">
        <div class="panel-label">PDF 原文</div>
        <PDFViewer
          :pdf-url="pdfUrl"
          :scale="scale"
          :highlights="compareStore.highlightsReview"
          :active-block-id="activeBlockId"
          @scale-change="handleScaleChange"
          @click-block="handlePdfBlockClick"
          @scroll="handlePdfScroll"
        />
      </div>

      <!-- 右侧：识别结果 -->
      <div class="compare-panel right-panel" ref="ocrPanelRef">
        <div class="panel-header">
          <span class="panel-label">识别结果</span>
          <el-button size="small" :loading="optimizeLoading" @click="handleOptimize">
            AI 优化排版
          </el-button>
        </div>
        <div ref="ocrContainerRef" class="ocr-render-container"></div>
      </div>
    </main>

    <!-- 历史记录抽屉 -->
    <el-drawer v-model="historyVisible" title="修改历史记录" size="400px" direction="rtl">
      <div v-loading="historyLoading">
        <div v-if="historyList.length === 0 && !historyLoading" class="history-empty">
          暂无修改记录
        </div>
        <div v-else class="history-list">
          <div v-for="item in historyList" :key="item.id" class="history-item">
            <div class="history-meta">
              <span class="history-time">{{ formatTime(item.created_at || item.timestamp) }}</span>
              <span v-if="item.operator || item.user" class="history-user">{{ item.operator || item.user }}</span>
            </div>
            <div class="history-content">
              <div class="history-label">原文：</div>
              <div class="history-original">{{ item.original_content || item.originalContent }}</div>
            </div>
            <div class="history-content">
              <div class="history-label">修改后：</div>
              <div class="history-modified">{{ item.modified_content || item.modifiedContent }}</div>
            </div>
            <div v-if="item.page_no || item.pageNo" class="history-page">
              第 {{ item.page_no || item.pageNo }} 页
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- AI 优化结果抽屉 -->
    <el-drawer v-model="optimizedVisible" title="AI 优化排版结果" size="60%" direction="rtl">
      <div class="optimized-content" v-loading="optimizeLoading">
        <pre v-if="optimizedContent">{{ optimizedContent }}</pre>
        <div v-else-if="!optimizeLoading" class="optimized-empty">暂无优化结果</div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.review-container { display: flex; flex-direction: column; height: 100vh; background: #f0f2f5; }
.header { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background: white; border-bottom: 1px solid #e0e0e0; flex-shrink: 0; }
.header-left, .header-center, .header-right { display: flex; align-items: center; gap: 10px; }
.doc-name { font-size: 15px; font-weight: 500; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.diff-counter { font-size: 14px; color: #555; white-space: nowrap; }
.main-content { flex: 1; display: flex; overflow: hidden; }
.compare-panel { flex: 1; overflow: hidden; position: relative; display: flex; flex-direction: column; }
.left-panel { border-right: 1px solid #ddd; }
.panel-label { background: rgba(0,0,0,0.5); color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; }
.panel-header { position: absolute; top: 10px; left: 10px; right: 10px; z-index: 10; display: flex; justify-content: space-between; align-items: center; }

/* 右侧结构化内容 */
.structured-wrapper { flex: 1; overflow-y: auto; padding: 20px; background: white; position: relative; }
.empty-tip { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; }

/* 编辑模式浮层 */
.edit-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.edit-dialog { background: white; padding: 20px; border-radius: 8px; width: 90%; max-width: 600px; }
.edit-header { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #333; }
.edit-textarea { width: 100%; min-height: 120px; font-size: 14px; line-height: 1.7; border: 1px solid #409eff; border-radius: 4px; padding: 8px; resize: vertical; box-sizing: border-box; outline: none; }
.edit-actions { margin-top: 12px; display: flex; justify-content: flex-end; gap: 10px; }

/* OCR 渲染样式 */
.ocr-render-container { flex: 1; overflow-y: auto; padding: 10px; background: #f5f5f5; }

/* 历史记录 */
.history-empty { text-align: center; padding: 40px; color: #999; font-size: 14px; }
.history-list { display: flex; flex-direction: column; gap: 16px; }
.history-item { padding: 12px; border: 1px solid #e8e8e8; border-radius: 6px; background: #fafafa; }
.history-meta { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: #666; }
.history-user { color: #409eff; }
.history-content { margin-bottom: 8px; }
.history-label { font-size: 12px; color: #888; margin-bottom: 4px; }
.history-original { font-size: 13px; color: #666; background: #f5f5f5; padding: 6px 8px; border-radius: 4px; text-decoration: line-through; }
.history-modified { font-size: 13px; color: #333; background: #e8f5e9; padding: 6px 8px; border-radius: 4px; }
.history-page { font-size: 11px; color: #999; margin-top: 4px; text-align: right; }

/* AI 优化排版 */
.optimized-content { padding: 16px; height: 100%; overflow-y: auto; }
.optimized-content pre { white-space: pre-wrap; word-break: break-word; font-size: 14px; line-height: 1.8; }
.optimized-empty { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; }
</style>

<style>
/* Global styles for OCR elements */
.ocr-page { position: relative; background: white; border: 1px solid #ccc; margin: 10px auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }
.ocr-element { position: absolute; overflow: visible; }
.ocr-page .page-num { position: absolute; bottom: 10px; right: 20px; font-size: 12px; color: #999; }
</style>