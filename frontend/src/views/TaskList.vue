<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentStore } from '@/stores/documents'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const documentStore = useDocumentStore()
const authStore = useAuthStore()

const loading = ref(false)
let pollTimer = null

// 跨文件比对：选中的两个文档
const compareSelection = ref([])

const hasProcessingDocs = computed(() =>
  documentStore.documents.some(d => d.status === 'PENDING' || d.status === 'PROCESSING')
)

const doneDocs = computed(() => documentStore.documents.filter(d => d.status === 'DONE'))

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    if (!hasProcessingDocs.value) {
      stopPolling()
      return
    }
    try {
      await documentStore.fetchDocuments()
    } catch {
      // 静默失败
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await documentStore.fetchDocuments()
    if (hasProcessingDocs.value) startPolling()
  } catch {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => { stopPolling() })

function getStatusType(status) {
  return { PENDING: 'info', PROCESSING: 'warning', DONE: 'success', FAILED: 'danger' }[status] || 'info'
}

function getStatusText(status) {
  return { PENDING: '待处理', PROCESSING: '处理中', DONE: '已完成', FAILED: '失败' }[status] || status
}

function handleReview(doc) {
  router.push(`/review/${doc.id}`)
}

async function handleDelete(doc) {
  try {
    await ElMessageBox.confirm('确定要删除此文档吗？', '提示', { type: 'warning' })
    await documentStore.deleteDocument(doc.id)
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function handleUpload() {
  router.push('/upload')
}

// 跨文件比对：勾选逻辑
function toggleCompareSelect(doc) {
  const idx = compareSelection.value.findIndex(d => d.id === doc.id)
  if (idx >= 0) {
    compareSelection.value.splice(idx, 1)
  } else {
    if (compareSelection.value.length >= 2) {
      ElMessage.warning('最多选择两个文档进行比对')
      return
    }
    compareSelection.value.push(doc)
  }
}

function isSelected(doc) {
  return compareSelection.value.some(d => d.id === doc.id)
}

function handleCompare() {
  if (compareSelection.value.length !== 2) {
    ElMessage.warning('请选择两个已完成的文档')
    return
  }
  const [a, b] = compareSelection.value
  router.push(`/compare/${a.id}/${b.id}`)
}
</script>

<template>
  <div class="task-list-container">
    <header class="header">
      <h1>审计文档处理系统</h1>
      <div class="header-actions">
        <template v-if="compareSelection.length > 0">
          <span class="compare-hint">已选 {{ compareSelection.length }}/2 个文档</span>
          <el-button type="success" :disabled="compareSelection.length !== 2" @click="handleCompare">开始比对</el-button>
          <el-button @click="compareSelection = []">取消</el-button>
        </template>
        <template v-else>
          <el-button @click="compareSelection.push()" v-if="false" />
          <el-button type="primary" @click="handleUpload">上传文件</el-button>
          <el-button @click="handleLogout">退出</el-button>
        </template>
      </div>
    </header>

    <main class="content">
      <div v-if="doneDocs.length >= 2" class="compare-tip">
        提示：在"操作"列勾选两个已完成的文档，可进行跨文件比对
      </div>

      <el-table :data="documentStore.documents" v-loading="loading" style="width: 100%" stripe>
        <el-table-column prop="file_name" label="文件名" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_pages" label="页数" width="80" />
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300">
          <template #default="{ row }">
            <el-button v-if="row.status === 'DONE'" type="primary" size="small" @click="handleReview(row)">核验</el-button>
            <el-button v-if="row.status === 'DONE'" type="success" size="small" @click="router.push(`/review-new/${row.id}`)">新核验</el-button>
            <el-button
              v-if="row.status === 'DONE'"
              :type="isSelected(row) ? 'success' : ''"
              size="small"
              plain
              @click="toggleCompareSelect(row)"
            >{{ isSelected(row) ? '✓ 已选' : '选择比对' }}</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </main>
  </div>
</template>

<style scoped>
.task-list-container { min-height: 100vh; background: #f5f5f5; }
.header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.header h1 { margin: 0; font-size: 24px; color: #333; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.compare-hint { font-size: 14px; color: #409eff; }
.content { padding: 40px; max-width: 1200px; margin: 0 auto; }
.compare-tip { margin-bottom: 16px; padding: 10px 16px; background: #e8f4ff; border-radius: 6px; font-size: 13px; color: #409eff; border: 1px solid #b3d8ff; }
</style>
