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
let scrollSyncer = null

const pdfUrlA = computed(() => api.getDocumentFileUrl(docAId))
const pdfUrlB = computed(() => api.getDocumentFileUrl(docBId))

onMounted(async () => {
  compareStore.reset()
  loading.value = true
  try {
    await compareStore.loadDocuments(docAId, docBId)
    await compareStore.loadDiffs(docAId, docBId)
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
      <div class="panel-label-item">识别结果（文档 B）</div>
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

      <!-- 右侧：文档 B 识别结果 -->
      <div class="compare-panel right-panel" ref="rightPanelRef">
        <div class="structured-wrapper">
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
.panel-label-item { flex: 1; padding: 6px 20px; font-size: 12px; color: #666; font-weight: 500; }
.panel-label-item:first-child { border-right: 1px solid #eee; }

.main-content { flex: 1; display: flex; overflow: hidden; }
.compare-panel { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.left-panel { border-right: 1px solid #ddd; }

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
