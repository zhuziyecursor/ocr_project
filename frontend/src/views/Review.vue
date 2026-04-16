<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDocumentStore } from '@/stores/documents'
import { useCompareStore } from '@/stores/compare'
import { ElMessage, ElMessageBox } from 'element-plus'
import PDFViewer from '@/components/compare/PDFViewer.vue'
import StructuredViewer from '@/components/compare/StructuredViewer.vue'
import { ScrollSyncer } from '@/utils/ScrollSyncer'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const documentStore = useDocumentStore()
const compareStore = useCompareStore()

const docId = route.params.docId
const scale = ref(1.0)
const activeBlockId = ref(null)
const pdfPanelRef = ref(null)
const structuredPanelRef = ref(null)
let scrollSyncer = null

// 编辑模式
const editingBlock = ref(null)
const editContent = ref('')

// 历史记录
const historyVisible = ref(false)
const historyList = ref([])
const historyLoading = ref(false)

const pdfUrl = computed(() => api.getDocumentFileUrl(docId))

onMounted(async () => {
  compareStore.reset()
  try {
    await documentStore.fetchDocument(docId)
    await compareStore.loadDocument(docId)
  } catch {
    ElMessage.error('加载文档失败')
  }
})

// 在 DOM 渲染后初始化滚动同步器
watch([pdfPanelRef, structuredPanelRef], ([pdfEl, structEl]) => {
  if (pdfEl && structEl) {
    scrollSyncer?.destroy()
    scrollSyncer = new ScrollSyncer(pdfEl, structEl)
  }
})

onUnmounted(() => { scrollSyncer?.destroy() })

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
  if (structuredPanelRef.value) {
    const el = structuredPanelRef.value.querySelector(`[data-block-id="${blockId}"]`)
    el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
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
      <div class="compare-panel right-panel" ref="structuredPanelRef">
        <div class="panel-label">识别结果</div>
        <div class="structured-wrapper">
          <StructuredViewer
            :blocks="compareStore.blocksA"
            :active-block-id="activeBlockId"
            @click-block="handleBlockClick"
            @dblclick-block="handleDblClick"
          />

          <!-- 编辑模式浮层 -->
          <template v-if="editingBlock">
            <div class="edit-overlay" @click.self="cancelEdit">
              <div class="edit-dialog">
                <div class="edit-header">编辑内容（第 {{ editingBlock.pageNo }} 页）</div>
                <textarea
                  v-model="editContent"
                  class="edit-textarea"
                  autofocus
                  @keydown="handleEditKeydown"
                />
                <div class="edit-actions">
                  <el-button @click="cancelEdit">取消 (Esc)</el-button>
                  <el-button type="primary" @click="saveEdit">保存 (Enter)</el-button>
                </div>
              </div>
            </div>
          </template>

          <div v-if="!compareStore.blocksA.length" class="empty-tip">
            <span v-if="documentStore.currentDocument?.status !== 'DONE'">
              文档尚未处理完成（状态：{{ documentStore.currentDocument?.status }}）
            </span>
            <span v-else>暂无识别内容</span>
          </div>
        </div>
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
.panel-label { position: absolute; top: 10px; left: 10px; z-index: 10; background: rgba(0,0,0,0.5); color: white; padding: 3px 10px; border-radius: 4px; font-size: 12px; pointer-events: none; }

/* 右侧结构化内容 */
.structured-wrapper { flex: 1; overflow-y: auto; padding: 20px; background: white; position: relative; }
.empty-tip { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; }

/* 编辑模式浮层 */
.edit-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.edit-dialog { background: white; padding: 20px; border-radius: 8px; width: 90%; max-width: 600px; }
.edit-header { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #333; }
.edit-textarea { width: 100%; min-height: 120px; font-size: 14px; line-height: 1.7; border: 1px solid #409eff; border-radius: 4px; padding: 8px; resize: vertical; box-sizing: border-box; outline: none; }
.edit-actions { margin-top: 12px; display: flex; justify-content: flex-end; gap: 10px; }

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
</style>