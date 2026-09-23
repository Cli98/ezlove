import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 部署子路径（Vite base）解析——服务器固定构建通过环境变量注入：
// - VITE_BASE_PATH 由服务器构建环境提供（/ezlove/），构建产物资源引用将带该前缀；
// - 若其为空（防异常误配），以 VITE_API_BASE_URL 是否存在判定为服务器构建，回退 /ezlove/；
// - 本地构建两者均不存在，使用根路径 '/'（与本地 nginx 配置一致）。
const envBase = (process.env.VITE_BASE_PATH || '').trim()
const basePath = envBase || (process.env.VITE_API_BASE_URL ? '/ezlove/' : '/')

export default defineConfig({
  base: basePath,
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') }
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  }
})
