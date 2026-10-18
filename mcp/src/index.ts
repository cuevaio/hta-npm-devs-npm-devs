import { OAuthProvider, type OAuthHelpers } from "@cloudflare/workers-oauth-provider";
import { createMcpHandler } from "agents/mcp/server";
import { presentedKey, safeEqual } from "./auth";
import { authHandler } from "./oauth";
import { createServer } from "./tools";

function mcp(request: Request, env: Env, ctx: ExecutionContext) {
  return createMcpHandler(() => createServer(env), { route: "/mcp" })(request, env, ctx);
}

const providers = new Map<string, OAuthProvider<Env>>();

function provider(publicUrl: string) {
  let p = providers.get(publicUrl);
  if (!p) {
    p = new OAuthProvider<Env>({
      apiRoute: "/mcp",
      apiHandler: { fetch: (request, env, ctx) => mcp(request as Request, env, ctx) },
      defaultHandler: {
        fetch: (request, env) => {
          if (new URL(request.url).pathname === "/health") return Response.json({ status: "ok" });
          return authHandler(request as Request, env as Env & { OAUTH_PROVIDER: OAuthHelpers });
        },
      },
      authorizeEndpoint: "/authorize",
      tokenEndpoint: "/oauth/token",
      clientRegistrationEndpoint: "/oauth/register",
      clientIdMetadataDocumentEnabled: true,
      scopesSupported: ["mcp"],
      requiredScopes: ["mcp"],
      resourceMetadata: {
        resource: `${publicUrl}/mcp`,
        authorization_servers: [publicUrl],
        resource_name: "Certera",
      },
    });
    providers.set(publicUrl, p);
  }
  return p;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    // La API key estática sigue valiendo para mcp-remote, tests y e2e; el resto pasa por OAuth.
    if (new URL(request.url).pathname === "/mcp" && env.MCP_API_KEY) {
      const key = presentedKey(request);
      if (key && (await safeEqual(key, env.MCP_API_KEY))) return mcp(request, env, ctx);
    }
    return provider(env.PUBLIC_URL).fetch(request, env, ctx);
  },
} satisfies ExportedHandler<Env>;
