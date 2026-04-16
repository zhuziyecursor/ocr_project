import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default {
  login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return apiClient.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  register(userData) {
    return apiClient.post('/auth/register', userData)
  },
  uploadDocument(file) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  getDocuments(skip = 0, limit = 100) {
    return apiClient.get(`/documents/?skip=${skip}&limit=${limit}`)
  },
  getDocument(docId) {
    return apiClient.get(`/documents/${docId}`)
  },
  getDocumentStatus(docId) {
    return apiClient.get(`/documents/${docId}/status`)
  },
  deleteDocument(docId) {
    return apiClient.delete(`/documents/${docId}`)
  },
  createReviewRecord(recordData) {
    return apiClient.post('/reviews/', recordData)
  },
  getDocumentReviews(docId) {
    return apiClient.get(`/reviews/document/${docId}`)
  },
  updateReviewRecord(recordId, recordData) {
    return apiClient.put(`/reviews/${recordId}`, recordData)
  },

  // 识别结果
  getDocumentResult(docId) {
    return apiClient.get(`/documents/${docId}/result`)
  },

  // 跨文件比对
  compareDocuments(docAId, docBId) {
    return apiClient.post('/documents/compare', { doc_a_id: docAId, doc_b_id: docBId })
  },

  // Markdown 导出（blob 下载）
  exportDocument(docId) {
    return apiClient.get(`/documents/${docId}/export`, { responseType: 'blob' })
  },

  // 获取文档原始文件（用于 PDFViewer）
  getDocumentFileUrl(docId) {
    const token = localStorage.getItem('access_token')
    return `/api/documents/${docId}/file${token ? '?token=' + token : ''}`
  }
}
