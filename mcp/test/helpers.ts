import { exports } from "cloudflare:workers";
import { vi } from "vitest";
import contract from "../../backend/openapi.json";

export const MCP_KEY = "clave-mcp-de-prueba";
export const SERVICE_KEY = "clave-servicio-de-prueba";
export const UPSTREAM = "https://domain-api.test";

export interface UpstreamCall {
  method: string;
  path: string;
  query: Record<string, string>;
  body: unknown;
  apiKey: string | null;
}

type Operation = { responses: Record<string, { content?: { "application/json"?: { example?: unknown } } }> };

/** Ejemplo 200 de cada ruta /v1/tools/* del contrato (el mismo que sirve Prism). */
export function contractExamples(): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [path, item] of Object.entries(contract.paths)) {
    if (!path.startsWith("/v1/tools/")) continue;
    for (const op of Object.values(item) as Operation[]) {
      out[path] = op.responses["200"]?.content?.["application/json"]?.example;
    }
  }
  return out;
}

/**
 * Sustituye el fetch saliente por un upstream simulado construido desde
 * backend/openapi.json. Lo que no está en el contrato responde 404;
 * `notFound` fuerza 404 con detail para ciertos valores (alias desconocido).
 */
export function mockUpstream(notFound: (call: UpstreamCall) => string | null = () => null) {
  const examples = contractExamples();
  const calls: UpstreamCall[] = [];
  const realFetch = globalThis.fetch;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const request = new Request(input as RequestInfo, init);
    const url = new URL(request.url);
    if (url.origin !== UPSTREAM) return realFetch(input as RequestInfo, init);
    const text = request.method === "POST" ? await request.text() : "";
    const call: UpstreamCall = {
      method: request.method,
      path: url.pathname,
      query: Object.fromEntries(url.searchParams),
      body: text ? JSON.parse(text) : undefined,
      apiKey: request.headers.get("X-API-Key"),
    };
    calls.push(call);
    if (call.apiKey !== SERVICE_KEY) {
      return Response.json({ detail: "API key inválida" }, { status: 401 });
    }
    const detail = notFound(call);
    if (detail) return Response.json({ detail }, { status: 404 });
    if (!(call.path in examples)) return Response.json({ detail: "Not Found" }, { status: 404 });
    return Response.json(examples[call.path]);
  });
  return calls;
}

let nextId = 1;
export async function rpc(method: string, params: unknown, key: string | null = MCP_KEY) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };
  if (key) headers.Authorization = `Bearer ${key}`;
  const response = await exports.default.fetch("https://mcp.test/mcp", {
    method: "POST",
    headers,
    body: JSON.stringify({ jsonrpc: "2.0", id: nextId++, method, params }),
  });
  const raw = await response.text();
  const data = raw.startsWith("event:") || raw.includes("\ndata:") || raw.startsWith("data:")
    ? raw.split("\n").find((l) => l.startsWith("data:"))!.slice(5).trim()
    : raw;
  return { status: response.status, json: JSON.parse(data) };
}

export const initializeParams = {
  protocolVersion: "2025-06-18",
  capabilities: {},
  clientInfo: { name: "test", version: "1.0.0" },
};
