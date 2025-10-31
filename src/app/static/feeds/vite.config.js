// vite.config.js
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
  plugins: [vue()],
  root: ".",
  base: "/feeds/",          // <- IMPORTANTÍSSIMO
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  resolve: {
    alias: { "@": path.resolve(process.cwd(), "./src") },
  },
});
