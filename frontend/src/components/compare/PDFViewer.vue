<script setup>
import { ref, shallowRef, watch, onMounted, nextTick, computed } from 'vue'
import { CoordinateMapper } from '@/utils/CoordinateMapper'

// pdfjs 通过 index.html 的 <script type="module"> 加载，自动挂载到 globalThis.pdfjsLib
// 这样完全绕过 Vite 模块系统，不会出现多实例导致的私有字段访问报错
function getPdfjs() {
  const lib = window.pdfjsLib
  if (!lib) throw new Error('pdfjsLib 未加载，请检查 index.html 中的 script 标签')
  lib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'
  return lib
}

const props = defineProps({
  pdfUrl: String,
  scale: { type: Number, default: 1.0 },
  highlights: { type: Array, default: () => [] },
  activeBlockId: String
})
const emit = defineEmits(['scale-change', 'click-block', 'scroll'])

const container = ref(null)
const canvasContainer = ref(null)
const pages = shallowRef([])
const mappers = ref(new Map())
const pdfDoc = shallowRef(null)
const loadError = ref(null)
const pdfLoaded = ref(false)

async function loadPDF() {
  try {
    loadError.value = null
    const url = props.pdfUrl
    console.log('[PDFViewer] Loading PDF from:', url)

    const pdfjs = getPdfjs()
    const loadingTask = pdfjs.getDocument(url)
    pdfDoc.value = await loadingTask.promise
    console.log('[PDFViewer] PDF loaded, pages:', pdfDoc.value.numPages)

    for (let i = 1; i <= pdfDoc.value.numPages; i++) {
      const page = await pdfDoc.value.getPage(i)
      pages.value = [...pages.value, { num: i, page }]
      mappers.value.set(i, new CoordinateMapper(page, props.scale))

      await nextTick()
      await nextTick()

      const canvas = canvasContainer.value?.querySelector(`#page-${i}`)
      if (canvas) {
        const viewport = page.getViewport({ scale: props.scale })
        canvas.width = viewport.width
        canvas.height = viewport.height
        await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise
        console.log(`[PDFViewer] Page ${i} rendered successfully`)
      }
    }
    pdfLoaded.value = true
  } catch (e) {
    console.error('[PDFViewer] Load error:', e)
    loadError.value = e.message
  }
}

const visibleHighlights = computed(() => {
  const result = []
  for (const h of props.highlights) {
    const mapper = mappers.value.get(h.page)
    if (mapper) result.push({ ...h, ...mapper.transform(h.bbox) })
  }
  return result
})

function handleScroll() { emit('scroll', props.activeBlockId) }

watch(() => props.scale, async () => {
  if (!pdfDoc.value) return
  for (const { page, num } of pages.value) {
    mappers.value.set(num, new CoordinateMapper(page, props.scale))
  }
  await nextTick()
  for (let i = 1; i <= pdfDoc.value.numPages; i++) {
    const pageInfo = pages.value.find(p => p.num === i)
    if (pageInfo) {
      const canvas = canvasContainer.value?.querySelector(`#page-${i}`)
      if (canvas) {
        const viewport = pageInfo.page.getViewport({ scale: props.scale })
        canvas.width = viewport.width
        canvas.height = viewport.height
        await pageInfo.page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise
      }
    }
  }
})

onMounted(async () => {
  if (props.pdfUrl) {
    await loadPDF()
  }
})
</script>

<template>
  <div class="pdf-viewer" ref="container" @scroll="handleScroll">
    <div class="controls">
      <el-button-group>
        <el-button @click="emit('scale-change', props.scale / 1.2)">-</el-button>
        <el-button disabled>{{ Math.round(props.scale * 100) }}%</el-button>
        <el-button @click="emit('scale-change', props.scale * 1.2)">+</el-button>
      </el-button-group>
    </div>
    <div v-if="loadError" class="load-error">PDF加载失败: {{ loadError }}</div>
    <div v-else-if="!pdfLoaded" class="loading-tip">正在加载PDF...</div>
    <div class="canvas-container" ref="canvasContainer">
      <canvas
        v-for="pageInfo in pages"
        :key="pageInfo.num"
        :id="'page-' + pageInfo.num"
        class="pdf-page"
      />
      <svg class="highlight-overlay" v-if="pages.length > 0">
        <rect
          v-for="h in visibleHighlights"
          :key="h.id"
          :x="h.left"
          :y="h.top"
          :width="h.width"
          :height="h.height"
          :class="['highlight', h.type]"
          @click="emit('click-block', h.blockId)"
        />
      </svg>
    </div>
  </div>
</template>

<style scoped>
.pdf-viewer { height: 100%; overflow: auto; background: #525659; }
.controls { position: sticky; top: 0; z-index: 100; padding: 10px; background: rgba(0,0,0,0.5); }
.canvas-container { position: relative; display: flex; flex-direction: column; align-items: center; padding: 20px; }
.pdf-page { border: 1px solid #ccc; margin-bottom: 10px; display: block; }
.highlight-overlay { position: absolute; top: 20px; left: 0; pointer-events: none; }
.highlight { fill-opacity: 0.3; stroke: #ff6600; stroke-width: 2; cursor: pointer; }
.highlight.modified { fill: #FFF9C4; }
.highlight.added { fill: #E8F5E9; }
.highlight.deleted { fill: #FFEBEE; }
.highlight.need_review { fill: #E3F2FD; }
.load-error { text-align: center; padding: 40px; color: #ff6b6b; font-size: 14px; }
.loading-tip { text-align: center; padding: 40px; color: #999; font-size: 14px; }
</style>
