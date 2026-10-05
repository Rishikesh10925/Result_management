import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// dev: /api calls go to Flask on :5000 (same origin, so session cookies just work)
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:5000' } },
})
