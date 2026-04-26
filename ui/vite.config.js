import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5500,
    proxy: {
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});