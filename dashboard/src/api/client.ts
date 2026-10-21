import type { components, paths } from "./types";

export type Envelope<T> = {
  data: T;
  is_replay: boolean;
  provenance: components["schemas"]["Provenance"][];
  time_range: components["schemas"]["TimeRange"];
  updated_at: string;
};

export type Provenance = components["schemas"]["Provenance"];
export type Fleet = components["schemas"]["FleetOverview"];
export type Vehicle = components["schemas"]["VehiculoResumen"];
export type Trip = components["schemas"]["TripStatus"];
export type Replay = components["schemas"]["ReplayState"];
export type FreightBoard = components["schemas"]["FreightBoard"];
export type Freight = components["schemas"]["FleteDetalle"];
export type Aggregate = components["schemas"]["AgregadoFletes"];
export type Corridor = components["schemas"]["Corredor"];

type JsonOf<P extends keyof paths> = paths[P] extends {
  get: { responses: { 200: { content: { "application/json": infer B } } } };
}
  ? B
  : never;

// Verifica en compilación que los sobres del contrato coinciden con Envelope<T>.
export type FleetResponse = JsonOf<"/v1/fleet"> & Envelope<Fleet>;
export type ReplayResponse = JsonOf<"/v1/replay"> & Envelope<Replay>;
export type TripResponse = JsonOf<"/v1/trips/{trip_id}"> & Envelope<Trip>;
export type FreightBoardResponse = JsonOf<"/v1/freights"> & Envelope<FreightBoard>;
export type CorridorsResponse = JsonOf<"/v1/corridors"> & Envelope<components["schemas"]["CorridorList"]>;

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:4010").replace(/\/$/, "");

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const readFleet = () => get<FleetResponse>("/v1/fleet");
export const readReplay = () => get<ReplayResponse>("/v1/replay");
export const readFreights = () => get<FreightBoardResponse>("/v1/freights");
export const readCorridors = () => get<CorridorsResponse>("/v1/corridors");
export const readTrip = (tripId: string) =>
  get<TripResponse>(`/v1/trips/${encodeURIComponent(tripId)}`);

export type Snapshot = {
  fleet: FleetResponse;
  replay: ReplayResponse;
  trips: Record<string, Trip>;
};

export async function readSnapshot(): Promise<Snapshot> {
  const [fleet, replay] = await Promise.all([readFleet(), readReplay()]);
  const ids = [...new Set(fleet.data.vehiculos.map((v) => v.viaje_id).filter((x): x is string => !!x))];
  const found = await Promise.all(ids.map((id) => readTrip(id).catch(() => null)));
  const trips: Record<string, Trip> = {};
  found.forEach((t, i) => {
    if (t) trips[ids[i]] = t.data;
  });
  return { fleet, replay, trips };
}

// Nota revisada (Atomic Memory, opcional): memoria compartida del operador de la flota. La clave de notas
// la escribe el operador en pantalla y viaja en X-Notes-Key; nunca va en el build ni en el almacenamiento.
export type VehicleNote = components["schemas"]["VehicleNote"];

export class NoteError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function note(method: "GET" | "PUT" | "DELETE", alias: string, key: string | null, body?: unknown): Promise<VehicleNote> {
  const headers: Record<string, string> = {};
  if (key) headers["X-Notes-Key"] = key;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_URL}/v1/vehicles/${encodeURIComponent(alias)}/note`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => null);
  if (!res.ok) throw new NoteError(typeof json?.detail === "string" ? json.detail : `HTTP ${res.status}`, res.status);
  return json as VehicleNote;
}

export const readVehicleNote = (alias: string, key: string | null) => note("GET", alias, key);
export const saveVehicleNote = (alias: string, key: string, texto: string) =>
  note("PUT", alias, key, { texto, consentimiento: true });
export const deleteVehicleNote = (alias: string, key: string) => note("DELETE", alias, key);
