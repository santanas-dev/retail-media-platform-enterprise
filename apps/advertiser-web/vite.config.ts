import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxy = {
  "/api": "http://localhost:8000",
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    proxy: apiProxy,
  },
  // vite preview (production bundle) does NOT inherit server.proxy — the CI
  // smoke job serves the built app via `vite preview`, so mirror the proxy
  // here (UI-SMOKE-STABILITY-004B).
  preview: {
    port: 3001,
    proxy: apiProxy,
  },
});
