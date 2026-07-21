import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The browser only ever talks to this dev server (same origin => no CORS, and
// localhost is a "secure context" so the microphone is allowed). Every /api/*
// call is transparently forwarded to the voice service on the pod, which you
// reach via your SSH tunnel:  ssh ... -L 8770:127.0.0.1:8770 -N
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8770',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
