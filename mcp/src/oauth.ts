import {
  AuthorizationError,
  CimdFetchError,
  authorizationErrorRedirect,
  type ConsentDescription,
  type OAuthHelpers,
} from "@cloudflare/workers-oauth-provider";

export const GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize";
export const GITHUB_TOKEN = "https://github.com/login/oauth/access_token";
export const GITHUB_USER = "https://api.github.com/user";

export interface AuthProps {
  login: string;
}

type OAuthEnv = Env & { OAUTH_PROVIDER: OAuthHelpers };

const escape = (value: string) => value.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

function html(body: string, status = 200, headers = new Headers()) {
  headers.set("Content-Type", "text/html; charset=utf-8");
  return new Response(
    `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">` +
      `<style>body{font:16px system-ui;max-width:32rem;margin:3rem auto;padding:0 1rem}button{font:inherit;padding:.5rem 1rem}</style>` +
      body,
    { status, headers },
  );
}

function consentPage(d: ConsentDescription, handle: string) {
  const name = escape(d.clientName);
  const origin = d.clientDomain
    ? `Publicada por <strong>${escape(d.clientDomain)}</strong>.`
    : "La aplicación se registró sola; su nombre no está verificado.";
  const local = d.redirectIsLoopback
    ? "<p><strong>El acceso irá a una aplicación de tu computadora.</strong> Continúa solo si acabas de iniciar sesión desde ella.</p>"
    : "";
  return `<title>Autorizar ${name}</title>
<h1>¿Permitir que ${name} consulte Certera?</h1>
<p>${origin} El acceso se enviará a <strong>${escape(d.redirectHost)}</strong>.</p>${local}
<p>Podrá leer la flota y controlar el replay de la demo. Te pediremos iniciar sesión con GitHub.</p>
<form method="post">
<input type="hidden" name="handle" value="${escape(handle)}">
<button name="decision" value="approve">Permitir</button> <button name="decision" value="deny">Rechazar</button>
</form>`;
}

async function s256(verifier: string) {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

export function allowedLogins(env: Env): Set<string> {
  return new Set(
    (env.GITHUB_ALLOWED_USERS ?? "")
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean),
  );
}

async function authorize(request: Request, env: OAuthEnv): Promise<Response> {
  const oauth = env.OAUTH_PROVIDER;
  if (request.method === "GET") {
    const authRequest = await oauth.parseAuthRequest(request);
    const details = await oauth.describeConsent(authRequest);
    const consent = await oauth.beginConsent(authRequest);
    return html(consentPage(details, consent.handle), 200, consent.headers);
  }
  const form = await request.formData();
  const handle = String(form.get("handle"));
  if (form.get("decision") !== "approve") {
    const denied = await oauth.denyConsent(request, handle);
    return new Response(null, { status: 302, headers: denied.headers });
  }
  const approved = await oauth.approveConsent(request, handle);
  const verifier = crypto.randomUUID() + crypto.randomUUID();
  const { state, headers } = await oauth.beginUpstream(approved.request, {
    data: { verifier },
    headers: approved.headers,
  });
  const github = new URL(GITHUB_AUTHORIZE);
  github.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  github.searchParams.set("redirect_uri", new URL("/callback", request.url).href);
  github.searchParams.set("state", state);
  github.searchParams.set("code_challenge", await s256(verifier));
  github.searchParams.set("code_challenge_method", "S256");
  github.searchParams.set("allow_signup", "false");
  headers.set("Location", github.href);
  return new Response(null, { status: 302, headers });
}

async function githubLogin(code: string, verifier: string, redirectUri: string, env: Env) {
  const tokenResponse = await fetch(GITHUB_TOKEN, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({
      client_id: env.GITHUB_CLIENT_ID,
      client_secret: env.GITHUB_CLIENT_SECRET,
      code,
      redirect_uri: redirectUri,
      code_verifier: verifier,
    }),
  });
  const token = (await tokenResponse.json()) as { access_token?: string };
  if (!token.access_token) return null;
  const userResponse = await fetch(GITHUB_USER, {
    headers: { Authorization: `Bearer ${token.access_token}`, "User-Agent": "fleet-mcp", Accept: "application/json" },
  });
  if (!userResponse.ok) return null;
  const user = (await userResponse.json()) as { login?: string };
  return user.login ?? null;
}

async function callback(request: Request, env: OAuthEnv): Promise<Response> {
  const oauth = env.OAUTH_PROVIDER;
  const { request: original, data, headers } = await oauth.finishUpstream<{ verifier: string }>(request);
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const login = code
    ? await githubLogin(code, data.verifier, new URL("/callback", request.url).href, env)
    : null;
  if (!login || !allowedLogins(env).has(login.toLowerCase())) {
    headers.set("Location", authorizationErrorRedirect(original, "access_denied"));
    return new Response(null, { status: 302, headers });
  }
  const { redirectTo } = await oauth.completeAuthorization({
    request: original,
    userId: login.toLowerCase(),
    metadata: { login },
    scope: original.scope,
    props: { login } satisfies AuthProps,
  });
  headers.set("Location", redirectTo);
  return new Response(null, { status: 302, headers });
}

/** Rutas propias del servidor de autorización: consentimiento y vuelta de GitHub. */
export async function authHandler(request: Request, env: OAuthEnv): Promise<Response> {
  const { pathname } = new URL(request.url);
  if ((pathname === "/authorize" || pathname === "/callback") && (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET)) {
    return html(
      "<h1>Inicio de sesión no disponible</h1><p>El servidor no tiene configurada la aplicación de GitHub (GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET). Avísale al administrador de Certera.</p>",
      503,
    );
  }
  try {
    if (pathname === "/authorize") return await authorize(request, env);
    if (pathname === "/callback") return await callback(request, env);
  } catch (error) {
    if (error instanceof AuthorizationError && error.redirectTo) {
      return Response.redirect(error.redirectTo, 302);
    }
    if (error instanceof AuthorizationError || error instanceof CimdFetchError) {
      const message = error instanceof AuthorizationError ? error.description : "No se pudo verificar la aplicación.";
      return html(`<p>${escape(message ?? "Solicitud inválida.")}</p>`, 400);
    }
    throw error;
  }
  return new Response("Not found", { status: 404 });
}
