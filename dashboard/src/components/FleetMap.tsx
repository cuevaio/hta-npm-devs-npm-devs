import * as maplibregl from "maplibre-gl";
// MapLibre 6 arma la URL de su worker en tiempo de ejecución y Vite no la detecta al compilar:
// sin esto el build no incluye el worker y el mapa base queda en negro ("Worker failed to load").
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { useEffect, useRef } from "react";
import type { Vehicle } from "../api/client";

const DEFAULT_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const configured = import.meta.env.VITE_MAP_STYLE as string | undefined;
// "empty" = estilo vacío local, para tests sin red.
const STYLE: string | maplibregl.StyleSpecification =
  configured === "empty" ? { version: 8, sources: {}, layers: [] } : configured || DEFAULT_STYLE;

maplibregl.setWorkerUrl(workerUrl);

type Props = { vehicles: Vehicle[]; selected: string | null; onSelect: (alias: string) => void };
type LngLat = [number, number];

const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Lleva el marcador de donde está a `to` en 1,8 s (menos que el polling de 2 s), sin saltos. */
function glide(mk: maplibregl.Marker, to: LngLat, anim: Map<maplibregl.Marker, number>) {
  cancelAnimationFrame(anim.get(mk) ?? 0);
  const p = mk.getLngLat();
  const from: LngLat = [p.lng, p.lat];
  if (reduce() || (from[0] === to[0] && from[1] === to[1])) {
    mk.setLngLat(to);
    return;
  }
  const start = performance.now();
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / 1800);
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    mk.setLngLat([from[0] + (to[0] - from[0]) * e, from[1] + (to[1] - from[1]) * e]);
    if (t < 1) anim.set(mk, requestAnimationFrame(step));
  };
  anim.set(mk, requestAnimationFrame(step));
}

export function FleetMap({ vehicles, selected, onSelect }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef(new Map<string, maplibregl.Marker>());
  const anim = useRef(new Map<maplibregl.Marker, number>());
  const fitted = useRef(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const m = new maplibregl.Map({ container: box.current!, style: STYLE, center: [-75.5, -12.5], zoom: 5 });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.current = m;
    const current = markers.current;
    const frames = anim.current;
    return () => {
      frames.forEach((id) => cancelAnimationFrame(id));
      frames.clear();
      current.clear();
      m.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const seen = new Set<string>();
    for (const v of vehicles) {
      seen.add(v.alias);
      const lngLat: LngLat = [v.posicion.lon, v.posicion.lat];
      let mk = markers.current.get(v.alias);
      if (!mk) {
        const el = document.createElement("button");
        el.type = "button";
        el.className = "marker";
        el.setAttribute("aria-label", v.alias);
        el.innerHTML = '<span class="pin" aria-hidden="true"></span><span class="tag"></span>';
        el.querySelector(".tag")!.textContent = v.alias;
        el.addEventListener("click", () => onSelectRef.current(v.alias));
        mk = new maplibregl.Marker({ element: el }).setLngLat(lngLat).addTo(m);
        markers.current.set(v.alias, mk);
      } else {
        glide(mk, lngLat, anim.current);
      }
      const el = mk.getElement();
      el.dataset.estado = v.estado;
      el.classList.toggle("is-selected", v.alias === selected);
    }
    for (const [alias, mk] of markers.current) {
      if (!seen.has(alias)) {
        cancelAnimationFrame(anim.current.get(mk) ?? 0);
        anim.current.delete(mk);
        mk.remove();
        markers.current.delete(alias);
      }
    }
    if (!fitted.current && vehicles.length > 0) {
      fitted.current = true;
      const b = new maplibregl.LngLatBounds();
      vehicles.forEach((v) => b.extend([v.posicion.lon, v.posicion.lat]));
      m.fitBounds(b, { padding: 80, maxZoom: 8, duration: reduce() ? 0 : 1200 });
    }
  }, [vehicles, selected]);

  useEffect(() => {
    const v = vehicles.find((x) => x.alias === selected);
    if (v && map.current) map.current.easeTo({ center: [v.posicion.lon, v.posicion.lat], zoom: Math.max(map.current.getZoom(), 7), duration: reduce() ? 0 : 900 });
    // solo al cambiar la selección
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  return <div ref={box} className="map" data-testid="fleet-map" />;
}
