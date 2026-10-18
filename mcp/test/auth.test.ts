import { createExecutionContext } from "cloudflare:test";
import { env, exports } from "cloudflare:workers";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MCP_KEY, initializeParams, mockUpstream } from "./helpers";

afterEach(() => vi.restoreAllMocks());

function post(headers: Record<string, string>) {
  return exports.default.fetch("https://mcp.test/mcp", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream", ...headers },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: initializeParams }),
  });
}

describe("auth de /mcp", () => {
  it("sin key responde 401", async () => {
    expect((await post({})).status).toBe(401);
  });

  it("con key incorrecta responde 401", async () => {
    expect((await post({ Authorization: "Bearer mala" })).status).toBe(401);
    expect((await post({ "X-API-Key": "mala" })).status).toBe(401);
  });

  it("con Bearer correcto responde 200", async () => {
    expect((await post({ Authorization: `Bearer ${MCP_KEY}` })).status).toBe(200);
  });

  it("con X-API-Key correcta responde 200", async () => {
    expect((await post({ "X-API-Key": MCP_KEY })).status).toBe(200);
  });

  it("no llama a la Domain API sin key", async () => {
    const calls = mockUpstream();
    await post({});
    expect(calls).toHaveLength(0);
  });

  it("sin MCP_API_KEY configurada ninguna key estática da acceso", async () => {
    const { default: worker } = await import("../src/index");
    const noKey = { ...env, MCP_API_KEY: undefined } as unknown as Env;
    for (const key of [MCP_KEY, "undefined", ""]) {
      const request = new Request("https://mcp.test/mcp", {
        method: "POST",
        headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
        body: "{}",
      });
      const response = await worker.fetch(request, noKey, createExecutionContext());
      expect(response.status).toBe(401);
    }
  });

  it("/health es público", async () => {
    const response = await exports.default.fetch("https://mcp.test/health");
    expect(response.status).toBe(200);
  });
});
