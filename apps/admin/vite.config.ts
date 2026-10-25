import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3002,
    proxy: {
      '/api/catalog': { target: 'http://catalog:8080', rewrite: (path) => path.replace('/api/catalog', '/api/v1/catalog') },
      '/api/pricing': { target: 'http://pricing:8080', rewrite: (path) => path.replace('/api/pricing', '/api/v1/pricing') },
      '/api/inventory': { target: 'http://inventory:8080', rewrite: (path) => path.replace('/api/inventory', '/api/v1/inventory') },
    },
  },
})
