import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Listen on all interfaces so a cloudflared quick tunnel (and phones on
    // the same network) can reach the dev server.
    host: true,
    // Allow trycloudflare.com quick-tunnel hostnames (see frontend/README.md).
    allowedHosts: ['.trycloudflare.com'],
  },
})
