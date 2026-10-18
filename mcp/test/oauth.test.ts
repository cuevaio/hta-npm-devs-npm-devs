import { exports } from "cloudflare:workers";
import { afterEach, describe, expect, it, vi } from "vitest";
import { initializeParams, mockUpstream } from "./helpers";

const BASE = "https://mcp.test";
const REDIRECT = "https://client.test/cb";

afterEach(() => vi.restoreAllMocks());

class Browser {
  cookies = new Map<string, string>();
  async fetch(url: string, init: RequestInit = {}) {
    const headers = new Headers(init.headers);
    if (this.cookies.size) {
      headers.set("Cookie", [...this.cookies].map(([k, v]) => `${k}=${v}`).join("; "));
    }
    const response = await exports.default.fetch(url, { ...init, headers, redirect: "manual" });
    for (const c of response.headers.getSetCookie()) {
      const [pair] = c.split(";");
      const i = pair!.indexOf("=");
      this.cookies.set(pair!.slice(0, i), pair!.slice(i + 1));
    }
    return response;
  }
}

async function pkce() {
  const verifier = crypto.randomUUID() + crypto.randomUUID();
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  const challenge = btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return { verifier, challenge };
}

async function register(name = "Cliente <b>de prueba</b>") {
  const response = await exports.default.fetch(`${BASE}/oauth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_name: name,
      redirect_uris: [REDIRECT],
      token_endpoint_auth_method: "none",
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"],
    }),
  });
  expect(response.status).toBe(201);
  return ((await response.json()) as { client_id: string }).client_id;
}

/** GitHub simulado: intercambio de código y /user con el login dado. */
function mockGithub(login: string) {
  const seen: { token?: Record<string, string> } = {};
  mockUpstream();
  const inner = globalThis.fetch;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const request = new Request(input as RequestInfo, init);
    if (request.url === "https://github.com/login/oauth/access_token") {
      seen.token = (await request.json()) as Record<string, string>;
      return Response.json(seen.token.code === "gh-code" ? { access_token: "gh-token" } : { error: "bad_verification_code" });
    }
    if (request.url === "https://api.github.com/user") {
      const ok = request.headers.get("Authorization") === "Bearer gh-token";
      return ok ? Response.json({ login }) : new Response("", { status: 401 });
    }
    return inner(input as RequestInfo, init);
  });
  return seen;
}

/** Recorre consentimiento + GitHub y devuelve la redirección final al cliente. */
async function authorizeAs(login: string, decision = "approve") {
  const clientId = await register();
  const { verifier, challenge } = await pkce();
  const browser = new Browser();
  const query = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    redirect_uri: REDIRECT,
    scope: "mcp",
    state: "estado-cliente",
    code_challenge: challenge,
    code_challenge_method: "S256",
    resource: `${BASE}/mcp`,
  });
  const page = await browser.fetch(`${BASE}/authorize?${query}`);
  expect(page.status).toBe(200);
  const body = await page.text();
  expect(body).toContain("Cliente &#60;b&#62;de prueba&#60;/b&#62;");
  expect(body).toContain("client.test");
  const handle = body.match(/name="handle" value="([^"]+)"/)![1]!;

  const seen = mockGithub(login);
  const approve = await browser.fetch(`${BASE}/authorize`, {
    method: "POST",
    body: new URLSearchParams({ handle, decision }),
  });
  expect(approve.status).toBe(302);
  const location = new URL(approve.headers.get("Location")!);
  if (decision !== "approve") return { location, clientId, verifier, seen };

  expect(location.origin + location.pathname).toBe("https://github.com/login/oauth/authorize");
  expect(location.searchParams.get("client_id")).toBe("github-client-de-prueba");
  expect(location.searchParams.get("redirect_uri")).toBe(`${BASE}/callback`);
  const state = location.searchParams.get("state")!;

  const back = await browser.fetch(`${BASE}/callback?code=gh-code&state=${encodeURIComponent(state)}`);
  expect(back.status).toBe(302);
  return { location: new URL(back.headers.get("Location")!), clientId, verifier, seen };
}

describe("OAuth del MCP con GitHub", () => {
  it("publica los metadatos de descubrimiento", async () => {
    const resource = await exports.default.fetch(`${BASE}/.well-known/oauth-protected-resource/mcp`);
    expect(resource.status).toBe(200);
    expect(await resource.json()).toMatchObject({
      resource: `${BASE}/mcp`,
      authorization_servers: [BASE],
    });
    const server = await exports.default.fetch(`${BASE}/.well-known/oauth-authorization-server`);
    expect(await server.json()).toMatchObject({
      authorization_endpoint: `${BASE}/authorize`,
      token_endpoint: `${BASE}/oauth/token`,
      registration_endpoint: `${BASE}/oauth/register`,
    });
  });

  it("/mcp sin credenciales responde 401 apuntando a los metadatos", async () => {
    const response = await exports.default.fetch(`${BASE}/mcp`, { method: "POST", body: "{}" });
    expect(response.status).toBe(401);
    expect(response.headers.get("WWW-Authenticate")).toContain("resource_metadata");
  });

  it("un usuario permitido obtiene un token que abre /mcp", async () => {
    const { location, clientId, verifier, seen } = await authorizeAs("josephrobles23");
    expect(seen.token).toMatchObject({ client_secret: "github-secret-de-prueba", code_verifier: expect.any(String) });
    expect(location.origin + location.pathname).toBe(REDIRECT);
    expect(location.searchParams.get("state")).toBe("estado-cliente");
    const code = location.searchParams.get("code")!;

    const tokenResponse = await exports.default.fetch(`${BASE}/oauth/token`, {
      method: "POST",
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code,
        redirect_uri: REDIRECT,
        client_id: clientId,
        code_verifier: verifier,
        resource: `${BASE}/mcp`,
      }),
    });
    expect(tokenResponse.status).toBe(200);
    const { access_token } = (await tokenResponse.json()) as { access_token: string };

    const mcp = await exports.default.fetch(`${BASE}/mcp`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${access_token}`,
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: initializeParams }),
    });
    expect(mcp.status).toBe(200);
  });

  it("un usuario fuera de la allowlist vuelve al cliente con access_denied", async () => {
    const { location } = await authorizeAs("intruso");
    expect(location.origin + location.pathname).toBe(REDIRECT);
    expect(location.searchParams.get("error")).toBe("access_denied");
    expect(location.searchParams.get("code")).toBeNull();
  });

  it("rechazar el consentimiento no pasa por GitHub", async () => {
    const { location, seen } = await authorizeAs("josephrobles23", "deny");
    expect(location.origin + location.pathname).toBe(REDIRECT);
    expect(location.searchParams.get("error")).toBe("access_denied");
    expect(seen.token).toBeUndefined();
  });

  it("el callback sin la cookie del navegador se rechaza", async () => {
    const response = await exports.default.fetch(`${BASE}/callback?code=gh-code&state=robado`, { redirect: "manual" });
    expect(response.status).toBe(400);
  });
});
