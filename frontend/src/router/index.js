import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/tasks',
    name: 'TaskList',
    component: () => import('@/views/TaskList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('@/views/Upload.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/review/:docId',
    name: 'Review',
    component: () => import('@/views/Review.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/review-new/:docId',
    name: 'ReviewNew',
    component: () => import('@/views/ReviewNew.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/compare/:docAId/:docBId',
    name: 'Compare',
    component: () => import('@/views/Compare.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ocr-render',
    name: 'OcrRender',
    component: () => import('@/views/OcrRender.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
