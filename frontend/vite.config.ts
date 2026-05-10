import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: false,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': process.env.VITE_BACKEND_TARGET ?? 'http://127.0.0.1:8000',
    },
  },
  build: {
    cssMinify: 'esbuild',
    chunkSizeWarningLimit: 700,
  },
  plugins: [react()],
})
