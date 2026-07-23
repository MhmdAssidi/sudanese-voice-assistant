import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The browser only ever talks to this dev server (same origin => no CORS, and
// localhost is a "secure context" so the microphone is allowed even over http).
// Every /api/* call is forwarded to the voice backend on the pod.
//
// Point it at the backend with VITE_API_TARGET, either:
//   1) an SSH port-forward (most private):
//        ssh -tt -i <key> -L 8771:127.0.0.1:8771 -N <pod>@ssh.runpod.io
//        VITE_API_TARGET=http://127.0.0.1:8771   (this is the default)
//   2) the pod's cloudflared tunnel URL:
//        VITE_API_TARGET=https://<something>.trycloudflare.com
const target = process.env.VITE_API_TARGET || 'http://127.0.0.1:8771'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target,
        changeOrigin: true,
        // Tunnel hostnames present a valid cert, but keep this tolerant so a
        // self-signed or proxied endpoint does not break local development.
        secure: false,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
