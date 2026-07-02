import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    root: 'src',
    include: ['**/__tests__/**/*.test.{js,ts}', '**/*.test.{js,ts}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      include: ['src/stores/**', 'src/components/**', 'src/composables/**'],
    },
    setupFiles: [],
  },
})
