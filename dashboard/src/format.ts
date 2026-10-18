import type { Provenance, Vehicle } from "./api/client";

export const ESTADO: Record<Vehicle["estado"], string> = {
  en_viaje: "En viaje",
  detenido: "Detenido",
  ralenti: "Ralentí",
};

export const PROCEDENCIA: Record<Provenance, string> = {
  fead_observed: "FEAD real reproducida",
  synthetic_demo: "Sintético",
  human_reported: "Reporte del conductor",
  external_enrichment: "Fuente externa",
  model_inferred: "Calculado por el sistema",
};

/** UTC en la base, hora de Lima (UTC−5, sin horario de verano) en pantalla (ADR 0012). */
export function horaLima(iso: string): string {
  const d = new Date(new Date(iso).getTime() - 5 * 3600_000);
  return `${d.toISOString().slice(0, 16).replace("T", " ")} hora de Lima`;
}

export const STALE_MS = 5 * 60_000;

/** Desactualizado: la hora del evento va más de 5 min (de replay) detrás de la hora de replay. */
export function isStale(horaEvento: string, horaReplay: string): boolean {
  return new Date(horaReplay).getTime() - new Date(horaEvento).getTime() > STALE_MS;
}

const SOLES = new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN", maximumFractionDigits: 0 });

/** Monto en soles sin decimales; "–" si no se conoce aún (p. ej. un flete en curso). */
export function pen(v: number | null | undefined): string {
  return v == null ? "–" : SOLES.format(v);
}
