import type * as maplibregl from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { readCorridors, type Replay, type Trip, type Vehicle } from "../api/client";
import { cargarMotor, configurarStandard, type Gl, type GlMap, type GlMarker } from "../map/engine";
import * as mv from "../map/motion";
import { tagMarkup, truckMarkup } from "./truck";

/**
 * Mapa de la flota (docs/dev/plan-mapa-mapbox.md). Con VITE_MAPBOX_TOKEN usa Mapbox Standard de noche;
 * sin token (CI, Playwright) MapLibre, con el mismo código (map/engine.ts). Los camiones avanzan sobre la
 * vía real cuadro a cuadro (map/motion.ts) y al elegir uno la cámara vuela hasta él, se inclina y lo
 * sigue por las curvas hasta que el usuario mueve el mapa.
 */

type LngLat = mv.LngLat;
type Camara = "libre" | "volando" | "siguiendo";

const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

// Cámara al elegir un tráiler (patrón de Vora: vuelo en parábola y luego revelado en 3D).
const VUELO_MS = 2000;
const REVELADO_MS = 900;
const ZOOM_SEGUIR = 15.5;
const PITCH_VUELO = 20;
const PITCH_3D = 60;
const BEARING_3_4 = -15; // un poco de costado: se ve el camión de tres cuartos
const SUAVE_BEARING = 0.06; // fracción por cuadro con la que la cámara gira hacia el rumbo
// Un tractocamión con semirremolque mide ~18 m; el SVG mide ~48 px de largo a escala 1.
const LARGO_CAMION_M = 18;
const LARGO_SVG_PX = 48;
const ARRASTRE_PX = 4;

type Props = {
  vehicles: Vehicle[];
  trips: Record<string, Trip>;
  replay: Replay;
  selected: string | null;
  onSelect: (alias: string | null) => void;
};

type Pieza = { truck: GlMarker; tag: GlMarker; s: mv.Seguimiento };

function crearMapa(gl: Gl, style: string | maplibregl.StyleSpecification, mapbox: boolean, container: HTMLElement): GlMap {
  const m = new gl.Map({
    container, style, center: [-75.5, -12.5], zoom: 5,
    ...(mapbox ? { antialias: true } : { attributionControl: { compact: true } }),
  } as maplibregl.MapOptions);
  if (mapbox) m.on("style.load", () => configurarStandard(m));
  return m;
}

function capas(m: GlMap, mapbox: boolean) {
  // slot y emissive-strength son de Mapbox Standard; MapLibre rechaza la capa si los ve
  const slot = mapbox ? { slot: "middle" } : {};
  const emisiva = mapbox ? { "line-emissive-strength": 1 } : {};
  const ancho = (base: number) => ["interpolate", ["exponential", 1.6], ["zoom"], 5, base, 12, base * 2.2, 17, base * 9];
  m.addSource("corredores", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  m.addSource("estela", { type: "geojson", lineMetrics: true, data: { type: "FeatureCollection", features: [] } });
  const add = (layer: object) => m.addLayer(layer as maplibregl.LayerSpecification);
  add({
    id: "corredores-borde", type: "line", source: "corredores", ...slot,
    layout: { "line-join": "round", "line-cap": "round" },
    paint: { "line-color": "#05070A", "line-width": ancho(2.6), "line-opacity": 0.55, ...emisiva },
  });
  add({
    id: "corredores", type: "line", source: "corredores", ...slot,
    layout: { "line-join": "round", "line-cap": "round" },
    paint: { "line-color": "#AEB8B2", "line-width": ancho(1.1), "line-opacity": 0.5, ...emisiva },
  });
  add({
    id: "estela", type: "line", source: "estela", ...slot,
    layout: { "line-join": "round", "line-cap": "round" },
    paint: {
      "line-width": ancho(1.8),
      "line-gradient": ["interpolate", ["linear"], ["line-progress"], 0, "rgba(216,243,106,0)", 1, "rgba(216,243,106,.85)"],
      ...emisiva,
    },
  });
}

const VACIO = { type: "FeatureCollection" as const, features: [] };

export function FleetMap({ vehicles, trips, replay, selected, onSelect }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<GlMap | null>(null);
  const glRef = useRef<Gl | null>(null);
  const piezas = useRef(new Map<string, Pieza>());
  const lineas = useRef(new Map<string, mv.Linea>());
  const fitted = useRef(false);
  const camara = useRef<Camara>("libre");
  const vuelo = useRef(0); // id del vuelo en curso: un vuelo viejo no revela ni sigue
  const agarre = useRef<{ x: number; y: number } | null>(null); // puntero apretado sobre el mapa
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const [motor, setMotor] = useState<"mapbox" | "maplibre" | null>(null);
  const [listo, setListo] = useState(false);
  const [modo, setModo] = useState<Camara>("libre");
  const [corredores, setCorredores] = useState<{ corredor: string; coordenadas: LngLat[] }[]>([]);

  const ponerCamara = (c: Camara) => {
    camara.current = c;
    setModo(c);
  };

  // Mapa, capas y bucle de animación
  useEffect(() => {
    let vivo = true;
    let raf = 0;
    let m: GlMap | null = null;
    let quitarPuntero = () => {};
    const pzs = piezas.current;
    void cargarMotor().then(({ gl, style, tipo }) => {
      if (!vivo || !box.current) return;
      const mapbox = tipo === "mapbox";
      glRef.current = gl;
      setMotor(tipo);
      m = crearMapa(gl, style, mapbox, box.current);
      map.current = m;
      m.addControl(new gl.NavigationControl({ showCompass: true, visualizePitch: true }), "top-right");
      m.on("load", () => {
        if (!vivo || !m) return;
        capas(m, mapbox);
        setListo(true);
      });
      // el usuario toma el control: deja de seguir al camión. mousedown no: el clic sobre el marcador
      // también lo dispara y soltaría el seguimiento al volver a elegirlo.
      const soltar = (e: { originalEvent?: unknown }) => {
        if (!e.originalEvent || camara.current === "libre") return;
        vuelo.current++;
        ponerCamara("libre");
      };
      for (const ev of ["dragstart", "wheel", "rotatestart", "pitchstart"] as const) m.on(ev, soltar);
      // El jumpTo de cada cuadro corta el arrastre antes de que el mapa emita dragstart, así que el
      // arrastre se detecta aquí: con el puntero apretado la cámara no sigue, y si se mueve más de
      // ARRASTRE_PX se suelta. Un clic (sin moverse) no suelta: el seguimiento continúa al levantar.
      const contenedor = m.getCanvasContainer();
      const abajo = (e: PointerEvent) => {
        agarre.current = { x: e.clientX, y: e.clientY };
      };
      const mueve = (e: PointerEvent) => {
        const g = agarre.current;
        if (g && Math.hypot(e.clientX - g.x, e.clientY - g.y) > ARRASTRE_PX) soltar({ originalEvent: e });
      };
      const arriba = () => {
        agarre.current = null;
      };
      contenedor.addEventListener("pointerdown", abajo);
      window.addEventListener("pointermove", mueve);
      window.addEventListener("pointerup", arriba);
      quitarPuntero = () => {
        contenedor.removeEventListener("pointerdown", abajo);
        window.removeEventListener("pointermove", mueve);
        window.removeEventListener("pointerup", arriba);
      };
      const escala = () => {
        if (!m || !box.current) return;
        const mpp = mv.metrosPorPixel(m.getCenter().lat, m.getZoom());
        const e = Math.min(1.6, Math.max(0.45, LARGO_CAMION_M / mpp / LARGO_SVG_PX));
        box.current.style.setProperty("--escala", e.toFixed(3));
      };
      m.on("zoom", escala);
      escala();

      let antes = performance.now();
      const cuadro = (ahora: number) => {
        raf = requestAnimationFrame(cuadro);
        const dt = Math.min(ahora - antes, 100);
        antes = ahora;
        const mm = map.current;
        const d = box.current?.dataset;
        if (!mm || !d) return;
        for (const [alias, p] of pzs) {
          if (!reduce()) mv.avanzar(p.s, ahora, dt);
          p.truck.setLngLat(p.s.pos);
          p.tag.setLngLat(p.s.pos);
          const el = p.truck.getElement();
          el.style.setProperty("--rumbo", `${p.s.rumbo.toFixed(2)}deg`);
          el.dataset.lng = p.s.pos[0].toFixed(6);
          el.dataset.lat = p.s.pos[1].toFixed(6);
          if (alias !== selectedRef.current) continue;
          // con un zoom de los botones en curso no se pisa la animación: la cámara alcanza al camión después
          if (camara.current === "siguiendo" && !mm.isZooming() && !agarre.current) {
            const b = mm.getBearing();
            const objetivo = mv.unwrap(b, p.s.rumbo + BEARING_3_4);
            mm.jumpTo({ center: p.s.pos, bearing: reduce() ? objetivo : b + (objetivo - b) * SUAVE_BEARING });
          }
          const pts = mv.estela(p.s);
          (mm.getSource("estela") as maplibregl.GeoJSONSource | undefined)?.setData(
            pts.length > 1 ? { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: pts } } : VACIO,
          );
        }
        const c = mm.getCenter();
        d.pitch = mm.getPitch().toFixed(1);
        d.bearing = mm.getBearing().toFixed(1);
        d.zoom = mm.getZoom().toFixed(2);
        d.centro = `${c.lng.toFixed(6)},${c.lat.toFixed(6)}`;
        d.camara = camara.current;
      };
      raf = requestAnimationFrame(cuadro);
    });
    return () => {
      vivo = false;
      cancelAnimationFrame(raf);
      quitarPuntero();
      pzs.forEach((p) => { p.truck.remove(); p.tag.remove(); });
      pzs.clear();
      m?.remove();
      map.current = null;
    };
  }, []);

  // Geometría de los corredores: una vez (no cambia durante el replay)
  useEffect(() => {
    let vivo = true;
    readCorridors()
      .then((r) => { if (vivo) setCorredores(r.data.corredores.map((c) => ({ corredor: c.corredor, coordenadas: c.coordenadas as LngLat[] }))); })
      .catch(() => { /* sin geometría los camiones van a su última posición, como antes */ });
    return () => { vivo = false; };
  }, []);

  useEffect(() => {
    lineas.current.clear();
    for (const c of corredores) {
      if (c.coordenadas.length < 2) continue;
      const ida = mv.linea(c.coordenadas);
      lineas.current.set(`${c.corredor}:ida`, ida);
      lineas.current.set(`${c.corredor}:vuelta`, mv.invertida(ida));
    }
    const src = listo ? (map.current?.getSource("corredores") as maplibregl.GeoJSONSource | undefined) : undefined;
    src?.setData({
      type: "FeatureCollection",
      features: corredores.map((c) => ({ type: "Feature", properties: { corredor: c.corredor }, geometry: { type: "LineString", coordinates: c.coordenadas } })),
    });
  }, [corredores, listo]);

  // Lecturas del polling: crea, actualiza y quita camiones
  useEffect(() => {
    const m = map.current;
    const gl = glRef.current;
    if (!m || !gl) return;
    const ahora = performance.now();
    const ritmoReplay = replay.estado === "playing" && !reduce() ? replay.velocidad : 0;
    const vistos = new Set<string>();
    for (const v of vehicles) {
      vistos.add(v.alias);
      const trip = v.viaje_id ? trips[v.viaje_id] : undefined;
      const clave = trip && trip.estado === "en_curso" ? `${trip.corredor}:${trip.sentido}` : null;
      const lectura: mv.Lectura = {
        pos: [v.posicion.lon, v.posicion.lat],
        velocidadKmh: v.estado === "en_viaje" ? v.velocidad_kmh : 0,
        linea: clave ? lineas.current.get(clave) ?? null : null,
        clave,
        replay: ritmoReplay,
      };
      let p = piezas.current.get(v.alias);
      if (!p) {
        const el = document.createElement("button");
        el.type = "button";
        el.className = "marker";
        el.setAttribute("aria-label", v.alias);
        el.innerHTML = truckMarkup(v.alias);
        el.addEventListener("click", () => onSelectRef.current(v.alias));
        const tagEl = document.createElement("div");
        tagEl.className = "marker-tag";
        tagEl.innerHTML = tagMarkup();
        tagEl.querySelector("b")!.textContent = v.alias;
        tagEl.addEventListener("click", () => onSelectRef.current(v.alias));
        const s = mv.nuevo(lectura, ahora);
        // el camión va acostado sobre la pista y gira con el mapa; la etiqueta queda siempre de frente
        const truck = new gl.Marker({ element: el, rotationAlignment: "map", pitchAlignment: "map" }).setLngLat(s.pos).addTo(m);
        const tag = new gl.Marker({ element: tagEl, anchor: "left", offset: [20, 0] }).setLngLat(s.pos).addTo(m);
        p = { truck, tag, s };
        piezas.current.set(v.alias, p);
      } else {
        mv.observar(p.s, lectura, ahora);
        if (reduce()) mv.avanzar(p.s, ahora, 1e9); // sin animación: va directo a la lectura
      }
      const el = p.truck.getElement();
      el.dataset.estado = v.estado;
      el.classList.toggle("is-selected", v.alias === selected);
      const tagEl = p.tag.getElement();
      tagEl.dataset.estado = v.estado;
      tagEl.classList.toggle("is-selected", v.alias === selected);
      tagEl.querySelector(".tag-dato")!.textContent = v.estado === "en_viaje" ? `${Math.round(v.velocidad_kmh)} km/h` : "";
    }
    for (const [alias, p] of piezas.current) {
      if (!vistos.has(alias)) {
        p.truck.remove();
        p.tag.remove();
        piezas.current.delete(alias);
      }
    }
    if (!fitted.current && vehicles.length > 0) {
      fitted.current = true;
      const b = new gl.LngLatBounds();
      vehicles.forEach((v) => b.extend([v.posicion.lon, v.posicion.lat]));
      m.fitBounds(b, { padding: 80, maxZoom: 8, duration: reduce() ? 0 : 1200 });
    }
  }, [vehicles, trips, replay, selected, motor]);

  /** Vuelo → revelado en 3D → seguimiento. */
  const volarA = (alias: string) => {
    const m = map.current;
    const p = piezas.current.get(alias);
    if (!m || !p) return;
    const id = ++vuelo.current;
    m.stop();
    if (reduce()) {
      m.jumpTo({ center: p.s.pos, zoom: ZOOM_SEGUIR, pitch: PITCH_3D, bearing: p.s.rumbo + BEARING_3_4 });
      ponerCamara("siguiendo");
      return;
    }
    ponerCamara("volando");
    // el camión sigue avanzando durante el vuelo: se apunta a donde va a estar al llegar
    m.flyTo({ center: mv.adelantado(p.s, VUELO_MS), zoom: ZOOM_SEGUIR, pitch: PITCH_VUELO, curve: 1.3, duration: VUELO_MS });
    m.once("moveend", () => {
      if (vuelo.current !== id) return;
      m.easeTo({
        center: mv.adelantado(p.s, REVELADO_MS), pitch: PITCH_3D, bearing: mv.unwrap(m.getBearing(), p.s.rumbo + BEARING_3_4),
        duration: REVELADO_MS, easing: (t) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
      });
      m.once("moveend", () => { if (vuelo.current === id) ponerCamara("siguiendo"); });
    });
  };

  useEffect(() => {
    if (selected && motor) volarA(selected);
    if (!selected) {
      vuelo.current++;
      ponerCamara("libre");
      (map.current?.getSource("estela") as maplibregl.GeoJSONSource | undefined)?.setData(VACIO);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, motor]);

  const verFlota = () => {
    const m = map.current;
    const gl = glRef.current;
    onSelectRef.current(null);
    if (!m || !gl || piezas.current.size === 0) return;
    m.stop();
    const b = new gl.LngLatBounds();
    for (const p of piezas.current.values()) b.extend(p.s.pos);
    m.fitBounds(b, { padding: 80, maxZoom: 8, pitch: 0, bearing: 0, duration: reduce() ? 0 : 1600 });
  };

  return (
    <div className="map-wrap">
      {/* Mapbox pide el contenedor vacío: los controles propios van al lado, no adentro */}
      <div ref={box} className="map" data-testid="fleet-map" data-motor={motor ?? ""} />
      {selected && (
        <div className="camara" role="group" aria-label="Cámara">
          <span className="dato">{modo === "siguiendo" ? `Siguiendo ${selected}` : modo === "volando" ? `Yendo a ${selected}` : selected}</span>
          {modo === "libre" && <button type="button" onClick={() => volarA(selected)}>Seguir</button>}
          <button type="button" onClick={verFlota}>Ver flota</button>
        </div>
      )}
    </div>
  );
}
