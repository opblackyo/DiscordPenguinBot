import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Registers the already-installed @vitejs/plugin-react so JSX uses React's
// automatic runtime (no `import React` needed in every file) and dev Fast
// Refresh works. Without this config Vite falls back to esbuild's classic
// JSX transform, which throws "React is not defined" at runtime.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    // Dev-only convenience: mirror the production same-origin /api path so the
    // Dashboard fetches /api/music/status in dev too. In Docker this proxy is
    // provided by nginx (see apps/dashboard/nginx.conf); the app never calls a
    // hardcoded host. Override the target with VITE_DEV_API_TARGET if needed.
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_API_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
