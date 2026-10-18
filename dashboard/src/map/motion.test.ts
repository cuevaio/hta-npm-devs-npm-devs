import { describe, expect, it } from "vitest";
import { adelantado, along, avanzar, estela, invertida, linea, metrosPorPixel, nuevo, observar, rumboEn, ubicar, type LngLat } from "./motion";

// Serpentín: media vuelta de ~1 km de radio alrededor de (-76, -12), como una curva de la Carretera Central.
const R = 1 / 111.195; // ~1 km en grados
const k = Math.cos((12 * Math.PI) / 180);
const curva: LngLat[] = Array.from({ length: 181 }, (_, i) => {
  const a = (i * Math.PI) / 180;
  return [-76 + (R * Math.sin(a)) / k, -12 + R * Math.cos(a)];
});
const L = linea(curva);
const distM = (p: LngLat) => ubicar(L, p).distM;

describe("vía", () => {
  it("mide el largo de la media vuelta (π km)", () => {
    expect(L.largo).toBeCloseTo(Math.PI, 2);
  });
  it("along e ubicar son inversos", () => {
    for (const km of [0.1, 1.2, 2.9]) expect(ubicar(L, along(L, km)).km).toBeCloseTo(km, 4);
  });
  it("el rumbo sigue la tangente: al este arriba, al sur a mitad, y al revés en vuelta", () => {
    // a 50 m del inicio la tangente ya giró 0,05 rad (2,9°) en una curva de 1 km de radio
    expect(Math.abs(rumboEn(L, 0.05) - 92.9)).toBeLessThan(0.5);
    expect(Math.abs(rumboEn(L, L.largo / 2) - 180)).toBeLessThan(0.5);
    // en vuelta arranca abajo yendo al este y gira hacia el norte
    expect(Math.abs(rumboEn(invertida(L), 0.05) - 87.1)).toBeLessThan(0.5);
  });
});

describe("seguimiento", () => {
  const lectura = (km: number, v = 80, replay = 60) => ({ pos: along(L, km), velocidadKmh: v, linea: L, clave: "C:ida", replay });

  it("entre dos lecturas recorre la curva, no la recta", () => {
    let t = 0;
    const s = nuevo(lectura(0.2), t);
    observar(s, lectura(2.8), t); // salto de 2,6 km: la cuerda cruzaría por adentro de la curva
    let peor = 0;
    for (let i = 0; i < 400; i++) {
      t += 16;
      avanzar(s, t, 16);
      peor = Math.max(peor, distM(s.pos));
    }
    expect(peor).toBeLessThan(2);
    expect(s.km).toBeGreaterThan(2.5);
  });

  it("avanza a la velocidad del replay sin nuevas lecturas, y no se escapa", () => {
    const s = nuevo(lectura(0.5, 72, 60), 0); // 72 km/h x 60 = 1,2 km por segundo
    for (let t = 16; t <= 1000; t += 16) avanzar(s, t, 16);
    expect(s.km).toBeGreaterThan(1.2);
    expect(s.km).toBeLessThan(1.75);
    for (let t = 1016; t <= 20000; t += 16) avanzar(s, t, 16);
    expect(s.km).toBeLessThanOrEqual(0.5 + 1.2 * 4 + 1e-6); // horizonte de 4 s
  });

  it("una corrección chica hacia atrás no lo hace retroceder", () => {
    const s = nuevo(lectura(1.5, 0, 1), 0);
    for (let t = 16; t <= 500; t += 16) avanzar(s, t, 16);
    observar(s, lectura(1.45, 0, 1), 500);
    const antes = s.km;
    for (let t = 516; t <= 2000; t += 16) avanzar(s, t, 16);
    expect(s.km).toBeGreaterThanOrEqual(antes);
  });

  it("un seek (salto de más de 3 km) se aplica de golpe", () => {
    const larga = linea([[-76, -12], [-76, -12.2]]);
    const s = nuevo({ pos: along(larga, 1), velocidadKmh: 80, linea: larga, clave: "X:ida", replay: 1 }, 0);
    observar(s, { pos: along(larga, 15), velocidadKmh: 80, linea: larga, clave: "X:ida", replay: 1 }, 100);
    expect(s.km).toBeCloseTo(15, 3);
  });

  it("detenido en la berma se queda donde cayó la lectura", () => {
    const berma: LngLat = [along(L, 1)[0] + 0.00006, along(L, 1)[1]];
    const s = nuevo({ pos: berma, velocidadKmh: 0, linea: L, clave: "C:ida", replay: 60 }, 0);
    for (let t = 16; t <= 1000; t += 16) avanzar(s, t, 16);
    expect(Math.hypot(s.pos[0] - berma[0], s.pos[1] - berma[1])).toBeLessThan(1e-7);
  });

  it("fuera de la vía va directo a la lectura y toma el rumbo del desplazamiento", () => {
    const s = nuevo({ pos: [-70, -15], velocidadKmh: 50, linea: null, clave: null, replay: 1 }, 0);
    observar(s, { pos: [-69.99, -15.01], velocidadKmh: 50, linea: null, clave: null, replay: 1 }, 2000);
    for (let t = 2016; t <= 4000; t += 16) avanzar(s, t, 16);
    expect(s.pos[0]).toBeCloseTo(-69.99, 4);
    expect(s.rumbo).toBeGreaterThan(90);
    expect(s.rumbo).toBeLessThan(180);
  });

  it("adelantado y estela", () => {
    const s = nuevo(lectura(2, 72, 60), 0);
    expect(ubicar(L, adelantado(s, 1000)).km).toBeCloseTo(3.1, 1);
    const e = estela(s, 1);
    expect(e.length).toBeGreaterThan(10);
    expect(ubicar(L, e[0]).km).toBeCloseTo(1, 2);
  });
});

it("metros por píxel: zoom 17 en Lima ronda 0,6 m (teselas de 512 px)", () => {
  expect(metrosPorPixel(-12, 17)).toBeGreaterThan(0.5);
  expect(metrosPorPixel(-12, 17)).toBeLessThan(0.7);
});
