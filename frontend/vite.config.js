import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    host: "localhost", // or "0.0.0.0" if accessed from LAN/another device
    open: true,
    hmr: {
      protocol: "ws",           // or "wss" for secure connections
      host: "localhost",
      port: 3000,
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
})
