# Analítica sobre telemetría y reportes: GraphRAG vs Postgres tipado

> Fecha de la investigación: 2026-10-18. Alcance: MVP de hackathon de Certera (antes "Fleet Intelligence").
> Metodología: solo fuentes primarias (docs oficiales, repos de los propios proyectos, especificaciones, paper original). Cada afirmación lleva su URL. Lo que no se pudo verificar está marcado como **[NO VERIFICADO]**. Los bloques SQL son **bosquejos** (sketches), no probados contra los datos reales de FEAD.
> Contexto leído: `docs/product/PRODUCT_CONTEXT_CERTERA.md` (secciones 6-12), y de `/home/user/Projects/luca`: `docs/dev/plan-mcp-m5.md`, `CONTEXT.md`, `services/luca-mcp/src/{index,gasClient}.ts`, `wrangler.toml`, `README.md`.

---

## 0. Resumen y recomendación

**Recomendación: no usar GraphRAG. Usar Postgres (Supabase) con esquema relacional + PostGIS, herramientas MCP tipadas de solo lectura que devuelven análisis ya calculados por SQL, y pgvector/búsqueda de texto solo si los reportes de WhatsApp crecen más de lo que un filtro SQL puede manejar.**

Razones, en una línea cada una:

1. GraphRAG se definió para *sensemaking global sobre corpus de texto no estructurado* (preguntas tipo "¿cuáles son los temas principales?" sobre ~1 M de tokens), construyendo un grafo de entidades extraídas por LLM y resúmenes de comunidades. Este proyecto es lo contrario: series numéricas + entidades ya estructuradas con claves foráneas + unos pocos mensajes cortos. [paper](https://arxiv.org/abs/2404.16130), [docs](https://microsoft.github.io/graphrag/)
2. El grafo "vehículo-viaje-flete-conductor-reporte-evento-alerta" ya existe como esquema relacional con profundidad fija (1-2 joins). No hay recorridos multi-salto de profundidad variable que justifiquen un motor de grafos.
3. Apache AGE no aparece en las extensiones de Supabase (ver 1.3), y SQL/PGQ fue revertido de PostgreSQL 19 antes del release (ver 1.3). Un grafo aparte añade un segundo sistema que sincronizar sin ganancia demostrable.
4. TimescaleDB está **deprecado en Supabase con Postgres 17** y en Supabase solo hay edición Apache 2 (sin continuous aggregates, que viven bajo la licencia Timescale). Para este volumen no hace falta: tablas de rollup precalculadas + `pg_partman`/índices son suficientes (sección 2).
5. La carga de la demo (29 camiones, 26,1 M filas a ~10 Hz de FEAD, un mes) es "pequeña/mediana" para Postgres si se **reduce la resolución a 1 Hz o 1 min antes de cargar** (sección 2.1). Cargar las 26 M filas crudas no cabe en el plan Free de Supabase (500 MB).
6. Cruzar telemetría con reportes humanos es un **join temporal determinista en SQL** (rangos de tiempo + distancia + categoría). El LLM se usa en los bordes: extraer estructura del texto del conductor al ingresar, y redactar la respuesta; nunca para decidir hechos numéricos (sección 4).
7. Capa MCP: herramientas tipadas, solo lectura, que llaman a FastAPI (no a la base directamente), con límites de tamaño propios (el spec de MCP no pagina `tools/call`) y alcance por empresa aplicado en el servicio (sección 3).

**Cuándo GraphRAG sí valdría la pena** (sección 1.5): cientos o miles de narrativas largas (informes de incidentes, manuales, bitácoras) y preguntas globales de tema ("¿qué patrones recurrentes de fallas hay en la flota este trimestre?") que un `GROUP BY` sobre categorías extraídas no resuelve. No es el caso del MVP.

---

## 1. ¿Es GraphRAG el ajuste técnico correcto?

### 1.1 Qué es GraphRAG (definición original)

- Paper original: "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (Edge et al., Microsoft; v1 24-abr-2024, v2 19-feb-2025). Afirma que "RAG fails on global questions directed at an entire text corpus", porque esas preguntas son tareas de *resumen*, no de recuperación. Método: un LLM extrae un grafo de entidades del corpus, pregenera resúmenes por comunidad de entidades, y al consultar combina respuestas parciales de cada resumen. Evaluado en datasets de ~1 M de tokens para preguntas de "sensemaking" global. Fuente: <https://arxiv.org/abs/2404.16130>
- Documentación del proyecto: pipeline = TextUnits -> extracción de entidades/relaciones/afirmaciones -> comunidades jerárquicas (Leiden) -> resúmenes de comunidad. Modos de consulta: Global, Local (entidades y vecinos), DRIFT, Basic. Fuente: <https://microsoft.github.io/graphrag/> y <https://microsoft.github.io/graphrag/query/overview/>
- Qué problema dice resolver: el RAG base "struggles to connect the dots" y falla al "holistically understand summarized semantic concepts" sobre colecciones grandes. Fuente: <https://microsoft.github.io/graphrag/>
- Advertencias del propio repo: "GraphRAG indexing can be an expensive operation... start small"; el repo se describe como proyecto de investigación, mayormente en modo mantenimiento, "not an officially supported Microsoft offering". Fuente: <https://github.com/microsoft/graphrag>
- Costo de consulta Global: escanea todos los reportes de comunidad en estilo map-reduce, "costly in resources". Fuente: <https://microsoft.github.io/graphrag/query/overview/>

### 1.2 Qué necesita este proyecto

Según el handoff (`docs/product/PRODUCT_CONTEXT_CERTERA.md`, secs. 7-12):

| Necesidad | Naturaleza | Ajuste |
|---|---|---|
| Consumo, ralentí, desviación vs. baseline | Series numéricas, agregaciones por ventana | SQL |
| Estado de viaje/flete, asignaciones | Entidades con FKs | SQL |
| Cuellos de botella por viaje (paradas, duración, motivo) | Agrupar eventos estructurados | SQL |
| Reportes WhatsApp ("esperando descargar") | Pocos textos cortos | Extracción LLM a categoría + guardar texto original |
| Memoria contextual / RAG | Decisión abierta (sec. 12 del handoff) | Postgres primero; pgvector solo si hay volumen |

Dato de escala verificado: FEAD EMS dataset-2 = 29 camiones, 26 145 539 filas (abril 2020), engine status "for every 100 milliseconds"; licencia no declarada en el README; datasets solo como enlaces a Google Drive. Fuente: <https://github.com/Torreskai0722/FEAD>. Los reportes humanos, según el handoff, son sintéticos o muy pocos; no hay un corpus de texto.

### 1.3 Comparación de alternativas

| Opción | Encaje | Veredicto |
|---|---|---|
| **SQL relacional + herramientas tipadas** | Todas las consultas de la tabla anterior | **Recomendado.** |
| **Joins / CTE recursivas en Postgres** | `WITH RECURSIVE` permite recorridos de profundidad variable, con `CYCLE` para detectar ciclos. <https://www.postgresql.org/docs/current/queries-with.html> | Disponible si aparece un caso multi-salto; hoy no hay ninguno (ej.: efecto cascada de un retraso al siguiente viaje del mismo camión se resuelve con `lead()` sobre viajes ordenados). |
| **Apache AGE** | Extensión de Postgres, openCypher dentro de SQL; README: soporta PG 11-18, release 1.8.0 en el badge. <https://github.com/apache/age> | **No disponible en Supabase** (evidencia abajo). |
| **pgvector + híbrido** | Búsqueda semántica + texto completo con fusión RRF. Supabase documenta `hybrid_search`. <https://supabase.com/docs/guides/ai/hybrid-search> | Opcional, solo para "incidentes similares" sobre texto libre. |
| **Graph DB aparte** | Relaciones multi-salto de gran escala | No justificado: doble almacenamiento, sincronización y operación. [NO VERIFICADO con fuente primaria de un proveedor de grafos; la conclusión sale del análisis de las consultas del proyecto, no de una cita]. |
| **GraphRAG** | Corpus de texto grande, preguntas globales | No encaja (1.1 vs 1.2). |

**¿Soporta Supabase Apache AGE? Evidencia:**
- La página de docs de extensiones de Supabase no lista las extensiones en el texto recuperado, y la URL `https://supabase.com/docs/guides/database/extensions/age` devuelve 404 (consultada). <https://supabase.com/docs/guides/database/extensions>
- El repo `supabase/postgres` (imagen de Postgres de Supabase) define sus extensiones en `nix/ext/`; el listado incluye `pgvector`, `postgis`, `pg_partman`, `pg_cron`, `pgrouting`, `timescaledb`, `hypopg`, `index_advisor`, etc., y **no incluye ningún `age`**. Listado: <https://github.com/supabase/postgres/tree/develop/nix/ext>
- Conclusión: AGE no está soportado en Supabase gestionado. **[NO VERIFICADO al 100%]**: no pude obtener la lista completa renderizada del dashboard; confirmar en Dashboard > Database > Extensions antes de decidir. Existe `pgrouting` (versión 3.4.1 para PG 15 y 17 según <https://github.com/supabase/postgres/blob/develop/nix/ext/versions.json>) y Supabase publicó una guía de pgRouting como grafo en Postgres: <https://supabase.com/blog/pgrouting-postgres-graph-database>

**SQL/PGQ nativo en PostgreSQL 19:** se commiteó el 2026-03-16 ([commitfest 4904](https://commitfest.postgresql.org/patch/4904/)), pero el anuncio oficial de PostgreSQL 19 Beta 4 (2026-09-24) lista "Revert SQL/PGQ (property graph query) support". Fuente: <https://www.postgresql.org/about/news/postgresql-19-beta-4-released-3386/>. No planificar sobre esto. Además Supabase ofrece Postgres 15 y 17 (`ansible/vars.yml`: <https://github.com/supabase/postgres/blob/develop/ansible/vars.yml>), no 19.

### 1.4 Por qué "datos relacionales" no implica "necesito grafo"

Un modelo relacional ya representa relaciones. Un motor de grafos aporta valor cuando las consultas son recorridos de longitud variable o algoritmos de grafo (caminos, comunidades, centralidad) sobre muchas aristas. Aquí las rutas son fijas: `alert -> operational_event -> trip -> (vehicle, shipment, driver)` y `human_report -> trip`. Son joins de 2-3 saltos con índices en FK. [Razonamiento propio; apoyado en el esquema del handoff sec. 7.]

### 1.5 Cuándo GraphRAG SÍ valdría la pena (disparadores)

Reconsiderar solo si se cumplen **varios**:
1. Hay un corpus real de texto no estructurado del orden de cientos a miles de documentos largos (informes de incidente, manuales de taller, bitácoras de conductores), no mensajes de una línea. (El paper evalúa en ~1 M de tokens: <https://arxiv.org/abs/2404.16130>.)
2. Las preguntas son globales y temáticas ("¿cuáles son los modos de falla recurrentes en toda la flota?") y un `GROUP BY categoria` sobre campos extraídos por LLM + búsqueda híbrida no las responde con calidad aceptable.
3. Las entidades relevantes solo existen dentro del texto (no están en el esquema) y hay que relacionarlas entre documentos.
4. Hay presupuesto para indexado caro y reindexado (el repo advierte del costo: <https://github.com/microsoft/graphrag>).

Camino de menor costo antes de GraphRAG: extraer con LLM `{categoria, entidad, severidad}` por reporte -> columnas SQL -> agregaciones; luego pgvector/híbrido; luego (si falla) GraphRAG.

---

## 2. Analítica rápida y barata en Supabase/Postgres (series temporales + geoespacial)

### 2.1 Dimensionar antes de optimizar

- FEAD: 26 145 539 filas, 29 camiones, ~10 Hz. <https://github.com/Torreskai0722/FEAD>
- Supabase Free: 500 MB de base de datos; Pro: desde 25 USD/mes con 8 GB de disco incluido; proyectos Free inactivos se pausan tras 1 semana. <https://supabase.com/pricing>, <https://supabase.com/docs/guides/platform/manage-your-usage/disk-size>
- Estimación propia **[no medida]**: 26 M filas con ~10 columnas numéricas más índices probablemente superan 500 MB con holgura. Medir con `pg_total_relation_size` tras cargar una muestra.
- Decisión práctica: el replay del handoff ya exige batching (sec. 6.2). Cargar **resolución reducida** (p. ej. 1 Hz, o agregados de 1 min con min/avg/max por señal) y solo los camiones usados en la demo. 1 Hz equivale a ~1/10 de las filas (aritmética sobre los 10 Hz nominales; el handoff advierte que la frecuencia real puede variar por archivo). Conservar el crudo en archivos (Parquet/CSV) fuera de la DB.

### 2.2 Disponibilidad de TimescaleDB en Supabase (verificado)

- Docs de Supabase: "The `timescaledb` extension is deprecated in projects using Postgres 17." Sigue soportada en Postgres 15, pero debe eliminarse antes de pasar a 17. Se redirige a "native partitioning managed by `pg_partman`". <https://supabase.com/docs/guides/database/extensions/timescaledb>
- Los builds de timescaledb en la imagen de Supabase listan solo PG 15 (versiones 2.9.1 y 2.16.1). <https://github.com/supabase/postgres/blob/develop/nix/ext/versions.json>
- "Supabase projects come with TimescaleDB Apache 2 Edition"; las funciones solo de Community Edition "not available". <https://supabase.com/docs/guides/database/extensions/timescaledb>
- Los continuous aggregates están en el directorio `tsl/` de timescaledb, que se licencia bajo Timescale License (no Apache): <https://github.com/timescale/timescaledb/blob/main/LICENSE> y <https://github.com/timescale/timescaledb/tree/main/tsl> (README lista Continuous Aggregates, Compression). Inferencia: **continuous aggregates y compresión no están disponibles en Supabase** (Apache 2 edition). La doc de Supabase no lo dice con esas palabras **[inferencia, no cita directa]**.
- Los continuous aggregates son "a TimescaleDB-only feature"; funcionan como materialized views con refresco incremental. <https://www.tigerdata.com/docs/use-timescale/latest/continuous-aggregates/about-continuous-aggregates>
- Conclusión: **no depender de TimescaleDB**. Alternativas nativas abajo.

### 2.3 Particionado

- Cuándo conviene: "worthwhile only when a table would otherwise be very large... a rule of thumb is that the size of the table should exceed the physical memory of the database server." <https://www.postgresql.org/docs/current/ddl-partitioning.html>
- La poda de particiones depende de las restricciones de la clave de partición, no de índices; la PK/UNIQUE debe incluir la clave de partición; demasiadas particiones encarecen la planificación; retención = `DROP`/`DETACH` de partición (más rápido que `DELETE` y sin `VACUUM`). Misma URL.
- `pg_partman` 5.3.1 está disponible en Supabase para PG 15 y 17 (<https://github.com/supabase/postgres/blob/develop/nix/ext/versions.json>) y su doc muestra `create_parent` con `p_control`, `p_interval`, `p_premake` y programación con `pg_cron` o ejecución manual de `partman.run_maintenance_proc()`. <https://supabase.com/docs/guides/database/extensions/pg_partman>
- Recomendación MVP: FEAD es **un solo mes** (abril 2020), por lo que particionar por tiempo no aporta poda. **No particionar la tabla de telemetría en el MVP.** Si se carga un volumen grande, particionar por `vehicle_id` (hash) o por semana + `pg_partman`; decidir tras medir. Para producción "live" mensual/semanal por `event_time`.

### 2.4 Índices: B-tree vs BRIN

- BRIN: "designed for handling very large tables in which certain columns have some natural correlation with their physical location within the table"; índice muy pequeño; `pages_per_range` controla precisión/tamaño. <https://www.postgresql.org/docs/current/brin.html>
- Consecuencia: BRIN sobre `event_time` solo sirve si las filas se insertan **ordenadas por tiempo globalmente**. Si el replay carga camión por camión, la correlación física con `event_time` es baja. Verificar con `select correlation from pg_stats where tablename='telemetry_reading' and attname='event_time'` (columna `correlation` de `pg_stats`; **[no verificado en doc en esta investigación]**).
- Para consultas por vehículo y rango (la consulta dominante) usar **B-tree compuesto** `(vehicle_id, event_time)`, que además es la PK natural. BRIN solo como complemento barato si la tabla se vuelve muy grande y ordenada.
- Índices para rangos de tiempo de eventos: GiST sobre `tstzrange` y constraint de exclusión para evitar solapes. <https://www.postgresql.org/docs/current/rangetypes.html>

### 2.5 PostGIS

- Habilitar en un esquema dedicado (`extensions`), nunca `public`. Índice: `create index ... using gist (location)`. `<->` usa el índice en `order by` (kNN). <https://supabase.com/docs/guides/database/extensions/postgis>
- `geography` vs `geometry`: para un área pequeña, geometry con proyección adecuada rinde mejor; geography tiene menos funciones y más CPU. <https://postgis.net/docs/using_postgis_dbmanagement.html>
- BRIN en PostGIS: soporta geometry/geography, índice mucho menor y de construcción rápida, pero lectura más lenta, solo para tablas muy grandes ordenadas espacialmente y sin kNN. Misma URL.
- Recomendación: **no indexar espacialmente cada fila de telemetría**. Guardar `lat/lon` como columnas `real` en la telemetría (más barato) y crear `geography/geometry` + GiST solo en tablas pequeñas (`operational_event`, `stop`, `human_report`, hitos de viaje). La trayectoria de un viaje se puede guardar como `LineString` simplificada por viaje.

### 2.6 Rollups, vistas materializadas y refresco

- `REFRESH MATERIALIZED VIEW` reemplaza todo el contenido; `CONCURRENTLY` evita bloquear lecturas pero exige un índice `UNIQUE` sobre columnas simples y solo corre un refresco a la vez. <https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html>
- Dado que el replay es **determinista y finito**, lo más simple y barato es una **tabla de rollup normal** (`telemetry_1min`, `trip_summary`) poblada por un job al terminar de cargar (o por el replay mientras avanza), con `INSERT ... ON CONFLICT DO UPDATE` para idempotencia. Programar con `pg_cron` si se necesita periodicidad (Supabase doc de `pg_partman` muestra `cron.schedule`). Las herramientas MCP leen **solo** rollups y tablas de hechos de viaje, no la telemetría cruda.
- Sketch de tablas (no probado):

```sql
-- SKETCH
create table telemetry_1min (
  vehicle_id   int         not null,
  bucket       timestamptz not null,           -- date_trunc('minute', event_time), UTC
  n            int         not null,
  speed_avg    real, rpm_avg real,
  fuel_rate_avg real, fuel_l real,              -- litros estimados en el minuto (ver nota)
  lat_last     double precision, lon_last double precision,
  provenance   text not null default 'fead_observed',
  primary key (vehicle_id, bucket)
);
-- Nota: el handoff (sec. 8) exige llamar "estimación o proxy" a cualquier consumo
-- que no sea litros medidos; la resolución de combustible de EMS es 10 mL con 6.1%-6.5% de error (README FEAD).

create table trip_summary (
  trip_id uuid primary key, vehicle_id int not null,
  start_ts timestamptz, end_ts timestamptz,
  distance_km real, fuel_l_est real, idle_min real, stopped_min real,
  baseline_l_per_100km real, deviation_pct real,
  computed_at timestamptz not null, model_version text not null
);
```

### 2.7 Patrones de consulta (bosquejos)

Funciones de ventana disponibles: `lag`, `lead`, `first_value`, `row_number`, `ntile`, etc.; ojo: `last_value`/`nth_value` usan el frame por defecto y pueden dar resultados engañosos. <https://www.postgresql.org/docs/current/functions-window.html>

**a) Detección de ralentí / parada (gaps-and-islands).** No se puede anidar una función de ventana dentro de otra, por eso hay dos niveles de CTE. Umbrales ilustrativos, calibrar con FEAD.

```sql
-- SKETCH: tramos de ralentí >= 10 min para un vehículo y rango
with m as (
  select bucket,
         (speed_avg < 1.0 and rpm_avg > 300) as idle      -- umbrales a calibrar
  from telemetry_1min
  where vehicle_id = $1 and bucket >= $2 and bucket < $3
),
flag as (
  select *, case when idle is distinct from lag(idle) over (order by bucket) then 1 else 0 end as chg
  from m
),
isl as (
  select *, sum(chg) over (order by bucket) as grp from flag
)
select min(bucket) as start_ts,
       max(bucket) + interval '1 minute' as end_ts,
       count(*) as minutes
from isl
where idle
group by grp
having count(*) >= 10;
```

**b) Baseline de combustible por viaje.** Mediana robusta por vehículo y segmento comparable (Nivel 1 del handoff, sec. 8). `percentile_cont` es un agregado de conjunto ordenado estándar de Postgres **[no verificado en esta investigación contra la doc]**.

```sql
-- SKETCH
with hist as (
  select vehicle_id, route_class,
         percentile_cont(0.5) within group (order by l_per_100km) as med,
         count(*) as n_baseline
  from trip_summary_hist group by 1,2
)  -- MAD (opcional): segundo CTE con la mediana de abs(l_per_100km - med) por grupo
select t.trip_id,
       t.fuel_l_est / nullif(t.distance_km,0) * 100          as l_per_100km,
       h.med, (t.fuel_l_est / nullif(t.distance_km,0) * 100 - h.med) / nullif(h.med,0) as deviation_pct
from trip_summary t join hist h using (vehicle_id, route_class);
```
Calcular `mad` en dos CTE (mediana, luego mediana de |x - mediana|). Anomalía = `deviation_pct` fuera de umbral y `n_viajes_baseline >= k`; si no hay histórico suficiente, devolver "sin baseline", no inventar (handoff sec. 15).

**c) Anomalía por ventana móvil.** `avg()/stddev()` sobre `rows between 59 preceding and current row` en `telemetry_1min`, marcando desviaciones; igual: umbrales calibrados, no son evidencia de anomalía real (handoff sec. 8).

**d) Proximidad geográfica** (parada cerca de un hito/cliente):

```sql
-- SKETCH
select s.event_id from operational_event s join site c on ST_DWithin(s.geog, c.geog, 300)  -- metros si geography
```

### 2.8 Medir antes de afinar

`EXPLAIN (ANALYZE, BUFFERS)` sobre las 3-5 consultas benchmark que pide el handoff (sec. 12, "Entregable de research"). Supabase ofrece `hypopg` e `index_advisor` en su imagen (<https://github.com/supabase/postgres/tree/develop/nix/ext>) **[uso concreto no verificado en docs]**. Pooler: para servicios con muchas conexiones cortas usar el pooler en modo transacción (puerto 6543) y desactivar prepared statements; conexión directa es IPv6 por defecto. <https://supabase.com/docs/guides/database/connecting-to-postgres> **[NO VERIFICADO dónde se desplegará FastAPI]**: si es un contenedor persistente, la conexión directa o el pooler de sesión sirven; si es serverless, pooler en modo transacción.

---

## 3. Capa MCP: rendimiento y seguridad

### 3.1 Patrón de referencia en Luca (resumen)

Fuente: `/home/user/Projects/luca/docs/dev/plan-mcp-m5.md`, `CONTEXT.md`, `services/luca-mcp/src/{index.ts,gasClient.ts}`, `wrangler.toml`.
- `services/luca-mcp` es un Worker de Cloudflare multi-tenant, fork de `vera-mcp` (CoS-Agent). Dominio propio `mcp.lucaa.lat`.
- `index.ts` compone `OAuthProvider` (`@cloudflare/workers-oauth-provider`: `/authorize`, `/token`, `/register`, protege `/mcp`; `accessTokenTTL` 24 h para reducir writes de KV) con `createMcpHandler` de `agents/mcp/server`, **stateless**: un `McpServer` nuevo por request (`buildServer(env)`).
- Emparejamiento: código de 8 caracteres de un solo uso (10 min) desde la app del usuario; el Worker guarda en D1 el *tenant* (URL del backend + hash del secreto + `aud`/`sub` del token); KV guarda estado OAuth.
- `tools.ts` registra tools v0 con `registerTool` y shapes zod (`get_summary`, `category_breakdown`, `top_merchants`, `list_transactions`, `budget_status`, `add_expense`); cada tool resuelve el tenant desde `props.tenantId` y hace `proxy(env, op, args)` -> `callGas` (POST JSON al backend con secreto). **El Worker no tiene datos de usuarios**, solo el tenant. Todo el acoplamiento con el backend está en `gasClient.ts`.
- Cuota: KV Free 1 000 writes/día por cuenta; disparador de plan Paid si Writes(24h) > 600 (README de luca-mcp).
- Adaptación a Certera: reemplazar "tenant -> Web App de GAS" por "empresa -> FastAPI" con un token de servicio; `callGas` pasa a ser `callDomainApi(path, params)`; las tools son las del handoff sec. 11 (`get_trip_status`, `get_fuel_analysis`, `get_operational_bottlenecks` primero).

### 3.2 Tools tipadas de solo lectura sobre un servicio, no SQL al modelo

- El handoff ya lo exige: "Una tool MCP no debe equivaler a acceso irrestricto a la base de datos" (sec. 11) y "evita que el LLM ejecute SQL arbitrario" (sec. 10).
- El spec de MCP **obliga** a los servidores a: validar todas las entradas, implementar control de acceso, limitar la tasa y sanear salidas. <https://modelcontextprotocol.io/specification/2025-11-25/server/tools>
- Definir `inputSchema` estricto (enums, rangos de fechas máximos, `limit` con tope) y `outputSchema` + `structuredContent` (con el JSON también como texto por compatibilidad). Errores de validación y de negocio se devuelven con `isError: true` y mensaje accionable para que el modelo se corrija. Mismo spec.
- `annotations` (p. ej. solo lectura) son **no confiables** para el cliente salvo servidor de confianza; no usarlas como control de seguridad. Mismo spec.
- Devolver **análisis ya calculados** (p. ej. "tramos de ralentí con evidencia, baseline, desviación, confianza, `data_as_of`, `provenance`") en vez de filas crudas; el modelo de frontera narra, no calcula. Así Claude/ChatGPT pueden pedir "predicciones y cuellos de botella" con respuestas de pocos KB.

### 3.3 Límites de tamaño y paginación

- El spec de paginación de MCP cubre solo `resources/list`, `resources/templates/list`, `prompts/list` y `tools/list` con cursores opacos; **`tools/call` no está en esa lista**. <https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination>
- Por tanto la paginación de resultados de una tool es **diseño propio**: argumentos `limit` (tope duro, p. ej. 50) y `cursor` (opaco, firmado, ligado a empresa y a los filtros), y respuesta con `next_cursor`, `truncated: true` y `total_estimate`. Preferir keyset (`(event_time, id) > cursor`) sobre `OFFSET`.
- **[NO VERIFICADO]** el límite de tamaño de resultado de herramienta que cada cliente (Claude, ChatGPT) acepta; no encontré cifra en fuentes primarias. Diseñar con tope conservador de pocos KB y ranking Top-N.

### 3.4 Caché en el borde de Cloudflare

- Cache API: `cache.put` solo con método `GET`; el contenido es **por centro de datos** (no se replica); funciona en dominios personalizados; honra `Cache-Control`; no soporta `stale-while-revalidate` con `put/match`. <https://developers.cloudflare.com/workers/runtime-apis/cache/>
- `fetch` con `cf: { cacheTtl, cacheTtlByStatus, cacheEverything, cacheKey }`, solo `GET`/`HEAD`. <https://developers.cloudflare.com/workers/runtime-apis/request/>
- Las llamadas MCP son `POST /mcp`, no cacheables directamente. Cachear en la subrequest Worker -> FastAPI (hacerla `GET` con parámetros en la URL) o dentro de FastAPI.
- Reglas: la **clave de caché debe incluir la empresa** (nunca compartir entre empresas); datos históricos del replay inmutables -> TTL largo; alertas/estado -> TTL de segundos; incluir `data_as_of` en la respuesta.

### 3.5 Límites del Worker (verificados en la doc actual)

Fuente: <https://developers.cloudflare.com/workers/platform/limits/>

| Límite | Free | Paid |
|---|---|---|
| CPU por request HTTP | 10 ms | 5 min (por defecto 30 s) |
| Duración (wall) HTTP | sin límite mientras el cliente siga conectado | igual |
| Subrequests externas por invocación | 50 | 10 000 (hasta 10 M) |
| Conexiones salientes simultáneas | 6 | 6 |
| Memoria por isolate | 128 MB | 128 MB |
| Peticiones diarias | 100 000/día | sin límite |
| Cuerpo de respuesta | sin límite impuesto | igual |

- Esperar a `fetch()`/KV/DB **no cuenta como CPU**; sí como wall time. Misma URL.
- Implicación: el Worker solo hace validación + 1 subrequest a FastAPI por tool call; CPU de milisegundos. 10 ms de CPU en Free es ajustado si se hace mucho JSON/crypto (la doc cita 10-20 ms para trabajo tipo autenticación), por lo que **usar Workers Paid (5 USD/mes en el README de luca-mcp)** si se despliega algo serio, o aceptar el riesgo en la demo.
- Luca ya depende del plan Free y de KV (1 000 writes/día/cuenta); para la hackathon es suficiente.

### 3.6 Worker -> FastAPI vs Worker -> Supabase directo

- **Recomendado: Worker -> FastAPI -> Supabase.** Mantiene un solo lugar con lógica de dominio, autorización por empresa y rollups; el Worker queda delgado y sin secretos de DB; coincide con el handoff (sec. 10: "Domain API... evita que el LLM ejecute SQL").
- Hyperdrive: acelera consultas a bases existentes, "any Postgres or MySQL", con pooling global y caché por defecto. <https://developers.cloudflare.com/hyperdrive/>. **[NO VERIFICADO]** que funcione con Supabase (la página no lo menciona por nombre). Solo relevante si se quisiera saltar FastAPI, lo cual no se recomienda.
- Si se opta por PostgREST/supabase-js desde el Worker: las políticas RLS se aplican con el token del usuario; la clave `service_role` tiene `bypassrls` y solo se salta RLS si la petición no lleva token de usuario. <https://supabase.com/docs/guides/database/postgres/row-level-security>

### 3.7 Alcance por empresa y RLS

- Postgres: `ENABLE ROW LEVEL SECURITY`; sin política = denegar todo; superusuarios, roles con `BYPASSRLS` y dueños de tabla la omiten (salvo `FORCE ROW LEVEL SECURITY`). <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
- Supabase: RLS obligatorio en tablas de esquemas expuestos; indexar columnas usadas en políticas; envolver `auth.uid()` en `(select ...)`; usar `TO <rol>`; las vistas omiten RLS salvo `security_invoker = true` (PG 15+). <https://supabase.com/docs/guides/database/postgres/row-level-security>
- Patrón recomendado (mi diseño, el patrón de `set_config` no está documentado como "patrón RLS" en las fuentes citadas): FastAPI se conecta con un rol **sin** `BYPASSRLS`, y por transacción ejecuta `select set_config('app.company_id', $1, true)` (`is_local=true`: solo vale en la transacción actual, <https://www.postgresql.org/docs/current/functions-admin.html>); las políticas usan `company_id = current_setting('app.company_id')::uuid`. Todas las tablas llevan `company_id`. Sketch:

```sql
-- SKETCH
alter table trip enable row level security;
create policy trip_by_company on trip for select to certera_api
  using (company_id = (select current_setting('app.company_id', true)::uuid));
create index on trip (company_id, start_ts);
```
- Defensa en profundidad: el servicio también filtra por `company_id` explícitamente. Con el pooler en modo transacción las variables de sesión no persisten, por eso `is_local=true` dentro de una transacción es lo correcto. <https://supabase.com/docs/guides/database/connecting-to-postgres>
- Identidad: el token OAuth del Worker (como en Luca) lleva `companyId`; FastAPI valida un token de servicio + `company_id` firmado, no confía en parámetros del modelo.
- Texto de reportes de conductor = entrada no confiable (riesgo de inyección de prompt, handoff sec. 12 pregunta 6): se devuelve a las tools como dato citado, nunca como instrucción.

---

## 4. Cruzar telemetría con reportes humanos

### 4.1 Principio

Separar **hechos observados** (telemetría), **eventos derivados** (SQL determinista), **reportes humanos** (texto + extracción) y **correlación** (vínculo con confianza). Cada fila lleva `provenance` (handoff sec. 7: `fead_observed`, `synthetic_demo`, `human_reported`, `model_inferred`). Importante honestidad de demo: si los reportes son sintéticos y se generan atados a un viaje, la correlación es por construcción; etiquetarlos así.

### 4.2 Diseño del join temporal

1. **Eventos derivados** en `operational_event` con `vehicle_id`, `kind` (`stop`, `idle`, `detour`), `during tstzrange`, `geog`, `evidence` (ids de buckets). Se generan con el patrón 2.7a. Índice GiST en `during`.
2. **Reportes**: `human_report(trip_id, vehicle_id, event_ts_reported, received_at, text, category, category_conf, extracted jsonb, provenance)`. Guardar **dos** tiempos (el que dice el conductor y el de recepción), porque el conductor puede reportar tarde (handoff sec. 7).
3. **Ventana de tolerancia** alrededor del reporte (p. ej. +-15 min, ajustable por categoría) y solape de rangos con `&&`.
4. **Asociación vehículo-viaje** vía `trip_vehicle_assignment` por tramo temporal (el reporte llega con el teléfono del conductor -> conductor -> viaje activo; si es ambiguo, pedir aclaración, handoff sec. 9).

```sql
-- SKETCH: candidatos de correlación reporte <-> evento, con puntaje explicable
select r.report_id, e.event_id,
  -- solape temporal normalizado 0..1
  coalesce(extract(epoch from (upper(w.ov) - lower(w.ov))), 0)
    / nullif(extract(epoch from (upper(e.during) - lower(e.during))), 0)           as t_overlap,
  (r.category = any (compat(e.kind)))                                              as cat_ok,   -- tabla de compatibilidad (waiting_unload ~ stop/idle)
  case when r.geog is null or e.geog is null then null
       else ST_Distance(r.geog, e.geog) end                                        as dist_m
from human_report r
join operational_event e
  on e.vehicle_id = r.vehicle_id
 and e.during && tstzrange(r.event_ts_reported - interval '15 min',
                           r.event_ts_reported + interval '15 min')
left join lateral (select e.during * tstzrange(r.event_ts_reported - interval '15 min',
                                               r.event_ts_reported + interval '15 min') as ov) w on true;
```

5. **Confianza** = combinación determinista y documentada (heurística, calibrar): `conf = w1*t_overlap + w2*cat_ok + w3*prox(dist_m) * conf_extraccion`, con tope en confianza baja si el reporte es único. Guardar `link_confidence` y `link_basis` (jsonb). No es probabilidad calibrada; en la respuesta mostrar "reporte coincide con la parada de 35 min (confianza media)" y nunca "causa confirmada".
6. Salida a la tool: `{event, duration_min, linked_reports[{text, received_at, confidence}], provenance, data_as_of}`. Si no hay reporte, devolver parada sin causa (handoff sec. 15: no inventar causas).

### 4.3 Dónde va el LLM y dónde SQL

| Paso | Herramienta | Por qué |
|---|---|---|
| Calcular parada/ralentí, duración, litros, desviación | **SQL determinista** | Reproducible, auditable, barato |
| Extraer `{categoria, hora mencionada, lugar, vehículo}` del texto WhatsApp | **LLM con salida estructurada** (al ingresar, una vez) | Lenguaje libre; guardar texto original + extracción + `category_conf` (handoff sec. 9) |
| Resolver tiempo relativo ("hace 20 min", "en el km 70") | LLM extrae, **SQL/código valida** contra el viaje | Evita alucinar horas |
| Unir reporte con evento | **SQL** (4.2) | Determinista |
| Reportes similares/incidentes pasados | **pgvector + texto completo** (opcional) | Solo si hay volumen; `hybrid_search` con RRF <https://supabase.com/docs/guides/ai/hybrid-search>; con índice aproximado el filtro se aplica después del índice y puede devolver menos filas: usar iterative scan <https://github.com/pgvector/pgvector> |
| Redactar respuesta/alerta | LLM del cliente o de Zavu, con evidencia dada por la tool | Presentación, no cálculo |

pgvector hace búsqueda exacta por defecto (recall perfecto) y para pocos miles de filas un escaneo exacto basta; el índice HNSW (o IVFFlat) solo hace falta con volumen. <https://github.com/pgvector/pgvector>. Para el MVP, **no** incrustar nada: filtrar por `vehicle_id`/`trip_id`/tiempo y categoría.

---

## 5. Arquitectura recomendada y plan por fases

### 5.1 Arquitectura (corta)

```
FEAD (archivos) -> Replay Service (reduce a 1 Hz / 1 min, idempotente) -> FastAPI /ingest
Zavu (WhatsApp) -> webhook tool (HTTPS) -> FastAPI /reports  -> extracción LLM -> human_report
                                   |
                         Supabase Postgres (+PostGIS, pg_cron)
   hechos: vehicle, driver, shipment, trip, assignment, telemetry_1min (y crudo reducido)
   derivados: operational_event, trip_summary, report_event_link, alert
                                   |
                       FastAPI Domain API (company scoping, rollups, baselines, caché)
                         ^                                 ^
        Cloudflare Worker MCP (OAuth, tools tipadas)      Next.js (Vercel) dashboard
                         ^
        Claude / ChatGPT (análisis: predicciones, cuellos de botella)
```
- Zavu: según el handoff (sec. 9) y la memoria del proyecto, el agente de WhatsApp acotado llama a HTTPS (defineTool/webhook tools); no hay soporte documentado de cliente MCP en Zavu (dato dado por el usuario; **no re-verificado aquí**, fuera del alcance de esta investigación).
- Sin grafo ni vector store en la primera versión.

### 5.2 Fases

**Fase 0 (primeras horas): datos**
- Perfilar FEAD (columnas, unidades, frecuencia real, licencia: no declarada en el README, <https://github.com/Torreskai0722/FEAD>). Elegir 2-3 camiones y un rango de días.
- Esquema mínimo con `company_id` en todo; `provenance` en cada fila; UTC.

**Fase 1: pipeline numérico (P0)**
- Replay -> `telemetry_1min` (idempotente, `on conflict`).
- `operational_event` por SQL (ralentí/parada, bosquejo 2.7a), `trip_summary` con km, litros estimados (rotulado como estimación/proxy), `idle_min`.
- Baseline Nivel 1 (mediana por vehículo/ruta) y desviación (2.7b).

**Fase 2: Domain API + MCP (P0)**
- FastAPI: 3 endpoints GET (`trip_status`, `fuel_analysis`, `operational_bottlenecks`), `limit` + keyset, `data_as_of`, `provenance`.
- Worker MCP clonando el patrón Luca (OAuth + `createMcpHandler` + zod), 3 tools de solo lectura, `outputSchema`.
- Probar con Claude/ChatGPT contra el Worker desplegado.

**Fase 3: reportes WhatsApp (P0)**
- Webhook de Zavu -> FastAPI; extracción LLM a `human_report`; correlación SQL (4.2) y tool `get_recent_reports`.
- Demo A del handoff (35 min de ralentí + "esperando descargar").

**Fase 4: alertas y dashboard (P1)**
- Regla de alerta con deduplicación y salida por Zavu; mapa/flota mínimo en Next.js.

**Diferir explícitamente**
- GraphRAG, graph DB, AGE, TimescaleDB, particionado, BRIN, caché en el borde (agregar solo si se mide lentitud), embeddings/pgvector (hasta que haya volumen de texto real), modelo supervisado (Nivel 2), mantenimiento predictivo (Demo C).

**Criterios para revisar la decisión (ADR)**
- Alguna de las 3-5 consultas benchmark tarda más de lo aceptable tras índices y rollups.
- Aparece un corpus de texto real que no cabe en filtros SQL (ver 1.5).
- Se necesita recorrido multi-salto de profundidad variable (probar primero `WITH RECURSIVE ... CYCLE`).

---

## 6. Lista de puntos NO VERIFICADOS

1. Lista completa de extensiones en el dashboard de Supabase (AGE ausente en repo y docs, pero la lista renderizada no se pudo recuperar).
2. Que "continuous aggregates no disponibles en Supabase" sea literal: es inferencia a partir de "Apache 2 Edition" + ubicación de `cagg` en `tsl/`.
3. Tamaño en disco de 26 M filas (estimación sin medir) y rendimiento real de cualquier consulta (no se ejecutó SQL; todo SQL es bosquejo).
4. Límite de tamaño de resultado de tools aceptado por clientes Claude/ChatGPT.
5. Compatibilidad de Hyperdrive con Supabase (la doc no lo nombra).
6. `percentile_cont` y `pg_stats.correlation` citados de memoria técnica, no contra la doc en esta sesión.
7. Dónde y cómo se desplegará FastAPI (afecta modo de conexión al pooler).
8. Soporte MCP en Zavu (dato del usuario, no re-verificado).
9. Hallazgo sobre PostgreSQL 19: el estado "RC 1 publicado el 2026-10-15" proviene del banner de la página de Beta 4; no se abrió el anuncio de RC 1.
10. Ninguna fuente primaria de proveedor de grafos (Neo4j, etc.) fue consultada.

---

## 7. Fuentes

**GraphRAG**
- Paper: <https://arxiv.org/abs/2404.16130>
- Docs: <https://microsoft.github.io/graphrag/>
- Modos de consulta: <https://microsoft.github.io/graphrag/query/overview/>
- Repo: <https://github.com/microsoft/graphrag>

**Postgres / extensiones**
- BRIN: <https://www.postgresql.org/docs/current/brin.html>
- Particionado: <https://www.postgresql.org/docs/current/ddl-partitioning.html>
- WITH RECURSIVE / CYCLE: <https://www.postgresql.org/docs/current/queries-with.html>
- Funciones de ventana: <https://www.postgresql.org/docs/current/functions-window.html>
- Vistas materializadas (REFRESH): <https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html>
- Tipos de rango / exclusión: <https://www.postgresql.org/docs/current/rangetypes.html>
- RLS: <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
- `set_config`: <https://www.postgresql.org/docs/current/functions-admin.html>
- PG19 Beta 4 (revert SQL/PGQ): <https://www.postgresql.org/about/news/postgresql-19-beta-4-released-3386/>
- Commitfest SQL/PGQ: <https://commitfest.postgresql.org/patch/4904/>
- Apache AGE: <https://github.com/apache/age>
- pgvector: <https://github.com/pgvector/pgvector>
- PostGIS gestión/índices: <https://postgis.net/docs/using_postgis_dbmanagement.html>
- TimescaleDB licencia: <https://github.com/timescale/timescaledb/blob/main/LICENSE>, <https://github.com/timescale/timescaledb/tree/main/tsl>
- Continuous aggregates: <https://www.tigerdata.com/docs/use-timescale/latest/continuous-aggregates/about-continuous-aggregates>

**Supabase**
- Extensiones (general): <https://supabase.com/docs/guides/database/extensions>
- timescaledb (deprecación): <https://supabase.com/docs/guides/database/extensions/timescaledb>
- pg_partman: <https://supabase.com/docs/guides/database/extensions/pg_partman>
- PostGIS: <https://supabase.com/docs/guides/database/extensions/postgis>
- pgvector: <https://supabase.com/docs/guides/database/extensions/pgvector>
- Hybrid search: <https://supabase.com/docs/guides/ai/hybrid-search>
- RLS: <https://supabase.com/docs/guides/database/postgres/row-level-security>
- Conexión/pooler: <https://supabase.com/docs/guides/database/connecting-to-postgres>
- Pricing: <https://supabase.com/pricing>; disco: <https://supabase.com/docs/guides/platform/manage-your-usage/disk-size>
- Imagen de Postgres (extensiones y versiones): <https://github.com/supabase/postgres/tree/develop/nix/ext>, <https://github.com/supabase/postgres/blob/develop/nix/ext/versions.json>, <https://github.com/supabase/postgres/blob/develop/ansible/vars.yml>
- pgRouting como grafo: <https://supabase.com/blog/pgrouting-postgres-graph-database>

**Cloudflare**
- Límites de Workers: <https://developers.cloudflare.com/workers/platform/limits/>
- Cache API: <https://developers.cloudflare.com/workers/runtime-apis/cache/>
- `fetch` con `cf`: <https://developers.cloudflare.com/workers/runtime-apis/request/>
- Hyperdrive: <https://developers.cloudflare.com/hyperdrive/>

**MCP**
- Tools: <https://modelcontextprotocol.io/specification/2025-11-25/server/tools>
- Paginación: <https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination>

**Datos**
- FEAD: <https://github.com/Torreskai0722/FEAD>

**Locales (repos del usuario)**
- `/home/user/Projects/npm-devs/docs/product/PRODUCT_CONTEXT_CERTERA.md`
- `/home/user/Projects/luca/docs/dev/plan-mcp-m5.md`, `/home/user/Projects/luca/CONTEXT.md`, `/home/user/Projects/luca/services/luca-mcp/`
