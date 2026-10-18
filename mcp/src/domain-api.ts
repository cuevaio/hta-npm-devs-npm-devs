// Cliente fino de la Domain API. Sin lógica de dominio (ADR 0004): arma la
// petición, reenvía la key de servicio y devuelve la respuesta tal cual.

export interface DomainApiEnv {
  DOMAIN_API_URL: string;
  DOMAIN_API_KEY: string;
}

export interface DomainApiResult {
  ok: boolean;
  status: number;
  body: unknown;
}

export async function callTool(
  env: DomainApiEnv,
  name: string,
  args: Record<string, unknown>,
): Promise<DomainApiResult> {
  const base = `${env.DOMAIN_API_URL.replace(/\/+$/, "")}/v1/tools/${name}`;
  const headers = { "X-API-Key": env.DOMAIN_API_KEY, Accept: "application/json" };

  let response: Response;
  if (name === "control_replay") {
    response = await fetch(base, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(args),
    });
  } else {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(args)) {
      if (value !== undefined) query.set(key, String(value));
    }
    const qs = query.toString();
    response = await fetch(qs ? `${base}?${qs}` : base, { headers });
  }

  const text = await response.text();
  let body: unknown = text;
  try {
    body = JSON.parse(text);
  } catch {
    // cuerpo no JSON: se devuelve como texto
  }
  return { ok: response.ok, status: response.status, body };
}
