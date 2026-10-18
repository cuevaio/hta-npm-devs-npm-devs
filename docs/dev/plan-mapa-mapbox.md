# Plan: mapa del dashboard en Mapbox, con camiones que van sobre la pista

> 2026-10-18 · Estado: implementado (D40). Cambios respecto del plan: la distancia recorrida y el rumbo se calculan en el cliente (`motion.ts`) en vez de en `VehiculoResumen`; el camión 3D (glTF) no se hizo: se usa el SVG acostado sobre la pista; no se agregó CSP porque el dashboard no tiene ninguna configurada. Dueño del dashboard: Lian (@KevinPinto123).
> Referencia: Vora.IA (`vora-frontend/src/components/map/views/MapboxMapView.tsx`, `docs/Map-route/Prompt_MapBox_Vora.md`).

## 1. Por qué hoy el camión "pasa por encima de las casas"

Son tres causas que se suman. Cambiar a Mapbox no corrige ninguna por sí solo.

| # | Causa | Dónde | Medida |
|---|---|---|---|
| 1 | **El frontend interpola en línea recta entre dos lecturas.** `glide()` mueve el marcador del punto A al B en 1,8 s cada vez que llega el polling (cada 2 s). A 60x de replay, el camión avanza unos 2,7 km entre lecturas: la recta corta curvas y serpentines. | `dashboard/src/components/FleetMap.tsx` (`glide`) | Error de cientos de metros en curvas |
| 2 | **La ruta guardada está remuestreada cada 100 m.** OSRM devuelve un vértice cada ~24 m (7 m en curvas) y `rutas.py` lo reduce a uno cada 100 m. En la Carretera Central eso aparta el trazo de la pista real. | `data/fleetdata/rutas.py` (`PASO_M = 100`) | Desvío medio 4,9 m, p95 16 m, **máximo 62 m** (medido sobre Lima–Huancayo) |
| 3 | **Ruido de GPS y paradas "al costado".** El generador suma ±3 m de ruido y deja las paradas 30 m al norte de la vía, sin mirar hacia dónde está la berma. | `data/fleetdata/peru.py` (`_ruido`, `_quieto`) | Hasta 30 m fuera de la pista |

Por eso el plan ataca primero la geometría (datos), después el movimiento (frontend) y recién al final la cámara y el estilo.

## 2. Qué se toma de Vora y qué no

| Patrón de Vora | Se adopta | Ajuste para Certera |
|---|---|---|
| `mapbox-gl` 3.x directo, sin `react-map-gl`; el mapa se crea en un `useEffect` con dependencias vacías y se destruye en el cleanup | Sí | Igual. Vite no necesita `transpilePackages` ni `dynamic(ssr:false)` |
| Estilo **Mapbox Standard** configurado en `style.load` con `setConfigProperty('basemap', …)`: `lightPreset`, `theme`, `show3dObjects`, POI | Sí | `lightPreset: 'night'` y `theme: 'monochrome'` para calzar con la marca, que es de tinta y solo oscura. Sin POI comerciales. Edificios 3D solo con zoom ≥ 15 |
| Restaurar el viewport si un cambio de config recarga el estilo (`once('style.load', restoreViewport)`) | Sí | Igual |
| Cámara cinemática de dos fases: `flyTo` con `curve: 1.3`, `pitch: 20` y llegada a zoom alto; en `moveend`, un `easeTo` que inclina a `pitch: 62` | Sí, al seleccionar un tráiler | `bearing` = rumbo del camión, no un −20 fijo. Después sigue la **fase 3, seguimiento**, que Vora no tiene (§5) |
| Abortar la animación con `dragstart`, `touchstart`, `wheel` o `mousedown` del usuario | Sí | Si el usuario mueve el mapa, se sale del seguimiento |
| `essential: true` (ignora `prefers-reduced-motion`) | **No** | El dashboard ya respeta reduced-motion (`reduce()`). Se conserva: sin vuelo y con `jumpTo` |
| Rutas como `line` layer desde un GeoJSON source | Sí | Los cuatro corredores, debajo de las etiquetas (`slot: 'middle'`) |
| Token público en el bundle y restringido por URL en la cuenta de Mapbox; CSP con `worker-src blob:` | Sí | `VITE_MAPBOX_TOKEN` en Vercel, nunca en el repo. URLs permitidas: dominio de producción, `https://*.vercel.app` y `http://127.0.0.1:4173` |
| `MapProviderSwitcher` (Google y Mapbox) | No | Un solo proveedor. MapLibre queda como fallback sin token, para CI (§7) |

## 3. Fase 0: spike (medio día, se descarta después)

Hay que responder tres preguntas antes de comprometer el diseño:

1. **Alineación:** ¿la geometría de OSRM (OSM) calza con las calles de Mapbox Standard a zoom 17–18 en tres lugares (Ticlio, el serpentín de la Cuesta de Pasamayo y la entrada a Arequipa)? Si no calza, la Fase 1 baja la geometría con la **Mapbox Directions API** (`geometries=polyline6&overview=full`) en vez de OSRM.
2. **Camión 3D:** ¿el `model` layer de Mapbox v3 (glTF) mueve 6 tractocamiones a 60 fps actualizando el source por frame? Si no, se usa el SVG actual como `Marker` con `rotationAlignment: 'map'` y `pitchAlignment: 'map'`, que queda "acostado" sobre la pista al inclinar la cámara.
3. **Tests sin red:** ¿Playwright puede levantar `mapbox-gl` con un estilo vacío y sin token? Si no, el componente cae a MapLibre cuando no hay `VITE_MAPBOX_TOKEN`, que es como corre hoy (§7).

Entregable: tres capturas, un sí o no por pregunta y la decisión anotada como D38 en `docs/research/validacion-producto-decisiones.md`.

## 4. Fase 1: geometría fiel a la pista (data)

- `rutas.py` guarda la **geometría completa** de OSRM (o de Mapbox Directions, según el spike) como polyline6, unos 400 KB para los cuatro corredores. El remuestreo a 100 m queda solo como malla de la física (`fisica.py`).
- `peru.py` interpola las posiciones sobre la geometría completa por distancia acumulada, no sobre la malla de 100 m.
- Paradas: desplazamiento perpendicular a la derecha del sentido de marcha (unos 6 m, en la berma), no 30 m al norte.
- El ruido de GPS se mantiene en los datos porque es realista. El frontend dibuja la posición ajustada a la vía (§5).
- Salida nueva: `corridors.geojson` con cada corredor como LineString de ida.
- **Tests:** p95 de la distancia de cada lectura en marcha a la geometría completa < 4 m; ninguna lectura > 10 m sin contar paradas; regenerar los datos da la misma salida (sigue siendo determinista).

## 5. Fase 2: el backend entrega lo que el mapa necesita

- Migración: tabla `corridors (corridor, via, geom geography(LineString))`, cargada por `load_demo_data.py` desde `corridors.geojson`.
- `GET /v1/corridors` devuelve un FeatureCollection con la geometría de cada corredor. Es estática, así que se cachea en el cliente.
- `VehiculoResumen` suma `corredor`, `sentido`, `km_ruta` (distancia recorrida en el sentido del viaje, calculada en PostGIS con `ST_LineLocatePoint` sobre el corredor) y `rumbo_deg` (tangente de la vía en ese punto). Así el frontend no adivina el rumbo entre lecturas, como hace hoy con `MIN_MOVE_DEG`.
- **Tests por HTTP:** `km_ruta` crece monótonamente durante un viaje del fixture; `rumbo_deg` coincide con la tangente de la vía con ±10°; `/v1/corridors` trae los cuatro corredores. Hay que regenerar el contrato con `gen-api.sh`.

## 6. Fase 3: movimiento realista (frontend)

Módulo puro `dashboard/src/map/motion.ts`, sin dependencia de Mapbox, para poder testearlo aparte:

- **Seguir la vía, no la recta.** Cada camión tiene un objetivo `(corredor, sentido, km_ruta)`. En cada frame (`requestAnimationFrame`), la posición dibujada es `along(línea, km)`, con `km` que avanza a `velocidad_kmh × velocidad_replay`. Entre dos lecturas el camión recorre las curvas reales.
- **Corrección suave.** Cuando llega una lectura nueva: si el error es menor a ~1 km, se compensa en 1 s ajustando la velocidad, sin saltar ni retroceder. Si es mayor (por un `seek`), salta directo.
- **Rumbo de la vía.** El rumbo sale de la tangente de la línea en `km`, suavizado para que no "tiemble" en serpentines. El camión rota con `rotationAlignment: 'map'`.
- **Fuera de viaje** (en terminal o detenido): se queda en la última posición y se ve el halo de ralentí que ya existe.
- **Estela:** los últimos ~3 km recorridos como `line` con `line-gradient`, que se desvanece hacia atrás. Solo en el camión seleccionado, para no saturar.
- **Reduced motion:** sin animación por frame; la posición se actualiza en cada lectura.
- Se hace una sola actualización de source por frame para todos los camiones; nada de 6 `setLngLat` independientes.

## 7. Fase 4: Mapbox en el dashboard

- `mapbox-gl@3` en `dashboard/package.json`, más su CSS. Se quita `maplibre-gl` solo si el spike resuelve los tests sin red; si no, queda como fallback sin token.
- `FleetMap.tsx` pasa a ser una fachada: con `VITE_MAPBOX_TOKEN`, usa `MapboxFleetMap`; sin token (CI, Playwright), usa el MapLibre actual. Las dos usan `motion.ts`.
- Capas en Standard: corredores (`slot: 'middle'`, `line-emissive-strength: 1` para que se lean en `night`), estela, camiones (model o marker según el spike) y terminales como símbolos con su nombre.
- `vercel.json`: CSP con `api.mapbox.com`, `events.mapbox.com`, `*.tiles.mapbox.com` y `worker-src blob:`.
- Atribución de Mapbox y OSM visible (lo exigen los términos).

## 8. Fase 5: cámara al seleccionar un tráiler

Al seleccionar un tráiler en la lista o con clic en el mapa:

1. **Vuelo:** `flyTo` hasta el camión con `zoom: 15.5`, `pitch: 20`, `curve: 1.3` y `duration: 2000`. Mapbox aleja la cámara al despegar y la acerca al llegar. Como el camión sigue moviéndose durante el vuelo, el destino se calcula 2 s adelante sobre la vía (`along(km + v·2s)`).
2. **Revelado:** en `moveend`, `easeTo` a `pitch: 60` y `bearing: rumbo − 15°` en 900 ms, con la misma curva de Vora. Se ve la pista en 3D y el camión de tres cuartos.
3. **Seguimiento:** en cada frame la cámara centra el camión (`jumpTo` con el centro interpolado) y gira el `bearing` hacia el rumbo con suavizado lento (~0,1 por frame). Así acompaña las curvas sin marear.
4. **Salida:** arrastrar, hacer zoom con la rueda o tocar el mapa termina el seguimiento (patrón de abort de Vora). Un botón "Ver flota" vuelve a `fitBounds` de todos los camiones con `pitch: 0`.
5. Cambiar de tráiler durante el vuelo cancela el `moveend` pendiente antes de arrancar el nuevo vuelo (igual que `flyRevealCleanupRef` en Vora).

## 9. Criterios de aceptación y tests

| Criterio | Cómo se prueba |
|---|---|
| A zoom 17, el camión en marcha nunca sale de la pista más de 5 m | Test de datos (Fase 1) y, en Playwright, comparar la posición dibujada con `along(línea, km)` en un frame |
| Entre dos lecturas el camión sigue la curva, no la recta | Test unitario de `motion.ts`: con dos lecturas en un serpentín, todos los puntos intermedios están a < 2 m de la línea |
| Seleccionar un tráiler vuela, inclina y sigue al camión | Playwright: después del clic, la cámara termina con `pitch` ≥ 55 y el centro a < 50 m del camión durante 3 s |
| Mover el mapa termina el seguimiento | Playwright: arrastrar y comprobar que el centro deja de seguir al camión |
| Reduced motion: sin vuelo ni animación por frame | Playwright con `reducedMotion: 'reduce'` |
| El token no está en el repo y la CSP no bloquea el worker | `git grep pk\.` vacío; smoke contra la URL de Vercel sin errores de consola |
| Sin token, CI sigue en verde | `make test-dashboard` sin `VITE_MAPBOX_TOKEN` |

`motion.ts` necesita un runner de tests unitarios en `dashboard/`: vitest, igual que `mcp/` y `zavu/`.

## 10. Orden, dependencias y esfuerzo

| Fase | Depende de | Carpeta | Esfuerzo estimado |
|---|---|---|---|
| 0 Spike | token de Mapbox | dashboard | 0,5 día |
| 1 Geometría fiel | 0 (fuente de la geometría) | data | 0,5–1 día |
| 2 Corredores, `km_ruta` y `rumbo_deg` | 1 | backend | 1 día |
| 3 Movimiento sobre la vía | 2 | dashboard | 1–1,5 días |
| 4 Mapbox Standard | 0 | dashboard | 1 día |
| 5 Cámara cinemática y seguimiento | 3, 4 | dashboard | 1 día |

Las fases 1–2 y la 4 pueden avanzar en paralelo. Antes de empezar se necesita **una cuenta de Mapbox con un token público restringido por URL**. El plan gratuito de Mapbox GL JS en web cubre 50 000 cargas de mapa al mes, de sobra para la demo.

## 11. Fuera de alcance

- Map matching en vivo contra la API de Mapbox: el ajuste a la vía se hace con nuestra geometría, sin llamadas por lectura.
- Tráfico en tiempo real y rutas alternativas.
- Cambiar los datos de fondo del replay (fechas, corredores).
