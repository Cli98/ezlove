import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
})

let refreshPromise = null

function clearAuth() {
  localStorage.removeItem('community_access_token')
  localStorage.removeItem('community_refresh_token')
  localStorage.removeItem('community_worker')
  localStorage.removeItem('community_current_id')
  router.push('/login')
}

function refreshAccessToken() {
  if (refreshPromise) return refreshPromise

  const refreshToken = localStorage.getItem('community_refresh_token')
  if (!refreshToken) {
    clearAuth()
    ElMessage.error('登录已过期，请重新登录')
    return Promise.reject(new Error('缺少刷新令牌'))
  }
  let latestRefreshToken = refreshToken

  refreshPromise = axios.post(
    `${API_BASE_URL}/community/auth/refresh`,
    { refresh_token: refreshToken }
  ).then(async ({ data }) => {
    localStorage.setItem('community_access_token', data.access_token)
    if (data.refresh_token) {
      latestRefreshToken = data.refresh_token
      localStorage.setItem('community_refresh_token', data.refresh_token)
    }

    const currentCommunityId = localStorage.getItem('community_current_id')
    if (currentCommunityId && currentCommunityId !== data.worker?.community_id) {
      const switched = await axios.post(
        `${API_BASE_URL}/community/auth/switch-community`,
        { community_id: currentCommunityId },
        { headers: { Authorization: `Bearer ${data.access_token}` } }
      )
      localStorage.setItem('community_access_token', switched.data.access_token)
      if (switched.data.refresh_token) {
        localStorage.setItem('community_refresh_token', switched.data.refresh_token)
      }
      return switched.data.access_token
    }

    return data.access_token
  }).catch(error => {
    if ([refreshToken, latestRefreshToken].includes(localStorage.getItem('community_refresh_token'))) {
      clearAuth()
      ElMessage.error('登录已过期，请重新登录')
    }
    throw error
  }).finally(() => {
    refreshPromise = null
  })

  return refreshPromise
}

request.interceptors.request.use(config => {
  const token = localStorage.getItem('community_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  response => response.data,
  async error => {
    const originalRequest = error.config
    const isLoginRequest = originalRequest?.url?.includes('/community/auth/login')

    if (error.response?.status === 401 && isLoginRequest) {
      ElMessage.error(error.response?.data?.detail || '手机号或密码错误')
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const newToken = await refreshAccessToken()
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return request(originalRequest)
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    } else {
      ElMessage.error(error.response?.data?.detail || '请求失败')
    }
    return Promise.reject(error)
  }
)

/**
 * 确保 access token 未过期，过期则自动刷新。
 * 供非 axios 请求（如 fetch SSE 流）在发起请求前调用。
 */
export async function ensureFreshToken(force = false) {
  const token = localStorage.getItem('community_access_token')
  if (!token) return token

  if (!force) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      if (payload.exp * 1000 > Date.now()) return token
    } catch {
      // token 格式异常，走刷新逻辑
    }
  }

  try {
    return await refreshAccessToken()
  } catch {
    return null
  }
}

export const api = {
  get: (url, params) => request.get(url, { params }),
  post: (url, data) => request.post(url, data),
  put: (url, data) => request.put(url, data),
  delete: (url) => request.delete(url),
}

export default request
