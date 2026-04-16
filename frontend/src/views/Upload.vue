<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentStore } from '@/stores/documents'
import { ElMessage } from 'element-plus'

const router = useRouter()
const documentStore = useDocumentStore()

const fileList = ref([])
const loading = ref(false)
const uploadRef = ref(null)

const allowedTypes = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.docx', '.xlsx']

function handleExceed() {
  ElMessage.warning('只能上传一个文件')
}

function beforeUpload(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowedTypes.includes(ext)) {
    ElMessage.error('不支持的文件格式')
    return false
  }
  if (file.size > 500 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过500MB')
    return false
  }
  return true
}

async function handleUpload() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择文件')
    return
  }

  const file = fileList.value[0].raw
  loading.value = true

  try {
    await documentStore.uploadDocument(file)
    ElMessage.success('上传成功')
    router.push('/tasks')
  } catch (error) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  router.push('/tasks')
}
</script>

<template>
  <div class="upload-container">
    <header class="header">
      <h1>上传文件</h1>
    </header>

    <main class="content">
      <el-upload ref="uploadRef" v-model:file-list="fileList" class="upload-area" drag :auto-upload="false" :limit="1" :on-exceed="handleExceed" :before-upload="beforeUpload" action="#">
        <div class="upload-content">
          <div class="upload-icon">+</div>
          <div class="upload-text">拖拽文件到此处，或<span class="link">点击选择文件</span></div>
          <div class="upload-hint">支持格式：PDF / DOCX / XLSX / JPG / PNG / TIFF<br />单文件大小限制：500MB</div>
        </div>
      </el-upload>

      <div class="actions">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" :loading="loading" :disabled="fileList.length === 0" @click="handleUpload">开始处理</el-button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.upload-container { min-height: 100vh; background: #f5f5f5; }
.header { padding: 20px 40px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.header h1 { margin: 0; font-size: 24px; color: #333; }
.content { padding: 40px; max-width: 800px; margin: 0 auto; }
.upload-area { width: 100%; }
.upload-content { padding: 60px 0; text-align: center; }
.upload-icon { font-size: 48px; color: #409eff; margin-bottom: 20px; }
.upload-text { font-size: 16px; color: #666; margin-bottom: 10px; }
.upload-text .link { color: #409eff; cursor: pointer; }
.upload-hint { font-size: 14px; color: #999; }
.actions { margin-top: 30px; display: flex; justify-content: flex-end; gap: 10px; }
</style>
