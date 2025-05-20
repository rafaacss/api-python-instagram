import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
    plugins: [vue()],
    build: {
        outDir: '../static',
        emptyOutDir: false,
        rollupOptions: {
            input: './src/main.js', // Seu entrypoint JS
            output: {
                entryFileNames: 'bridge.js', // O arquivo gerado será ../static/bridge.js
                // Evita criação de subpastas assets
                assetFileNames: '[name][extname]'
            }
        }
    }
});
