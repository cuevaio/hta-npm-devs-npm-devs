// Secretos cargados con `wrangler secret put` (no los genera `wrangler types`).
interface Env {
  MCP_API_KEY: string;
  DOMAIN_API_KEY: string;
  GITHUB_CLIENT_ID: string;
  GITHUB_CLIENT_SECRET: string;
}
