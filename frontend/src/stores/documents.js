import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useDocumentStore = defineStore('documents', () => {
  const documents = ref([])
  const currentDocument = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchDocuments() {
    loading.value = true
    error.value = null
    try {
      const response = await api.getDocuments()
      documents.value = response.items
      return response
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchDocument(docId) {
    loading.value = true
    error.value = null
    try {
      currentDocument.value = await api.getDocument(docId)
      return currentDocument.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file) {
    loading.value = true
    error.value = null
    try {
      const result = await api.uploadDocument(file)
      documents.value.unshift(result)
      return result
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteDocument(docId) {
    try {
      await api.deleteDocument(docId)
      documents.value = documents.value.filter(d => d.id !== docId)
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  return {
    documents,
    currentDocument,
    loading,
    error,
    fetchDocuments,
    fetchDocument,
    uploadDocument,
    deleteDocument
  }
})
