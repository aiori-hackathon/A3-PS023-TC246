import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";

const outDir = fs.existsSync(path.resolve(import.meta.dirname, "../src/controller/dashboard"))
  ? path.resolve(import.meta.dirname, "../src/controller/dashboard")
  : path.resolve(import.meta.dirname, "../controller/dashboard");

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir,
    emptyOutDir: false,
  },
  server: {
    port: 3000,
    proxy: {
      "/nodes": "http://127.0.0.1:8000",
      "/vms": "http://127.0.0.1:8000",
      "/decisions": "http://127.0.0.1:8000",
      "/images": "http://127.0.0.1:8000",
      "/events": "http://127.0.0.1:8000",
      "/scheduler": "http://127.0.0.1:8000",
      "/terminal-sessions": "http://127.0.0.1:8000",
    },
  },
});
