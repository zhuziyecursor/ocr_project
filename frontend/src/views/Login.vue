<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const isRegister = ref(false)
const username = ref('')
const password = ref('')
const email = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    await authStore.login(username.value, password.value)
    ElMessage.success('登录成功')
    router.push('/tasks')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!username.value || !password.value || !email.value) {
    ElMessage.warning('请输入用户名、邮箱和密码')
    return
  }
  loading.value = true
  try {
    await authStore.register(username.value, password.value, email.value)
    ElMessage.success('注册成功，请登录')
    isRegister.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-box">
      <h1 class="title">审计文档处理系统</h1>
      <el-form @submit.prevent="isRegister ? handleRegister() : handleLogin()" class="login-form">
        <el-form-item>
          <el-input
            v-model="username"
            placeholder="用户名"
            size="large"
          />
        </el-form-item>
        <el-form-item v-if="isRegister">
          <el-input
            v-model="email"
            type="email"
            placeholder="邮箱"
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="密码"
            size="large"
            @keyup.enter="isRegister ? handleRegister() : handleLogin()"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="isRegister ? handleRegister() : handleLogin()"
            class="login-btn"
          >
            {{ isRegister ? '注册' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      <div class="toggle-mode">
        <a v-if="!isRegister" @click="isRegister = true" class="toggle-link">没有账号？立即注册</a>
        <a v-else @click="isRegister = false" class="toggle-link">已有账号？去登录</a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  background: white;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 400px;
}

.title {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
  font-size: 24px;
}

.login-form {
  width: 100%;
}

.login-btn {
  width: 100%;
}

.toggle-mode {
  text-align: center;
  margin-top: 16px;
}

.toggle-link {
  color: #409eff;
  font-size: 14px;
  cursor: pointer;
  text-decoration: none;
}

.toggle-link:hover {
  text-decoration: underline;
}
</style>
