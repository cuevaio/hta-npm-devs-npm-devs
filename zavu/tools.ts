// Adaptador delgado de las tools de lectura (ADR 0004): un solo fetch a la
// Domain API con la API key de servicio, y el sobre se devuelve tal cual.
// `control_replay` es solo del MCP (decisión D14) y no está aquí.

export interface ToolDef {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ToolError {
  error: string;
  status?: number;
  detail?: unknown;
}

const REPLAY =
  "Los datos son un replay de telemetría histórica de FEAD, nunca tiempo real. " +
  "La respuesta es un sobre con procedencia, rango de tiempo y updated_at.";

const noParams = { type: "object", properties: {} };

const tripParams = {
  type: "object",
  properties: { trip_id: { type: "string", description: "Identificador del viaje, p. ej. V-001" } },
  required: ["trip_id"],
};

export const TOOL_DEFS: ToolDef[] = [
  {
    name: "get_fleet_overview",
    description: `Resumen de la flota: estado de cada vehículo y viajes en curso del replay. ${REPLAY}`,
    parameters: noParams,
  },
  {
    name: "get_vehicle_status",
    description: `Estado de un vehículo (alias anónimo T01…T28): viaje actual, sentido, posición y última lectura. ${REPLAY}`,
    parameters: {
      type: "object",
      properties: { alias: { type: "string", description: "Alias del vehículo, p. ej. T03" } },
      required: ["alias"],
    },
  },
  {
    name: "get_trip_status",
    description: `Estado de un viaje: vehículo, corredor, sentido, avance por tramo y paradas. ${REPLAY}`,
    parameters: tripParams,
  },
  {
    name: "get_fuel_analysis",
    description: `Análisis de combustible de un viaje: consumo por tramo frente a la línea base de sus pares en el mismo sentido y sobreconsumo detectado. ${REPLAY}`,
    parameters: tripParams,
  },
  {
    name: "get_operational_bottlenecks",
    description: `Cuellos de botella de un viaje: tiempo perdido por paradas sin explicar o ralentí prolongado, ordenado por impacto. ${REPLAY}`,
    parameters: tripParams,
  },
  {
    name: "get_alerts",
    description: `Alertas vigentes de la flota (sobreconsumo, cuellos de botella) con su procedencia. ${REPLAY}`,
    parameters: noParams,
  },
];

type Env = Record<string, string | undefined>;

export async function callDomainApi(
  name: string,
  args: Record<string, unknown> = {},
  env: Env = process.env,
  fetchImpl: typeof fetch = fetch,
): Promise<unknown | ToolError> {
  if (!TOOL_DEFS.some((t) => t.name === name)) {
    return { error: `Tool desconocida: ${name}` } satisfies ToolError;
  }
  const url = env.DOMAIN_API_URL;
  const key = env.DOMAIN_API_KEY;
  if (!url || !key) {
    return {
      error: "Falta configurar DOMAIN_API_URL o DOMAIN_API_KEY; no tengo acceso a los datos de la flota.",
    } satisfies ToolError;
  }

  const query = new URLSearchParams();
  for (const [k, v] of Object.entries(args)) {
    if (v !== undefined && v !== null) query.set(k, String(v));
  }
  const qs = query.toString();
  const base = `${url.replace(/\/+$/, "")}/v1/tools/${name}`;

  let response: Response;
  try {
    response = await fetchImpl(qs ? `${base}?${qs}` : base, {
      headers: { "X-API-Key": key, Accept: "application/json" },
    });
  } catch (e) {
    return { error: "No se pudo contactar la Domain API", detail: String(e) } satisfies ToolError;
  }

  const text = await response.text();
  let body: unknown = text;
  try {
    body = JSON.parse(text);
  } catch {
    // cuerpo no JSON: se devuelve como texto
  }
  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as { detail: unknown }).detail
        : body;
    return { error: "La Domain API no devolvió el dato", status: response.status, detail } satisfies ToolError;
  }
  return body;
}
