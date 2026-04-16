import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const user = ref(null)

  async function login(username, password) {
    const response = await api.login(username, password)
    token.value = response.access_token
    localStorage.setItem('access_token', response.access_token)
    return response
  }

  async function register(username, password, email) {
    const response = await api.register({ username, password, email })
    return response
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('access_token')
  }

  return { token, user, login, logout, register }
})
