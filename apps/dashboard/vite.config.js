import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Registers the already-installed @vitejs/plugin-react so JSX uses React's
// automatic runtime (no `import React` needed in every file) and dev Fast
// Refresh works. Without this config Vite falls back to esbuild's classic
// JSX transform, which throws "React is not defined" at runtime.
export default defineConfig({
  plugins: [react()],
  server: { host: true },
});
