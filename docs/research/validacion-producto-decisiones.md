# Validación del producto · decisiones del grilling

Registro de las decisiones tomadas en las sesiones de grilling (skill `grilling`) sobre [`PRODUCT_CONTEXT_FLEET_INTELLIGENCE.md`](../product/PRODUCT_CONTEXT_FLEET_INTELLIGENCE.md). Cada decisión cita la evidencia que la respalda cuando existe.

## Evidencia disponible

| Investigación | Archivo | Veredicto corto |
|---|---|---|
| FEAD EMS dataset-2 | [`fead-ems-dataset2-perfil.md`](fead-ems-dataset2-perfil.md) | Viable para replay y consumo observado (`x7001` L/h, `x7002` L acumulados). ~1 Hz, no 100 ms. Sin altitud, carga, temperatura ni fallas. Sin licencia; anonimizar matrículas/IMEI. |
| Zavu / WhatsApp | [`zavu-whatsapp-capacidades.md`](zavu-whatsapp-capacidades.md) | Tools del agente pueden llamar nuestra API por HTTP; Zavu no consume MCP. Alertas fuera de 24 h requieren plantilla aprobada (24–72 h). Free: 2 000 msg/mes, 100/día. |
| Perfil del piloto desde FEAD | [`fead-perfil-piloto.md`](fead-perfil-piloto.md) | Troncal interprovincial de larga distancia, tractocamiones 24/7 (~1 200 km/día, 32,5 L/100 km). Ralentí = 0,8 % del combustible. La pendiente domina el consumo por tramo. `r_level` no distingue urbano/carretera. |

## Decisiones

| # | Tema | Decisión | Fecha |
|---|---|---|---|
| D1 | Plazo y capacidad | 2 días hasta la demo; ~32 h por persona, desarrollando con agentes y subagentes. | 2026-10-18 |
| D2 | Perfil del piloto | Se deriva de los datos reales de FEAD EMS dataset-2, no se elige a priori. | 2026-10-18 |
| D3 | Nombre y marca | "Cuadra" deja de ser el nombre. Se reutiliza su sistema visual (color, tipografía, tokens); el logo se retira hasta tener uno nuevo. Placeholder: *Fleet Intelligence*. | 2026-10-18 |
| D4 | Web | P0. Primero landing nueva, luego dashboard mínimo (camiones, alertas con evidencia, mapa del replay, controles de replay). Dueña: Lian. | 2026-10-18 |
| D5 | Roles | Juan: datos + replay + hub + baseline. Joseph: Zavu + agente + MCP + alertas + coordinación. Contrato entre ambos: la Domain API. | 2026-10-18 |
| D6 | Stack | Backend en **Python / FastAPI** en **GCP Cloud Run**, 1 instancia sin cold start. Perfilado y baseline en Python. **Servidor MCP en Cloudflare** (TS), llamando a la Domain API. Zavu en TS. | 2026-10-18 |
| D7 | MCP | Se mantiene en P0; Zavu no consume MCP, así que sirve a agentes externos y como plan B del agente. Número de tools: ver D14. | 2026-10-18 |
| D8 | Plantilla WhatsApp | Enviar hoy a revisión una plantilla *utility* de alerta; plan B: abrir ventana de 24 h antes de la demo. Guardar tarjeta en Zavu (tope 250/día). | 2026-10-18 |
| D9 | Recorte | Fuera: todo P1, Demo C (mantenimiento) y research de memoria contextual (Postgres+PostGIS queda como ADR). P0 = Demo A + Demo B + web. | 2026-10-18 |
| D10 | Anomalías | Episodios reales para la narrativa + anomalías sintéticas etiquetadas (`synthetic_demo`) para medir el detector. | 2026-10-18 |
| D11 | Datos en el repo | Sin datos crudos ni licencia: script de descarga + extracción de 3–5 camiones + anonimización. Se cita el paper. | 2026-10-18 |
| D12 | Proceso | Cada dev arranca con un ticket de `grill-with-docs` sobre los tickets que va a tomar. | 2026-10-18 |
| D13 | Tests | Harness con capa e2e permanente: Playwright en la web, tests en el backend y tests en el servicio MCP de Cloudflare. | 2026-10-18 |
| D14 | Tools | 7: `get_fleet_overview`, `get_vehicle_status`, `get_trip_status`, `get_fuel_analysis` (incluye desglose por tramo y sentido; `r_level` no sirve, ver D27), `get_operational_bottlenecks`, `get_alerts` + `control_replay` (escritura, solo MCP). Sin `predict_trip_fuel`. | 2026-10-18 |
| D15 | Base de datos | **Cloud SQL** Postgres 16 + PostGIS (no Supabase: el subconjunto ronda 0,8–1,3 GB y el free de Supabase es 500 MB). Telemetría 1 Hz solo de 3–5 camiones; agregados por minuto/tramo; días 1–12 = baseline, 13–19 = replay. | 2026-10-18 |
| D16 | Cloud Run | `min=max=1`, `--no-cpu-throttling`; replay como tarea asyncio dentro de FastAPI. | 2026-10-18 |
| D17 | Tickets | GitHub Issues con dependencias nativas (`to-tickets`); `docs/dev/mapa-dependencias.md` como vista Mermaid. **Sin PRs**: merge local a `main` con tests en verde, como en Tesorito. | 2026-10-18 |
| D18 | Grilling por dev | Ticket de `grill-with-docs` (máx. 1 h) que bloquea los tickets de cada dev; produce ADRs y términos en `CONTEXT.md`. | 2026-10-18 |
| D19 | Repo | `backend/`, `data/` (Juan) · `mcp/`, `zavu/` (Joseph) · `web/` (Lian) · `e2e/` compartido · `CONTEXT.md` en la raíz. | 2026-10-18 |
| D20 | Contrato | OpenAPI de FastAPI versionado en `backend/openapi.json`; tipos TS generados para `mcp/`, `zavu/`, `web/`. Primer ticket de Juan publica el contrato con datos de ejemplo. | 2026-10-18 |
| D21 | Harness | pytest+httpx (backend, PostGIS en Docker), vitest + vitest-pool-workers (MCP), Playwright (web y e2e contra URL pública). Checks obligatorios en PR. Ticket 0. | 2026-10-18 |
| D22 | Web stack | Vite + TS (framework a decidir por Lian en su grilling), MapLibre, Cloudflare Pages. | 2026-10-18 |
| D23 | Auth | `X-API-Key` en rutas de MCP, Zavu y control de replay; lecturas del dashboard públicas (datos anónimos). Secrets en Secret Manager / Worker / Zavu. | 2026-10-18 |
| D24 | Infra GCP | La levanta Joseph (proyecto, Cloud SQL, Cloud Run, Secret Manager, Artifact Registry). | 2026-10-18 |
| D25 | Perfil del piloto | **Transporte troncal interprovincial de larga distancia** con tractocamiones pesados en relevo 24/7, en corredores fijos (p. ej. Harbin–Guangzhou ~3 450 km). Fuente: `fead-perfil-piloto.md`. | 2026-10-18 |
| D26 | Geografía y narrativa | Se muestran las trayectorias reales en China, sin reproyectar a Perú: "telemetría real de una flota en China (FEAD, abril 2020), reproducida; fletes, conductores y mensajes sintéticos". Panamericana / Carretera Central solo como analogía oral. | 2026-10-18 |
| D27 | Línea base | **Por tramo y sentido de corredor, comparando con pares**, no por camión (una baseline por camión da falsos positivos en cada subida). El ralentí se muestra como evidencia, no como causa principal del sobreconsumo. Candidatos: T03, T04, T28, T22, T09 (control) y T07 (falso positivo evitado). | 2026-10-18 |
| D28 | Región GCP | `us-central1` para Cloud Run y Cloud SQL (misma región). | 2026-10-18 |
| D29 | Modelo de dominio | Viaje ≠ flete (1:1 en la demo); tramo ≈ 10 km por sentido; sobreconsumo → anomalía → alerta; parada ≥ 10 min; cuello de botella = tiempo perdido sin explicar; reporte en vivo = `human_reported`; roles: solo gestor de flota y conductor. Glosario en [`CONTEXT.md`](../../CONTEXT.md), ADRs 0001–0007 en [`docs/adr/`](../adr/). | 2026-10-18 |
| D30 | Equipo y carpetas | Se suma Ismael (@Ismaelrojas0112) para la landing. `web/` pasa a ser la landing (Ismael) y el dashboard vive en `dashboard/` (Lian, @KevinPinto123). Corrige D4 y D19. | 2026-10-18 |
| D31 | Tickets | 22 tickets publicados como sub-issues de la spec #4 (#5–#26), con dependencias nativas. Ver `docs/dev/mapa-dependencias.md`. | 2026-10-18 |

## Preguntas abiertas

Ninguna a nivel de producto. Las de implementación se resuelven en los tickets de grilling de cada dev (#7, #8, #9).
