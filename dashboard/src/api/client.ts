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

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:4010").replace(/\/$/, "");

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const readFleet = () => get<FleetResponse>("/v1/fleet");
export const readReplay = () => get<ReplayResponse>("/v1/replay");
export const readFreights = () => get<FreightBoardResponse>("/v1/freights");
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
