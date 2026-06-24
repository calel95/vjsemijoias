import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../frontend',
    emptyOutDir: false, // CRÍTICO: Não apagar para preservar imagens de catálogo em frontend/images/
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      },
      // Proxy para imagens e PDFs servidos pelo backend
      '/images': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      },
      '/pdf': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
});
