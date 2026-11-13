import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";

// Read token server-side in Node.js from environment or secrets.env
let defaultToken = process.env.PS023_API_TOKEN || "";
if (!defaultToken) {
  const secretsPath = path.resolve(import.meta.dirname, "../secrets.env");
  if (fs.existsSync(secretsPath)) {
    const content = fs.readFileSync(secretsPath, "utf-8");
    const m = content.match(/^PS023_API_TOKEN=["']?([^"'\r\n]+)["']?/m);
    if (m) defaultToken = m[1].trim();
  }
}

const srcControllerDashboard = path.resolve(import.meta.dirname, "../src/controller/dashboard");
const controllerDashboard = srcControllerDashboard;

function createProxy(target = "http://127.0.0.1:8000", ws = false) {
  return {
    target,
    ws,
    changeOrigin: true,
    configure: (proxy: any) => {
      proxy.on("proxyReq", (proxyReq: any, req: any) => {
        const auth = req.headers["authorization"];
        if ((!auth || auth === "Bearer " || auth === "Bearer undefined" || auth === "Bearer null") && defaultToken) {
          proxyReq.setHeader("Authorization", `Bearer ${defaultToken}`);
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    {
      name: "ps023-dev-auth-helper",
      configureServer(server) {
        server.middlewares.use("/api/auth/token", (_req, res) => {
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ token: defaultToken }));
        });
      },
      closeBundle() {
        // Ensure both controller/dashboard and src/controller/dashboard stay in sync on build
        if (fs.existsSync(srcControllerDashboard) && srcControllerDashboard !== controllerDashboard) {
          try {
            fs.cpSync(controllerDashboard, srcControllerDashboard, { recursive: true });
          } catch {
            // Ignore
          }
        }
      },
    },
  ],
  base: "./",
  build: {
    outDir: controllerDashboard,
    emptyOutDir: false,
  },
  server: {
    port: 3000,
    proxy: {
      "/nodes": createProxy(),
      "/vms": createProxy("http://127.0.0.1:8000", true),
      "/decisions": createProxy(),
      "/images": createProxy(),
      "/events": createProxy(),
      "/scheduler": createProxy(),
      "/terminal-sessions": createProxy(),
      "/cluster": createProxy(),
      "/health": createProxy(),
    },
  },
});
