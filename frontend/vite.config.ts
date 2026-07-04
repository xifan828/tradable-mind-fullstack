import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  base: '/app/',
  plugins: [react(), tailwindcss()],
  build: {
    // Emit into the backend so the build output is inside the LangGraph
    // build context (langgraph.json lives in backend/) and ships in the image.
    outDir: '../backend/frontend_dist',
    emptyOutDir: true,
  },
})
