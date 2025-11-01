// vite.config.js
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
  plugins: [vue()],
  root: ".",
  base: "/static/feeds/",          // <- IMPORTANTÍSSIMO
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: path.resolve(process.cwd(), "index.html"),
        widget: path.resolve(process.cwd(), "src/widget-loader.ts"),
      },
      output: {
        entryFileNames: (chunkInfo) => {
          // Widget loader tem nome fixo para facilitar inclusão
          if (chunkInfo.name === 'widget') {
            return 'instagram-feed-widget.js';
          }
          return 'assets/[name]-[hash].js';
        },
      },
    },
  },
  resolve: {
    alias: { "@": path.resolve(process.cwd(), "./src") },
  },
});
