import * as maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { Vehicle } from "../api/client";

const DEFAULT_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const configured = import.meta.env.VITE_MAP_STYLE as string | undefined;
// "empty" = estilo vacío local, para tests sin red.
const STYLE: string | maplibregl.StyleSpecification =
  configured === "empty" ? { version: 8, sources: {}, layers: [] } : configured || DEFAULT_STYLE;

type Props = { vehicles: Vehicle[]; selected: string | null; onSelect: (alias: string) => void };

export function FleetMap({ vehicles, selected, onSelect }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef(new Map<string, maplibregl.Marker>());
  const fitted = useRef(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const m = new maplibregl.Map({ container: box.current!, style: STYLE, center: [114, 34], zoom: 3 });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.current = m;
    const current = markers.current;
    return () => {
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
      const lngLat: [number, number] = [v.posicion.lon, v.posicion.lat];
      let mk = markers.current.get(v.alias);
      if (!mk) {
        const el = document.createElement("button");
        el.type = "button";
        el.className = "marker";
        el.setAttribute("aria-label", v.alias);
        el.textContent = v.alias;
        el.addEventListener("click", () => onSelectRef.current(v.alias));
        mk = new maplibregl.Marker({ element: el }).setLngLat(lngLat).addTo(m);
        markers.current.set(v.alias, mk);
      } else {
        mk.setLngLat(lngLat);
      }
      const el = mk.getElement();
      el.dataset.estado = v.estado;
      el.classList.toggle("is-selected", v.alias === selected);
    }
    for (const [alias, mk] of markers.current) {
      if (!seen.has(alias)) {
        mk.remove();
        markers.current.delete(alias);
      }
    }
    if (!fitted.current && vehicles.length > 0) {
      fitted.current = true;
      const b = new maplibregl.LngLatBounds();
      vehicles.forEach((v) => b.extend([v.posicion.lon, v.posicion.lat]));
      m.fitBounds(b, { padding: 60, maxZoom: 8, duration: 0 });
    }
  }, [vehicles, selected]);

  useEffect(() => {
    const v = vehicles.find((x) => x.alias === selected);
    if (v && map.current) map.current.easeTo({ center: [v.posicion.lon, v.posicion.lat], duration: 400 });
    // solo al cambiar la selección
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  return <div ref={box} className="map" data-testid="fleet-map" />;
}
