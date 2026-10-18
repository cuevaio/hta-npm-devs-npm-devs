import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// vitest solo toma los tests unitarios de src/; tests/ es de Playwright.
// El token de Mapbox puede venir como VITE_MAPBOX_TOKEN o NEXT_PUBLIC_MAPBOX_TOKEN (el mismo .env que Vora).
export default defineConfig({
  plugins: [react()],
  envPrefix: ["VITE_", "NEXT_PUBLIC_MAPBOX_"],
  test: { include: ["src/**/*.test.ts"] },
});
