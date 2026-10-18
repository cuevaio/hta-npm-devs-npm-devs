/**
 * Movimiento de los camiones sobre la vía real (docs/dev/plan-mapa-mapbox.md §6). Puro: no sabe nada
 * del motor de mapas, así se prueba solo (motion.test.ts).
 *
 * Entre dos lecturas del polling el camión no va en línea recta: avanza por la polilínea del corredor
 * a su velocidad por la del replay, y cada lectura nueva corrige con suavidad la distancia recorrida.
 */

export type LngLat = [number, number];

const M_POR_GRADO = 111_195;
/** Una lectura a más de esto de la vía no se ajusta (terminal, desvío): se dibuja donde cayó. */
export const MAX_AJUSTE_M = 80;
/** Saltos mayores (un seek del replay) se aplican de golpe, sin animar. */
export const SALTO_KM = 3;
/** Sin lecturas nuevas, la predicción no se aleja más que esto de la última observada. */
const HORIZONTE_MS = 4000;
const SUAVIZADO_MS = 350;
const SUAVIZADO_RUMBO_MS = 300;

export type Linea = {
  coords: LngLat[];
  /** km acumulado hasta cada vértice */
  cum: number[];
  largo: number;
  /** cos(lat media): proyección local en metros */
  k: number;
};

function distKm(a: LngLat, b: LngLat, k: number): number {
  return Math.hypot((b[0] - a[0]) * k, b[1] - a[1]) * M_POR_GRADO / 1000;
}

export function linea(coords: LngLat[]): Linea {
  const k = Math.cos((coords.reduce((s, c) => s + c[1], 0) / coords.length) * Math.PI / 180);
  const cum = [0];
  for (let i = 1; i < coords.length; i++) cum.push(cum[i - 1] + distKm(coords[i - 1], coords[i], k));
  return { coords, cum, largo: cum[cum.length - 1], k };
}

/** La misma vía recorrida al revés (sentido vuelta). */
export function invertida(l: Linea): Linea {
  return linea([...l.coords].reverse());
}

function segmento(l: Linea, km: number): number {
  let lo = 0;
  let hi = l.cum.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (l.cum[mid] <= km) lo = mid;
    else hi = mid;
  }
  return lo;
}

/** Punto de la vía a `km` del inicio (acotado a la línea). */
export function along(l: Linea, km: number): LngLat {
  const d = Math.min(Math.max(km, 0), l.largo);
  const i = segmento(l, d);
  const j = Math.min(i + 1, l.coords.length - 1);
  const len = l.cum[j] - l.cum[i];
  const t = len > 0 ? (d - l.cum[i]) / len : 0;
  const a = l.coords[i];
  const b = l.coords[j];
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
}

/** Rumbo de `a` a `b` en grados (0 = norte, horario). */
export function rumbo(a: LngLat, b: LngLat): number {
  const rad = Math.PI / 180;
  const dLon = (b[0] - a[0]) * rad;
  const y = Math.sin(dLon) * Math.cos(b[1] * rad);
  const x = Math.cos(a[1] * rad) * Math.sin(b[1] * rad) - Math.sin(a[1] * rad) * Math.cos(b[1] * rad) * Math.cos(dLon);
  return (Math.atan2(y, x) / rad + 360) % 360;
}

/** Rumbo de la vía en `km`, mirando 25 m atrás y adelante (no tiembla en un vértice). */
export function rumboEn(l: Linea, km: number): number {
  return rumbo(along(l, km - 0.025), along(l, km + 0.025));
}

/** Ángulo acumulado que llega a `target` por el camino corto (de 350° a 10° gira 20°, no 340°). */
export function unwrap(current: number, target: number): number {
  return current + (((((target - current) % 360) + 540) % 360) - 180);
}

/**
 * km de la vía más cercano a `p` y a qué distancia queda (m). Con `cercaDe` busca primero en ±5 km de
 * ahí (un camión no salta de un extremo al otro del corredor entre dos lecturas).
 */
export function ubicar(l: Linea, p: LngLat, cercaDe?: number): { km: number; distM: number } {
  const buscar = (i0: number, i1: number) => {
    let best = { km: 0, distM: Infinity };
    const px = p[0] * l.k;
    const py = p[1];
    for (let i = i0; i < i1; i++) {
      const a = l.coords[i];
      const b = l.coords[i + 1];
      const ax = a[0] * l.k, ay = a[1], dx = b[0] * l.k - ax, dy = b[1] - ay;
      const l2 = dx * dx + dy * dy;
      const t = l2 > 0 ? Math.min(1, Math.max(0, ((px - ax) * dx + (py - ay) * dy) / l2)) : 0;
      const d = Math.hypot(px - ax - t * dx, py - ay - t * dy) * M_POR_GRADO;
      if (d < best.distM) best = { km: l.cum[i] + t * (l.cum[i + 1] - l.cum[i]), distM: d };
    }
    return best;
  };
  const n = l.coords.length - 1;
  if (cercaDe !== undefined) {
    const cerca = buscar(segmento(l, cercaDe - 5), Math.min(segmento(l, cercaDe + 5) + 1, n));
    if (cerca.distM <= MAX_AJUSTE_M) return cerca;
  }
  return buscar(0, n);
}

/** Estado de un camión en pantalla. */
export type Seguimiento = {
  pos: LngLat;
  rumbo: number;
  /** vía y sentido que sigue ("LIM-AQP:ida"); null si va fuera de una vía conocida */
  clave: string | null;
  linea: Linea | null;
  km: number;
  kmObs: number;
  obsEn: number;
  /** km por ms de reloj real */
  ritmo: number;
  /** destino fuera de la vía (o detenido en la berma) */
  destino: LngLat;
};

export type Lectura = {
  pos: LngLat;
  velocidadKmh: number;
  /** vía del viaje en su sentido; null si no hay viaje o no se conoce la geometría */
  linea: Linea | null;
  clave: string | null;
  /** velocidad del replay (0 en pausa) */
  replay: number;
};

export function nuevo(l: Lectura, ahora: number): Seguimiento {
  const s: Seguimiento = { pos: l.pos, rumbo: 0, clave: null, linea: null, km: 0, kmObs: 0, obsEn: ahora, ritmo: 0, destino: l.pos };
  observar(s, l, ahora, true);
  return s;
}

/** Incorpora una lectura del polling. `inicial` = primera vez: se ubica sin animar. */
export function observar(s: Seguimiento, l: Lectura, ahora: number, inicial = false): void {
  s.destino = l.pos;
  const loc = l.linea ? ubicar(l.linea, l.pos, s.clave === l.clave ? s.km : undefined) : null;
  if (!l.linea || !loc || loc.distM > MAX_AJUSTE_M) {
    if (s.linea === null && !inicial) {
      // fuera de la vía: el rumbo sale del desplazamiento (~30 m para que no sea ruido del GPS)
      if (Math.hypot((l.pos[0] - s.pos[0]) * Math.cos(l.pos[1] * Math.PI / 180), l.pos[1] - s.pos[1]) * M_POR_GRADO > 30) {
        s.rumbo = unwrap(s.rumbo, rumbo(s.pos, l.pos));
      }
    }
    s.linea = null;
    s.clave = null;
    if (inicial) s.pos = l.pos;
    return;
  }
  const cambio = s.clave !== l.clave;
  s.linea = l.linea;
  s.clave = l.clave;
  if (inicial || cambio || Math.abs(loc.km - s.km) > SALTO_KM) {
    s.km = loc.km;
    s.pos = l.velocidadKmh < 1 ? l.pos : along(l.linea, loc.km);
    s.rumbo = unwrap(s.rumbo, rumboEn(l.linea, loc.km));
  }
  s.kmObs = loc.km;
  s.obsEn = ahora;
  s.ritmo = (l.velocidadKmh * l.replay) / 3_600_000;
}

/** Avanza el dibujo `dt` ms. Devuelve true si algo cambió (para no repintar de más). */
export function avanzar(s: Seguimiento, ahora: number, dt: number): boolean {
  const a = 1 - Math.exp(-dt / SUAVIZADO_MS);
  const antes = s.pos;
  if (s.linea) {
    const prediccion = s.kmObs + s.ritmo * Math.min(ahora - s.obsEn, HORIZONTE_MS);
    const diff = prediccion - s.km;
    // nunca retrocede por una corrección chica: espera a que la predicción lo alcance
    if (diff > 0) s.km += diff * a;
    if (s.ritmo === 0 && Math.abs(diff) < 0.001) {
      // detenido: si está en la berma se queda donde lo dejó la lectura
      s.pos = [s.pos[0] + (s.destino[0] - s.pos[0]) * a, s.pos[1] + (s.destino[1] - s.pos[1]) * a];
    } else {
      s.pos = along(s.linea, s.km);
      const r = unwrap(s.rumbo, rumboEn(s.linea, s.km));
      s.rumbo += (r - s.rumbo) * (1 - Math.exp(-dt / SUAVIZADO_RUMBO_MS));
    }
  } else {
    s.pos = [s.pos[0] + (s.destino[0] - s.pos[0]) * a, s.pos[1] + (s.destino[1] - s.pos[1]) * a];
  }
  return antes[0] !== s.pos[0] || antes[1] !== s.pos[1];
}

/** Dónde estará el camión en `ms` (para que el vuelo de la cámara llegue a donde va, no a donde estaba). */
export function adelantado(s: Seguimiento, ms: number): LngLat {
  return s.linea ? along(s.linea, s.km + s.ritmo * ms) : s.pos;
}

/** Los últimos `km` recorridos (estela del camión seleccionado). */
export function estela(s: Seguimiento, km = 3): LngLat[] {
  if (!s.linea) return [];
  const l = s.linea;
  const desde = Math.max(0, s.km - km);
  const pts: LngLat[] = [along(l, desde)];
  for (let i = segmento(l, desde) + 1; i < l.coords.length && l.cum[i] < s.km; i++) pts.push(l.coords[i]);
  pts.push(s.pos);
  return pts;
}

/** Metros por píxel a una latitud y zoom (teselas de 512 px, como Mapbox y MapLibre). */
export function metrosPorPixel(lat: number, zoom: number): number {
  return (40_075_016.686 * Math.cos(lat * Math.PI / 180)) / (512 * 2 ** zoom);
}
