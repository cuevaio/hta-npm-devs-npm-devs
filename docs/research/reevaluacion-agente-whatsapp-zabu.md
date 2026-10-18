# Reevaluación: agente de WhatsApp para cobrar fletes, "Zabu" y marco legal del demo

> Fecha: 18 de octubre de 2026 · Tipo: research contra fuentes primarias
> Insumos leídos completos: `docs/gestion-de-facturacion-de-transporte-peru.md`, `docs/rubrica-evaluacion.md`, `docs/feedback/gonza.md`, el análisis previo (hoy está en `docs/analisis-facturacion-transporte-peru.md`: git lo marca como borrado de `docs/research/` y como no rastreado en `docs/`), `docs/research/README_demo.md`, `docs/research/INSTRUCTIVO_DEMO.md` y los 6 PDF y 4 PNG de `docs/research/`.
> Convención: cada afirmación lleva su URL. **[no verificado]** = no se pudo confirmar en fuente primaria. **[2ria]** = solo se confirmó en fuente secundaria. Fuera de alcance por decisión del usuario: cualquier trazabilidad de ubicación del vehículo (GPS, Samsara, telemetría, OBD).

---

## Resumen ejecutivo (veredicto)

- **El giro a "agente de WhatsApp del transportista" mejora el producto y el encaje con la rúbrica.** Ataca de frente el dolor de gonza: rechazos documentarios por formato, como "hoja azul vs. verde" (`docs/feedback/gonza.md`). Además, el canal ya está pactado en el caso: la OS-1042 dice que el POD "podrá ser presentado… por el canal de WhatsApp registrado" (`orden_servicio_OS-1042.pdf`, cl. 3). La base técnica del análisis previo sigue valiendo: Supabase con Edge Functions, Gemini con *function calling* y salida estructurada sobre un motor de reglas determinista, PSE/OSE para emitir y el Managed Agent fuera del camino crítico.
- **"Zabu" es casi seguro "Zavu" (zavu.dev). Confianza media-alta (~70 %).** En español la *b* y la *v* suenan igual. No existe ninguna API de WhatsApp llamada "Zabu". Zavu es una API multicanal para agentes de IA que conecta WhatsApp mediante el *Embedded Signup* de Meta, es decir, sobre la Cloud API oficial ([docs Zavu](https://docs.zavu.dev/guides/whatsapp/connect-whatsapp.md)). Hay un segundo "Zabu" real y peruano: una app Android de *tracking* del transportista de Lima Innovation Lab, de 2023. Está fuera de alcance (ubicación) y no menciona WhatsApp ([APKPure](https://apkpure.com/zabu/com.lilab.hound)). **Confirmado por el usuario el 2026-10-18: se refería a Zavu.**
- **Recomendación de canal.** Para el hackathon: Zavu como adaptador principal *si el usuario lo confirma*, detrás de una interfaz `MessagingPort`, con un adaptador directo a la Cloud API de Meta como respaldo y un **simulador de WhatsApp dentro del panel web** como plan B. Primero, un *spike* de 2 h que reciba una imagen de punta a punta. Para el piloto: Cloud API directa o Zavu, solo después de verificar su estatus de partner de Meta, el DPA y el SLA. **Descartadas:** APIs no oficiales tipo Z-API, que funcionan por sesión de WhatsApp Web ([developer.z-api.io](https://developer.z-api.io/)).
- **Ojo con "cualquier tipo de consultas".** Desde el 15 de enero de 2026, los términos de Meta (sección 4.7, "AI Providers") prohíben ofrecer asistentes de IA de propósito general cuando son la funcionalidad principal ([Meta Terms](https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform); [Meta, AI Providers](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/ai-providers.md)). El agente debe responder **cualquier consulta del negocio del transportista** (POD, OS, facturas, plazos, SPOT) y redirigir lo que quede fuera de ese dominio.
- **Hallazgo legal 1: el plazo de conformidad del demo usa el régimen equivocado.** Para una **factura electrónica** rige el D.U. 013-2020 y la RS 165-2021/SUNAT: **8 días calendario desde la puesta a disposición** en la plataforma SUNAT, que en SEE-SOL ocurre el mismo día de emisión ([RS 165-2021, El Peruano](https://busquedas.elperuano.pe/dispositivo/NL/2012062-1)). Los "8 días hábiles" del art. 7 de la Ley 29623 quedaron para comprobantes impresos o importados ([texto actualizado de la Ley 29623](https://www.cavali.com.pe/storage/uploads/shares/marco_legal/normativa/Ley_29623_que_promueve_el_financiamiento_a_trav__s_de_la_factura_comercial.pdf)). Consecuencia: el límite pasa del **vie 23-oct** al **mié 21-oct**, y la conformidad presunta queda el **jue 22-oct**. Hay un matiz sobre el día inicial, explicado en §4.
- **Hallazgo legal 2: la Ley 31362 es correcta y aplica entre privados.** El pago debe hacerse en un máximo de 30 días calendario **desde la emisión**. Un plazo mayor exige un acuerdo por escritura pública o con firmas legalizadas, y hay intereses moratorios desde el día siguiente al vencimiento ([Ley 31362](https://busquedas.elperuano.pe/dispositivo/NL/2016188-1); [D.S. 120-2022-EF](https://busquedas.elperuano.pe/dispositivo/NL/2076849-4)). El **jue 12-nov-2026** está bien calculado. La ley trae además su propia conformidad del servicio: 8 días calendario desde la recepción del servicio (art. 2.2), algo que el demo no aprovecha.
- **Los montos cuadran.** El SPOT es el 4 % sobre el mayor entre el importe y el valor referencial (S/ 4,590): S/ 183.60, que redondeado al entero da **S/ 184** (RS 178-2005/SUNAT, [FAQ SUNAT](https://orientacion.sunat.gob.pe/preguntas-frecuentes-detracciones)). El neto es **S/ 4,300**. Hay un posible error de catálogo: la factura usa el tipo de operación "0101". Para transporte de carga con detracción correspondería el **1004** del Catálogo 51 **[2ria]**.
- **Faltan piezas en el repo y hay incoherencias en el material del demo.** Faltan `ground_truth.json`, `ground_truth.csv`, `demo_estado.json` y los `.eml`. Los scripts viven en `/workspace/chofex/src/`, que no existe en esta máquina. La "política interna del 01/10" que el agente debería citar en el caso B **no aparece** en `observacion_B_formato_nuevo.pdf`. Si el agente la cita, estaría inventando, que es justo lo que el pitch promete que no hace.

---

## 1. Qué cambió con el nuevo material

### 1.1 El producto

| Antes (propuesta y análisis previo) | Ahora (README_demo e INSTRUCTIVO) |
|---|---|
| Plataforma web de gestión documental de punta a punta (contrato → OS → POD → liquidación → factura → cobranza) con agentes por rol | **Agente de WhatsApp** del transportista MYPE que: (1) recibe las fotos del POD del conductor, (2) las valida contra la cláusula 3 de la OS **antes** de presentarlas, (3) clasifica las observaciones del cliente como `observacion_valida` o `requisito_no_pactado` citando la cláusula, (4) redacta respuestas que el transportista **aprueba**, (5) arma los datos de la factura con SPOT y (6) sigue los plazos de conformidad y pago |
| Usuario principal difuso (cliente, operador, transportista) | Usuario claro: **dueño de la MYPE transportista** (aprueba) y **conductor** (sube evidencia) |
| Demo de 9 pasos sin datos | Caso completo y ficticio, coherente en lo esencial: OS-1042, GRE EG01-00004521, dos cargos, dos observaciones y factura E001-000123 |

### 1.2 Lo que se verificó en los archivos

- **OS-1042:** cl. 2.1, crédito a 30 días calendario desde la emisión "conforme a la Ley N° 31362". Cl. 2.3, revisión del POD en 1 día hábil, y las observaciones deben llegar por correo indicando el requisito de la cl. 3 que se incumple. Cl. 3, cinco requisitos (a–e), "No se exigirán formatos, documentos o evidencias adicionales". Cl. 3.1, los cambios requieren una adenda escrita y solo aplican a servicios posteriores.
- **Cargos:** `cargo_completo.png` y `cargo_sin_sello.png` coinciden con el ground truth del README: Carmen Rosa Poma Sotelo, DNI 99776655, 10/10/2026 14:35, "OS-1042" manuscrito (dos veces) y sello "RECIBIDO 10 OCT 2026" solo en el completo.
- **Factura:** total S/ 4,484; SPOT 027; VR ilustrativo S/ 4,590; detracción S/ 184; neto S/ 4,300; vence el 12/11/2026.

### 1.3 Archivos que faltan y otras incoherencias

| # | Hallazgo | Impacto |
|---|---|---|
| 1 | `ground_truth.json`, `ground_truth.csv`, `demo_estado.json`, `observacion_A_falta_sello.eml` y `observacion_B_formato_nuevo.eml` se mencionan en README_demo §2 e INSTRUCTIVO §2, pero **no están en el repo** (solo hay un resumen embebido en README §5) | Sin ellos no hay evaluación automática de la extracción ni máquina de estados reproducible: se pierde puntaje en "Calidad técnica" (20 %) |
| 2 | Los scripts de generación (`gen_os.py`, `gen_cargo.py`, …, `data.py`) viven en `/workspace/chofex/src/`, **que no existe en esta máquina**. El README §6 da comandos que no se pueden ejecutar | Los documentos no se pueden regenerar. Hay que traer los scripts al repo (p. ej. `tools/demo-docs/`) |
| 3 | README e INSTRUCTIVO dicen que la "política interna" del cliente "es del 01/10, anterior a la OS del 07/10". **`observacion_B_formato_nuevo.pdf` no trae ninguna fecha de la política**: solo dice "nueva política interna de recepción" | Si el agente cita "01/10", **alucina**. Hay que corregir el PDF (añadir la fecha) o quitar el argumento del guion y de la respuesta modelo |
| 4 | `observacion_A_falta_sello.pdf` dice que el POD incluía "la foto de la carga descargada", pero en "Adjuntos (hilo)" solo aparece `cargo_sin_sello.png` | Menor. Conviene alinearlo para que la extracción no detecte una contradicción |
| 5 | `foto_descarga.png` muestra unos 11 pallets visibles, mientras el *overlay* dice "24 pallets". Además trae coordenadas (-12.0560, -75.2140) | La visión podría marcar una discrepancia. Las coordenadas son dato de ubicación: no construir nada sobre ellas (fuera de alcance) y tratarlas como dato personal |
| 6 | La factura indica "Tipo de operación: 0101 - Venta interna (sujeta a detracción)". SUNAT lista **1004, "Operación sujeta a detracción – Servicio de transporte carga"** ([cpe.sunat.gob.pe/factura-con-detraccion](https://cpe.sunat.gob.pe/factura-con-detraccion), 403 desde aquí, **[2ria]**) | Detalle técnico que un jurado tributarista podría notar |
| 7 | README "hoy sáb 17-oct" | Hoy es dom 18-oct. Recalcular los contadores (ver §4) |
| 8 | La GRE Transportista V001-00000318 se cita en la GRE, la OS y la factura, pero no se incluye | Aceptable (el README lo dice), pero el agente no debe "verificarla" |
| 9 | Nombre del cliente o mentor: "Chofex" (INSTRUCTIVO, ruta de scripts) frente a "Chopex" (gonza.md) | Unificar en el pitch |
| 10 | El análisis previo citaba "8 días hábiles" (Ley 29623 art. 7) como plazo de conformidad | Corregido en §4: para factura electrónica son 8 días calendario |

---

## 2. Zabu y opciones de WhatsApp

### 2.1 Qué es "Zabu": candidatos con evidencia

| Candidato | Qué es | Evidencia | ¿Encaja con "integración con WhatsApp para cualquier tipo de consultas"? |
|---|---|---|---|
| **Zavu (zavu.dev)**, probablemente lo que quiso decir el usuario | "Agentic communication infrastructure": una API para WhatsApp, SMS, voz, email, Telegram, Messenger e Instagram. Fundador y CEO: Victor Villalobos, ex Cornershop/Uber ([zavu.dev](https://www.zavu.dev/en)). Su perfil en X lo ubica en Venezuela y Chile **[2ria]** | Conecta WhatsApp con el "Meta Business Embed signup flow" ([docs](https://docs.zavu.dev/guides/whatsapp/connect-whatsapp.md)). Tiene agentes de IA con "Functions" ("Build a working WhatsApp agent in 10 minutes", [llms.txt](https://docs.zavu.dev/llms.txt)) y webhook `message.inbound` con imágenes y documentos ([events](https://docs.zavu.dev/guides/receiving-messages/events.md)) | **Alto.** Fonética (b = v), producto orientado a agentes y origen latinoamericano |
| Zabu (Lima Innovation Lab, `com.lilab.hound`) | App Android: "actualizar en tiempo real el status de la mercadería que se transporta… registrar evidencia… conformidad del servicio". Versión 1.20 del 28-sep-2023 ([APKPure](https://apkpure.com/zabu/com.lilab.hound)). La ficha de Google Play da 404 ([Play](https://play.google.com/store/apps/details?id=com.lilab.hound)). El desarrollador sería LIMA INNOVATION LAB E.I.R.L., RUC 20604947805 **[2ria]** ([ruc.pe](https://ruc.pe/lima-innovation-lab-eirl/)) | No menciona WhatsApp. Es de *tracking*, fuera de alcance. Parece descontinuada **[no verificado]** | **Bajo**, salvo que el usuario conozca al equipo de LILAB |
| Z-API (z-api.io) | API **no oficial** de origen brasileño, por instancia ("no approval queue"), US$ 19.99 al mes por instancia ([z-api.io](https://z-api.io/en)). Funciona con una sesión de WhatsApp Web vinculada por QR **[2ria]** ([developer.z-api.io](https://developer.z-api.io/)) | — | Bajo por nombre; **descartado** por riesgo |
| Zabu (Linkup Circle LLC, EE. UU.) | App de "AI insight", sin relación con WhatsApp ([App Store](https://apps.apple.com/us/app/zabu/id6756039910)) | — | Nulo |

**Conclusión:** con una confianza de ~70 %, "Zabu" = **Zavu**. **Acción:** confirmar con el usuario antes de crear la cuenta.

### 2.2 Zavu en detalle (candidato principal)

| Aspecto | Hallazgo | Fuente |
|---|---|---|
| ¿Oficial o no oficial? | **Sobre la plataforma oficial**: el número se conecta con el *Embedded Signup* de Meta y se verifica por llamada o SMS. Zavu se presenta como "official BSP". **No se encontró en el directorio de partners de Meta** **[no verificado]** | [connect-whatsapp](https://docs.zavu.dev/guides/whatsapp/connect-whatsapp.md), [blog Zavu](https://www.zavu.dev/en/blog/api-whatsapp-guia-completo) |
| Riesgo de baneo | Bajo en lo técnico (Cloud API). Siguen vigentes las políticas de Meta, incluida la 4.7 sobre AI Providers (ver §2.4) | [Meta Terms](https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform) |
| Precio | WhatsApp "at cost, with no markup" (Meta factura las plantillas). **Planes contradictorios**: la portada dice "Pro US$ 20 al mes con US$ 20 de crédito"; el blog de precios dice "Free 2,000 msgs", "Hobby US$ 25" y "Pro US$ 199" **[no verificado]**. El blog además describe el modelo **por conversación**, que Meta reemplazó por cobro **por mensaje** el 1-jul-2025: señal de contenido desactualizado | [zavu.dev](https://www.zavu.dev/en), [blog pricing](https://www.zavu.dev/en/blog/whatsapp-business-api-pricing), [Meta pricing](https://developers.facebook.com/docs/whatsapp/pricing) |
| Recibir imágenes y PDF | Sí. `message.inbound` "includes text, images, videos, audio, documents…". Llega `content.mediaId` y después un `content.mediaUrl` **permanente** (Zavu descarga y guarda el archivo) | [events](https://docs.zavu.dev/guides/receiving-messages/events.md) |
| Webhooks | Por *sender*. Firma `X-Zavu-Signature` con secreto. Hay que "respond with 2xx status within 30 seconds" según la doc; el blog dice "< 2 s" (inconsistente) | [webhooks](https://docs.zavu.dev/guides/receiving-messages/webhooks.md), [blog](https://www.zavu.dev/en/blog/api-whatsapp-guia-completo) |
| Mensajes iniciados por la empresa | Plantillas "with the 24-hour window handled for you" | [zavu.dev](https://www.zavu.dev/en) |
| Tiempo de alta | Promete unos 5 minutos de OAuth con Meta. La verificación de negocio sigue siendo de Meta: sin ella, un portafolio nuevo tiene un límite de 250 destinatarios únicos en 24 h fuera de la ventana de servicio | [blog](https://www.zavu.dev/en/blog/api-whatsapp-guia-completo), [Meta limits](https://developers.facebook.com/docs/whatsapp/messaging-limits) |
| Perú | No menciona Perú ni números peruanos (el plan Pro incluye un número de EE. UU.). Se puede registrar un número propio, por ejemplo un chip peruano **[no verificado en la práctica]** | [zavu.dev](https://www.zavu.dev/en), [connect-whatsapp](https://docs.zavu.dev/guides/whatsapp/connect-whatsapp.md) |
| Madurez | Startup reciente (© 2026, programas para startups, 500 Global). Sin SLA ni DPA revisados **[no verificado]** | [zavu.dev](https://www.zavu.dev/en) |

### 2.3 Tabla comparativa

| | **Zavu** | **Meta Cloud API directa** | **Twilio** | Z-API (no oficial) |
|---|---|---|---|---|
| Base | Cloud API vía *Embedded Signup* | Oficial (Graph API) | BSP oficial | Sesión de WhatsApp Web **[2ria]** |
| Imagen / PDF entrante | Sí; URL permanente guardada por Zavu | Sí: JPEG/PNG de hasta 5 MB y PDF de hasta 100 MB. La URL de descarga **expira en 5 min**; el *media ID* del webhook dura **7 días** ([media](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media)) | Sí, por webhook "When a Message Comes in" ([sandbox](https://www.twilio.com/docs/whatsapp/sandbox)) | "Files up to 100MB" (sin detalle) |
| Webhooks y fiabilidad | Firma propia; 2xx en 30 s | `X-Hub-Signature-256` (HMAC-SHA256 con el *app secret*). **Reintentos durante hasta 7 días y posibles duplicados**: "Your server should handle deduplication" ([create endpoint](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint.md), [overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview.md)) | Webhook y *status callback* | Webhooks, con alerta si la instancia se cae |
| Plantillas y ventana de 24 h | Gestionadas | Los mensajes que no son plantilla solo van dentro de la ventana y son gratis. Las *utility* dentro de la ventana son gratis; las de *marketing* siempre se cobran ([pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing.md)) | Igual que Meta. En el sandbox solo hay plantillas preaprobadas | Sin plantillas (no aplica) |
| Costo | 0 % de *markup* + Meta; plan con precio confuso | Solo Meta, por mensaje. **Facturación en PEN desde el 1-abr-2026**; Perú tiene tarifa propia (montos en el *rate card*, **[no verificado]**) | **US$ 0.005 por mensaje entrante o saliente** + Meta ([Twilio pricing](https://www.twilio.com/en-us/whatsapp/pricing)) | US$ 19.99 al mes por instancia |
| Alta para demo | Minutos más el *Embedded Signup* | Número de prueba y token temporal desde "API Setup" ([get started](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started.md)). Límite de destinatarios del número de prueba **[no verificado]** | **Sandbox inmediato**: número compartido +14155238886, `join <código>`, la sesión expira a las 72 h y se envía un mensaje cada 3 s ([sandbox](https://www.twilio.com/docs/whatsapp/sandbox)) | Escanear un QR |
| Riesgo | Proveedor joven | El equipo opera tokens, reintentos y descarga de media | *Markup* por mensaje; el sandbox muestra la marca Twilio | **Baneo del número y violación de términos**: inaceptable para un producto que cobra facturas |

### 2.4 Restricción de política que condiciona "cualquier tipo de consultas"

- **Sección 4.7, "AI Providers"** (términos actualizados el 23-sep-2026). Prohíbe a proveedores de LLM y "asistentes de IA de uso general" usar la plataforma cuando esa tecnología es la funcionalidad **principal** "(em vez de incidental ou auxiliar)". También prohíbe usar los datos de la plataforma para "criar, desenvolver, treinar ou melhorar" modelos de IA, salvo el ajuste de un modelo de uso exclusivo ([Meta Terms](https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform)).
- Rige desde el **15-ene-2026**. Solo se permite donde Meta esté legalmente obligada, como el EEE o Brasil **[2ria]** ([Meta, AI Providers](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/ai-providers.md); [TechCrunch](https://techcrunch.com/2025/10/18/whatssapp-changes-its-terms-to-bar-general-purpose-chatbots-from-its-platform/)).
- **Implicación de diseño:** el agente responde *cualquier pregunta sobre el negocio del transportista* y redirige lo demás. Para no permitir que se entrenen modelos con los datos, Gemini debe usarse en *tier* de pago: en el gratuito el contenido "se usa para mejorar los productos" ([Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), citado en el análisis previo).

### 2.5 Recomendación

| Fase | Canal | Por qué |
|---|---|---|
| **Hackathon** | **Zavu**, si el usuario confirma que "Zabu" = Zavu, detrás de un `MessagingPort` con dos adaptadores (`ZavuAdapter` y `MetaCloudAdapter`). **Spike de 2 h hoy:** número conectado → foto entrante → webhook firmado → archivo en Storage → respuesta. Si falla, se pasa a la Cloud API directa. **Siempre**, un simulador de WhatsApp en el panel que llama al mismo *pipeline* | Respeta la preferencia del usuario. La URL permanente de media y los SDK ahorran trabajo. El `MessagingPort` suma puntos de arquitectura (30 %) y quita el riesgo de depender de un solo proveedor |
| **Piloto** (1–3 MYPE) | Cloud API directa (un WABA por transportista con *Embedded Signup* si se actúa como Tech Provider) o Zavu, solo tras confirmar su estatus de partner en Meta, DPA, SLA, residencia de datos y precio por escrito | Verificación de negocio de cada MYPE, plantillas *utility* aprobadas, facturación en PEN y control de los datos |
| **Nunca** | APIs no oficiales (Z-API, Baileys, Evolution) | Baneo y términos de uso |

---

## 3. Diseño del agente conversacional

### 3.1 Actores y permisos

| Actor | Canal | Puede |
|---|---|---|
| Conductor | WhatsApp (número registrado en `drivers`) | Enviar fotos o PDF de evidencia, recibir el checklist y las alertas ("falta sello") y preguntar "¿qué me falta?" |
| Transportista (dueño o aprobador) | WhatsApp y panel | Todo lo anterior, más subir la OS, reenviar observaciones del cliente, **aprobar, editar o descartar borradores**, consultar estado, montos y plazos, y pedir los datos de la factura |
| Cliente | Correo (las observaciones del demo llegan por correo, OS cl. 2.3) | El agente **nunca** le escribe sin aprobación. En el MVP, el transportista reenvía el correo como PDF o captura al WhatsApp del agente |

### 3.2 Ruteo de intenciones (determinista primero, LLM después)

1. **Pre-ruteo determinista:**
   - Si el mensaje es una respuesta de botón interactivo, va a `decision_borrador`.
   - Si trae media y viene de un conductor, va a `subir_evidencia`.
   - Si trae un PDF y viene del dueño, va a `clasificar_documento` (OS u observación).
   - Si es texto, va al paso 2.
2. **Clasificador Gemini** con salida estructurada sobre un `enum` cerrado ([structured output](https://ai.google.dev/gemini-api/docs/structured-output)), filtrado por los permisos del rol:

| Intención | Ejemplo | Herramientas | Salida |
|---|---|---|---|
| `registrar_os` | (PDF de la OS) | `extract_os` → `upsert_contract_clauses` | "OS-1042: S/ 3,800 + IGV, crédito 30 d, 5 requisitos de POD (cl. 3)" |
| `subir_evidencia` | (foto del cargo) | `store_media` → `extract_pod` → `validate_pod` | Checklist a–e con ✅/❌ y la acción concreta para el conductor |
| `registrar_observacion` | (PDF reenviado del correo del cliente) | `extract_observation` → `classify_observation` → `draft_reply` → `request_approval` | Clasificación por ítem con cláusula y cita, más un borrador con botones |
| `decision_borrador` | botón "Aprobar", "Editar" o "Descartar" | `approve_draft` / `send_to_client` | Confirmación y evento en el expediente |
| `consultar_estado` | "¿cuándo me pagan la 1042?" | `get_expediente` → `compute_deadlines` | "Conformidad: vence mié 21-oct (presunta jue 22-oct). Pago: jue 12-nov, neto S/ 4,300" |
| `preparar_factura` | "arma la factura" | `compute_invoice` | Borrador con IGV, SPOT, base mayor, neto y cuota. **No emite** (PSE/OSE en el piloto) |
| `pregunta_dominio` | "¿el cliente puede pedirme su formato amarillo?" | RAG sobre las cláusulas de la OS y notas legales curadas | Respuesta con cita y aviso de "referencial" |
| `fuera_de_dominio` | "escríbeme un poema" | — | Redirección amable (política 4.7) |
| `ayuda` | "menú" | — | Lista interactiva de opciones |

### 3.3 Herramientas: LLM frente a código

| Herramienta | Tipo | Notas |
|---|---|---|
| `extract_pod(media)` | Gemini visión con esquema `PODExtraction {receptor, dni, fecha, hora, os, firma:bool, sello:bool, sello_texto, legible:bool, confianza_por_campo}` | Imagen inline de hasta 20 MB ([image understanding](https://ai.google.dev/gemini-api/docs/image-understanding)). Los PDF admiten hasta 1000 páginas ([document processing](https://ai.google.dev/gemini-api/docs/document-processing)) |
| `validate_pod` | **Determinista** | Cruza `PODExtraction` con `contract_clauses` (a–e). Si la confianza de `sello` es baja, devuelve `pedir_nueva_foto`, nunca "cumple" |
| `classify_observation` | Gemini con esquema `{items:[{pedido, clasificacion: observacion_valida\|requisito_no_pactado\|ambiguo, clausula_id, cita_os, cita_observacion}], adenda_detectada}` | El modelo elige; el código valida las citas (ver §3.4) |
| `draft_reply` | Gemini en modo texto con plantilla de tono "cordial y firme" | Solo usa hechos del expediente |
| `compute_invoice` / `compute_deadlines` | **Deterministas** | IGV 18 %, SPOT 4 % sobre max(importe, VR) y redondeo; relojes del D.U. 013-2020 y la Ley 31362 con tabla de feriados |
| `send_to_client` | Determinista | Solo se ejecuta si existe `approvals(draft_id, draft_hash, approver)` válido |

### 3.4 Guardrails

1. **Aprobación humana obligatoria.** `send_to_client` exige una aprobación con el hash exacto del borrador, emitida por el número del dueño. Si el borrador se edita, se genera uno nuevo y hace falta otra aprobación. El LLM no tiene ninguna herramienta que envíe sin aprobación.
2. **No inventar evidencia.** El agente nunca genera ni edita imágenes, sellos o firmas. Si no está seguro, dice "no legible, reenvía la foto". La línea ética ya está en la propuesta (§3.6) y en el INSTRUCTIVO §7.
3. **Citas verificables.** Cada `clausula_id` debe existir en `contract_clauses`. `cita_os` y `cita_observacion` deben ser *substrings* (con normalización) del texto extraído. Si una cita no aparece, se bloquea el borrador. **Ejemplo real:** "la política es del 01/10" no está en la observación B, así que este validador lo bloquearía (§1.3 #3).
4. **Números y fechas fuera del LLM.** Montos, SPOT y plazos los calcula el código; el LLM solo los redacta.
5. **Inyección de instrucciones.** El texto de correos o PDF del cliente es **dato**, nunca instrucción: va en un bloque delimitado y nunca se ejecuta como orden.
6. **Alcance (política 4.7).** El agente redirige las consultas ajenas al negocio.
7. **Aviso legal.** Toda respuesta con base legal termina con "referencial; validar con asesor".
8. **Datos personales.** DNI, nombres y teléfonos: minimización, RLS por empresa y retención definida. Falta la revisión de la Ley 29733 **[no verificado]**.
9. **Idempotencia de salida.** Cada envío lleva una `dedupe_key`, así que un reintento no duplica el mensaje al cliente.

### 3.5 Estados del expediente (alineados con INSTRUCTIVO §6)

```text
os_registrada
  → evidencia_recibida
      → pod_incompleto ──(nueva foto)──┐
      → pod_completo ◄─────────────────┘
  → pod_presentado                       (borrador aprobado + enviado)
      → observado {valida | no_pactado | ambiguo}
          → corregido (A) | defendido (B)  (borrador → aprobado → enviado)
  → pod_aceptado                         (Ley 31362 art. 2.1: recién aquí se emite)
  → factura_borrador → factura_emitida   (PSE/OSE en piloto; demo: borrador)
  → conformidad_pendiente                (D.U. 013-2020: 8 d calendario)
      → conformidad_expresa | conformidad_presunta | disconformidad(→ NC, nuevo ciclo)
  → pago_pendiente                       (Ley 31362: 30 d calendario desde emisión)
      → pagado | vencido → recordatorio (plantilla utility) + intereses moratorios
```

Recordatorios fuera de la ventana de 24 h (conformidad presunta, pago vencido) requieren **plantillas *utility* aprobadas**: crearlas hoy. La aprobación tardaría de 24 a 48 h según Zavu **[no verificado en Meta]**.

---

## 4. Revalidación legal y de montos

### 4.1 Tabla afirmación → veredicto → fuente

| # | Afirmación del demo | Veredicto | Detalle y fuente |
|---|---|---|---|
| 1 | Ley 31362: pago en un máximo de 30 días calendario a proveedores MYPE | **Correcta** | Art. 3: "plazo máximo de hasta treinta (30) días calendario, contados a partir de la fecha de emisión" ([Ley 31362, El Peruano 28-nov-2021](https://busquedas.elperuano.pe/dispositivo/NL/2016188-1)) |
| 2 | ¿Aplica entre privados? | **Sí** | Art. 1: facturas "girados a empresas privadas y entidades públicas". El régimen transitorio de 60 días para privadas venció a los 180 días ([Ley 31362](https://busquedas.elperuano.pe/dispositivo/NL/2016188-1)) |
| 3 | ¿Desde cuándo se cuenta? | **Desde la emisión del comprobante** | Ley art. 3 y Reglamento art. 3 ([D.S. 120-2022-EF](https://busquedas.elperuano.pe/dispositivo/NL/2076849-4)). La OS cl. 2.1 dice lo mismo |
| 4 | Pago el jue 12-nov-2026 | **Correcto** | 13-oct + 30 días calendario = 12-nov (jueves). Intereses moratorios desde el 13-nov (Ley art. 4); si no hay pacto, a la tasa BCRP para operaciones entre personas ajenas al sistema financiero (Reglamento art. 6) |
| 5 | (No mencionado) Requisitos del proveedor MYPE | **Falta en el demo** | Ventas anuales ≤ 1,700 UIT (Reglamento art. 2). Al emitir, la MYPE entrega la DJ de renta del ejercicio anterior y su cuenta bancaria (art. 4). **Debe ir al checklist de factura del agente** |
| 6 | (No mencionado) Pactar más de 30 días | **Argumento fuerte para el pitch** | Solo excepcionalmente, por escritura pública o con firmas legalizadas notarialmente, con un contenido mínimo y declaración de no abuso (Reglamento art. 5). Contesta directamente los "cobros a 90 días" de gonza |
| 7 | (No mencionado) Conformidad del **servicio** en la Ley 31362 | **Falta en el demo** | Art. 2.1: la factura se emite "en el momento que se apruebe la conformidad". Art. 2.2: 8 días **calendario** desde la recepción del servicio, por escrito. Entrega el sáb 10-oct → el plazo vence el dom 18-oct. La ley no fija una presunción por silencio en este artículo **[no verificado]**. La OS cl. 2.3 es más estricta: 1 día hábil |
| 8 | Conformidad de la factura: "8 días hábiles desde la recepción (Ley 29623)" → vie 23-oct | **Incorrecta para factura electrónica** | El art. 7 actualizado de la Ley 29623 aplica los 8 días **hábiles** a comprobantes "impresos y/o importados" ([texto actualizado](https://www.cavali.com.pe/storage/uploads/shares/marco_legal/normativa/Ley_29623_que_promueve_el_financiamiento_a_trav__s_de_la_factura_comercial.pdf)). Para la factura electrónica a crédito rige el **D.U. 013-2020**: "plazo de ocho días calendario, computado desde la fecha de la puesta a disposición", en la plataforma SUNAT (RS 165-2021/SUNAT, art. 4.1, vigente desde el 17-dic-2021) ([El Peruano](https://busquedas.elperuano.pe/dispositivo/NL/2012062-1); [PDF SUNAT](https://www.sunat.gob.pe/legislacion/superin/2021/165-2021.pdf)) |
| 9 | ¿Cuándo empieza a contar? | **Con la puesta a disposición, no con la "recepción"** | En SEE-SOL, la factura "es puesta a disposición en la fecha de emisión" (art. 3.2). En SEE-Del contribuyente, SFS u OSE, cuando hay CDR aceptada (art. 3.3). SUNAT avisa al buzón electrónico del adquirente (RS 165-2021). La serie E001 sugiere SEE-SOL **[no verificado]** → puesta a disposición el 13-oct |
| 10 | Conformidad presunta | **Correcta como concepto; cambia la fecha** | Se presume "vencido el plazo… sin que el adquirente… manifieste su disconformidad" (RS 165-2021 art. 1.7). Si la disconformidad o la subsanación se registra el último día, el plazo se amplía 2 días calendario (art. 4.1.b). Las causales de disconformidad son plazo de pago, monto neto pendiente o reclamo, y se subsanan con nota de crédito (arts. 4–5) |
| 11 | Nueva fecha de conformidad | **mié 21-oct** (presunta el **jue 22-oct**) | 8 días calendario desde el 13-oct, excluyendo el día inicial: 14 al 21. Si el día de puesta a disposición contara como día 1, vencería el mar 20-oct. El texto dice "computado desde la fecha" y no resuelve el punto: **parametrizarlo y validarlo con un asesor** **[no verificado]**. Feriados irrelevantes (son días calendario) |
| 12 | Feriados oct–nov 2026 | **Sin impacto** | Jue 8-oct (Combate de Angamos) y dom 1-nov (Todos los Santos). El vie 9-oct no se declaró no laborable **[2ria]** ([El Comercio](https://elcomercio.pe/respuestas/por-que/por-que-este-8-de-octubre-del-2026-es-feriado-nacional-para-todos-los-trabajadores-peruanos-tdpe-noticia/), [La República](https://larepublica.pe/sociedad/2026/10/05/cuantos-feriados-quedan-en-2026-lista-oficial-de-descansos-remunerados-en-lo-que-resta-del-ano-203285)). Incluso con la regla de hábiles del README, el rango del 14 al 23 de octubre no tiene feriados: el conteo del README era aritméticamente correcto, pero bajo el régimen equivocado |
| 13 | SPOT código 027, transporte de carga | **Plausible** | El código 027 aparece en catálogos derivados del Excel oficial de SUNAT **[2ria]** ([AnexosIyII xlsx](https://www2.sunat.gob.pe/facturador/AnexosIyII_Formato1.3.4.xlsx), no abierto) |
| 14 | 4 % sobre el mayor entre el importe y el VR; el umbral de S/ 400 aplica | **Correcta** | "cuatro por ciento (4%) sobre el importe de la operación o el valor referencial, el que resulte mayor"; aplica si el monto es "mayor a S/.400.00". **Quien deposita es el usuario (el cliente)**, hasta la fecha de pago o el 5.º día hábil del mes siguiente a la anotación en el Registro de Compras ([SUNAT](https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre)) |
| 15 | Base S/ 4,590 → S/ 183.60 → **S/ 184** | **Correcta** | 4 % × 4,590 = 183.60. El redondeo es facultativo ("se podrá hacer sin incluir decimales"): con decimal ≥ 5 se sube a la unidad superior (RS 178-2005/SUNAT, [FAQ SUNAT](https://orientacion.sunat.gob.pe/preguntas-frecuentes-detracciones)). Sin VR serían 4 % × 4,484 = 179.36 → S/ 179 |
| 16 | Neto S/ 4,300 en 1 cuota | **Correcta** | 4,484 − 184 = 4,300 |
| 17 | VR 18 TM × S/ 255 = S/ 4,590 "ilustrativo" | **Correcto como ilustración** | La tabla oficial viene del D.S. 020-2021-MTC y sus modificatorias; usa TM × tarifa de la ruta con un piso del 70 % de la carga útil nominal ([SUNAT](https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre)). Mantener la etiqueta "ILUSTRATIVO" |
| 18 | Tipo de operación "0101" en una factura con detracción de transporte | **Probablemente incorrecto** | Catálogo 51: **1004**, "Operación sujeta a detracción – Servicio de transporte carga" **[2ria]** ([cpe.sunat.gob.pe](https://cpe.sunat.gob.pe/factura-con-detraccion), 403) |
| 19 | El comprobante debe consignar la leyenda SPOT, el registro MTC, el VR, la configuración vehicular y origen/destino | **La factura cumple** | Requisitos en [SUNAT](https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre). La factura del demo trae todos |
| 20 | Contador "hoy" | **Actualizar** | Hoy, dom 18-oct: quedan **3 días calendario** para la conformidad (19, 20 y 21-oct) y **25 días** para el pago |

### 4.2 Timeline corregido

| Fecha | Hito | Base |
|---|---|---|
| Sáb 10-oct 14:35 | Entrega y firma del cargo | — |
| Mar 13-oct 17:30 | Factura emitida y puesta a disposición (SEE-SOL) | RS 165-2021 art. 3.2 |
| Dom 18-oct | Fin de los 8 días calendario para la conformidad del **servicio** (ya cumplida el 13-oct con la aceptación del POD) | Ley 31362 art. 2.2 |
| **Mié 21-oct** | Fin del plazo de conformidad o disconformidad de la factura (el mar 20-oct si cuenta el día inicial) | D.U. 013-2020 art. 7.1; RS 165-2021 art. 4.1 |
| **Jue 22-oct** | Conformidad presunta si no hubo disconformidad | RS 165-2021 art. 1.7 |
| **Jue 12-nov** | Vencimiento del pago del neto S/ 4,300 | Ley 31362 art. 3; OS cl. 2.1 |
| Vie 13-nov | Empiezan a correr los intereses moratorios | Ley 31362 art. 4; D.S. 120-2022-EF art. 6 |

**Matiz abierto:** la RS 165-2021 define "transacción al crédito" como aquella cuyo plazo de pago "inicia el día calendario siguiente al día en que vence el plazo de ocho días calendario para dar conformidad". La Ley 31362 cuenta los 30 días desde la emisión. Para el demo basta con la fecha de vencimiento consignada en la factura (12-nov), pero conviene que un asesor confirme cómo conviven ambas reglas **[no verificado]**.

---

## 5. Arquitectura actualizada

### 5.1 Diagrama

```text
 Conductor / Dueño (WhatsApp)                      Jurado / Dueño (navegador)
        │                                                   │
        ▼                                                   ▼
 ┌──────────────┐   webhook firmado     ┌────────────────────────────────┐
 │ Zavu         │──────────────────────►│ Supabase Edge Fn  wa-webhook    │
 │ (o Meta      │  X-Zavu-Signature /   │ 1. verifica firma (raw body)    │
 │  Cloud API)  │  X-Hub-Signature-256  │ 2. INSERT inbound_events        │
 └──────▲───────┘                       │    UNIQUE(provider,msg_id)      │
        │ send (solo tras aprobación)   │    → duplicado = 200 y fin      │
        │                               │ 3. pgmq.send('inbound')         │
        │                               │ 4. 200 OK (< 2 s)               │
        │                               │ 5. waitUntil(worker) (rápido)   │
        │                               └──────────────┬─────────────────┘
        │                                              ▼
        │                               ┌────────────────────────────────┐
        │                               │ Edge Fn  agent-worker           │
        │                               │ (pgmq consumer + pg_cron)       │
        │                               │ a. descarga media → Storage     │
        │                               │    (sha256; Meta: URL 5 min)    │
        │                               │ b. router (determinista→Gemini) │
        │                               │ c. tools: extract_pod (visión), │
        │                               │    classify_observation (JSON), │
        │                               │    draft_reply                  │
        │                               │ d. motor de reglas (TS/SQL):    │
        │                               │    validate_pod, compute_invoice│
        │                               │    compute_deadlines            │
        │                               │ e. guardrails (citas, HITL)     │
        └───────────────────────────────┤ f. outbox (dedupe_key)          │
                                        └──────────────┬─────────────────┘
                                                       ▼
                    ┌───────────────────────────────────────────────────────┐
                    │ Postgres (RLS por empresa): companies, drivers,        │
                    │ contracts, contract_clauses, shipments(expediente),    │
                    │ evidence, extractions, observations, drafts, approvals,│
                    │ invoices(borrador), deadlines, events (append-only),   │
                    │ inbound_events, outbox, holidays                       │
                    │ pg_cron: recordatorios (plantillas utility)            │
                    └──────────────┬────────────────────────────────────────┘
                                   │ Realtime
                                   ▼
                    ┌───────────────────────────────────────────────────────┐
                    │ Next.js en Vercel (URL pública)                        │
                    │ • Expediente OS-1042: timeline, checklist a–e,         │
                    │   cláusula citada resaltada, borrador y aprobación,    │
                    │   relojes legales, SPOT/neto                           │
                    │ • Simulador WhatsApp (plan B) → mismo pipeline         │
                    │ • Eval: extracción vs ground_truth.json                │
                    └───────────────────────────────────────────────────────┘
```

### 5.2 Decisiones por capa

| Capa | Elección | Justificación y fuente |
|---|---|---|
| Canal | `MessagingPort` con `ZavuAdapter` y `MetaCloudAdapter` | §2.5 |
| Webhook | **Supabase Edge Function** `wa-webhook`, mínimo: verifica, persiste, encola y responde 200 | Meta reintenta durante hasta 7 días y puede duplicar ([overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview.md)), por eso hay idempotencia con `UNIQUE(provider, message_id)`. Una Edge Function tiene 2 s de CPU sin contar la E/S ([límites](https://supabase.com/docs/guides/functions/limits)), así que el trabajo pesado no va aquí |
| Asincronía | `EdgeRuntime.waitUntil` para latencia baja y **Supabase Queues (pgmq)** como garantía | waitUntil mantiene la instancia hasta que termina la promesa ([background tasks](https://supabase.com/docs/guides/functions/background-tasks)). pgmq da "Guaranteed Message Delivery" ([Queues](https://supabase.com/docs/guides/queues)) |
| Media | Descargar de inmediato a Storage con SHA-256 (cadena de custodia). Con Meta, la URL expira en 5 min y el *media ID* dura 7 días; Zavu da una URL permanente | [Meta media](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media), [Zavu events](https://docs.zavu.dev/guides/receiving-messages/events.md) |
| IA | Gemini en *tier* de pago: visión para el cargo, salida estructurada para la clasificación con cláusula y texto para redactar. *Function calling* para las herramientas | [image understanding](https://ai.google.dev/gemini-api/docs/image-understanding), [structured output](https://ai.google.dev/gemini-api/docs/structured-output), [function calling](https://ai.google.dev/gemini-api/docs/function-calling). El Managed Agent antigravity sigue **fuera** del camino crítico (análisis previo §4.2) |
| Reglas | TypeScript puro, testeable: POD a–e, IGV, SPOT, plazos, feriados | Probado con los casos A y B y con el ground truth |
| Datos | Postgres con RLS y eventos *append-only* | Análisis previo §3 |
| Front | Next.js en Vercel con Supabase Realtime | URL pública (25 %) |
| Emisión | Borrador en el demo; PSE/OSE en el piloto | Análisis previo §3.3 |
| Correo del cliente (piloto) | Ingesta de correo (Gmail API o *inbound email*) para no depender del reenvío manual | **[no verificado]**; fuera del MVP |

### 5.3 ¿Apps Script + Sheets? Sigue descartado, y con más motivos

- Para verificar el webhook hacen falta los **headers** (`X-Hub-Signature-256`). El objeto de evento documentado de un web app de Apps Script (`e.parameter`, `e.postData`, …) **no expone headers** ([Web Apps](https://developers.google.com/apps-script/guides/web)). Sin firma, cualquiera podría inyectar "fotos de POD".
- ContentService responde con una **redirección** a `script.googleusercontent.com` ([Content Service](https://developers.google.com/apps-script/guides/content)). Meta espera un 200 directo, así que habría riesgo de reintentos **[no verificado en la práctica]**.
- Siguen en pie los límites de concurrencia y de triggers del análisis previo. Sheets queda, a lo sumo, como exportación.

---

## 6. Demo y factor wow frente a la rúbrica

### 6.1 Guion (6 min, **empezando por el caso B**, como pide el INSTRUCTIVO §7)

| Min | Pantalla (teléfono espejado + panel en la URL pública) | Wow |
|---|---|---|
| 0:00 | Problema en una frase. Panel: "OS-1042 cargada, 5 requisitos de POD (cl. 3)" | Contexto contractual a la vista |
| 0:40 | **B.1**: el "conductor" envía `cargo_completo.png` y `foto_descarga.png` | En unos 10 s llegan el checklist ✅×5 por WhatsApp y el expediente en vivo en el panel |
| 1:30 | **B.2**: el dueño reenvía `observacion_B_formato_nuevo.pdf` | Clasificación **requisito no pactado**: F-REC-07 y la foto en góndola no están en la cl. 3, la cl. 3 prohíbe exigir adicionales y la cl. 3.1 exige una adenda que no existe. **Las citas aparecen resaltadas** en la OS |
| 2:30 | **B.3**: borrador con botones [Aprobar] [Editar]. El dueño aprueba | El panel muestra "aprobado por J.C. Rojas, hash…, enviado". *Nunca envía sin aprobación* |
| 3:10 | **Cierre**: "arma la factura" | IGV, SPOT 027, base mayor S/ 4,590, **S/ 184**, **neto S/ 4,300**. Relojes: **conformidad 21-oct (D.U. 013-2020)** y **pago 12-nov (Ley 31362)**, más el checklist MYPE (DJ renta y cuenta) |
| 4:00 | **Caso A rápido**: `cargo_sin_sello.png` | Al instante: "Falta el sello del CD Huancayo. Pídeselo a la Sra. Carmen Poma antes de irte". Se corrige en el andén |
| 4:40 | Panel de evaluación: extracción frente a `ground_truth.json` (campos 100 % / sello ✅) | Rigor técnico (requiere regenerar el archivo) |
| 5:10 | QR para que el jurado le escriba al bot: "¿cuándo me pagan la OS-1042?" | Interacción real. Requiere un número de producción (ver §7) |
| 5:40 | Arquitectura y *trade-offs* | Claridad |

**Frase de *cashflow*** (gonza: "el cashflow es el efecto wow"): "S/ 4,300 con fecha cierta el 12-nov. Sin el agente, el caso B se arrastra días de reprocesos; con el agente, el POD se defiende el mismo día."

### 6.2 Cómo ve el jurado WhatsApp y el panel

- **Teléfono del demo espejado** en el proyector (scrcpy o la captura nativa) y, al lado, **el panel en la URL pública**. El panel es la evidencia del 25 %: todo lo que pasa en WhatsApp queda reflejado y auditable allí.
- **Simulador en el panel** (`/demo/chat`): permite subir los mismos archivos al mismo *pipeline*. Así el jurado puede reproducir el flujo completo desde la URL aunque no tenga WhatsApp ni acceso al número.
- **Modo replay** (plan C): si Gemini falla, se usan respuestas cacheadas por hash de archivo, con una etiqueta visible "replay". Es honesto y sirve como prueba.

### 6.3 Rúbrica: qué sube y qué falta

| Criterio (peso) | Qué sube con el giro a WhatsApp | Qué falta |
|---|---|---|
| Complejidad técnica (30 %) | Integración real con WhatsApp (webhook firmado, media, plantillas), visión, salida estructurada con citas verificadas, motor de reglas legal, colas, idempotencia y HITL | Construirlo. Prioridad: webhook → extracción → validación → clasificación → aprobación |
| Funcionamiento (25 %) | El flujo A y B es corto y vistoso | URL pública estable (cuidado con la pausa de Supabase Free tras 7 días de inactividad, [pricing](https://supabase.com/pricing)), simulador y número de WhatsApp operativo |
| Calidad técnica (20 %) | Un dominio acotado y testeable | **Traer** el ground truth, `demo_estado.json`, los `.eml` y los scripts generadores. Tests del motor de reglas (SPOT, plazos), *evals* de extracción, ADRs (canal, D.U. 013-2020 frente a Ley 29623) y migraciones con RLS |
| Problema e impacto (15 %) | El caso B es literalmente el dolor de gonza. La Ley 31362 da una palanca concreta | Un usuario real (Chopex/Chofex) que valide el caso B. Datos MTC del análisis previo §1.3 |
| Claridad (10 %) | Línea ética clara (no fabricar evidencia, HITL) | Tabla de *trade-offs* (Zavu frente a Meta, LLM frente a reglas) y corregir los errores legales antes de que un jurado los señale |

### 6.4 Gonza: qué cubre el nuevo enfoque

| Punto de gonza | Estado |
|---|---|
| "Rechazan documentos por formato (hoja azul vs. verde)" | **Cubierto** por el caso B |
| "POD customizable y agéntico; el agente detecta el formato requerido" | **Parcial.** El agente detecta si el formato está *pactado*. Falta un "perfil de POD por cliente", derivado de la cl. 3 o de la adenda, que genere la carátula o el checklist del formato pactado **sin fabricar sellos** |
| "Cashflow es el wow" | **Parcial.** Hace falta mostrar el neto, la fecha cierta y los días ganados en el panel |
| "Ciclo real de 45–60 días; cobros a 90" | **Argumentable** con la Ley 31362 (30 días; más plazo solo con escritura pública). Las cifras siguen siendo de entrevista **[no verificado]** |
| Trazabilidad GPS + WhatsApp + ERP; Samsara | **Fuera de alcance por decisión del usuario.** WhatsApp se usa para evidencia y conversación, no para ubicación. Decirlo como *trade-off* |
| "Facturas electrónicas no resuelven: piden impresión con sello" | **Cubierto**: el POD es requisito contractual y el agente valida su presencia |

---

## 7. Riesgos, plan B y preguntas abiertas

### 7.1 Riesgos del demo en vivo

| Riesgo | Prob. | Mitigación / plan B |
|---|---|---|
| El alta de WhatsApp se traba (Embedded Signup, verificación del número, restricción de la cuenta Meta) | Media | Spike hoy. Respaldo: Cloud API con número de prueba. Último recurso: sandbox de Twilio (alta inmediata, [sandbox](https://www.twilio.com/docs/whatsapp/sandbox)). Siempre está el simulador |
| El jurado no puede escribir al bot (número de prueba con destinatarios limitados **[no verificado]** o límite de 250 para un portafolio nuevo, [limits](https://developers.facebook.com/docs/whatsapp/messaging-limits)) | Media | Mensajes iniciados por el usuario dentro de la ventana. QR hacia un número real. Si no se puede, el simulador |
| Plantillas sin aprobar para los recordatorios | Media | Crearlas hoy. En el demo, mantener la ventana de 24 h abierta (el teléfono escribe primero) |
| Gemini lee mal el sello ilustrado o tarda | Media | Umbral de confianza → "reenvía la foto". Calentar el modelo antes. Modo replay etiquetado |
| Webhook duplicado → doble respuesta al cliente | Baja | `UNIQUE(message_id)` y `dedupe_key` en el outbox |
| Wi-Fi del recinto | Media | Hotspot propio y video de respaldo de 90 s |
| Zavu: precio confuso, estatus de partner no verificado, proveedor joven | Media | `MessagingPort` y respaldo con Meta directo |
| Política 4.7 de Meta | Baja (si el agente se mantiene en su dominio) | Ruteo `fuera_de_dominio` |
| Error legal en pantalla (8 días hábiles, "política 01/10") | **Alta si no se corrige** | Aplicar §4 y §1.3 #3 |
| Supabase Free pausado | Baja | Actividad diaria o plan Pro |

### 7.2 Preguntas abiertas

1. **¿"Zabu" = Zavu?** Si es otro producto (p. ej., la app de LILAB), ¿cuál es su URL?
2. ¿Quién aprueba los borradores: solo el dueño o también un operador? ¿Desde WhatsApp, el panel o ambos?
3. ¿El agente envía al cliente por correo (requiere integración de correo) o el dueño copia el texto aprobado? Para el MVP se recomienda lo segundo, más el registro del envío.
4. ¿Quién regenera y sube `ground_truth.*`, `demo_estado.json`, los `.eml` y los scripts de `/workspace/chofex/src/`?
5. ¿Se corrige `observacion_B_formato_nuevo.pdf` para incluir la fecha de la política (01/10) o se quita el argumento?
6. Cómputo exacto del plazo del D.U. 013-2020: ¿se incluye o no el día de puesta a disposición? ¿Cómo convive la "transacción al crédito" de la RS 165-2021 con los 30 días de la Ley 31362?
7. Monitoreo de conformidad en el piloto: la plataforma SUNAT tiene un servicio web API REST (RS 165-2021 art. 2). Faltan credenciales y alcance para el emisor **[no verificado]**.
8. Tarifas de Meta para Perú en PEN (*rate card*) **[no verificado]**.
9. Ley 29733 (datos personales: DNI, teléfonos, fotos) **[no verificado]**.
10. Tipo de operación 1004 frente a 0101 en la factura del demo **[2ria]**.

---

## Fuentes

**Normas peruanas (primarias)**
- Ley 31362, Ley de pago de facturas MYPE a treinta días (El Peruano, 28-nov-2021): https://busquedas.elperuano.pe/dispositivo/NL/2016188-1
- D.S. 120-2022-EF, Reglamento de la Ley 31362 (El Peruano, 12-jun-2022): https://busquedas.elperuano.pe/dispositivo/NL/2076849-4
- RS 000165-2021/SUNAT, plataforma de conformidad (D.U. 013-2020): https://busquedas.elperuano.pe/dispositivo/NL/2012062-1 · https://www.sunat.gob.pe/legislacion/superin/2021/165-2021.pdf
- D.U. 013-2020 (El Peruano, 23-ene-2020; el visor PDF no cargó): https://busquedas.elperuano.pe/normaslegales/decreto-de-urgencia-que-promueve-el-financiamiento-de-la-mip-decreto-de-urgencia-n-013-2020-1848441-1/
- Ley 29623, original: https://leyes.congreso.gob.pe/documentos/leyes/29623.pdf · texto actualizado con notas de la Ley 30308 y del D.U. 013-2020 (compilación publicada por CAVALI, ICLV): https://www.cavali.com.pe/storage/uploads/shares/marco_legal/normativa/Ley_29623_que_promueve_el_financiamiento_a_trav__s_de_la_factura_comercial.pdf
- SUNAT, FAQ de factura negociable (antigua, régimen de tercera copia): https://orientacion.sunat.gob.pe/02-preguntas-frecuentes-factura-negociable
- SUNAT, Detracciones en el transporte de bienes por vía terrestre: https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre
- SUNAT, FAQ de detracciones (redondeo, RS 178-2005): https://orientacion.sunat.gob.pe/preguntas-frecuentes-detracciones
- SUNAT CPE, Factura con detracción (403 desde aquí): https://cpe.sunat.gob.pe/factura-con-detraccion · Anexos I y II (xlsx, no abierto): https://www2.sunat.gob.pe/facturador/AnexosIyII_Formato1.3.4.xlsx

**Meta / WhatsApp (primarias)**
- Términos de Meta para WhatsApp Business Platform (sección 4.7): https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform
- Precios: https://developers.facebook.com/docs/whatsapp/pricing · https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing.md
- AI Providers: https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/ai-providers.md
- Media: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media
- Webhooks: https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview.md · https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint.md
- Límites de mensajería: https://developers.facebook.com/docs/whatsapp/messaging-limits
- Primeros pasos: https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started.md

**Proveedores**
- Zavu: https://www.zavu.dev/en · https://docs.zavu.dev/llms.txt · https://docs.zavu.dev/guides/whatsapp/connect-whatsapp.md · https://docs.zavu.dev/guides/receiving-messages/events.md · https://docs.zavu.dev/guides/receiving-messages/webhooks.md · blog (autopromocional): https://www.zavu.dev/en/blog/api-whatsapp-guia-completo · https://www.zavu.dev/en/blog/whatsapp-business-api-pricing
- Twilio: https://www.twilio.com/en-us/whatsapp/pricing · https://www.twilio.com/docs/whatsapp/sandbox
- Z-API: https://z-api.io/en · https://developer.z-api.io/
- App "Zabu" (Lima Innovation Lab): https://apkpure.com/zabu/com.lilab.hound · https://play.google.com/store/apps/details?id=com.lilab.hound (404)
- App "Zabu" (Linkup Circle): https://apps.apple.com/us/app/zabu/id6756039910

**Google / Supabase**
- Gemini: https://ai.google.dev/gemini-api/docs/image-understanding · https://ai.google.dev/gemini-api/docs/document-processing · https://ai.google.dev/gemini-api/docs/structured-output · https://ai.google.dev/gemini-api/docs/function-calling · https://ai.google.dev/gemini-api/docs/pricing
- Apps Script: https://developers.google.com/apps-script/guides/web · https://developers.google.com/apps-script/guides/content
- Supabase: https://supabase.com/docs/guides/functions/limits · https://supabase.com/docs/guides/functions/background-tasks · https://supabase.com/docs/guides/queues · https://supabase.com/pricing

**Secundarias (solo donde la primaria no fue accesible)**
- TechCrunch, prohibición de chatbots generales: https://techcrunch.com/2025/10/18/whatssapp-changes-its-terms-to-bar-general-purpose-chatbots-from-its-platform/
- Feriados 2026: https://elcomercio.pe/respuestas/por-que/por-que-este-8-de-octubre-del-2026-es-feriado-nacional-para-todos-los-trabajadores-peruanos-tdpe-noticia/ · https://larepublica.pe/sociedad/2026/10/05/cuantos-feriados-quedan-en-2026-lista-oficial-de-descansos-remunerados-en-lo-que-resta-del-ano-203285
- RUC de Lima Innovation Lab: https://ruc.pe/lima-innovation-lab-eirl/

**Nota de acceso:** `cpe.sunat.gob.pe` devolvió 403. El PDF del D.U. 013-2020 en El Peruano no cargó, así que su art. 7 se cita a través de la RS 165-2021, que lo desarrolla. Los PDF de SUNAT y CAVALI se leyeron descomprimiendo su texto localmente.
