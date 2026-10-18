const encoder = new TextEncoder();

// Comparación en tiempo constante: se comparan digests SHA-256 de largo fijo.
async function digest(value: string): Promise<Uint8Array> {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", encoder.encode(value)));
}

export async function safeEqual(a: string, b: string): Promise<boolean> {
  const [da, db] = await Promise.all([digest(a), digest(b)]);
  let diff = 0;
  for (let i = 0; i < da.length; i++) diff |= da[i]! ^ db[i]!;
  return diff === 0;
}

export function presentedKey(request: Request): string | null {
  const bearer = request.headers.get("Authorization")?.match(/^Bearer\s+(.+)$/i)?.[1];
  return bearer ?? request.headers.get("X-API-Key");
}

/** Devuelve una respuesta de error si la petición no está autorizada, o null si pasa. */
export async function checkAuth(request: Request, expected: string | undefined) {
  if (!expected) {
    return Response.json({ error: "MCP_API_KEY no está configurada" }, { status: 503 });
  }
  const key = presentedKey(request);
  if (!key || !(await safeEqual(key, expected))) {
    return Response.json(
      { error: "API key ausente o incorrecta" },
      { status: 401, headers: { "WWW-Authenticate": "Bearer" } },
    );
  }
  return null;
}
