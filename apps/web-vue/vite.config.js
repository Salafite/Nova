import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8070' } },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router') || id.includes('node_modules/pinia')) {
            return 'vue'
          }
          if (id.includes('node_modules/axios')) {
            return 'http'
          }
        },
      },
    },
    chunkSizeWarningLimit: 400,
    cssCodeSplit: true,
    sourcemap: false,
  },
})
