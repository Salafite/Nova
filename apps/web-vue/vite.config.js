import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8070' },
    headers: {
      'Service-Worker-Allowed': '/'
    }
  },
  build: {
    chunkSizeWarningLimit: 400,
    cssCodeSplit: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia']
        }
      }
    }
  },
})

