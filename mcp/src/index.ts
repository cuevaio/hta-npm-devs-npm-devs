import { createMcpHandler } from "agents/mcp/server";
import { checkAuth } from "./auth";
import { createServer } from "./tools";

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return Response.json({ status: "ok" });
    }
    if (url.pathname === "/mcp") {
      const denied = await checkAuth(request, env.MCP_API_KEY);
      if (denied) return denied;
      return createMcpHandler(() => createServer(env), { route: "/mcp" })(request, env, ctx);
    }
    return new Response("Not found", { status: 404 });
  },
} satisfies ExportedHandler<Env>;
