# Zavu + WhatsApp: capacidades para el MVP de inteligencia de flota

> Investigado el 2026-10-18 contra fuentes primarias: docs oficiales de Zavu (`docs.zavu.dev`, servidas como `.md`), página de precios `zavu.dev/pricing`, paquetes npm `zavudev@0.14.1` (CLI) y `@zavudev/functions@0.3.1`, y documentación/términos oficiales de Meta. Cada afirmación cita URL + sección. Contexto: `docs/product/PRODUCT_CONTEXT_CERTERA.md` §9 y §11; agente base en `zavu/index.ts`.
>
> Leyenda: **CONFIRMADO** = la fuente lo dice explícitamente. **LIMITACIÓN** = confirmado, pero restringe nuestro diseño. **NO ENCONTRADO** = ninguna fuente primaria lo documenta (no asumir).

Flujos objetivo: (a) conductor → reporte libre → nuestro backend; (b) gestor consulta → agente con tools → nuestra Domain API por HTTP; (c) backend → alertas proactivas (plantillas fuera de la ventana de 24 h).

---

## 1. ¿Una tool de `defineAgent` puede hacer fetch HTTP a un backend externo?

- **CONFIRMADO: fetch libre.** "Standard `fetch`. Functions have unrestricted egress (today)." Incluye un ejemplo que llama a una API externa con `Authorization: Bearer ${process.env.POS_API_KEY}`. — https://docs.zavu.dev/guides/functions/defining-tools.md § "Calling external services"
- **CONFIRMADO: el valor de retorno vuelve al LLM**, y si se lanza una excepción el LLM recibe `success: false` junto con el mensaje. Conviene devolver campos con nombres semánticos y recortar las listas en el servidor. — misma página, § "Return value", § "Error handling" y § "Returning a list back to the LLM"
- **CONFIRMADO: `ctx.contactPhone`** (E.164) llega al handler. Sirve para que nuestra API autorice según el número que escribe. — misma página, § "`ctx` properties"
- **CONFIRMADO: el modelo puede encadenar hasta 5 rondas de tools por respuesta** en canales de texto (WhatsApp incluido). — https://docs.zavu.dev/concepts/agent-architecture.md § "Where tools run"
- **Secretos, CONFIRMADO.** `npx zavudev fn secrets set KEY value`, también desde stdin con `-`. Se cifran con AES-256-GCM y se inyectan como `process.env`. Solo se aplican en el siguiente `deploy`. Límites: 50 secretos por función, valores de hasta 4096 caracteres y 4 KB de entorno en total. Prefijos reservados: `AWS_`, `LAMBDA_`. Se auto-provisiona `ZAVU_API_KEY` con los scopes `messages:send`, `messages:read` y `contacts:read`. — https://docs.zavu.dev/guides/functions/secrets.md § "Constraints", § "When changes take effect" y § "Auto-provisioned secrets"
- **Timeouts, LIMITACIÓN (la documentación se contradice).**
  - "Timeout per invocation | 180 sec (default 30)". Una tool llamada durante una conversación es síncrona: "a tool that takes 60 seconds is a conversation that looks broken." — https://docs.zavu.dev/guides/functions/advanced-patterns.md § "Limits to know" y § "Choosing a timeout"
  - Otra página dice "30s budget by default (configurable up to 15min)". — https://docs.zavu.dev/guides/functions/defining-tools.md § "Long-running tasks"
  - Nuestra lectura: diseñar para ≤ 5–10 s por llamada a la Domain API. Las Webhook Tools del dashboard recomiendan "under 10 seconds". — https://docs.zavu.dev/guides/ai-agents/tools.md § "Best Practices"
- **Runtime, CONFIRMADO.** Node sobre AWS Lambda (layer `zavu-nodejs24`), arm64 por defecto. Hasta 1024 MB, 900 KB de código fuente, zip de 6 MB y 30 dependencias. Recomiendan ~20 tools como máximo práctico ("LLM degrades past ~10"). Funciona como serverless: el estado de módulo no persiste entre invocaciones. — https://docs.zavu.dev/guides/functions/runtime.md § "Checking your pin" y § "CPU architecture"; advanced-patterns.md § "Limits to know"; comentario de cabecera en `zavu/index.ts`
- **CONFIRMADO: existe una alternativa sin código ("Webhook Tools").** Zavu hace POST a nuestra URL con `{tool, arguments, context:{messageId, contactPhone, sessionId}, timestamp}` y la cabecera `X-Zavu-Signature` (HMAC-SHA256, solo si hay secreto configurado). — https://docs.zavu.dev/guides/ai-agents/tools.md § "Webhook Payload", § "Headers" y § "Signature Verification". Ojo: un agente gestionado por `defineAgent` bloquea las ediciones desde el dashboard (https://docs.zavu.dev/concepts/functions.md § "How it relates to AI Agents"), así que conviene elegir uno de los dos modelos.

## 2. Webhooks entrantes hacia un servidor propio

- **CONFIRMADO: Sender Webhooks.** Hay un webhook por sender, con eventos `message.inbound`, `conversation.new`, `message.queued|sent|delivered|read|failed` y `template.status_changed`. Se configuran desde el dashboard o con `PATCH /v1/senders/{id}` (`webhookUrl`, `webhookEvents`). — https://docs.zavu.dev/guides/receiving-messages/webhooks.md § "Sender Webhooks" y § "Available Events"
- **Firma, CONFIRMADO.** Cabecera `X-Zavu-Signature: t=<seg>,v2=<hex>`. El esquema v2 es `HMAC_SHA256(secret, "{t}.{rawBody}")` y el v1, heredado, es `HMAC_SHA256(secret, rawBody)`. El cuerpo debe verificarse en crudo (`express.raw`). La documentación recomienda rechazar firmas con más de 300 s de antigüedad o con desfase de más de 60 s, y comparar en tiempo constante. El secreto `whsec_…` se muestra una sola vez y puede regenerarse. — https://docs.zavu.dev/guides/receiving-messages/security.md § "Signature Header", § "The two schemes" y § "Verifying"; webhooks.md § "Regenerate Secret"
- **Payload, CONFIRMADO.** Sobre común `{id, type, timestamp(ms, despacho), senderId, projectId, data}`. Para `message.inbound`: `data = {messageId, from, to, channel, messageType, text, profileName, providerTimestamp}`, además de variantes para imagen, audio, ubicación y otros tipos. — https://docs.zavu.dev/guides/receiving-messages/events.md § "message.inbound"; webhooks.md § "Webhook Payload"
- **LIMITACIÓN: `from` puede ser un BSUID** (p. ej. `US.1349…`) en lugar de un teléfono, cuando el usuario de WhatsApp usa nombre de usuario. Hay que tratarlo como un identificador opaco al mapear conductores. — events.md § "Username Contact (BSUID) Example"
- **Entrega, CONFIRMADO.** El servidor debe responder 2xx en menos de 30 s. Los reintentos llegan a 1 min, 5 min, 15 min, 1 h y 4 h; después de eso, la entrega se marca como fallida. — webhooks.md § "Handling Webhooks" y § "Retry Policy". Implicación: deduplicar por `data.messageId`.
- **CONFIRMADO: el webhook y el agente coexisten.** Si el agente está en pausa, "messages to its sender still reach your webhooks" (https://docs.zavu.dev/guides/functions/defining-agents.md § "Disabling without deleting"). Un trigger nativo `message.inbound` con un agente activo en el mismo sender hace que "two things happen" (https://docs.zavu.dev/guides/functions/triggers.md § "When triggers + defineAgent coexist"). Los mensajes de grupo también llegan a los webhooks aunque `groups` esté desactivado (defining-agents.md § "Group chats").
- **LIMITACIÓN: el agente solo ve texto por defecto** (`messageTypes: ["text"]`). Las notas de voz y fotos del conductor no llegan al LLM a menos que se configure; sí llegan al webhook. — defining-agents.md § "Optional fields"

## 3. Envío saliente iniciado por el negocio (alertas)

- **CONFIRMADO: API.** `POST /v1/messages` con `messageType: "template"` y `content: {templateId, templateVariables}`. El sender se elige con la cabecera opcional `Zavu-Sender` y hay un `idempotencyKey` opcional. — https://docs.zavu.dev/guides/whatsapp/templates/sending.md § "Quick Start"; https://docs.zavu.dev/api-reference/send-a-message.md (`SenderHeader` e `idempotencyKey`)
- **Ventana de 24 h, CONFIRMADO.** Fuera de la ventana solo se pueden enviar plantillas. Un mensaje libre fuera de ella se acepta con 202 y después falla por webhook `message.failed` con `errorCode` `131047`. — https://docs.zavu.dev/guides/whatsapp/overview.md § "The 24-Hour Conversation Window"; https://docs.zavu.dev/guides/whatsapp/error-codes.md (tabla, `131047`, y la nota sobre las dos vías de rechazo). Según Meta, la ventana se abre con cada mensaje del usuario y cierra 24 h después del último. — https://developers.facebook.com/docs/whatsapp/pricing § "Charge example"
- **Aprobación, LIMITACIÓN.** Las plantillas pasan por los estados `draft → pending → approved/rejected`. Se envían con `POST /v1/templates/{id}/submit` (`category`, `variableExamples`). El tiempo típico es de **24–48 h y puede llegar a 72 h**. El estado se sigue con el webhook `template.status_changed` o con `POST /v1/templates/sync`. — https://docs.zavu.dev/guides/whatsapp/templates/approval.md § "Approval Timeline", § "Sample Values for Variables" y § "Tracking Status Changes". Otra página dice "UTILITY … Fast (hours)" (sending.md, tabla de categorías). Recomiendan usar UTILITY para mensajes transaccionales (https://docs.zavu.dev/concepts/templates.md).
- **Costos, CONFIRMADO.**
  - Meta cobra por mensaje desde el 2025-07-01. "All non-template messages are free"; las plantillas utility son gratis dentro de una ventana abierta y se cobran fuera de ella; las de marketing siempre se cobran. — https://developers.facebook.com/docs/whatsapp/pricing § "Cloud API and Marketing Messages API for WhatsApp" y § "Charge example"
  - Zavu no añade margen: "Meta bills WhatsApp straight to your own Business account … We add nothing on top." — https://www.zavu.dev/pricing (sección WhatsApp)
  - **NO ENCONTRADO:** la tarifa utility para Perú en una fuente primaria verificada para este documento.
- **Límite de mensajería de Meta, CONFIRMADO.** Los portafolios nuevos pueden enviar a 250 usuarios únicos en 24 h fuera de la ventana. Es suficiente para la demo. — https://developers.facebook.com/docs/whatsapp/messaging-limits (introducción)
- **Número de prueba / sandbox, LIMITACIÓN.**
  - Una clave `zv_test_` envía desde el número sandbox compartido de Zavu, solo por WhatsApp y solo a teléfonos verificados del equipo (máximo 5 por proyecto; se verifican enviando `VERIFY-…` desde el propio teléfono). Esa clave ignora los senders propios. "The messages are delivered for real." — https://docs.zavu.dev/concepts/sending-limits.md § "Test-mode keys"; https://docs.zavu.dev/authentication.md (tabla de prefijos)
  - **NO ENCONTRADO:** si un agente `defineAgent` puede responder en el número sandbox, o si se pueden enviar plantillas propias desde él. Para la demo hay que contar con un número propio conectado vía Meta Embedded Signup: un número Zavu (verificación por llamada) o uno propio que no esté registrado en WhatsApp (verificación por SMS). — https://docs.zavu.dev/guides/whatsapp/connect-whatsapp.md § "Connection Options"

## 4. ¿Agente Zavu + alertas del backend por el mismo número?

- **CONFIRMADO (implícito): son dos caminos independientes.** El agente se asocia al sender ("A sender answers with at most one agent"), y la API de mensajes envía desde cualquier sender con `Zavu-Sender`. — https://docs.zavu.dev/concepts/agent-architecture.md § "Agents and senders"; send-a-message.md (`SenderHeader`). La auto-key de la función tiene `messages:send` (secrets.md).
- **LIMITACIÓN: un solo agente por sender.** Conductores y gestores que escriban al mismo número caen en el mismo agente. La distinción de rol tiene que hacerla una tool (`ctx.contactPhone` → nuestra API) o el prompt. Usar dos números (dos senders con dos agentes) es la vía "canónica": "Multiple senders / multiple functions is the canonical way". — agent-architecture.md § "Agents and senders"; advanced-patterns.md (sección previa a "Cost optimization")
- **NO ENCONTRADO:** si los mensajes enviados por API (las alertas) entran en el historial `contextWindowMessages` del agente. Si el gestor responde a una alerta, el agente podría no tener ese contexto. Mitigación: que una tool `get_alerts` lo recupere desde nuestra API.
- **NO ENCONTRADO:** un "handoff" o pausa del agente por contacto. Lo único documentado es la pausa global (`enabled:false`) y `NO_REPLY`, que hace que el agente no responda y aun así consume tokens. — defining-agents.md § "Staying silent with `NO_REPLY`"

## 5. ¿Soporta MCP (consumir un servidor MCP externo como tools)?

- **NO / LIMITACIÓN.** El shim de compatibilidad del CLI oficial incluye literalmente `defineMCPConnection = __stub("defineMCPConnection", "MCP connections are not supported on Zavu")` y `defineOpenAPIConnection … "call the API from a tool handler instead"`. — paquete npm `zavudev@0.14.1`, `dist/zavu.js`, bloque "Stubs for eve surfaces that have no Zavu equivalent" (relacionado: https://docs.zavu.dev/guides/functions/deploy-eve-project.md)
- **CONFIRMADO: el MCP que existe va en sentido contrario.** `@zavudev/sdk-mcp` expone la API de Zavu a asistentes como Claude, Cursor o VS Code; no sirve para consumir MCP desde un agente Zavu. — https://docs.zavu.dev/tools/mcp-server.md § "Quick Start"
- **Implicación:** nuestro MCP server (§11 del contexto de producto) sigue siendo útil para otros clientes. Para Zavu, cada tool `defineTool` hace un `fetch` a la Domain API, o al MCP server por HTTP si implementamos el cliente nosotros con una dependencia npm. Esto último es posible por el egress libre, pero no está documentado ni soportado.

## 6. Política de Meta para chatbots de IA (vigente desde 2026-01-15)

- **CONFIRMADO.** Sección 4.7 "Provedores de IA" de los Meta Terms for WhatsApp Business Platform (última actualización: 23-sep-2026; la versión en inglés prevalece según la §7.2). Prohíbe el acceso a los "AI Providers" (LLMs, plataformas de IA generativa, asistentes de uso general) **cuando la IA es la funcionalidad principal y no incidental o auxiliar**, según el criterio de Meta. — https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform §4.7 (redirigido desde https://www.whatsapp.com/legal/business-solution-terms)
- **CONFIRMADO: prohibición de entrenamiento.** No se pueden usar los datos de la plataforma, ni siquiera anonimizados, agregados o derivados, para crear, entrenar o mejorar modelos de ML. La única excepción es el ajuste fino de un modelo de uso exclusivo de la empresa. — misma página, §4.7
- **NO ENCONTRADO en la fuente primaria:** la fecha 2026-01-15. La §4.7 vigente no trae fecha de entrada en vigor; esa fecha proviene de cobertura secundaria (p. ej. TechCrunch, 2025-10-18) y se usa aquí solo como contexto.
- **Aplicación a nosotros:** un agente acotado a la operación de flota de la propia empresa, con IA auxiliar al servicio, encaja como uso permitido. Riesgos a evitar: que responda temas generales fuera del negocio (mantener el `# Scope` estricto en el prompt) y reutilizar las conversaciones para entrenar modelos.

## 7. Límites del plan gratuito relevantes para una demo en vivo

- **CONFIRMADO: el cupo cuenta mensajes en ambas direcciones.** WhatsApp, Telegram, Instagram y Messenger comparten 2,000 mensajes al mes en Free, y **cuentan tanto enviados como recibidos**. Al agotarse se bloquean el envío (429 `a2p_limit_exceeded`, incluidas las respuestas del agente) **y la recepción** (no se almacena el mensaje ni se dispara `message.inbound`). — https://docs.zavu.dev/concepts/sending-limits.md § "Monthly allowance on the app channels" y § "What happens at the cap"
- **CONFIRMADO: tope diario.** El grupo conversacional permite **100/día en cuentas Unverified** y 250/día en Free Verified (se verifica guardando una tarjeta sin cargo o con KYC). Se reinicia a las 00:00 UTC. — sending-limits.md § "Account levels" y § "Daily ceilings"
- **CONFIRMADO: Functions.** 300k invocaciones al mes en Free, con tope duro al alcanzarlas. — https://docs.zavu.dev/concepts/functions.md § "Plan quotas"; https://www.zavu.dev/pricing
- **CONFIRMADO: API.** 600 solicitudes/min por proyecto. — https://docs.zavu.dev/concepts/rate-limiting.md § "Request Limits"
- **CONFIRMADO: plan Free en precios.** "$0/mo … no credit card"; "only two connections (one can be WhatsApp)"; números de teléfono "—" en Free; $2 de crédito "for SMS, voice and email"; Pro cuesta $20/mes con mensajes ilimitados. El LLM vía proxy se cobra por token desde el saldo, y algunos modelos están "included in the base". — https://www.zavu.dev/pricing
- **NO ENCONTRADO:** si el consumo de tokens del modelo actual (`deepseek/deepseek-v4-flash-0731`) descuenta del crédito Free. Hay que verificarlo en el dashboard (`GET /v1/balance`) antes de la demo.
- **CONFIRMADO: pruebas sin costo.** `npx zavudev agents test` hace un dry run gratuito que no ejecuta tools; `fn invoke --tool` también es gratis. — https://docs.zavu.dev/concepts/agent-architecture.md § "What you can verify, and when"

---

## Implicaciones para el MVP

**Arquitectura recomendada**

| Vive en Zavu | Vive en nuestro backend |
|---|---|
| Sender WhatsApp con número propio conectado | `POST /webhooks/zavu`: verifica la firma v2 y deduplica por `messageId` |
| Agente `defineAgent` (prompt acotado, español, `channels:["whatsapp"]`) | Domain API autenticada (Bearer, guardado en `fn secrets`) |
| Tools delgadas que solo hacen `fetch` → Domain API: `get_trip_status`, `get_fuel_analysis`, `get_operational_bottlenecks`, `get_alerts`, `whoami` | Lógica de rol: `contactPhone`/BSUID → conductor, gestor o desconocido; ámbito por empresa |
| Plantillas UTILITY aprobadas (alertas) | Ingesta de reportes (a): extracción de intención → `human_report`/`operational_event` |
| | Alert service (c): reglas, deduplicación, envío con `POST /v1/messages` (plantilla, o texto libre si la ventana está abierta), bitácora con `message.delivered/failed` |

- **(a)** El webhook del sender es la fuente de verdad de la ingesta: recibe todo, incluidos audio e imágenes. Para no duplicar, el agente **no** debe registrar reportes por su cuenta. Ante un mensaje de un conductor, el agente responde un acuse breve (o `NO_REPLY`) según lo que devuelva `whoami`. Alternativa: usar dos números (conductores y gestores) y así eliminar la ambigüedad de rol.
- **(b)** Mantener cada tool por debajo de unos 5 s de latencia y devolver JSON pequeño con estado, evidencia, `updated_at` y siguiente acción. Nuestro MCP server queda para otros clientes; Zavu **no** lo consume de forma nativa.
- **(c)** Enviar a revisión **ya** 2–3 plantillas UTILITY con variables y ejemplos realistas, porque la aprobación toma 24–48 h y puede llegar a 72 h. Antes de la demo, hacer que el gestor escriba al número para abrir la ventana de 24 h: así las alertas pueden ir como texto libre y gratis aunque la plantilla no esté aprobada.

**Riesgos**

1. Plantilla rechazada o todavía pendiente el día de la demo.
2. Cupo Free: 100–250 mensajes/día y 2,000/mes contando ambas direcciones. Al agotarse se bloquea también la recepción. Mitigación: verificar la cuenta con tarjeta o pagar Pro ($20) durante el hackathon.
3. El número sandbox probablemente no sirve para el agente (no documentado), y conectar un número requiere Meta Embedded Signup.
4. Timeout de las tools: la documentación se contradice (180 s frente a 15 min) y la latencia la percibe el usuario.
5. `from` puede llegar como BSUID.
6. No está documentado si el agente ve las alertas enviadas por API.
7. Sobre la política de Meta: mantener el scope estrictamente operativo.

**Plan B**

- **B1:** desactivar el agente Zavu (`enabled:false`; los webhooks siguen llegando) y orquestar en nuestro backend: webhook → nuestro agente LLM con MCP → `POST /v1/messages` como respuesta dentro de la ventana de 24 h, que es gratis para mensajes sin plantilla.
- **B2:** si Zavu falla por completo, usar Meta Cloud API directo con su número de prueba (Quickstart: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started § "Step 3"), con la plantilla `hello_world` y respuestas libres dentro de la ventana.
- **B3:** para la demo, simular alertas como mensajes de sesión tras un "hola" del gestor.
