import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/login/index.vue') },
  {
    path: '/',
    component: () => import('@/views/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/index.vue') },
      { path: 'elders', name: 'Elders', component: () => import('@/views/elders/index.vue') },
      { path: 'elders/:id', name: 'ElderDetail', component: () => import('@/views/elders/detail.vue') },
      { path: 'canteen', name: 'Canteen', component: () => import('@/views/canteen/index.vue') },
      { path: 'events', name: 'Events', component: () => import('@/views/events/index.vue') },
      { path: 'agent', name: 'Agent', component: () => import('@/views/agent/index.vue') },
      { path: 'volunteers', name: 'Volunteers', component: () => import('@/views/volunteers/index.vue') },
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.path === '/login') {
    next()
    return
  }

  const token = localStorage.getItem('community_access_token')
  if (!token) {
    next('/login')
    return
  }

  // token 过期时由 axios 响应拦截器自动刷新并重试请求
  next()
})

export default router
