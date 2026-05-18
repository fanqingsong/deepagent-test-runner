import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react({
      fastRefresh: false,
      babel: {
        plugins: []
      }
    })
  ],
  resolve: {
    dedupe: ['react', 'react-dom', 'react-dom/client']
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    cors: true,
    hmr: false,
    compress: false
  },
  optimizeDeps: {
    force: true,
    include: [
      'react',
      'react-dom',
      'react-dom/client',
      '@tanstack/react-query',
      'axios'
    ]
  },
  build: {
    sourcemap: false
  }
});
