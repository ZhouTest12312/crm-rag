import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 代理目标须与当前 uvicorn 端口一致（你这边 stream 在 8000）
const API_TARGET = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/health': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})
