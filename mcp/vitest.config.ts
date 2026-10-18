import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        bindings: {
          MCP_API_KEY: "clave-mcp-de-prueba",
          DOMAIN_API_KEY: "clave-servicio-de-prueba",
          DOMAIN_API_URL: "https://domain-api.test",
          PUBLIC_URL: "https://mcp.test",
          GITHUB_CLIENT_ID: "github-client-de-prueba",
          GITHUB_CLIENT_SECRET: "github-secret-de-prueba",
          GITHUB_ALLOWED_USERS: "JosephRobles23, otra",
        },
      },
    }),
  ],
});
