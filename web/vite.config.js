import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        factsheet: resolve(__dirname, 'factsheet.html'),
        analysis: resolve(__dirname, 'data-analysis.html'),
      },
    },
  },
  server: {
    port: 5173,
    open: true,
  },
});
