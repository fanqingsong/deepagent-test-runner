import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react({
      fastRefresh: true,
    })
  ],
  resolve: {
    dedupe: ['react', 'react-dom', 'react-dom/client']
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: 'all',
    cors: true,
    hmr: true,
    proxy: {
      '/api/v1': {
        target: 'http://deepagent-tester-backend:8011',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://deepagent-tester-backend:8011',
        ws: true,
      },
    },
    watch: {
      usePolling: true,
      interval: 1000,
      ignored: ['**/node_modules/**', '**/.vite/**', '**/.cache/**'],
    },
    compress: false
  },
  optimizeDeps: {
    force: false,
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
