/**
 * Motor del mapa: Mapbox GL (estilo Standard, de noche) si hay `VITE_MAPBOX_TOKEN`, MapLibre si no
 * (CI, Playwright y desarrollo sin cuenta). Las dos librerías comparten la API que usa FleetMap.
 */
import * as maplibregl from "maplibre-gl";
// MapLibre 6 arma la URL de su worker en tiempo de ejecución y Vite no la detecta al compilar:
// sin esto el build no incluye el worker y el mapa base queda en negro ("Worker failed to load").
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

maplibregl.setWorkerUrl(workerUrl);

export type Gl = typeof maplibregl;
export type GlMap = maplibregl.Map;
export type GlMarker = maplibregl.Marker;

export type Motor = {
  tipo: "mapbox" | "maplibre";
  gl: Gl;
  style: string | maplibregl.StyleSpecification;
};

const TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN || import.meta.env.NEXT_PUBLIC_MAPBOX_TOKEN)?.trim() || undefined;
const DEFAULT_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const configured = import.meta.env.VITE_MAP_STYLE as string | undefined;

export const MAPBOX_STANDARD = "mapbox://styles/mapbox/standard";

export async function cargarMotor(): Promise<Motor> {
  if (TOKEN && configured !== "empty") {
    const [mod] = await Promise.all([import("mapbox-gl"), import("mapbox-gl/dist/mapbox-gl.css")]);
    const gl = (mod.default ?? mod) as unknown as Gl & { accessToken: string };
    gl.accessToken = TOKEN;
    return { tipo: "mapbox", gl, style: MAPBOX_STANDARD };
  }
  // "empty" = estilo vacío local, para tests sin red.
  const style = configured === "empty" ? { version: 8 as const, sources: {}, layers: [] } : configured || DEFAULT_STYLE;
  return { tipo: "maplibre", gl: maplibregl, style };
}

/**
 * Mapbox Standard con la iluminación de noche y el tema monocromo: la marca es de tinta (tokens.css) y
 * el color queda para los camiones y los corredores. Sin POI comerciales.
 */
export function configurarStandard(map: GlMap): void {
  const set = (map as unknown as { setConfigProperty?: (i: string, k: string, v: unknown) => void }).setConfigProperty;
  if (!set) return;
  const props: Record<string, unknown> = {
    lightPreset: "night",
    theme: "monochrome",
    show3dObjects: true,
    showPointOfInterestLabels: false,
    showTransitLabels: false,
  };
  for (const [k, v] of Object.entries(props)) {
    try {
      set.call(map, "basemap", k, v);
    } catch {
      // una propiedad que esta versión del estilo no conoce no debe tumbar el mapa
    }
  }
}
