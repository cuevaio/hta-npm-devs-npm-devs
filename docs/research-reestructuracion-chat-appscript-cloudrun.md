# Research: reestructuración de ia-academy a chat estilo Cowork + Apps Script + Cloud Run sandboxes

> **Fecha:** 2026-10-12 · **Autor:** agente de investigación (Claude) para Joseph Robles ·
> **Alcance:** evaluar (1) un user-flow de chat con vista dividida chat | assets y (2) una
> arquitectura con backend en Google Apps Script, sandbox en Cloud Run sandboxes, login Google
> restringido al dominio de Xertica y frontend Next.js tipo `luca`.
> **Regla de fuentes:** cada afirmación cita una URL oficial o `ruta/archivo:línea`. Rutas
> `main:<ruta>` = `git show main:<ruta>` en `/home/user/Projects/ia-academy`. Rutas `luca:` =
> `/home/user/Projects/luca/`. Repos externas clonadas (solo lectura, sin ejecutar nada) en
> `/tmp/research-repos/`. Lo que no se pudo comprobar está marcado **[no verificado]**.

## Índice

0. [Resumen ejecutivo](#0-resumen-ejecutivo)
1. [Qué se pidió y cómo se investigó](#1-qué-se-pidió-y-cómo-se-investigó)
2. [Estado actual de ia-academy](#2-estado-actual-de-ia-academy)
3. [luca: qué hay y qué se reutiliza](#3-luca-qué-hay-y-qué-se-reutiliza)
4. [Repos externas](#4-repos-externas)
5. [Límites oficiales verificados](#5-límites-oficiales-verificados)
6. [Evaluación: ¿Apps Script como backend?](#6-evaluación-apps-script-como-backend)
7. [Arquitectura objetivo propuesta](#7-arquitectura-objetivo-propuesta)
8. [Diseño del flujo chat + vista dividida](#8-diseño-del-flujo-chat--vista-dividida)
9. [Conservar / cambiar / tirar](#9-conservar--cambiar--tirar)
10. [Riesgos, trade-offs y alternativas](#10-riesgos-trade-offs-y-alternativas)
11. [Impacto en la decisión legal (AGPL de OpenMontage, licencia de Remotion)](#11-impacto-en-la-decisión-legal)
12. [Recomendación](#12-recomendación)
13. [Preguntas abiertas](#13-preguntas-abiertas)
14. [Plan por fases](#14-plan-por-fases)
15. [Fuentes](#15-fuentes)

---

## 0. Resumen ejecutivo

- **El user-flow tipo Cowork es viable y ya está a medio decidir.** La rama
  `refactor/agent-sandbox-workspace` de ia-academy fijó que "el usuario conversa desde el primer
  prompt, con imágenes y documentos de contexto, y el agente produce", con un agente **Autor** en
  un sandbox y gates HITL explícitos (`docs/adr/0017-autor-conduce-stages-de-contenido.md:7-17`).
  La vista dividida chat | assets es la UI que le falta a esa decisión. Las 7 pantallas actuales
  (`main:apps/web/app/_lib/screens.ts:25-33`) se reducen a: acceso, lista de proyectos, **una**
  página de proyecto (chat + panel) y ajustes.
- **Apps Script no sirve como backend principal de un pipeline de video agéntico.** Cada ejecución
  dura como máximo 6 min, también en Workspace. Hay un tope de 30 ejecuciones simultáneas por
  usuario. UrlFetch tiene un techo de 50 MB por llamada. Y la documentación de web apps no ofrece
  streaming, headers ni códigos HTTP propios
  ([cuotas](https://developers.google.com/apps-script/guides/services/quotas),
  [web apps](https://developers.google.com/apps-script/guides/web)). La Execution API no admite
  service accounts ([execute](https://developers.google.com/apps-script/api/how-tos/execute)).
  Una sesión del agente con render dura de minutos a horas y necesita eventos en tiempo real.
- **Se recomienda una arquitectura híbrida.** Next.js en Cloud Run, con Auth.js + Google y
  validación del claim `hd` en el servidor. Un control plane en Cloud Run que haga de gateway del
  agente y emita SSE. El **host de sandboxes** en Cloud Run con `--sandbox-launcher`, como ya decidió
  ADR-0022. El render en Cloud Run Jobs. GCS para los assets, con URLs firmadas o subida resumable.
  Y Apps Script como **capa opcional de Workspace** (Drive, Docs/Slides, Gmail), llamada con
  `scripts.run` y el token del usuario, en modo `executeAs: USER_ACCESSING` y `access: DOMAIN`.
- **De luca se reutiliza poco código, pero buenos patrones.** Sirve Auth.js v5 con refresh token
  (`luca:apps/web/src/auth.ts:20-99`), el contrato `{op,args}→{ok}` con lista blanca hacia GAS
  (`luca:gas/shared/webapp-runtime.js:17-27`) y el harness de tests de GAS en `vm`
  (`luca:tests/gas-harness.mjs`). luca **no tiene** restricción de dominio, chat, streaming, Cloud
  Run, Dockerfile ni CI. Además, Next.js no llama a Apps Script: lo hace un Worker de Cloudflare.
- **De ia-academy se reutiliza más que de luca**: los componentes de chat, el parser SSE con resume,
  `scene-renderer`, `workers/rendering`, los contratos, el GenerationBroker y todo el diseño de
  ADR-0016…0022.
- **`tanaikech/cloud-run-sandbox-gas` confirma el patrón GAS → Cloud Run sandbox, pero solo para
  ejecuciones cortas.** Usa un timeout de 15 s, no tiene persistencia y se autentica con una llave
  JSON de SA guardada en Script Properties
  (`/tmp/research-repos/cloud-run-sandbox-gas/cloud_run/deploy.sh:112-115`, `gas/Auth.js:73-89`).
  Esa llave choca con la regla "cero llaves JSON" de ADR-0012.
- **Hay que validar con spikes antes de comprometerse.** Que GAS invoque Cloud Run con
  `ScriptApp.getIdentityToken()` **no está documentado**: la doc no publica el `aud` del token. Y
  Cloud Run sandboxes sigue en **Preview** sin SLA y sin API REST: la CLI solo funciona dentro del
  contenedor ([code-execution](https://docs.cloud.google.com/run/docs/code-execution),
  [sandbox-cli](https://docs.cloud.google.com/run/docs/reference/sandbox-cli)).
- **El análisis AGPL no cambia con la nueva arquitectura.** Ejecutar OpenMontage dentro de un
  sandbox que sirve a usuarios por red cae en la §13. Ni Apps Script ni el sandbox lo evitan.
  Sigue vigente el clean-room de ADR-0001 (`docs/adr/0001-clean-room-reuse-of-openmontage.md:3-9`).

---

## 1. Qué se pidió y cómo se investigó

- **ia-academy:** lectura de `main` (código, ADR-0001…0014b, `docs/branding/ui-ux.md`, plan) y de la
  rama actual `refactor/agent-sandbox-workspace` (ADR-0015…0022, research T1/T2/T7/T14/T15, spikes).
  También se leyeron los archivos sin trackear `docs/pbi/PBI-proyectos-por-dueno-y-sandbox-autor.md`
  y `docs/html/sandbox-autor-byoc-vs-cloud-run.html`.
- **luca:** lectura completa de `/home/user/Projects/luca`, sin ejecutar nada.
- **Repos externas:** se clonaron `tanaikech/cloud-run-sandbox-gas` (commit `2baf6b8`) y
  `shivajibodkhe/google-apps-script-cicd-template` (commit `74e3cc9`). Se listaron las 150 repos
  de tanaikech (`/tmp/research-repos/tanaikech-repos.json`) y se descargaron 27 READMEs
  (`/tmp/research-repos/tanaikech-readmes/`).
- **Documentación oficial:** Apps Script (páginas actualizadas el 2026-09-03), Cloud Run y GCS
  (2026-10-09), Next.js 16.4, Google OpenID Connect y Auth.js.
- La investigación se repartió en subagentes paralelos y sus conclusiones se contrastaron por
  muestreo contra las fuentes. Por ejemplo, se comprobaron `gasClient.ts`, `auth.ts`, `main.py`,
  `deploy.sh` y la página de cuotas.

## 2. Estado actual de ia-academy

> Base: rama `main` (MVP tracer-bullet, 135 commits) y, donde se indica, la rama
> `refactor/agent-sandbox-workspace` (ADR-0015 a ADR-0022, spikes del sandbox), que **todavía no está
> en main**. Las rutas `main:` se leen con `git show main:<ruta>`.

### 2.1 Stack

| Capa | Tecnología en main | Fuente |
|---|---|---|
| Frontend | Next.js **14.2.35** (App Router), React 18.3, `@remotion/player` 4.0.517, vitest + Testing Library; design system propio `@ia/ui` (tokens "dark-room editorial") | `main:apps/web/package.json:14-33`, `main:packages/ui/src/` |
| Cliente API | `@ia/api-client` generado desde `contracts/openapi/openapi.v1.yaml` + `sse.ts` | `main:packages/api-client/src/`, ADR-0006 `docs/adr/0006-tech-stack.md:12-13` |
| Backend | FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 (uv) | `docs/adr/0006-tech-stack.md:3-5` |
| Persistencia | Postgres 16 con RLS por tenant (17 migraciones en main; la 0018 de dueño por proyecto está en la rama de ownership) | `main:libs/persistence/ia_persistence/migrations/versions/0001…0017`, ADR-0015 `docs/adr/0015-tenant-compartido-dueno-por-proyecto.md:21-27` |
| Motor de producción | *durable-lite*: Postgres + cola `run_dispatch` + worker reactivo `workers/orchestration` + outbox→SSE | `docs/adr/0008-productionworkflow-durable-lite.md:3-7`, `main:workers/orchestration/` |
| Render | Worker Node/Remotion (`workers/rendering`, Dockerfile, segmentos + ffmpeg) | `main:workers/rendering/src/{render,segments,ffmpeg}.ts` |
| LLM | Gemini vía `google-genai` (`gemini-2.5-flash` por defecto en el CreativeDirector; `gemini-3-flash-preview` en los productores vía Vertex `global`) | `main:apps/api/ia_api/adapters/creative_director.py:1-29`, `main:docker-compose.yml` (bloque `x-gcp-env`) |
| Proveedores | GenerationBroker con adaptador NanoBanana (imagen) + voz (ElevenLabs BYO) | `main:libs/generation-broker/ia_generation_broker/adapters/nanobanana.py`, `…/voice.py` |
| Infra | Cloud Run (api, orchestration, render) en el proyecto compartido `aifirst-dev`, GCS `ia-academy-assets-dev`, Secret Manager, ADC por impersonación, sin llaves JSON; web en Vercel | `docs/adr/0012-deployment-governance-shared-gcp-project.md:10-14,34-61,87-88`, `main:docker-compose.yml` |
| CI | GitHub Actions: Postgres de servicio, Node 20 + pnpm, uv, tests de RLS | `main:.github/workflows/ci.yml:1-40` |

Tamaño aproximado del código en main (líneas en `.py/.ts/.tsx/.json/.yaml`, sin generados):
`apps/api` ≈19.0k, `libs` ≈13.6k, `apps/web` ≈8.6k, `packages` ≈3.6k, `workers` ≈2.2k,
`contracts` ≈1.5k (conteo propio con `git show main:… | wc -l`).

### 2.2 User-flow actual (fases de creación de proyecto)

El App Flow son **7 pantallas** con un Stepper que es a la vez navegación y estado
(`main:apps/web/app/_lib/screens.ts:25-33`, `main:docs/branding/ui-ux.md:19-31`):

```
Onboarding (wizard BYO: llaves ElevenLabs + NanoBanana)
[01] Acceso ─▶ [02] Proyectos ─▶ [03] Brief ─▶ [04] Guion ─▶ [05] Workbench ─▶ [06] Export
                     └──────── [07] Ajustes · Proveedores (routing por proyecto) ────┘
```

| Pantalla | Ruta | Qué hace | Fuente |
|---|---|---|---|
| 01 Acceso | `/acceso` | "Continuar con Google", login por invitación | `main:docs/branding/ui-ux.md:40-42`, `main:apps/api/ia_api/routers/auth.py:3-11` |
| 02 Proyectos | `/proyectos` | Grid de tarjetas con mini-rail de etapas, "+ Nuevo proyecto", board en vivo por SSE | `main:apps/web/app/proyectos/page.tsx:4-8`, `ui-ux.md:44-46` |
| 03 Brief | `/proyectos/{id}/brief` | Chat con el **CreativeDirector** (Gemini) que conversa y **extrae** la ficha técnica (`brief_version`); chips de proveedor; cierra el brief → guion | `main:apps/web/app/proyectos/[projectId]/brief/page.tsx:1-31`, `ui-ux.md:48-51`, `main:apps/api/ia_api/adapters/creative_director.py:1-20` |
| 04 Guion | `/proyectos/{id}/guion` | `ReviewGate` aprobar / pedir cambios (HITL) | `ui-ux.md:53-55` |
| 05 Workbench | `/proyectos/{id}/workbench` | 3 columnas: chat en vivo · filmstrip + preview (point-to-regenerate) · decisiones/actividad | `ui-ux.md:57-66` |
| 06 Export | `/proyectos/{id}/export` | MP4, SRT, JSON de provenance/costos | `ui-ux.md:68-70` |
| 07 Ajustes | `/ajustes` | ProviderCards, FeatureFlags, credenciales BYO, RoutingPolicy | `ui-ux.md:72-76` |

Pipeline detrás de las pantallas (stages del Run):
`research → proposal(GATE+budget) → script(GATE) → scene_plan(GATE) → sample(GATE) → [assets ∥ narration] → timeline → render → final_review(GATE) → publish`
(`docs/adr/0008-productionworkflow-durable-lite.md:11-14`). En main, `research/proposal/script`
los produce un LLM y `scene_plan` es determinista (`main:libs/domain/ia_domain/stages.py:12-19`).

### 2.3 Endpoints (API `/api/v1`, main)

| Área | Endpoints | Fuente |
|---|---|---|
| Auth | `GET /auth/google/login`, `GET /auth/google/callback`, `GET/DELETE /auth/session`, `GET /auth/dev-login` | `main:apps/api/ia_api/routers/auth.py:95,116,147,158,169` |
| Proyectos | `POST/GET /projects`, `GET /projects/{id}`, `GET /projects/{id}/board` | `…/routers/projects.py:66,88,101`, `…/runs.py:264` |
| Brief/chat | `GET/PUT /projects/{id}/brief`, `POST /conversations/{id}/messages` (SSE) | `…/routers/conversations.py:105,122,257` |
| Eventos | `GET /projects/{id}/events` (SSE outbox, `Last-Event-ID`) | `…/routers/events.py:1-18,115` |
| Runs | `POST /runs`, `GET /runs/{id}`, `/export`, `/retry`, `/scenes`, `POST /runs/{id}/stages/{stage}/approve` | `…/routers/runs.py:159,224,301,364,492,604` |
| Comandos | comandos tipados, revisiones y `POST /scenes/{id}/revisions/{rev}/promote` | `…/routers/commands.py:128,281,941,964` |
| Assets | `POST /projects/{id}/assets/upload-url` (URL firmada GCS, ≤200 MB, allowlist MIME), `/assets/{id}/attach`, `GET /assets/{id}` | `…/routers/assets.py:45,55,74-122,125,160` |
| Proveedores | `/providers`, `/provider-configs/{p}` (+`/test`, `/voices`), `/routing-policies` | `…/providers.py:93-206`, `…/routing.py:55,76`, `…/voices.py:40` |
| Métricas | `GET /metrics` | `…/metrics.py:57` |

### 2.4 Modelo de datos (Postgres, main)

Tablas (clases ORM): `tenant`, `user`, `membership`, `project`, `outbox`, `credential_ref`,
`provider_config`, `routing_policy`, `tenant_quota`, `audit_log`, `run`, `stage_run`,
`generation_job`, `conversation`, `message`, `creative_brief`, `brief_version`, `approval`,
`budget_reservation`, `cost_entry`, `quality_result`, `artifact`, `artifact_version`,
`scene_document`, `scene_revision`, `run_dispatch`, `asset`
(`main:libs/persistence/ia_persistence/models.py:139-1205`). Todas con `tenant_id` y RLS
(ADR-0002, ADR-0009). ADR-0015 agrega `project.owner_user_id` y RLS encadenada por dueño
(`docs/adr/0015-tenant-compartido-dueno-por-proyecto.md:17-27`).

### 2.5 Cómo corre hoy el agente y el streaming

- **En main no hay sandbox.** El "agente" es el `CreativeDirector`: una llamada a Gemini con
  structured output por turno, dentro del request de FastAPI, timeout 60 s
  (`main:apps/api/ia_api/adapters/creative_director.py:28-32`).
- El "streaming" del chat es **simulado**: la respuesta completa se trocea por palabras y se
  emite como `message.token` (`main:apps/api/ia_api/routers/conversations.py:231-240`). El
  frontend lo consume con `fetch` + `ReadableStream` porque `EventSource` no admite POST
  (`main:apps/web/lib/streamMessages.ts:1-13`).
- El progreso de producción llega por SSE del outbox con resume por `Last-Event-ID`, dedupe por
  UUIDv7 y fallback a polling (`main:apps/web/lib/useProjectEvents.ts:1-25`).

### 2.6 Lo que ya decidió la rama `refactor/agent-sandbox-workspace` (no está en main)

Esta rama **ya movió el producto hacia la experiencia que Joseph describe ahora**:

- ADR-0017: "el usuario conversa desde el primer prompt, con imágenes y documentos de contexto, y el
  agente produce"; el **Autor** (agente en una AgentSession) conduce `research → proposal → script →
  scene_plan → authoring`; la producción sigue siendo determinista; los gates se aprueban solo con
  acción registrada en la UI, nunca interpretando el chat; el CreativeDirector se retira
  (`docs/adr/0017-autor-conduce-stages-de-contenido.md:7-17,35-52`).
- ADR-0016: sandbox desechable, **ProjectWorkspace durable** en GCS; retomar = sandbox nuevo +
  hidratar desde el último checkpoint; la conversación vive en Postgres
  (`docs/adr/0016-sandbox-desechable-workspace-durable.md:6-21`).
- ADR-0019: workspace por contenido (blobs sha256 + manifiesto en Postgres), carpetas fijas
  `inputs/` (adjuntos, solo lectura), `brand/`, `catalog/`, `scenes/`, `assets/`, `work/`; tokens
  reducidos (Credential Access Boundary) por proyecto (`docs/adr/0019-layout-y-checkpoint-del-project-workspace.md:7-45`).
- ADR-0020: herramientas de host (`generate_image`, `synthesize_narration`, `promote`,
  `start_run`…), sin gasto antes del Run, errores tipados, confirmación del usuario para dinero
  (`docs/adr/0020-herramientas-de-host-del-autor.md:7-41`).
- ADR-0021: Orchestrator en Cloud Run instances (`docs/adr/0021-orchestrator-en-cloud-run-instances-fase-1.md:8-15`).
- ADR-0022: **Sandbox del Autor en Cloud Run sandboxes** (host = Cloud Run service con
  `--sandbox-launcher`, bind mount del workspace, render final en Cloud Run Job; BYOC plan B)
  (`docs/adr/0022-sandbox-del-autor-en-cloud-run-sandboxes.md:8-39`), con evidencia medida en
  `docs/research/t7-spike-sandbox-resultados.md` (preview 4 s en 5.7 s vs 86 s en BYOC; crear sandbox
  ~0.5 s; ciclo hidratar→checkpoint→recrear idéntico; tar por HTTP no pasa por el límite de 32 MiB).
- PBI (sin trackear) `docs/pbi/PBI-proyectos-por-dueno-y-sandbox-autor.md:28-37`: dueño por
  proyecto, registro abierto con **lista de dominios permitidos**, cuota 10 runs/50 regeneraciones
  por usuario/día, y cierre del wayfinder con ADR del sandbox.
- HTML (sin trackear) `docs/html/sandbox-autor-byoc-vs-cloud-run.html`: explicativo para no
  técnicos de BYOC vs Cloud Run sandboxes y del ciclo T7 (mismo contenido que T2/T7/ADR-0022).

**Conclusión de la sección:** el nuevo user-flow tipo Cowork **no es un giro respecto de la rama**:
es la UI que le faltaba a ADR-0017/0020. Lo verdaderamente nuevo es la **arquitectura de
backend en Apps Script**, que choca con ADR-0006 (FastAPI), ADR-0008 (durable-lite en Postgres) y
ADR-0012 (Cloud Run + Postgres + Vercel).

---

## 3. luca: qué hay y qué se reutiliza

### 3.1 Qué es luca

luca es una app de gastos personales para Perú. Lee los correos de BCP/Yape del Gmail del usuario
y los convierte en movimientos dentro de **su propia** Google Sheet, sin base de datos
(`luca:README.md:31-37`, `luca:CLAUDE.md:3-9`, `luca:CONTEXT.md:14-15`). Tiene tres piezas:

| Pieza | Detalle | Fuente |
|---|---|---|
| Web | Next.js **16.3.8**, React 19.2.8, Auth.js v5 (`next-auth` ^5.0.0-beta.32), Tailwind 4, ECharts, Playwright, npm (sin workspaces). Desplegada en Vercel (`luca-sand`, dominio lucaa.lat) | `luca:apps/web/package.json:17-34`, `luca:package.json:6-21`, `luca:CLAUDE.md:71` |
| Apps Script | `gas/shared` (LucaLib, la librería versionada) y `gas/stub` (script ligado a una Sheet plantilla que copia cada usuario). Web app `doGet`/`doPost`, trigger cada 15 min y UI con `google.script.run` | `luca:gas/stub/Code.js:24-41`, `luca:gas/shared/webapp-runtime.js:17-27`, `luca:gas/stub/triggers.js:12-15` |
| MCP | Worker de **Cloudflare** (OAuth 2.1, D1, KV) que expone tools MCP y hace de proxy hacia el `/exec` de GAS de cada usuario | `luca:services/luca-mcp/src/index.ts:20-32`, `luca:services/luca-mcp/src/tools.ts:20-51` |

### 3.2 Auth

- Usa Auth.js con el proveedor Google, sesión JWT y scopes `openid email profile drive.file`, con
  `access_type: offline` y `prompt: consent` (`luca:apps/web/src/auth.ts:18-25,66-72`).
- El refresh del access token es manual contra `oauth2.googleapis.com/token`, 60 s antes de que
  expire (`luca:apps/web/src/auth.ts:43-64,88-89`).
- `session.accessToken` llega al cliente a propósito, para llamar a Drive y Sheets desde el
  navegador (`luca:apps/web/src/auth.ts:91-96`, `luca:apps/web/src/app/app/layout.tsx:25-33`).
- La guardia de sesión está en el layout de servidor `/app`. No hay `middleware.ts`
  (`luca:apps/web/src/app/app/layout.tsx:11-23`).
- Tiene un modo mock (`LUCA_MOCK=1`) para dev y e2e (`luca:apps/web/src/auth.ts:101-132`).
- **No restringe el dominio.** No hay `hd` ni callback `signIn`, y la pantalla de consentimiento es
  "Externo" (`luca:spikes/README.md:19`).

Para Xertica hay que añadir `authorization.params.hd = "<dominio>"` como pista de UI y, **sobre
todo**, un callback `signIn` que valide en el servidor `profile.hd === "<dominio>"` y
`email_verified`. Google es explícito: "Don't rely on this UI optimization to control who can
access your app" y hay que validar el claim `hd` del ID token
([OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)). El ejemplo
de Auth.js filtra con `email.endsWith("@example.com")`
([Auth.js Google](https://authjs.dev/getting-started/providers/google)), lo que es más débil que lo
que recomienda Google. Si el cliente OAuth se crea como **Interno** en el proyecto GCP de la
organización Xertica, Google ya limita el login a usuarios de la organización
([pantalla de consentimiento](https://support.google.com/cloud/answer/10311615)) **[no verificado
en esta sesión]**. Conviene hacer las dos cosas.

### 3.3 Cómo habla luca con Apps Script

- **No usa la Execution API (`scripts.run`)**: no aparece en el repo.
- El `/exec` se despliega como "Ejecutar como: yo / Acceso: cualquiera"
  (`luca:CONTEXT.md:20`, `luca:gas/shared/mcp-runtime.js:412`). La identidad se acredita con un
  **secreto compartido por usuario** en `UserProperties` y un challenge HMAC
  (`luca:gas/shared/secrets-runtime.js:10-33`, `luca:gas/shared/mcp-runtime.js:63-75`).
- Quien llama al `/exec` es el Worker, con `fetch(POST, redirect:'follow')`, porque GAS responde
  con un 302 hacia el contenido (`luca:services/luca-mcp/src/gasClient.ts:14-34`). No tiene timeout
  ni reintentos.
- GAS responde siempre HTTP 200 con `{ok, error}` (`luca:gas/shared/webapp-runtime.js:5`), aplica
  una lista blanca de ops (`luca:gas/shared/mcp-runtime.js:90-111`) y serializa con
  `LockService.getUserLock().waitLock(10000)` (`luca:gas/shared/webapp-runtime.js:43-44`).
- `ScriptApp.getIdentityToken()` solo se probó en un spike (`luca:spikes/s3-s4-gas-stub/Code.gs:30`,
  `luca:spikes/README.md:80-96,141`). Resultado: `aud` estable por copia. **No está implementado.**
- Discrepancia interna de luca: `CONTEXT.md:22-23` dice que se guarda el hash del secreto, pero el
  código lo guarda en claro en D1 (`luca:services/luca-mcp/schema.sql:12`).

### 3.4 UI, streaming, deploy y tests

- **No hay chat real.** `components/portada/AiChatDemo.tsx` es una animación de la landing. No hay
  SSE, AI SDK, markdown, subida de archivos ni split view. El estado vive en un Context propio con
  polling cada 5 s (`luca:apps/web/src/components/portada/AiChatDemo.tsx:1-16`,
  `luca:apps/web/src/components/LedgerProvider.tsx:20-80`,
  `luca:apps/web/src/components/Onboarding.tsx:33-43`).
- **No hay `.github/`, Dockerfile ni `clasp push` en CI.** El release lo hace un skill de Claude:
  tests, versión, `lib:push`, `stub:push`, `wrangler deploy` (`luca:.claude/skills/deploy-luca/SKILL.md:8-60`,
  `luca:package.json:9-14`).
- Los tests usan `node --test` y un harness de GAS que carga `gas/shared/*.js` en
  `vm.runInContext` con mocks de `UrlFetchApp`, `ScriptApp`, Sheets y Gmail
  (`luca:tests/gas-harness.mjs:20-39,212-220,279-280`). Hay e2e con Playwright en modo mock
  (`luca:apps/web/playwright.config.ts:7-45`).

### 3.5 Tabla de reutilización

| Módulo de luca | Veredicto | Rutas | Por qué |
|---|---|---|---|
| Auth.js + Google, JWT con access/refresh token y refresh manual | **Adaptar** | `apps/web/src/auth.ts:20-99`, `src/app/api/auth/[...nextauth]/route.ts` | Base sólida. Faltan `hd` + `signIn` con validación de `profile.hd` y los scopes que pida Apps Script (los scopes del token deben cubrir **todos** los del script para `scripts.run`). No exponer `accessToken` al cliente salvo que haga falta |
| Guardia del área privada | **Adaptar** | `src/app/app/layout.tsx:11-23` | Añadir `middleware`/`proxy` y revalidar sesión y dominio en cada route handler |
| Modo mock de auth y Google (dev/e2e) | **Tal cual** (patrón) | `auth.ts:101-132`, `lib/google-client.ts:18-21`, `lib/google.mock.ts`, `playwright.config.ts` | E2E sin credenciales |
| Cliente Google desde el navegador (`gapi`, backoff, Picker) | **Adaptar** | `src/lib/google.ts:14-159` | Útil si el usuario adjunta materiales desde Drive con Picker |
| Contrato HTTP con GAS `{op,args}→{ok,error}` + lista blanca | **Adaptar** | `gas/shared/webapp-runtime.js:17-27`, `mcp-runtime.js:55-111`, `services/luca-mcp/src/gasClient.ts` | El patrón vale. En un dominio Workspace es mejor `scripts.run` con el token del usuario, o web app `USER_ACCESSING` + `DOMAIN`, que el secreto compartido. Añadir timeout y reintentos |
| Dispatcher con lista blanca | **Tal cual** | `gas/shared/ui-runtime.js:173,245-251`, `gas/stub/Code.js:24-26` | Genérico y seguro |
| Librería versionada + stub por usuario | **No aplica** | `gas/shared`, `gas/stub` | Solo tiene sentido con una copia por usuario. Aquí basta un proyecto GAS central |
| Secretos por usuario en `UserProperties` | **Tal cual** si GAS guarda estado por usuario | `gas/shared/secrets-runtime.js:10-33` | Ojo: 9 KB por valor y 500 KB por store ([cuotas](https://developers.google.com/apps-script/guides/services/quotas)) |
| LLM desde GAS con timeout y backoff | **Referencia** | `gas/shared/llm-runtime.js:18-30,180-206` | El chat con streaming debe llamar al LLM desde Cloud Run, no desde GAS |
| Spike de identity token GAS → servicio externo | **Adaptar** (investigación) | `spikes/README.md:80-96,141` | Es justo el patrón GAS → Cloud Run. Falta probarlo contra Cloud Run IAM (§5.1) |
| Harness de tests GAS en `vm` | **Tal cual** | `tests/gas-harness.mjs` | Encaja con GAS sin módulos. Alternativa: gas-fakes (§4.3) |
| Worker MCP de Cloudflare | **No aplica** | `services/luca-mcp/*` | Otra nube. Las ideas de HMAC y storage aislado son portables |
| UI de chat, streaming, upload, split view | **No aplica** (no existe) | — | Sale de ia-academy (`packages/ui/src/chat/*`, `apps/web/lib/streamMessages.ts`) |
| AppShell, Toast, ThemeToggle, iconos, tokens | **Adaptar** | `components/AppShell.tsx`, `Toast.tsx`, `ThemeToggle.tsx`, `ui.tsx`, `DESIGN.md` | Esqueleto visual; cambiar marca y navegación |
| Context + polling | **Adaptar / sustituir** | `LedgerProvider.tsx`, `Onboarding.tsx:33-43` | Para el chat: store (zustand) o TanStack Query + SSE |
| PWA y copia offline | **No aplica** | `public/sw.js`, `lib/offline*.ts` | No es prioritario |
| Deploy y CI | **No aplica** | `.claude/skills/deploy-luca/SKILL.md`, `scripts/release-check.mjs` | Hay que crearlos. Solo vale la idea del `release-check` (misma versión en N sitios) |
| Convenciones de agentes (CLAUDE.md, CONTEXT.md, ADRs) | **Tal cual** (formato) | `CLAUDE.md`, `CONTEXT.md`, `docs/` | ia-academy ya usa el mismo formato |

**Conclusión:** de luca se aprovechan **Auth.js con refresh**, **el patrón de router con lista
blanca en GAS** y **el harness de tests de GAS**. Todo lo demás (chat, streaming, eventos,
uploads, render, deploy en GCP) sale de ia-academy o se escribe de cero.

---

## 4. Repos externas

### 4.1 `tanaikech/cloud-run-sandbox-gas`

Repo: https://github.com/tanaikech/cloud-run-sandbox-gas, clonada en
`/tmp/research-repos/cloud-run-sandbox-gas` (commit `2baf6b8`).

- **El sandbox no es una API gestionada.** Es un servicio Cloud Run propio con FastAPI, desplegado
  con `--sandbox-launcher`. Ese flag inyecta `/usr/local/gcp/bin/sandbox`, y el servicio ejecuta
  `sandbox do [--write] [--allow-egress] -- <cmd>` (`cloud_run/main.py:118-136`,
  `cloud_run/deploy.sh:101-115`). Es la misma primitiva que ADR-0022, pero en una versión
  "one-shot" (`do`) en lugar de `run`/`exec` de larga vida.
- **Contrato:** `POST /run {language: python|bash, code, allow_write, allow_egress, timeout_sec ≤ 12}`
  devuelve `{success, exit_code, stdout, stderr, duration_ms, is_sandboxed, timed_out}`
  (`cloud_run/main.py:40-73`, `:57-60`). Un timeout devuelve `exit_code=124`
  (`main.py:179-192`). Hay probes de aislamiento: metadata, env, fs y egress (`main.py:256-485`).
- **Archivos:** no hay entrada de archivos. El código va inline y los binarios salen como base64
  dentro de stdout (`gas/PracticalDemo.js:143-170`).
- **Límites del ejemplo:** timeout de Cloud Run de 15 s, 512 MiB / 1 vCPU, como mucho 1 instancia
  (`deploy.sh:112-115`, `README.md:135-136,239`). Arranque en frío de ~3,6 s y en caliente de
  322-539 ms (`README.md:309-326`). Sin persistencia (`README.md:473,483`).
- **Auth:**
  - Por defecto el servicio es **público** (`--allow-unauthenticated`, `deploy.sh:94-96`).
  - El modo privado firma un JWT con una **llave JSON de SA guardada en Script Properties** y lo
    canjea por un ID token con `target_audience` igual a la URL del servicio
    (`gas/Auth.js:73-127`).
  - **No usa `ScriptApp.getIdentityToken()`** ni IAM Credentials `generateIdToken` (grep sin
    resultados).
  - No documenta `roles/run.invoker`.
- **Qué aporta:** la forma de los probes de aislamiento y un contrato mínimo
  `POST /run → {stdout, stderr, exit_code}`, parecido al de ADR-0022 (`{command, cwd, timeout}`,
  `docs/adr/0022-sandbox-del-autor-en-cloud-run-sandboxes.md:20-23`).
- **Qué no sirve:** para video, el propio autor remite a Gemini Managed Agents (`README.md:25,483-485`).
  La auth con llave JSON está **prohibida** por ADR-0012 (`docs/adr/0012-deployment-governance-shared-gcp-project.md:34-37`).

### 4.2 `shivajibodkhe/google-apps-script-cicd-template`

Repo: https://github.com/shivajibodkhe/google-apps-script-cicd-template, en
`/tmp/research-repos/google-apps-script-cicd-template` (commit `74e3cc9`).

- Usa `@google/clasp ^3.0.0` y Node ≥ 20 (`package.json:11-16`). `.clasp.json` va con `rootDir: "."`
  (`.clasp.json.example:1-4`). `.claspignore` funciona como allowlist (`.claspignore:1-5`).
- El workflow valida en PR y en push a main. En main hace `clasp push --force` con
  `environment: production` (`.github/workflows/apps-script-cicd.yml:3-54,87-94`).
- **Credenciales:** el secret `CLASPRC_JSON`, es decir el `~/.clasprc.json` de un login humano, se
  escribe en `$HOME` (`:68-73`). Es un refresh token de usuario, no WIF.
- **Deployment fijo:** `clasp create-deployment --deploymentId $ID` redespliega la **misma URL**
  (`:96-103`). La condición `if: secrets.X != ''` (`:97`) **no funciona**, porque GitHub no permite
  secrets en `if:`
  ([docs GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)).
- **No tiene** TypeScript, bundler, tests, linter ni entornos dev/staging/prod: estos quedan como
  mejora futura (`README.md:100-104`). La "validación" es `node --check` más un script de regex
  (`scripts/validate-apps-script.mjs:1-55`).
- **Qué aporta:** el allowlist de `.claspignore`, el `.clasp.json` generado desde secrets y el
  redeploy a un deploymentId fijo. **Qué falta:** un scriptId por GitHub Environment, tests
  (gas-fakes o el harness de luca), un bundler TS → GAS (esbuild/rollup) y, sobre todo, una
  credencial de CI que no sea el refresh token de una persona. Con ADR-0012 esto último es un
  tema a negociar con IaC (§13).

### 4.3 Otras repos de tanaikech relevantes

Son 150 repos en total (`/tmp/research-repos/tanaikech-repos.json`). Dos observaciones
transversales:

- **Ninguna** muestra URLs firmadas de GCS desde GAS.
- **Ninguna** usa `ScriptApp.getIdentityToken()` para invocar Cloud Run. En todas, el patrón es
  `ScriptApp.getOAuthToken()` o una SA.

| Repo | Qué aporta | Aporte al refactor |
|---|---|---|
| [managed-agents-gas](https://github.com/tanaikech/managed-agents-gas) | GAS ↔ Gemini Managed Agents: sandbox Linux de 4 vCPU / 16 GB con FFmpeg y Playwright, `environmentId` persistente, `getOAuthToken()` por turno, binarios grandes vía ggsrun (sin pasar por UrlFetch), cliente Node con SSE | La alternativa "sandbox gestionado" ya evaluada en `docs/research/gemini-managed-agents-openmontage-sandbox.md`. Confirma que el binario no debe pasar por GAS |
| [UploadApp](https://github.com/tanaikech/UploadApp) | Subida resumable desde GAS en chunks de 16 MB, `limitProcessTime` de 300 s y reanudación en otra ejecución | El patrón aplica a GCS (`uploadType=resumable`) **[no verificado en el README]**. Para materiales del usuario es mejor que suba el navegador directo a GCS |
| [GeminiWithFiles](https://github.com/tanaikech/GeminiWithFiles) | Gemini API desde GAS con archivos de más de 50 MB (resumable), JSON estructurado y subagentes | Útil si GAS resume documentos de Drive antes del chat |
| [adk-gas (GASADK)](https://github.com/tanaikech/adk-gas) | ADK en GAS: aborta a los 280 s por el límite de 6 min; HITL con `suspend` / `resume(sessionId)` que guarda el estado | Muestra lo que cuesta un agente dentro de GAS: hay que trocearlo en ejecuciones de menos de 5 min |
| [MCPApp](https://github.com/tanaikech/MCPApp) / [ToolsForMCPServer](https://github.com/tanaikech/ToolsForMCPServer) | Servidor MCP (JSON-RPC) en `doPost`, con acceso "Anyone" + `accessKey` en la query | Exponer herramientas de Workspace (Drive, Docs, Slides) al Autor vía MCP. El accessKey en la query es seguridad débil |
| [A2AApp](https://github.com/tanaikech/A2AApp) / [MCPA2Aserver-GAS-Library](https://github.com/tanaikech/MCPA2Aserver-GAS-Library) / [a2a-for-google-apps-script](https://github.com/tanaikech/a2a-for-google-apps-script) | A2A en GAS, `streaming=False` en el agent card. Los SDK estándar se rompen con los 302 de las web apps | Confirma que **GAS no hace streaming** y que las redirecciones complican a los clientes estándar |
| [taking-advantage-of-Web-Apps-with-google-apps-script](https://github.com/tanaikech/taking-advantage-of-Web-Apps-with-google-apps-script) | Referencia sobre web apps: menos de 30 conexiones concurrentes, tokens según el modo de acceso, CORS, códigos de estado, redeploy sin cambiar la URL | Base para decidir llamar a GAS **server-to-server** desde Cloud Run, no desde el navegador |
| [RunAll](https://github.com/tanaikech/RunAll) | Concurrencia con `UrlFetchApp.fetchAll` contra la web app o la API | Fan-out desde GAS. No resuelve el límite de 6 min de quien coordina |
| [gas-asynchronous-mapreduce-broker](https://github.com/tanaikech/gas-asynchronous-mapreduce-broker) | Cola de jobs dentro de GAS: loopback con timeout de 1 s, ledger en Sheets, recuperación de zombies | Demuestra que una cola en GAS es posible **y frágil**. Para video, mejor Cloud Tasks / Pub/Sub / Postgres |
| [Resumable_Upload_For_WebApps](https://github.com/tanaikech/Resumable_Upload_For_WebApps), [AsynchronousResumableUploadForGoogleDrive](https://github.com/tanaikech/AsynchronousResumableUploadForGoogleDrive), [ResumableUploadForGoogleDrive_js](https://github.com/tanaikech/ResumableUploadForGoogleDrive_js) | El navegador sube los chunks directo a la API y GAS solo da la credencial (`google.script.run` está limitado a 50 MB) | Mismo principio que `upload-url` de ia-academy (`main:apps/api/ia_api/routers/assets.py:74-122`). En GCS, mejor una sesión resumable creada en el servidor que exponer un token |
| [Safe-Uploading-for-Google-Drive-by-HTML-in-External-Server…](https://github.com/tanaikech/Safe-Uploading-for-Google-Drive-by-HTML-in-External-Server-using-Google-Apps-Script) | Token acotado: el archivo se sube a una carpeta temporal y GAS lo mueve | Precedente de "credencial acotada" para subir desde un front externo |
| [DownloadLargeFilesByUrl](https://github.com/tanaikech/DownloadLargeFilesByUrl) | Descarga por rangos en paralelo y resumable a Drive encadenando triggers | Para **exportar el MP4 a Drive** desde GCS sin pasar 50 MB por UrlFetch |
| [FetchApp](https://github.com/tanaikech/FetchApp) / [BatchRequest](https://github.com/tanaikech/BatchRequest) | multipart/form-data y batch de Google APIs (incluido GCS JSON batch) | Utilidades si GAS habla con GCS |
| [IcebergApp](https://github.com/tanaikech/IcebergApp) | Único ejemplo de GAS → GCS JSON API: multipart hasta 50 MB, scope `devstorage.full_control` | Referencia de código; el scope es demasiado amplio |
| [gas-fakes](https://github.com/tanaikech/gas-fakes) / [Next-Level-Google-Apps-Script-Development](https://github.com/tanaikech/Next-Level-Google-Apps-Script-Development) | Emulador de servicios de GAS en Node | La pieza de tests que le falta al template de CI/CD |
| [ggsrun](https://github.com/tanaikech/ggsrun) | CLI y servidor MCP para E/S de Drive en streaming y para ejecutar GAS | Lo usa managed-agents-gas para mover binarios |
| [Linking-Google-Cloud-Platform-Project-to-Google-Apps-Script-Project-for-New-IDE](https://github.com/tanaikech/Linking-Google-Cloud-Platform-Project-to-Google-Apps-Script-Project-for-New-IDE) | Cómo vincular el script a un proyecto GCP estándar | Prerrequisito de `scripts.run` ([cloud-platform-projects](https://developers.google.com/apps-script/guides/cloud-platform-projects)) |

**Lectura transversal:** todo el trabajo de tanaike gira alrededor de **esquivar** tres límites de
GAS (6 min, 50 MB, sin streaming). Eso confirma la regla de diseño: **GAS orquesta metadatos y
entrega credenciales acotadas; los bytes y los procesos largos van por fuera.**

---

## 5. Límites oficiales verificados

### 5.1 Apps Script

| Límite | Valor | Fuente |
|---|---|---|
| Tiempo por ejecución | **6 min** (consumer **y** Workspace) | [quotas](https://developers.google.com/apps-script/guides/services/quotas) |
| Ejecuciones simultáneas | **30 por usuario**, 1 000 por script | quotas |
| Runtime total de triggers | 90 min/día (consumer), 6 h/día (Workspace) | quotas |
| Triggers | 20 por usuario y script; time-driven mínimo cada 1 min; la hora puede variar | quotas, [installable triggers](https://developers.google.com/apps-script/guides/triggers/installable), [ClockTriggerBuilder](https://developers.google.com/apps-script/reference/script/clock-trigger-builder) |
| UrlFetch | 20 000 llamadas/día (consumer), 100 000 (Workspace); **50 MB** por respuesta y por POST; 100 headers / 8 KB; URL de ~2 KB; `timeoutSeconds` por defecto 360 s | quotas, [UrlFetchApp](https://developers.google.com/apps-script/reference/url-fetch/url-fetch-app) |
| Properties | 9 KB por valor, 500 KB por store | quotas |
| CacheService | valor ≤ 100 KB, TTL máximo 6 h, ~1 000 ítems | [Cache](https://developers.google.com/apps-script/reference/cache/cache) |
| `google.script.run` | asíncrono; **10 llamadas concurrentes** (menos según el navegador) | [communication](https://developers.google.com/apps-script/guides/html/communication) |
| Web app: "execute as" | `USER_DEPLOYING` o `USER_ACCESSING` | [manifest web-app](https://developers.google.com/apps-script/manifest/web-app-api-executable) |
| Web app: acceso | `MYSELF`, **`DOMAIN`**, `ANYONE` (cualquier cuenta Google), `ANYONE_ANONYMOUS` | manifest |
| Web app: respuesta | `HtmlOutput`/`TextOutput`; el contenido se **redirige** a una URL de un solo uso en `script.googleusercontent.com` | [web](https://developers.google.com/apps-script/guides/web), [content](https://developers.google.com/apps-script/guides/content) |
| Streaming / SSE / WebSockets / headers / códigos HTTP / CORS | La doc no ofrece ninguna API para ello. **[No verificado como prohibición explícita; inferido por ausencia]**. Lo corroboran A2AApp (`streaming=False`) y el informe de tanaike sobre web apps | web, content |
| Execution API (`scripts.run`) | Deploy como API executable; **mismo proyecto GCP estándar** que el cliente OAuth; token con **todos** los scopes del script; **no admite service accounts**; máximo 6 min; solo tipos básicos | [execute](https://developers.google.com/apps-script/api/how-tos/execute) |
| `ScriptApp.getIdentityToken()` | ID token OIDC del usuario efectivo; requiere declarar el scope `openid`. **La doc no especifica `aud` ni expiración [no verificado]** | [ScriptApp](https://developers.google.com/apps-script/reference/script/script-app) |
| Latencia de web apps | Sin cifras oficiales **[no verificado]** | — |

**Implicación sobre GAS → Cloud Run con IAM:** Cloud Run acepta como `aud` la URL `*.run.app` o una
custom audience configurada con `--add-custom-audiences`
([custom audiences](https://docs.cloud.google.com/run/docs/configuring/custom-audiences)). Como el
`aud` del token de GAS no está documentado, la vía sin llaves "GAS → Cloud Run privado" queda
**[no verificada]** y necesita un spike. Hay dos candidatos:

- `getIdentityToken()` con el client ID del proyecto como custom audience, dando `run.invoker` al
  dominio.
- `getOAuthToken()` → IAM Credentials `generateIdToken` de una SA, con `serviceAccountTokenCreator`.

### 5.2 Cloud Run sandboxes

| Tema | Doc oficial (2026-10-09) | Fuente |
|---|---|---|
| Qué es | Ejecutar código no confiable aislado dentro de workloads de Cloud Run; `--sandbox-launcher` en service, job, worker pool o instance (gen2) | [code-execution](https://docs.cloud.google.com/run/docs/code-execution), [services/sandboxes](https://docs.cloud.google.com/run/docs/configuring/services/sandboxes) |
| Estado | **Preview** (Pre-GA, `gcloud beta`). Services desde el 2026-07-08 y todos los recursos desde el 2026-08-05. Sin GA | [release notes](https://docs.cloud.google.com/run/docs/release-notes), [blog](https://cloud.google.com/blog/topics/developers-practitioners/google-cloud-run-sandboxes-are-in-public-preview/) |
| API | **Sin API REST**: la CLI `/usr/local/gcp/bin/sandbox` solo funciona dentro de Cloud Run. Verbos `do`, `run [--detach]`, `exec`, `fork`, `tar`, `delete`. Sin `--user` ni `--timeout` | [sandbox-cli](https://docs.cloud.google.com/run/docs/reference/sandbox-cli) |
| Aislamiento | "completely isolated"; **la doc no nombra la tecnología** | code-execution |
| Red y secretos | Egreso bloqueado por defecto; sin env, sin secretos, sin metadata server | code-execution |
| Archivos | Root de solo lectura; `--write` = overlay tmpfs; bind mounts del host; `tar` persiste solo dentro de la misma instancia | sandbox-cli |
| Recursos | Comparten la CPU y la RAM del host; **sin límites por sandbox**; host de hasta 8 vCPU / 32 GiB | [quotas](https://docs.cloud.google.com/run/quotas) |
| Precio | "no additional cost or premium": se paga la instancia. Unos $0.32/h para 4 vCPU / 8 GiB en us-central1 (`docs/research/t2-limites-cloud-run-sandboxes.md:181-189`, tarifa no re-verificada hoy) | blog |
| IAM | Desplegar: `roles/run.developer` + `roles/iam.serviceAccountUser`. Invocar el host: `roles/run.invoker` | services/sandboxes |
| Regiones | No documentadas **[no verificado]** | — |

**Contraste con ADR-0022.** El ADR se sostiene en lo esencial, con estos matices:

1. **32 MiB por request solo aplica a HTTP/1**: "No limit if using HTTP/2 server"
   ([quotas](https://docs.cloud.google.com/run/quotas)). ADR-0022 dice "Cloud Run limita los requests
   a 32 MiB" (`docs/adr/0022-sandbox-del-autor-en-cloud-run-sandboxes.md:24-26`). La decisión de
   hidratar desde GCS con bind mount sigue siendo la correcta.
2. **gVisor, uid 0 y el código 141 son mediciones, no garantías.** La doc dice "sudo privileges as
   a non-root user", lo que **contradice** el uid 0 medido (`docs/research/t7-spike-sandbox-resultados.md:31-32`,
   ADR-0022:32-35). Conviene reportarlo a Google y no presentar gVisor como garantía.
3. **El pedido de IAM debe incluir también los roles de despliegue** (`run.developer`,
   `iam.serviceAccountUser`), no solo `run.invoker` (ADR-0022:55-56), salvo que IaC despliegue.
4. Coinciden: Preview sin SLA, bind mount, sin metadata ni egreso, rutas terminadas en `z`
   reservadas ([known issues](https://docs.cloud.google.com/run/docs/known-issues)) y afinidad de
   sesión "best effort"
   ([session affinity](https://docs.cloud.google.com/run/docs/configuring/session-affinity)).
5. Novedad: hay **SSH a services e instances** (Preview, 2026-10-07, release notes), útil para
   depurar el host.

**Alternativa gestionada:** Agent Platform Code Execution solo admite Python y JS, en máquinas de
hasta 4 vCPU / 4 GB y con 100 MB por request
([quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/sandbox/code-execution-quickstart)).
Al no aceptar una imagen propia, no sirve para Chromium/Remotion (inferencia).

### 5.3 Cloud Run (services y jobs), GCS y Next.js

| Tema | Valor | Fuente |
|---|---|---|
| Timeout de request | por defecto 5 min, **máximo 60 min** | [request-timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout) |
| Request / response | 32 MiB en HTTP/1 (sin límite en HTTP/2); la respuesta no tiene límite si es chunked o streaming | [quotas](https://docs.cloud.google.com/run/quotas) |
| WebSockets | Soportados, sujetos al timeout de 60 min; afinidad best effort | [websockets](https://docs.cloud.google.com/run/docs/triggering/websockets) |
| SSE | No mencionado explícitamente; funciona por streaming/chunked **[inferido]**. El MVP ya lo usa en Cloud Run (`main:apps/api/ia_api/routers/events.py:1-18`) | — |
| Job task | hasta **168 h** | quotas |
| IAP directo en Cloud Run | `--iap` + `--no-allow-unauthenticated` (GA 2026-03-13); `run.invoker` para el agente de IAP; `iap.httpsResourceAccessor` para los principales | [IAP Cloud Run](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run) |
| GCS signed URL V4 | máximo 7 días; endpoints XML | [signed-urls](https://docs.cloud.google.com/storage/docs/access-control/signed-urls) |
| GCS resumable | La sesión dura 1 semana; chunks múltiplos de 256 KiB; la URI de sesión funciona como credencial; **para el navegador, el servidor inicia la sesión con el header `Origin`** | [resumable-uploads](https://docs.cloud.google.com/storage/docs/resumable-uploads) |
| GCS CORS | Por bucket; la XML API lo respeta y la JSON API acepta cualquier origen | [cross-origin](https://docs.cloud.google.com/storage/docs/cross-origin) |
| Next.js streaming | Route Handlers devuelven `new Response(new ReadableStream())`, runtime nodejs | [route](https://nextjs.org/docs/app/api-reference/file-conventions/route) |
| Next.js en Docker | `output: 'standalone'` + copiar `public` y `.next/static`; `PORT`/`HOSTNAME`; `outputFileTracingRoot` en monorepo | [output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output) |
| Firestore realtime | `onSnapshot` entrega el estado actual y luego los cambios | [listen](https://firebase.google.com/docs/firestore/query-data/listen) |


---

## 6. Evaluación: ¿Apps Script como backend?

### 6.1 Lo que el producto le exige al backend

Requisitos sacados del plan (`docs/plan/plan-desarrollo-demo-video-saas.md:34-69`) y de ADR-0016/0017/0020:

| # | Exigencia | Por qué |
|---|---|---|
| R1 | Sesiones del agente de minutos a horas, con un loop LLM ↔ herramientas | El Autor conduce research → authoring en una AgentSession (ADR-0017:7-17) |
| R2 | Tokens del LLM y eventos de herramienta **en vivo** en el chat, y assets apareciendo en el panel | La UX de Cowork; "primer feedback visual antes de producir" (plan §3.2) |
| R3 | Estado durable y transaccional: runs, gates con digest, presupuesto, idempotencia | Plan §3.3; ADR-0008:30-55 |
| R4 | Aislamiento por dueño | ADR-0015:17-27 |
| R5 | Mover binarios de cientos de MB (materiales, stills, MP4) | `main:apps/api/ia_api/routers/assets.py:55` (200 MB) |
| R6 | Invocar el host de sandboxes de Cloud Run con identidad, sin llaves JSON | ADR-0012:34-37; ADR-0022:20-23 |
| R7 | Login solo para el dominio de Xertica | Pedido de Joseph; PBI `docs/pbi/…:31` |

### 6.2 Apps Script frente a cada exigencia

| # | ¿GAS lo cumple? | Evidencia |
|---|---|---|
| R1 | **No.** 6 min por ejecución; el agente tendría que trocearse en ejecuciones de menos de 5 min con estado serializado (como GASADK a los 280 s) y encadenarse con triggers (mínimo 1 min de granularidad, hora imprecisa, 6 h/día de triggers en Workspace) | [quotas](https://developers.google.com/apps-script/guides/services/quotas); `adk-gas` README; [installable triggers](https://developers.google.com/apps-script/guides/triggers/installable) |
| R2 | **No.** Sin streaming, SSE ni WebSockets en web apps ni en `scripts.run`; respuesta completa tras redirect. Habría que hacer polling o añadir un canal externo (Firestore/SSE en Cloud Run) | [content](https://developers.google.com/apps-script/guides/content), [execute](https://developers.google.com/apps-script/api/how-tos/execute); A2AApp `streaming=False` |
| R3 | **Débil.** No hay base de datos transaccional nativa: Properties (500 KB), Cache (100 KB/valor), Sheets. Hay `LockService`, pero sin cifras de timeout publicadas. Para R3 habría que llamar a Firestore o Cloud SQL **desde** GAS (JDBC/REST), con lo que GAS pasa a ser un proxy | quotas; [LockService](https://developers.google.com/apps-script/reference/lock/lock-service) |
| R4 | Posible con `USER_ACCESSING` (cada usuario ejecuta con su identidad), pero el aislamiento de datos lo seguiría dando la base externa | [manifest](https://developers.google.com/apps-script/manifest/web-app-api-executable) |
| R5 | **No para bytes.** 50 MB por llamada UrlFetch y por blob; `google.script.run` también ~50 MB. Solo sirve para **emitir** credenciales o sesiones resumables | quotas; `Resumable_Upload_For_WebApps` README |
| R6 | **No verificado** sin llaves. `getIdentityToken()` no documenta el `aud`. El único ejemplo público (tanaike) usa una llave JSON en Script Properties, prohibida por ADR-0012 | §5.1; `/tmp/research-repos/cloud-run-sandbox-gas/gas/Auth.js:73-127` |
| R7 | **Sí**: `access: DOMAIN` en la web app o en `executionApi` | manifest |
| — | **Concurrencia:** 30 ejecuciones simultáneas por usuario. Con `USER_DEPLOYING`, **todas** las requests cuentan contra el dueño, así que unos 30 usuarios activos a la vez lo saturan. Con `USER_ACCESSING` cada usuario tiene sus 30, pero cada uno debe autorizar los scopes del script | quotas; [web](https://developers.google.com/apps-script/guides/web) |
| — | **Deuda operativa:** el redeploy de versión a un deploymentId fijo funciona, pero el CI con `clasp` depende del refresh token de una persona (`CLASPRC_JSON`), sin WIF | `/tmp/research-repos/google-apps-script-cicd-template/.github/workflows/apps-script-cicd.yml:68-103` |

### 6.3 Veredicto

**Apps Script no es viable como backend del pipeline agéntico de video.** No cumple R1, R2, R5 ni
R6, y con R3 obliga a montar igualmente una base externa. Usarlo como backend principal
significaría reimplementar dentro de GAS una cola durable, un canal de eventos y un proxy de
binarios, que es justo lo que las repos de tanaike muestran como posible pero frágil.

**Sí es viable y útil como capa de Workspace**:

- importar materiales desde Drive, Docs o Slides;
- exportar el video y el guion a Drive o a una presentación;
- notificar por Gmail o Chat;
- exponer herramientas de Workspace al agente vía MCP (MCPApp).

Todo eso con la identidad del usuario (`USER_ACCESSING`) y acceso `DOMAIN`. Ahí sus límites no
estorban: son operaciones cortas, y los bytes viajan entre GCS y Drive con subida resumable.

> **Si existe una razón no técnica para "backend en Apps Script"** (por ejemplo, gobierno de
> Xertica, no poder pedir recursos al proyecto GCP compartido, o reutilizar el dominio Workspace
> como fuente de identidad), conviene explicitarla (ver §13): cambia qué variante de §10.3 es la
> adecuada.

---

## 7. Arquitectura objetivo propuesta

### 7.1 Diagrama

```
                         Usuario @xertica (navegador)
                                   │  HTTPS (cookie de sesión Auth.js)
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ web · Next.js 16 (App Router) en Cloud Run   [opcional: IAP --iap]       │
│  • Auth.js Google: hd=<dominio> + callback signIn valida profile.hd      │
│  • UI: /proyectos · /p/{id} (chat | panel de assets) · /ajustes          │
│  • BFF: route handlers → control plane (ID token de la SA de web)        │
│  • SSE passthrough  /api/p/{id}/events  (o el navegador va directo a api) │
└───────────────┬───────────────────────────────────────┬──────────────────┘
                │ HTTPS + ID token (run.invoker)         │ scripts.run con el
                ▼                                        │ OAuth token del usuario
┌──────────────────────────────────────────┐            ▼
│ api · control plane (Cloud Run)          │   ┌──────────────────────────────┐
│  FastAPI actual (o TS) · OpenAPI         │   │ Apps Script (capa Workspace)  │
│  • proyectos, conversación, gates, runs  │   │  executeAs USER_ACCESSING     │
│  • AgentSession: loop LLM (Vertex Gemini)│   │  access DOMAIN                │
│  • herramientas de host (ADR-0020)       │   │  • importar de Drive/Docs     │
│  • outbox → SSE (Last-Event-ID)          │   │  • exportar a Drive/Slides    │
│  • URLs firmadas / sesiones resumables   │   │  • Gmail/Chat: avisos         │
└───┬───────────┬──────────────┬───────────┘   │  • (opcional) servidor MCP    │
    │           │              │               └──────────────┬───────────────┘
    │ SQL       │ run.invoker  │ Cloud Run Jobs API           │ Drive API resumable
    ▼           ▼              ▼                              ▼
┌────────┐ ┌───────────────────────────────┐ ┌──────────────────┐   ┌──────────┐
│Postgres│ │ sandbox-host (Cloud Run svc)  │ │ render (Run Job) │   │  Drive   │
│Cloud   │ │ --sandbox-launcher · afinidad │ │ imagen atelier   │   │ usuario  │
│SQL     │ │ ┌──────┐ ┌──────┐ ┌──────┐    │ │ 1 task/segmento  │   └──────────┘
│RLS por │ │ │sbx p1│ │sbx p2│ │sbx p3│    │ │ ffmpeg concat    │        ▲
│dueño   │ │ └──┬───┘ └──────┘ └──────┘    │ └────────┬─────────┘        │
│(o Fire-│ │    │ bind mount /workspace     │          │                  │
│store)  │ │ hidratar ↓   ↑ checkpoint     │          │                  │
└────────┘ └────┼──────────────────────────┘          │                  │
                ▼                                     ▼                  │
        ┌───────────────────────────────────────────────────────┐        │
        │ GCS: tenant/{t}/project/{p}/workspace/blobs/… (CAB)   │────────┘
        │      tenant/{t}/asset/{id}  (assets, renders)          │  export
        └───────────────────────────────────────────────────────┘
           ▲  subida directa del navegador (signed URL / sesión resumable)
```

### 7.2 Piezas y decisiones

| Pieza | Decisión propuesta | Base |
|---|---|---|
| Frontend | Next.js 16 en **Cloud Run** con `output: 'standalone'`, en el mismo proyecto GCP. Se cambia Vercel para no sacar la sesión del perímetro y poder poner IAP. Vercel sigue siendo válido si IaC lo prefiere (ADR-0012:87-88) | [output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output); luca usa Vercel (`luca:CLAUDE.md:71`) |
| Login | Auth.js + Google, cliente OAuth **Interno** si el proyecto es de la organización Xertica, `hd` + validación de `profile.hd` en `signIn`. Defensa en profundidad opcional: IAP en el servicio web con `domain:` | §3.2; [OIDC](https://developers.google.com/identity/openid-connect/openid-connect); [IAP](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run) |
| Control plane | **Conservar el FastAPI de ia-academy** (19k líneas probadas, RLS, outbox, gates) con un adaptador de AgentSession. La alternativa es reescribirlo en TS dentro de Next.js. Ver §10 | `main:apps/api/` |
| Loop del agente | En el control plane (o en un servicio `agent` aparte), **no dentro del sandbox**: el sandbox no tiene egreso ni credenciales (ADR-0020:7-9). Usa Vertex Gemini con la SA adjunta (ADR-0012:76-81) | ADR-0020, ADR-0012 |
| Sandbox | Host de Cloud Run con `--sandbox-launcher` (ADR-0022), contrato `{command,cwd,timeout}→{stdout,stderr,exit_code}`, bind mount, checkpoint por contenido (ADR-0019) | ADR-0022:20-26 |
| Render | Cloud Run Job, un task por segmento, con la imagen atelier por digest | ADR-0022:27-28; ADR-0018:46-49 |
| Datos | **Postgres** (Cloud SQL) con RLS por dueño, como hoy. Firestore solo si se descarta Postgres; perdería RLS y las migraciones existentes | ADR-0015, ADR-0009 |
| Tiempo real | **SSE desde el control plane** (outbox + `Last-Event-ID` + dedupe por UUIDv7), con reconexión periódica (el stream se cierra antes de 60 min). Firestore `onSnapshot` es la alternativa si no hay servidor de larga vida | `main:apps/api/ia_api/routers/events.py:1-18`; `main:apps/web/lib/useProjectEvents.ts:1-25`; [request-timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout) |
| Uploads | El navegador sube directo a GCS con una sesión resumable iniciada por el servidor (header `Origin`) o con una URL firmada V4. El control plane copia la referencia a `inputs/` del workspace | `main:apps/api/ia_api/routers/assets.py:74-122`; [resumable](https://docs.cloud.google.com/storage/docs/resumable-uploads) |
| Apps Script | Proyecto GAS **estándar** vinculado al mismo proyecto GCP, desplegado como API executable con `access: DOMAIN`. Next.js (servidor) llama a `scripts.run` con el **access token del usuario** (Auth.js lo tiene). GAS nunca toca Postgres ni el sandbox; solo Workspace | [execute](https://developers.google.com/apps-script/api/how-tos/execute); `luca:apps/web/src/auth.ts:43-99` |
| CI/CD | GitHub Actions con **WIF** para Cloud Run (ADR-0012:83-85) + job de `clasp push`/`create-deployment` por entorno. La credencial de clasp debe acordarse con IaC | §4.2 |

### 7.3 Por qué Next.js → `scripts.run` y no web app `doPost`

- `scripts.run` exige un token OAuth del usuario con todos los scopes del script, y Auth.js ya lo
  tiene (`luca:apps/web/src/auth.ts:75-87`). Así GAS se ejecuta **como el usuario**, con acceso a
  su Drive, sin secretos compartidos.
- La web app `doPost` con `USER_ACCESSING` desde un servidor también necesitaría el token del
  usuario, y suma el 302 a `script.googleusercontent.com` y la falta de códigos HTTP
  ([content](https://developers.google.com/apps-script/guides/content)).
- Coste: al hacer login hay que pedir los scopes sensibles de Workspace (Drive), y Google puede
  exigir verificación del cliente OAuth salvo que sea Interno
  ([execute](https://developers.google.com/apps-script/api/how-tos/execute)). **Alternativa
  barata:** pedir esos scopes de forma incremental, solo cuando el usuario usa "Importar de Drive" o
  "Exportar a Drive".

---

## 8. Diseño del flujo chat + vista dividida

### 8.1 Pantallas

| Antes (main) | Después |
|---|---|
| 01 Acceso | **Acceso** (Google, solo dominio Xertica) |
| 02 Proyectos | **Proyectos**: lista + caja "¿Qué video quieres crear?" que crea el proyecto con el primer prompt |
| 03 Brief, 04 Guion, 05 Workbench, 06 Export | **Una página `/p/{id}`**: chat a la izquierda y panel a la derecha, que aparece cuando hay algo que mostrar |
| 07 Ajustes | **Ajustes** (proveedores, solo admins; ADR-0015) |

### 8.2 Layout

```
┌───────────────────────────────┬─────────────────────────────────────────┐
│ CHAT                          │ PANEL  [Assets] [Escenas] [Preview] [Archivos] │
│ ─ msg usuario + adjuntos ⧉    │                                         │
│ ─ Autor (tokens en vivo)      │  Assets: grid de tarjetas (generating → │
│   ▸ ToolCallCard "generate_   │          ready / failed), filtro por     │
│     image · escena 3 · $0.04" │          tipo, "adjuntos del usuario"    │
│ ─ ReviewGate inline:          │  Escenas: filmstrip (SceneThumb) con     │
│   "Propuesta · $3.20 · 90 s"  │          point-to-regenerate             │
│   [Aprobar] [Pedir cambios]   │  Preview: Remotion Player del           │
│                               │          SceneDocument / MP4 final       │
│ [📎 adjuntar] [Drive] [enviar] │  Archivos: árbol del workspace (manif.) │
└───────────────────────────────┴─────────────────────────────────────────┘
          CostMeter + StageRail compactos en la cabecera
```

- El panel arranca **cerrado**. Se abre solo con el primer `asset.*` o `still.rendered`, y el
  usuario lo puede fijar o colapsar. En móvil son pestañas Chat/Panel.
- Seleccionar un asset o una escena en el panel **contextualiza el chat**: el siguiente mensaje
  lleva `{selection: {scene_id | asset_id}}`. Esto cubre "seleccionar una escena contextualiza la
  conversación" (plan §3.2, `docs/plan/plan-desarrollo-demo-video-saas.md:54`).
- Los gates son **tarjetas en el chat** que requieren un clic. Nunca se aprueban interpretando
  texto (ADR-0017:35-36). `start_run` y `start_production` piden confirmación (ADR-0020:38-41).

### 8.3 Estados de la página

```
empty ──prompt──▶ conversing ──(adjuntos)──▶ conversing
conversing ──Autor propone Run──▶ gate:proposal ──aprobar──▶ authoring
authoring  ──stills/filmstrip──▶ gate:authoring ──aprobar──▶ producing
producing  (assets ∥ narration → timeline → render job) ──▶ gate:final_review
gate:final_review ──aprobar──▶ published ──(point-to-regenerate)──▶ authoring (Run nuevo)
cualquier estado ──fallo──▶ needs_attention (causa · etapa · acción) ──retry──▶ previo
sesión inactiva ──vuelve el usuario──▶ resuming (sandbox nuevo + hidratar) ──▶ previo
```

Los estados del Run y del StageRun ya existen (`pending/running/awaiting_human/completed/failed/cancelled`
e `in_session`; `CONTEXT.md`, ADR-0017:32-34). La página **deriva** su estado de ellos y de la
AgentSession; no hay que inventar otra máquina.

### 8.4 Eventos del agente que alimentan chat y panel

Es una extensión del envelope `SseEvent` actual, que ya incluye `message.token`,
`message.appended`, `job.status_changed` y `cost.updated` (`main:apps/web/features/brief/useBriefChat.ts:8-14`).
La línea de AG-UI ya se discutió en `docs/teach/learning-records/0002-ag-ui-decision-y-defensa.md`.

| Evento | Destino | Payload mínimo |
|---|---|---|
| `message.delta` / `message.completed` | chat | `message_id, delta / content` (tokens **reales** del LLM, no el troceo actual por palabras de `conversations.py:231-240`) |
| `tool.started` / `tool.progress` / `tool.completed` / `tool.failed` | chat (ToolCallCard) | `call_id, tool, target, cost_estimate, error_code` (errores tipados de ADR-0020:30-33) |
| `asset.created` / `asset.updated` | panel Assets | `asset_id, kind (image/audio/video/doc/upload), status, thumb_url, read_url (firmada, TTL corto), provenance` |
| `workspace.changed` | panel Archivos | `manifest_version, changed_paths[]` (ADR-0019) |
| `still.rendered` / `preview.ready` | panel Escenas/Preview | `scene_id, still_url / scene_package_digest` |
| `gate.opened` / `gate.resolved` | chat (ReviewGate) + StageRail | `stage, artifact_digest, budget, actor` |
| `run.status` / `stage.status` | cabecera | estados de ADR-0008/0017 |
| `cost.updated` | CostMeter | `spent, reserved, budget` |
| `session.state` | cabecera | `starting / active / idle / resuming / lost` (ADR-0016) |
| `error` | chat | `cause, stage, action` (plan §3.2) |

Todos salen del **outbox** de Postgres, con reanudación por `Last-Event-ID` y dedupe en el cliente
(`main:apps/web/lib/useProjectEvents.ts:1-25`). Así una recarga no pierde nada (plan §3.3).

### 8.5 Subida de materiales en la conversación

1. El usuario arrastra un archivo o elige uno de Drive (Picker, patrón de `luca:apps/web/src/lib/google.ts:112-159`).
2. **Archivo local:** `POST /projects/{id}/assets/upload-url` (ya existe; allowlist de MIME y ≤200 MB,
   `main:apps/api/ia_api/routers/assets.py:45-122`) → el navegador hace PUT o una subida resumable
   a GCS → `POST /assets/{id}/attach`. Para archivos grandes, una sesión resumable iniciada en el
   servidor con `Origin` ([resumable](https://docs.cloud.google.com/storage/docs/resumable-uploads)).
3. **Archivo de Drive:** Next.js llama a `scripts.run('importFromDrive', fileId)`. GAS, como el
   usuario, copia el archivo de Drive a GCS por subida resumable, en chunks y en varias ejecuciones
   si hace falta (patrón UploadApp). Alternativa más simple: el control plane descarga con el token
   del usuario por la Drive API, sin GAS.
4. El mensaje del chat lleva `attachments: [asset_id]`. El host lo coloca en `inputs/` del
   workspace, de solo lectura (ADR-0019:22-26), y emite `asset.created{kind: upload}`. El adjunto
   aparece en el panel con la etiqueta "del usuario".
5. Regla de licencias: nunca se incorpora código del usuario ni proyectos Remotion (ADR-0018:23-27).

---

## 9. Conservar / cambiar / tirar

| Elemento de ia-academy | Con el nuevo flujo y la nueva arquitectura | Fuente |
|---|---|---|
| ADR-0016/0019 (workspace durable, checkpoint por contenido, CAB) | **Conservar** | ADR-0016, ADR-0019 |
| ADR-0017/0020 (Autor, herramientas de host, gates explícitos) | **Conservar**: son la lógica del chat | ADR-0017, ADR-0020 |
| ADR-0022 + `spikes/sandbox/` (atelier, runner, adaptadores, batería) | **Conservar**: base del `sandbox-host` | `spikes/sandbox/` |
| ADR-0008 durable-lite (Postgres, outbox, gates, fan-out idempotente) | **Conservar** en producción (assets, narración, timeline, render) | ADR-0008 |
| `libs/persistence` + RLS + migraciones 0001-0017 (+0018) | **Conservar** si se mantiene Postgres; **tirar** si se pasa a Firestore o GAS | `main:libs/persistence/` |
| `libs/generation-broker`, `libs/quality-gate`, `libs/domain` | **Conservar** | `main:libs/` |
| `workers/rendering` (Remotion por segmentos + ffmpeg) | **Conservar** → Cloud Run Job | `main:workers/rendering/src/` |
| `workers/orchestration` | **Conservar** (ADR-0021: Cloud Run instance) | ADR-0021 |
| `contracts/*` (OpenAPI, SceneDocument, commands) | **Conservar y ampliar** (eventos del §8.4) | `main:contracts/` |
| `packages/ui` chat (ChatPanel, Message, ToolCallCard), gate (ReviewGate), pipeline (Filmstrip, PreviewPlayer, CostMeter, StageRail) | **Conservar**: son las piezas de la vista dividida | `main:packages/ui/src/` |
| `packages/scene-renderer` (Remotion Player) | **Conservar** (pestaña Preview) | `main:packages/scene-renderer/` |
| `apps/web/lib/streamMessages.ts`, `useProjectEvents.ts` | **Conservar** (parser SSE por POST, resume, fallback) | `main:apps/web/lib/` |
| Pantallas Brief/Guion/Workbench/Export y el Stepper de 7 pasos | **Cambiar** → una página `/p/{id}` | `main:apps/web/app/_lib/screens.ts:25-33` |
| `CreativeDirector` (extracción de brief por turno) y productores LLM fijos por stage | **Tirar** (ADR-0017 ya lo retira; el Autor lo reemplaza) | ADR-0017:50-52; `main:apps/api/ia_api/adapters/creative_director.py` |
| Streaming simulado por palabras | **Tirar** → tokens reales del LLM | `main:apps/api/ia_api/routers/conversations.py:231-240` |
| Auth propia en FastAPI (OAuth + cookie + CSRF) e invitación | **Cambiar** → Auth.js en Next.js con `hd`; la API confía en un ID token de servicio + `X-User` firmado, o valida el ID token del usuario | `main:apps/api/ia_api/routers/auth.py:1-60` |
| Lista de dominios permitidos de ADR-0015 (abierta por defecto) | **Cambiar** → cerrada al dominio Xertica | ADR-0015:28-30; PBI:31 |
| Next.js 14.2 | **Cambiar** → 16.x (como luca) | `main:apps/web/package.json:19`; `luca:apps/web/package.json:18` |
| Web en Vercel | **Cambiar** (opcional) → Cloud Run | ADR-0012:87-88 |
| Wizard BYO de llaves por tenant | **Revisar**: con un solo dominio corporativo, quizá basta Vertex de plataforma (ADR-0012:76-81) | `main:docs/branding/ui-ux.md:35-38` |

**Si el backend se moviera de verdad a Apps Script**, habría que tirar `apps/api` (~19k líneas),
`libs/persistence` y la RLS, el outbox→SSE y el motor durable-lite. Además GAS no puede alojar el
loop del agente, ni el render, ni hablar con el CLI del sandbox, porque este solo existe dentro de
Cloud Run. Es decir, igual haría falta un servicio Cloud Run grande.

---

## 10. Riesgos, trade-offs y alternativas

### 10.1 Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Cloud Run sandboxes sigue en Preview sin SLA y sin API REST; la doc contradice lo medido (uid 0) | Media | Alto | Puerto `SandboxProvider` con plan B GA (el mismo host sin `--sandbox-launcher`, otro usuario y SA sin permisos; `docs/research/t2-limites-cloud-run-sandboxes.md:164`) y BYOC (ADR-0022:37-39) |
| Afinidad: el sandbox vive en una instancia y Cloud Run puede reciclarla | Alta | Medio | Ya cubierto: retomar = hidratar desde el checkpoint (ADR-0016). Hay que diseñar el routing por proyecto (T9) |
| GAS → Cloud Run sin llaves no está verificado | Alta | Medio | En la arquitectura propuesta GAS **no** llama a Cloud Run; solo hace Workspace. Si hiciera falta, spike con custom audience |
| Scopes sensibles de Workspace al hacer login → verificación de Google y fricción | Media | Medio | Cliente OAuth **Interno**; scopes incrementales; GAS solo para export/import |
| Cuota de 30 ejecuciones simultáneas de GAS si se usa `USER_DEPLOYING` | Media | Medio | `USER_ACCESSING` / `scripts.run` con el token del usuario; GAS fuera del camino crítico |
| CI de clasp con el refresh token de una persona | Alta | Bajo-medio | Cuenta de servicio de Workspace o cuenta técnica acordada con IaC; GAS con poca superficie y pocos despliegues |
| Reescritura en un repo nuevo (`new-ai-academy`) que pierda las 135 iteraciones y los tests de main | Media | Alto | Portar módulos (§9) en lugar de reescribir; mantener los contratos |
| Coste de hosts calientes para baja latencia (~$231/mes 24/7 por host de 4 vCPU / 8 GiB) | Media | Bajo | min-instances 0 en dev; 1 en demo (`docs/research/t2-limites-cloud-run-sandboxes.md:36-37`) |
| Licencias: AGPL de OpenMontage y Company License de Remotion | — | Alto | §11 |

### 10.2 Trade-offs clave

- **FastAPI existente frente a un backend TS en Next.js.** Conservar FastAPI mantiene RLS, outbox,
  gates y miles de tests, a cambio de dos lenguajes. Pasar todo a TS unifica el stack (como luca),
  pero obliga a reescribir unas 30k líneas de Python probadas. **Se recomienda conservar.**
- **SSE propio frente a Firestore.** SSE ya está construido y probado, con resume. Firestore elimina
  el servidor de larga vida, pero duplica el estado y requiere reglas de seguridad.
- **Cloud Run frente a Vercel para la web.** Cloud Run da un solo perímetro, IAP y WIF. Vercel da
  previews y CDN sin tocar GCP.

### 10.3 Alternativas de arquitectura

| Alternativa | Descripción | Veredicto |
|---|---|---|
| **A. Híbrida (recomendada)** | §7: Next.js + control plane en Cloud Run + sandbox-host + Jobs + GCS; GAS solo para Workspace | Cumple R1-R7 |
| **B. "GAS-first"** | GAS como API (CRUD de proyectos en Sheets o Firestore vía REST, gates); Cloud Run solo para agente y render; progreso por Firestore `onSnapshot` | Viable para metadatos, pero el agente, el streaming y la durabilidad igual viven en Cloud Run. Quedan dos backends y gana el peor de los límites (6 min, 30 concurrentes, sin códigos HTTP). Solo si hay una razón organizacional fuerte |
| **C. Todo en Next.js (TS)** | Route handlers + un worker TS; sin FastAPI | Unifica el stack; obliga a reescribir el dominio. Tiene sentido solo si se descarta el código de main |
| **D. Sandbox gestionado** | Gemini Managed Agents o BYOC de Agent Platform en lugar del host propio | Ya evaluado: BYOC falló el ciclo de recrear y fue 15 veces más lento en preview (`docs/research/t7-spike-sandbox-resultados.md:12-24`). Managed Agents queda como referencia (`managed-agents-gas`) |

---

## 11. Impacto en la decisión legal

- **AGPL-3.0 de OpenMontage.** La §13 obliga a ofrecer el código fuente a quien interactúa por red
  con una versión modificada (`docs/adr/0001-clean-room-reuse-of-openmontage.md:3-9`;
  `docs/research/research-openmontage-web-app.md:23`). **Nada de la nueva arquitectura lo
  cambia**:
  - **Sandbox:** ejecutar OpenMontage dentro de un sandbox que sirve a usuarios es justo el
    supuesto de la §13. "El aislamiento por sandbox no cambia el análisis"
    (`docs/research/gemini-managed-agents-openmontage-sandbox.md:19,256`).
  - **Apps Script:** no altera nada. Es otra capa de red.
  - **Chat estilo "Claude Code sobre OpenMontage":** el riesgo práctico es que el Autor reciba
    skills, prompts o plantillas copiados de OpenMontage, o que el laboratorio "replique el
    andamiaje" de OpenMontage (`docs/research/discovery-laboratorio-managed-agent-video.md:243`).
    Si la imagen atelier o las instrucciones del Autor llevan archivos de OpenMontage, hay
    distribución de código AGPL. La regla de ADR-0001 sigue: **clean-room**, con skills y
    contratos propios, y OpenMontage solo como referencia fuera de la imagen. Cualquier copia exige
    primero la licencia comercial (ADR-0001:22-24).
  - **Recomendación:** añadir al build de la imagen atelier un control (lista de archivos o hash)
    que demuestre que no contiene archivos de `OpenMontage/`, y documentarlo en el ADR de la imagen.
- **Remotion.** El código de escena lo escribe solo el Autor; nunca se aceptan proyectos Remotion
  del usuario. Además se necesita la Company License según el tamaño del equipo (ADR-0018:23-27;
  `docs/research/remotion-license.md`). Con el chat, la regla de §8.5 punto 5 se vuelve más
  importante: el usuario podrá **pegar** código en la conversación.
- **Apps Script y Workspace:** si el cliente OAuth es Interno y no se publica fuera del dominio,
  no aplica la verificación pública de scopes **[no verificado en esta sesión; confirmarlo con el
  admin de Workspace]**.

---

## 12. Recomendación

1. **Adoptar el user-flow de chat con vista dividida** como la UI de ADR-0017/0020. Es una página
   `/p/{id}` con chat, panel (Assets · Escenas · Preview · Archivos) y gates inline, alimentada por
   el envelope de eventos del §8.4.
2. **No usar Apps Script como backend del pipeline.** Usarlo como **capa de Workspace** (importar y
   exportar Drive, Docs y Slides, avisos, MCP opcional) vía `scripts.run` con el token del usuario,
   en modo `USER_ACCESSING` y `access: DOMAIN`.
3. **Mantener ADR-0022** (Cloud Run sandboxes + Cloud Run Jobs), con tres correcciones: la nota de
   32 MiB solo en HTTP/1, los roles de despliegue en el pedido de IAM y una nota de que uid 0 y
   gVisor son mediciones.
4. **Login:** Auth.js con cliente OAuth Interno, `hd` y validación de `profile.hd` en el servidor,
   reutilizando la base de luca. IAP en Cloud Run como defensa extra opcional.
5. **No reescribir desde cero en `new-ai-academy`.** Portar los módulos del §9: el control plane
   FastAPI, las libs, `packages/ui`, `scene-renderer`, `workers/rendering`, los contratos y el
   spike del sandbox. Del frontend de luca: auth, guardia, mocks y esqueleto visual.
6. **Hacer los spikes de §14 F0 antes de escribir ADRs nuevos.**

---

## 13. Preguntas abiertas

1. **¿Por qué Apps Script como backend?** ¿Es una exigencia de Xertica (gobierno, coste, no poder
   pedir recursos al proyecto GCP compartido), una preferencia por reutilizar lo de luca, o la
   necesidad de actuar sobre el Drive y el Workspace del usuario? La respuesta decide entre las
   alternativas A y B (§10.3).
2. **¿`new-ai-academy` es un repo nuevo para reescribir o un destino para portar main?** ¿Se
   mantiene Python/FastAPI?
3. **Base de datos:** ¿se mantiene Postgres con RLS (recomendado) o se quiere Firestore / Sheets?
4. **Dominio exacto y organización:** ¿`xertica.com`, `xertica.ai` o ambos? ¿El proyecto GCP está en
   la organización Xertica, para poder usar un cliente OAuth **Interno**? ¿Puede haber invitados
   externos alguna vez?
5. **Proyecto GCP:** ¿se sigue con `aifirst-dev` compartido e IaC (ADR-0012), con Cloud Run
   sandboxes ya pedido (`docs/deployment/permisos-iam-sandbox-pedido-iac.md`), o hay un proyecto
   nuevo?
6. **¿Qué debe hacer Apps Script concretamente** el día 1? ¿Importar de Drive, exportar a Drive o
   Slides, avisos por Gmail o Chat, servidor MCP? Si nada de eso es MVP, GAS puede posponerse.
7. **Web en Vercel o en Cloud Run.** ¿Hace falta IAP?
8. **Credencial de CI para `clasp`:** ¿hay una cuenta técnica de Workspace permitida? (WIF no aplica
   a la Apps Script API.)
9. **Proveedores:** ¿se mantiene BYO por tenant o, al ser un solo dominio, todo va por Vertex de
   plataforma?
10. **AGPL:** ¿se confirma que la imagen atelier y las skills del Autor no llevarán archivos de
    OpenMontage? ¿Se va a explorar la licencia comercial?
11. **Remotion:** ¿está gestionada la Company License para el tamaño del equipo de Xertica?
12. **Escala objetivo:** ¿cuántos usuarios simultáneos y qué duración de video? Esto dimensiona los
    sandboxes por host y min-instances.

---

## 14. Plan por fases

| Fase | Objetivo | Entregables | Criterio de salida |
|---|---|---|---|
| **F0 · Decisiones y spikes** (1-2 semanas) | Despejar lo no verificado | (a) Spike `scripts.run` desde un route handler de Next.js con el token de Auth.js, script `access: DOMAIN`, medir latencia p50/p95. (b) Spike opcional GAS → Cloud Run privado con `getIdentityToken()` + custom audience. (c) Re-correr la batería T7 con el host como servicio con afinidad y varios sandboxes por host (T9). (d) Respuestas a §13. (e) ADR "rol de Apps Script" + ADR "frontend y auth" | Spikes con resultados medidos en `docs/research/`; ADRs aceptados |
| **F1 · Esqueleto** (1-2 semanas) | Login de dominio y deploy | Next.js 16 en Cloud Run (standalone), Auth.js con `hd` + `signIn`, modo mock (patrón luca), control plane FastAPI que confía en la identidad de la web, CI con WIF, job de clasp por entorno, tests de GAS (harness de luca o gas-fakes) | Usuario de otro dominio → 403; e2e de login en mock; deploy reproducible |
| **F2 · Chat + materiales** (2 semanas) | Conversar y adjuntar sin gasto | Página `/p/{id}` con chat (packages/ui), tokens reales del LLM, adjuntos por signed URL/resumable a `inputs/`, AgentSession con sandbox-host (sin herramientas de pago, ADR-0020), `session.state`, retomar | Recargar no pierde nada; matar el sandbox → retomar con el workspace intacto |
| **F3 · Vista dividida + producción** (2-3 semanas) | Panel de assets y gates inline | Eventos §8.4 en el outbox, panel Assets/Escenas/Preview/Archivos, herramientas de host de pago tras `gate:proposal`, filmstrip, point-to-regenerate | Golden path hasta el filmstrip aprobado desde el chat |
| **F4 · Render, export y Workspace** (2 semanas) | Video final y Drive | Render en Cloud Run Job, `final_review`, export MP4/SRT/provenance, `scripts.run('exportToDrive')` (resumable desde GCS) | MP4 Full HD en GCS y en el Drive del usuario |
| **F5 · Hardening** (2 semanas) | Demo con usuarios Xertica | Cuotas por usuario (PBI T4), alertas del host, coste por sesión, revisión de seguridad (CAB, CORS del bucket, TTL de URLs), control anti-OpenMontage en la imagen, runbooks | Criterios del plan §3 (`docs/plan/plan-desarrollo-demo-video-saas.md:34-69`) |

---

## 15. Fuentes

### Locales (ia-academy)
- `docs/adr/0001…0022` (en especial 0001, 0008, 0012, 0015-0022), `CONTEXT.md`,
  `docs/plan/plan-desarrollo-demo-video-saas.md`, `docs/branding/ui-ux.md`
- `docs/research/t2-limites-cloud-run-sandboxes.md`, `t7-spike-sandbox-resultados.md`,
  `research-openmontage-web-app.md`, `gemini-managed-agents-openmontage-sandbox.md`,
  `discovery-laboratorio-managed-agent-video.md`
- `docs/pbi/PBI-proyectos-por-dueno-y-sandbox-autor.md` (sin trackear),
  `docs/html/sandbox-autor-byoc-vs-cloud-run.html` (sin trackear)
- Código en `main`: `apps/web/app/_lib/screens.ts`, `apps/web/features/brief/useBriefChat.ts`,
  `apps/web/lib/{streamMessages,useProjectEvents}.ts`, `apps/api/ia_api/routers/*.py`,
  `apps/api/ia_api/adapters/creative_director.py`, `libs/persistence/ia_persistence/models.py`,
  `libs/domain/ia_domain/stages.py`, `docker-compose.yml`, `.github/workflows/ci.yml`, `spikes/sandbox/`

### Locales (luca)
- `apps/web/src/auth.ts`, `apps/web/src/app/app/layout.tsx`, `apps/web/src/lib/google.ts`,
  `gas/shared/{webapp-runtime,mcp-runtime,ui-runtime,secrets-runtime,llm-runtime}.js`,
  `gas/stub/{Code,triggers,config}.js`, `services/luca-mcp/src/{gasClient,index,tools,auth,storage}.ts`,
  `tests/gas-harness.mjs`, `spikes/README.md`, `CLAUDE.md`, `CONTEXT.md`, `README.md`

### Repos externas
- https://github.com/tanaikech/cloud-run-sandbox-gas (`/tmp/research-repos/cloud-run-sandbox-gas`, `2baf6b8`)
- https://github.com/shivajibodkhe/google-apps-script-cicd-template (`/tmp/research-repos/google-apps-script-cicd-template`, `74e3cc9`)
- Repos de tanaikech citadas en §4.3; listado completo en `/tmp/research-repos/tanaikech-repos.json`

### Documentación oficial
- Apps Script: https://developers.google.com/apps-script/guides/services/quotas ·
  https://developers.google.com/apps-script/guides/web ·
  https://developers.google.com/apps-script/guides/content ·
  https://developers.google.com/apps-script/manifest/web-app-api-executable ·
  https://developers.google.com/apps-script/api/how-tos/execute ·
  https://developers.google.com/apps-script/guides/cloud-platform-projects ·
  https://developers.google.com/apps-script/reference/script/script-app ·
  https://developers.google.com/apps-script/reference/url-fetch/url-fetch-app ·
  https://developers.google.com/apps-script/reference/cache/cache ·
  https://developers.google.com/apps-script/reference/lock/lock-service ·
  https://developers.google.com/apps-script/guides/html/communication ·
  https://developers.google.com/apps-script/guides/triggers/installable ·
  https://developers.google.com/apps-script/reference/script/clock-trigger-builder
- Cloud Run: https://docs.cloud.google.com/run/docs/code-execution ·
  https://docs.cloud.google.com/run/docs/reference/sandbox-cli ·
  https://docs.cloud.google.com/run/docs/configuring/services/sandboxes ·
  https://docs.cloud.google.com/run/docs/configuring/jobs/sandboxes ·
  https://docs.cloud.google.com/run/docs/release-notes ·
  https://docs.cloud.google.com/run/quotas ·
  https://docs.cloud.google.com/run/docs/configuring/request-timeout ·
  https://docs.cloud.google.com/run/docs/triggering/websockets ·
  https://docs.cloud.google.com/run/docs/configuring/session-affinity ·
  https://docs.cloud.google.com/run/docs/configuring/custom-audiences ·
  https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run ·
  https://docs.cloud.google.com/run/docs/known-issues ·
  https://cloud.google.com/blog/topics/developers-practitioners/google-cloud-run-sandboxes-are-in-public-preview/
- Agent Platform: https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/sandbox/code-execution-quickstart
- GCS: https://docs.cloud.google.com/storage/docs/access-control/signed-urls ·
  https://docs.cloud.google.com/storage/docs/resumable-uploads ·
  https://docs.cloud.google.com/storage/docs/cross-origin
- Next.js: https://nextjs.org/docs/app/api-reference/file-conventions/route ·
  https://nextjs.org/docs/app/api-reference/config/next-config-js/output
- Identidad: https://developers.google.com/identity/openid-connect/openid-connect ·
  https://authjs.dev/getting-started/providers/google ·
  https://support.google.com/cloud/answer/10311615 (tipo de usuario Interno; no verificado en esta sesión)
- Firestore: https://firebase.google.com/docs/firestore/query-data/listen
- GitHub Actions: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
