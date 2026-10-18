# Análisis: facturación agéntica del transporte de carga en Perú

> Fecha: 18 de octubre de 2026 · Tipo: research contra fuentes primarias
> Insumos: `docs/gestion-de-facturacion-de-transporte-peru.md` (la propuesta), `docs/rubrica-evaluacion.md`, `docs/feedback/gonza.md` y el proyecto de referencia `/home/user/Projects/luca` (Apps Script + Sheets).
> Convención: cada afirmación lleva su fuente. **[NV]** marca lo que no se pudo verificar en fuente primaria. **[2ria]** marca lo que solo se confirmó en fuentes secundarias porque la primaria no estaba accesible (ver la nota de acceso al final).

---

## Resumen ejecutivo (veredicto)

- **El marco normativo de la propuesta es correcto y prudente, pero se queda corto donde más pesa en el diseño.** Acierta al separar POD, GRE y factura, y al no inventar tasas. Le faltan tres reglas duras: (1) la factura se envía a SUNAT/OSE como máximo **3 días calendario** después de la fecha de emisión, y si no se envía pierde la calidad de factura ([RS 000003-2023/SUNAT](https://www.sunat.gob.pe/legislacion/superin/2023/000003-2023.pdf)); (2) la detracción del transporte de bienes es del **4 %** sobre el mayor entre el importe y el valor referencial, cuando supera S/ 400 ([SUNAT](https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre)); (3) **una factura emitida no se edita**: se corrige con nota de crédito o débito (catálogos 09 y 10), con comunicación de baja solo si aún no se entregó al cliente y dentro de 7 días desde el CDR, o con una factura nueva si fue rechazada ([SUNAT, Operatividad](https://orientacion.sunat.gob.pe/3529-operatividad)).
- **Hay mercado y es atomizado, con dato oficial.** El MTC registra **140 323 empresas** autorizadas para carga nacional y **373 240 vehículos** en 2025, unos **2,7 vehículos por empresa**. El 28,5 % de la flota supera los 15 años y el 11,6 % los 30 ([MTC, Servicios de carga](https://www.gob.pe/institucion/mtc/informes-publicaciones/344890-estadistica-servicios-de-transporte-terrestre-por-carretera-servicios-de-carga); [MTC, Parque automotor](https://www.gob.pe/institucion/mtc/informes-publicaciones/344892-estadistica-servicios-de-transporte-terrestre-por-carretera-parque-automotor)). Esto respalda el "muchos microtransportistas, camiones viejos" de gonza. Sus porcentajes de equipamiento (50 % / 30 %) y los cobros a 90 días siguen siendo datos de entrevista **[NV]**.
- **El MVP de la propuesta (contrato → POD → preliquidación, sin emitir en SUNAT) es el recorte correcto para la rúbrica.** Calza con "Problema e impacto" (15 %) y "Claridad" (10 %). Pero el 75 % técnico exige un flujo vivo en una URL pública (25 %) y un repositorio de calidad (20 %). La propuesta no define stack, integraciones ni demo desplegable: es el hueco principal.
- **Arquitectura: para este caso, Supabase (Postgres + RLS + Storage + Edge Functions) supera a Apps Script + Sheets.** El modelo de Luca (cada usuario tiene su propia copia de la Sheet) sirve para finanzas personales. Aquí hay varias partes (cliente, operador, transportista, subcontratista) que comparten un expediente con permisos por empresa y auditoría inmutable, y Sheets no ofrece eso. Sheets queda como adaptador de importación/exportación, no como sistema de registro.
- **Firma y envío a SUNAT: delegar en un PSE/OSE por API, no firmar en Apps Script.** Apps Script tiene RSA-SHA256 con clave PEM, pero no canonicalización XML (C14N), ni XMLDSig, ni lectura de PKCS#12 ([Utilities](https://developers.google.com/apps-script/reference/utilities/utilities), [XmlService](https://developers.google.com/apps-script/reference/xml-service/xml-service)). Habría que implementarlo a mano y guardar la clave privada del representante legal en Properties.
- **"Gemini Managed Agents con antigravity-preview" existe y está documentado, pero está en *preview*.** El agente `antigravity-preview-09-2026` se invoca con la Interactions API (que sí es GA). Corre en un sandbox Linux de Google, sobre Gemini 3.8 Flash por defecto ([docs](https://ai.google.dev/gemini-api/docs/antigravity-agent)). **No soporta salidas estructuradas**, sus esquemas pueden cambiar, la red de salida está abierta por defecto y una interacción consume entre 100 mil y 3 millones de tokens ([Agents overview](https://ai.google.dev/gemini-api/docs/agents)).
- **Recomendación para el agente.** No usar un agente autónomo de propósito general para "modificar facturas". Usar Gemini con *function calling* y *structured output* desde una Edge Function, sobre un motor de reglas determinista. El agente **propone** una corrección (NC tipo X, ND tipo Y, baja o reemisión) o un borrador antes de emitir. Un humano aprueba y el PSE/OSE emite. El managed agent queda, a lo sumo, para tareas offline no críticas.

---

## 1. Validación normativa y de valor

### 1.1 Tabla afirmación → veredicto → fuente

| # | Afirmación (propuesta §) | Veredicto | Comentario y fuente |
|---|---|---|---|
| 1 | La GRE sustenta el traslado; no es POD ni factura (§1, §3.4) | **Correcta** | Las GRE remitente, transportista y por evento regulan el traslado de bienes ([RS 000123-2022/SUNAT](https://www.sunat.gob.pe/legislacion/superin/2022/123-2022.pdf)). |
| 2 | La GRE-transportista "puede requerir" GRE-remitente previa, y no se debe exigir siempre ambas (§3.4) | **Correcta** | La GRE-remitente se emite antes de entregar los bienes al transportista (art. 4.2.a). El transportista **no está obligado** a emitir GRE-transportista si el remitente consigna en su GRE el registro MTC, la placa y los conductores (Anexo, num. 12). Una GRE-transportista puede agrupar varias GRE-remitente con el mismo destinatario, punto de partida y punto de llegada (art. 3.3.b) ([RS 000123-2022](https://www.sunat.gob.pe/legislacion/superin/2022/123-2022.pdf)). |
| 3 | Emitir guías "antes del traslado" (§3.4) | **Correcta, con matiz técnico** | Si se emite por SEE-Del contribuyente, "solo se puede sustentar el traslado cuando se cuente con la CDR con estado de aceptada" ([RS 000123-2022](https://www.sunat.gob.pe/legislacion/superin/2022/123-2022.pdf), art. 6). Para el diseño, eso significa una integración en línea antes de que salga el camión. La GRE va por la API REST de SUNAT con OAuth (credenciales API generadas en SOL), no por el canal SOAP de facturas **[2ria]** ([Greenter gre-api](https://github.com/thegreenter/gre-api); el manual oficial está en [cpe.sunat.gob.pe/guias-y-manuales](https://cpe.sunat.gob.pe/guias-y-manuales), que da 403 desde este entorno). |
| 4 | Obligatoriedad de la GRE (implícita) | **Falta en la propuesta** | El designado debe emitir GRE desde 2024 **[2ria]**. SUNAT no sanciona usar guía física cuando correspondía GRE en estas ventanas: remitente, infracciones detectadas del 1 de julio al **31 de agosto de 2026**; transportista, del 1 de julio de 2026 al **28 de febrero de 2027** ([RSNATI 000031-2026](https://www.sunat.gob.pe/legislacion/superAdjunta/rsnati/2026/rsnati-000031-2026.pdf)). Al 18 de octubre de 2026 el remitente ya puede ser sancionado y el transportista aún no. Es un argumento de valor: el transportista tiene meses para digitalizarse. |
| 5 | "PDF aislado ≠ emisión válida"; conservar XML, CDR y estado (§3.9, §5) | **Correcta** | El CDR "Aceptada" da "total validez tributaria". Con CDR "Rechazada" el comprobante "no tiene validez tributaria" y hay que emitir uno nuevo ([SUNAT, Operatividad](https://orientacion.sunat.gob.pe/3529-operatividad)). |
| 6 | Plazo de envío de la factura (no lo menciona) | **Omisión relevante** | La factura y su nota vinculada se envían "en la fecha de emisión... o, incluso, hasta en un plazo máximo de tres días calendario contado desde el día calendario siguiente". "Vencido ese plazo lo no enviado no tendrá la calidad de factura electrónica ni de nota electrónica, aun cuando hubiera sido entregada al adquirente" ([RS 000003-2023/SUNAT](https://www.sunat.gob.pe/legislacion/superin/2023/000003-2023.pdf), art. 12.2 de la RS 097-2012). La página de orientación de SUNAT todavía muestra un texto antiguo de "7 días" ([Operatividad](https://orientacion.sunat.gob.pe/3529-operatividad)), así que prevalece la resolución. **Implicación:** un borrador puede esperar indefinidamente; una factura emitida tiene un reloj de 3 días. |
| 7 | Detracción: umbral S/ 400; "el porcentaje… debe determinarse por operación" (§3.9) | **Correcta pero incompleta** | La tasa es **4 %** sobre el mayor entre el importe de la operación y el valor referencial. Si no hay valor referencial, o el vehículo lleva bienes de dos o más usuarios, se aplica sobre el importe. Aplica si el monto supera S/ 400. Las subcontrataciones también entran. El usuario deposita hasta la fecha de pago, o hasta el 5.º día hábil del mes siguiente a la anotación en el Registro de Compras. **El comprobante no puede incluir operaciones distintas al transporte** y debe consignar la leyenda SPOT, el registro MTC y el valor referencial ([SUNAT, Detracciones en transporte](https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre); base: RS 073-2006/SUNAT). La propuesta debería fijar el 4 % como parámetro versionado, no como "a determinar". |
| 8 | Valores referenciales MTC (§5) | **Correcta como precaución** | La tabla viene del D.S. 020-2021-MTC y sus modificatorias ([SUNAT](https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre)). Una de ellas es el D.S. 026-2024-MTC ([El Peruano](https://busquedas.elperuano.pe/dispositivo/NL/2357884-2)). Habría una actualización para 2026, el D.S. 022-2025-MTC **[2ria, NV en El Peruano]**. El cálculo es TM por tarifa de la ruta, con un piso del 70 % de la carga útil nominal y un factor de 1,4 en ciertos retornos en vacío de más de 200 km virtuales ([SUNAT](https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre)). Es una regla determinista ideal para el motor, no para el LLM. |
| 9 | Venta al crédito: monto neto pendiente, vencimientos y cuotas (§3.9) | **Correcta** | Si cambian el monto neto pendiente o las fechas, se corrige con la **NC tipo 13** ("Corrección del monto neto pendiente de pago y/o la(s) fecha(s) de vencimiento…") ([Anexo 3, RS 193-2020](https://www.sunat.gob.pe/legislacion/superin/2020/anexo3-193-2020.pdf); [Informe SUNAT 000057-2025](https://www.sunat.gob.pe/legislacion/oficios/2025/informe-oficios/i000057-2025-7T0000.pdf)). |
| 10 | Factura negociable: conformidad distinta de aceptación del POD (§3.7, §3.10) | **Correcta** | El adquirente tiene 8 días hábiles para manifestar disconformidad; si no lo hace, se presume la conformidad ([Ley 29623](https://leyes.congreso.gob.pe/documentos/leyes/29623.pdf), art. 7; [SUNAT FAQ](https://orientacion.sunat.gob.pe/02-preguntas-frecuentes-factura-negociable)). La factura electrónica se vuelve título valor con la anotación en cuenta en una ICLV (CAVALI). **Las NC y ND "solo generan efectos contables y tributarios… no sobre el título valor"** ([SUNAT FAQ 26](https://orientacion.sunat.gob.pe/02-preguntas-frecuentes-factura-negociable)). Esto es crítico para el agente: una NC posterior a la cesión no reduce lo que el factor puede cobrar. La plataforma SUNAT de conformidad citada como [S6] no se pudo abrir (403) **[NV]**. |
| 11 | Corrección o "modificación" de facturas (§3.9 menciona NC/ND solo de pasada) | **Omisión de diseño** | Ver §1.2. |
| 12 | Autorización MTC de transportistas (§3.4, §5) | **Correcta** | El registro MTC es obligatorio en la GRE si algún vehículo supera 2 TM de carga útil ([RS 000123-2022](https://www.sunat.gob.pe/legislacion/superin/2022/123-2022.pdf), Anexo num. 12.i). La página MTC citada como [S7] no se revisó en detalle. |
| 13 | Ransa, Dinet y Scharff como "referencias de segmento", no verificadas (§2) | **Correcta y honesta** | Ransa Comercial figura con 518 vehículos en el ranking MTC 2025 ([MTC](https://www.gob.pe/institucion/mtc/informes-publicaciones/344890-estadistica-servicios-de-transporte-terrestre-por-carretera-servicios-de-carga)). |
| 14 | Fuentes [S1]–[S8] de la propuesta | **Parcialmente verificables** | Las de `orientacion.sunat.gob.pe` abren. Las de `cpe.sunat.gob.pe` devuelven 403 desde este entorno y no se pudo comprobar su contenido **[NV]**. |
| 15 | Facturación electrónica con UBL 2.1, firma digital, OSE/PSE (implícito) | **Correcta en general** | La firma digital debe ser válida y vigente, con un certificado que identifique al titular con nombre o razón social y RUC ([RS 117-2017/SUNAT](https://www.sunat.gob.pe/legislacion/superin/2017/117-2017.pdf), def. 1.17). El OSE comprueba el comprobante y entrega el CDR ([RS 117-2017](https://www.sunat.gob.pe/legislacion/superin/2017/117-2017.pdf)). Los requisitos técnicos (X.509 v3, RSA ≥ 2048, SHA-256) y el formato UBL 2.1 están en las guías XML de SUNAT, que no se pudieron abrir (403) **[2ria]**. |

### 1.2 "Modificar" una factura en Perú: implicaciones para el diseño

Una factura emitida y aceptada **no se edita**. El sistema solo tiene estos caminos:

| Situación | Instrumento | Condición y plazo | Fuente |
|---|---|---|---|
| Borrador aún no emitido | Editar libremente | Sin restricción tributaria | Estado interno del producto |
| Emitida pero rechazada (CDR rechazo) | **Emitir una factura nueva** con otra numeración | La rechazada no tiene validez | [SUNAT, Operatividad](https://orientacion.sunat.gob.pe/3529-operatividad) |
| Aceptada y **no entregada** al cliente | **Comunicación de baja** | Hasta 7 días calendario desde el día siguiente al CDR aceptado; agrupa comprobantes de un mismo día | [SUNAT, Operatividad](https://orientacion.sunat.gob.pe/3529-operatividad) |
| Aceptada y entregada: error de RUC o cliente | **NC tipo 02** (anulación por error en el RUC) o **01** (anulación de la operación) y factura nueva | Plazo especial para error de adquirente o descripción: hay dos versiones, "15.º día hábil del mes siguiente" (orientación) y "10 días hábiles" (gob.pe) **[2ria]**; confirmar cuál está vigente | [Catálogo 09](https://www.sunat.gob.pe/legislacion/superin/2020/anexo3-193-2020.pdf) |
| Penalidad, descuento o menor tonelaje | **NC 04/05** (descuento) o **NC 09** (disminución en el valor) | Referencia a la factura | [Catálogo 09](https://www.sunat.gob.pe/legislacion/superin/2020/anexo3-193-2020.pdf) |
| Faltó cobrar espera, estiba o extra | **ND** (aumento en el valor o penalidades/otros) o factura nueva por el extra | Referencia a la factura **[2ria para el catálogo 10]** | Anexo 8, RS 097-2012 |
| Cambio de cuotas o vencimiento al crédito | **NC tipo 13** | — | [Anexo 3, RS 193-2020](https://www.sunat.gob.pe/legislacion/superin/2020/anexo3-193-2020.pdf) |

Las notas vinculadas también deben enviarse en 3 días ([RS 000003-2023](https://www.sunat.gob.pe/legislacion/superin/2023/000003-2023.pdf)).

**Reglas de diseño que se derivan de la tabla:**

1. La entidad `Invoice` es **inmutable** una vez tiene `cdr_status`. Las correcciones son entidades nuevas (`CreditNote`, `DebitNote`, `VoidCommunication`) que referencian la original. Esto calza con la regla de "inmutabilidad del original" de la propuesta (§4).
2. La máquina de estados de una corrección tiene **relojes legales**: 3 días para enviar la nota y 7 días para la baja. El motor de reglas los calcula; el LLM no.
3. Una NC referencia **un solo** comprobante. Validaciones de SUNAT rechazarían una NC que referencie más de uno **[2ria]**. Una liquidación quincenal con un error en varias facturas genera varias NC.
4. Si la factura fue **anotada en CAVALI** (factoring), una NC no reduce el título valor. El sistema debe bloquear o advertir antes de proponer una NC sobre una factura cedida.
5. Un servicio con detracción **no se mezcla** con otros servicios en el mismo comprobante. El "armado de factura" debe partir las líneas.

### 1.3 Tamaño del mercado (datos oficiales MTC)

| Indicador (ámbito nacional, 2025) | Valor | Fuente |
|---|---|---|
| Empresas autorizadas para transporte de carga por carretera | **140 323** (106 077 en 2016) | [MTC, xlsx "empresas autorizadas… 2016-2025"](https://www.gob.pe/institucion/mtc/informes-publicaciones/344890-estadistica-servicios-de-transporte-terrestre-por-carretera-servicios-de-carga) |
| Concentración en Lima y Callao | 111 031 empresas (79 %) | ídem |
| Flota vehicular autorizada | **373 240** unidades | [MTC, xlsx "ranking según flota operativa 2025"](https://www.gob.pe/institucion/mtc/informes-publicaciones/344890-estadistica-servicios-de-transporte-terrestre-por-carretera-servicios-de-carga) y [MTC, xlsx "según antigüedad"](https://www.gob.pe/institucion/mtc/informes-publicaciones/344892-estadistica-servicios-de-transporte-terrestre-por-carretera-parque-automotor) |
| Vehículos por empresa (promedio) | ≈ 2,7 | cálculo propio con los datos anteriores |
| Flota de las 32 empresas más grandes | 18 037 (4,8 % del total) | ídem ranking |
| Flota con más de 15 años | 28,5 % | cálculo propio, xlsx de antigüedad |
| Flota con más de 30 años | 11,6 % (43 157 unidades) | ídem |

Incluye personas naturales y jurídicas del Padrón de Transportistas de Carga Nacional. No hay dato oficial de facturación del segmento, de días de cobro ni de adopción tecnológica **[NV]**.

---

## 2. Alineación con la rúbrica y con el feedback de gonza

### 2.1 Rúbrica

| Criterio (peso) | Cómo la cubre la propuesta | Brecha y acción |
|---|---|---|
| Complejidad técnica (30 %) | Modelo de datos rico, agentes por rol, motor de reglas | **No hay arquitectura concreta.** Definir el stack y al menos dos integraciones reales: LLM multimodal para leer POD, y GRE/factura en sandbox de un PSE o en el entorno beta de SUNAT. El valor referencial y la detracción como motor determinista lucen bien ante un jurado. |
| Funcionamiento (25 %) | Happy path de 9 pasos (§8) | Hace falta una **URL pública** estable. Evitar dependencias en *preview* o que tarden minutos en el paso crítico del demo. Con Supabase Free, el proyecto se pausa tras 1 semana de inactividad ([pricing](https://supabase.com/pricing)), así que hay que mantenerlo activo o usar Pro. |
| Calidad técnica (20 %) | — | Repo con migraciones SQL, políticas RLS con tests pgTAP ([Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)), tests del motor de reglas y ADRs. Luca es un buen modelo de repo: ADRs, CONTEXT.md y 238 tests con un harness de mocks de Apps Script (`/home/user/Projects/luca/CLAUDE.md`). |
| Problema e impacto (15 %) | Fuerte: discovery honesto y KPIs medibles | Añadir los datos MTC de §1.3 y el reloj regulatorio de la GRE (§1.1 #4). Conseguir al menos un usuario real (gonza / Chopex). |
| Claridad (10 %) | Muy buena en límites ("no fabricar evidencia") | Añadir una tabla de trade-offs de arquitectura y del agente (este documento §3 y §4). |

### 2.2 Puntos de gonza frente a la propuesta y la normativa

| Punto de gonza | Estado | Observación |
|---|---|---|
| "Transporte es un negocio de finanzas; cobros a 90 días" | **[NV]** dato de entrevista | La propuesta lo trata bien como hipótesis (§9). El plazo de pago lo fija el contrato. Si no consta vencimiento en la factura negociable, vence a los 30 días ([Ley 29623](https://leyes.congreso.gob.pe/documentos/leyes/29623.pdf)). No se verificó si existe hoy una ley de plazo máximo de pago a MYPE **[NV]**. |
| "Camión cuesta ~$2,000" | **Inverosímil tal como está escrito** | Probablemente es un error de transcripción: costo mensual, por viaje o cuota. Confirmar con gonza antes de usarlo en el pitch **[NV]**. |
| "~50 % sin tecnología, ~30 % bien equipados" | **[NV]**, con un proxy oficial | No hay estadística oficial de telemática. El MTC muestra una flota envejecida (28,5 % con más de 15 años) y atomizada (2,7 vehículos por empresa) (§1.3), lo que es coherente con el diagnóstico. |
| Trazabilidad GPS + WhatsApp + ERP (Chopex); Samsara "$200M/año" | Fuera del foco del MVP | La propuesta lo trata correctamente como corroboración, no como conformidad (§3.5). La cifra de Samsara **no se verificó** y parece desactualizada **[NV]**. "Mofi, Geotap" probablemente se refiere a Geotab. |
| Rechazos por formato (hoja azul vs. verde), horarios, revisión lenta | **Coherente con la norma** | Son condiciones privadas, no de SUNAT. La propuesta lo dice bien (§1, §5). |
| "Facturas electrónicas no resuelven: el cliente exige impresión con sello" | **Coherente** | La validez tributaria la da el CDR. El papel sellado es un requisito contractual del cliente. |
| "El agente genera la evidencia según el formato del cliente, sin intervención manual" | **Hay que reconciliar** | La propuesta prohíbe fabricar sellos, firmas o conformidades (§3.6). La síntesis viable: el agente **arma la carátula, el índice y el formato** exigido por cada cliente y detecta faltantes, pero no crea evidencia. Si el cliente pide original sellado, lo coordina. Esta es la línea ética y legal; conviene decirla explícitamente en el pitch. |
| "Si el POD se acepta al 90 %, se libera liquidez inmediata" | **Exagerado** | La propuesta lo matiza bien (§3.10): acelera la facturación, no el plazo de crédito. Además, la conformidad de la factura negociable (8 días hábiles) es otro hito (§1.1 #10). |
| Foco: facturación y POD, no cashflow | **Alineado** con el MVP §8 | — |

---

## 3. Arquitectura: Apps Script + Sheets (tipo Luca) vs. Supabase + backend

### 3.1 Lo que enseña Luca

Luca funciona porque su dominio es **un usuario, sus propios datos**:

- Cada usuario copia una Sheet plantilla con un *stub* que delega en una librería versionada (LucaLib).
- Los secretos van en `UserProperties`.
- Un trigger cada 15 minutos procesa lotes de unos 200 segundos "para no chocar con los 6 min".
- `LockService.getUserLock()` serializa las escrituras.
- El LLM solo recibe `comercio + monto` (`/home/user/Projects/luca/README.md`, `CLAUDE.md`, `gas/shared/gmail-scan-runtime.js`, `gas/shared/webapp-runtime.js`).

Esos patrones son reutilizables: determinista primero, LLM al final, presupuesto por pasada, lote reanudable y relevo sin estado. La topología, en cambio, no lo es. El caso de transporte es **multi-parte**: cliente, operador, transportista y subcontratista ven partes distintas del mismo expediente, y no se puede compartir el precio del operador con el subcontratista (propuesta §6, caso B).

### 3.2 Límites oficiales relevantes

| Límite | Apps Script / Sheets | Supabase |
|---|---|---|
| Tiempo por ejecución | 6 min ([cuotas](https://developers.google.com/apps-script/guides/services/quotas)) | Edge Function: 150 s de reloj (Free) o 400 s (pago); **2 s de CPU** sin contar I/O asíncrona; 256 MB ([límites](https://supabase.com/docs/guides/functions/limits)) |
| Triggers | 90 min/día (consumer) o 6 h/día (Workspace); 20 triggers por usuario y script ([cuotas](https://developers.google.com/apps-script/guides/services/quotas)) | pg_cron, webhooks y colas en Postgres; sin cuota diaria equivalente documentada en las páginas revisadas |
| Llamadas HTTP salientes | UrlFetch: 20 000/día (consumer) o 100 000/día (Workspace); 50 MB por respuesta ([cuotas](https://developers.google.com/apps-script/guides/services/quotas)) | Invocaciones de Edge Functions: 500 mil (Free) o 2 millones (Pro) incluidas ([pricing](https://supabase.com/pricing)) |
| Concurrencia | 30 ejecuciones simultáneas por usuario; 1 000 por script ([cuotas](https://developers.google.com/apps-script/guides/services/quotas)); bloqueos por documento, script o usuario ([LockService](https://developers.google.com/apps-script/reference/lock/lock-service)) | Transacciones Postgres, restricciones e índices únicos |
| Tamaño | Sheets: **20 millones de celdas o 100 MB** por hoja ([Google](https://support.google.com/drive/answer/37603)). El "10M" del enunciado está desactualizado. Properties: 500 KB por almacén y 9 KB por valor | DB de 500 MB (Free) u 8 GB (Pro); Storage de 1 GB o 100 GB ([pricing](https://supabase.com/pricing)) |
| Permisos multi-tenant | Por archivo (compartir la Sheet); no hay permisos por fila | **RLS** por fila con `auth.uid()` y claims en `app_metadata` ([RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)) |
| Auditoría | Historial de versiones de la Sheet, editable por quien tenga acceso | `pgaudit` ([docs](https://supabase.com/docs/guides/database/extensions/pgaudit)), tablas *append-only* de eventos y triggers |
| Secretos | Properties (texto plano para quien edita el script) | Vault con cifrado AEAD ([docs](https://supabase.com/docs/guides/database/vault)) |
| Disponibilidad y costo | Gratis; sin pausa | Free se pausa tras 1 semana de inactividad; Pro desde US$ 25/mes; backups diarios solo en Pro ([pricing](https://supabase.com/pricing)) |

### 3.3 Firma XML y envío a SUNAT: ¿Apps Script o PSE/OSE?

**Qué exige la firma.** La firma digital debe hacerse con un certificado vigente que identifique al titular, con nombre o razón social y RUC ([RS 117-2017](https://www.sunat.gob.pe/legislacion/superin/2017/117-2017.pdf)). En la práctica es XMLDSig embebido en el UBL. La sintaxis exacta está en las guías XML de SUNAT **[2ria]**.

**Qué ofrece Apps Script:**
- `Utilities.computeRsaSha256Signature(value, key)` con clave "PEM formatted", y `computeDigest` ([Utilities](https://developers.google.com/apps-script/reference/utilities/utilities)).
- `XmlService` solo parsea, construye y serializa. **No hay C14N ni XMLDSig** ([XmlService](https://developers.google.com/apps-script/reference/xml-service/xml-service)).
- No hay API para PKCS#12 (.pfx). Habría que extraer la clave a PEM fuera de Apps Script y guardarla en Properties.

**Conclusión.** Firmar en Apps Script es *técnicamente posible* implementando a mano la canonicalización exclusiva y el ensamblado XMLDSig, pero es frágil y riesgoso: la clave privada del representante legal queda en texto plano para cualquier editor del script. Además, el emisor tendría que manejar el SOAP de facturas, la API REST de la GRE con OAuth, los reintentos, el CDR y las bajas. Un OSE, por norma, debe tener 99,96 % de disponibilidad e ISO 27001 ([RS 117-2017](https://www.sunat.gob.pe/legislacion/superin/2017/117-2017.pdf); [SUNAT OSE](https://cpe.sunat.gob.pe/aliados/ose)). Eso da una idea de la vara.

**Recomendación: delegar en un PSE/OSE con API JSON.** El producto envía datos estructurados y recibe XML, CDR y PDF. El padrón oficial de OSE está en [cpe.sunat.gob.pe/padron-ose](https://cpe.sunat.gob.pe/padron-ose) (no se pudo abrir desde aquí). Qué PSE concreto elegir y cómo es su API quedan **[NV]**: evaluarlo por sandbox, soporte de GRE, NC/ND, detracción y webhooks de CDR.

### 3.4 Recomendación por fase

| Fase | Stack recomendado | Por qué |
|---|---|---|
| **Hackathon / MVP** | **Supabase** (Postgres + RLS + Storage para originales con SHA-256 + Auth) con **Edge Functions** que llaman a Gemini. Frontend Next.js en Vercel o Cloudflare. **Adaptador Google Sheets/Excel** opcional, al estilo Luca, para importar tarifarios u OS y exportar la preliquidación. **Sin emisión real**: estado `listo_para_facturar` y borrador de factura, NC o ND en JSON/UBL de muestra, como ya plantea la propuesta (§8). | Encaja con el modelo relacional de §4 de la propuesta, demuestra multi-tenant con RLS (complejidad y calidad) y da una URL pública estable (funcionamiento). Las llamadas LLM son I/O-bound y caben en los 150 s y 2 s de CPU. Si alguna pasa de 150 s, se hace asíncrona con cola y *polling*. |
| **Piloto** (1–3 transportistas reales) | El MVP más Supabase Pro (backups, sin pausa), `pgaudit`, Vault para las API keys del PSE, y un PSE/OSE en sandbox y luego en producción para GRE y factura | Cumplir el reloj de 3 días y el CDR antes del traslado exige integración confiable y reintentos idempotentes. |
| **Producción** | Postgres gestionado (Supabase Team/Enterprise si se requiere SOC2 ([pricing](https://supabase.com/pricing))) o Cloud SQL. Workers de larga duración (Cloud Run) para OCR y agentes. Emisión 100 % vía PSE/OSE | Retención documental, segregación por empresa y observabilidad. |

**Si el equipo prefiere arrancar en Apps Script + Sheets (más rápido para quien viene de Luca), migrar a Postgres en cuanto ocurra cualquiera de estos casos:**
- dos o más empresas deben ver el mismo expediente con permisos distintos;
- se necesita auditoría que el usuario no pueda alterar;
- hay escrituras concurrentes desde el móvil de conductores;
- algún proceso pasa de 6 minutos o del presupuesto de 90 min/día de triggers;
- las hojas se acercan a millones de celdas;
- se custodian credenciales SOL o del PSE.

En la práctica, el caso B de la propuesta (operador → subcontratista) ya cumple el primer criterio.

---

## 4. Agente IA que "modifica" la factura

### 4.1 Qué existe realmente (octubre de 2026)

| Producto | Estado | Datos clave | Fuente |
|---|---|---|---|
| **Managed Agents en la Gemini API** | **Preview** (lanzado el 19 de mayo de 2026, Google I/O) | Una llamada crea un agente que razona, ejecuta código y maneja archivos en un sandbox Linux efímero | [Blog Google](https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/), [Agents overview](https://ai.google.dev/gemini-api/docs/agents) |
| **`antigravity-preview-09-2026`** | Preview; reemplaza a `-05-2026` | ID de **agente**, no de modelo: se pasa como `agent=` en `interactions.create(..., environment="remote")`. Usa "el mismo harness que el Antigravity IDE". Modelo por defecto `gemini-3.8-flash`; también 4 Argon, 3.6 Flash y 3.5 Flash-Lite. Contexto de 1 048 576 tokens (compactado a unos 135 mil); salida de 65 536 | [Antigravity agent](https://ai.google.dev/gemini-api/docs/antigravity-agent), [ficha](https://ai.google.dev/gemini-api/docs/models/antigravity-preview-09-2026), [custom agents](https://ai.google.dev/gemini-api/docs/custom-agents) |
| **Interactions API** | **GA** desde junio de 2026 | Guarda las interacciones por defecto: 55 días en pago, 1 día en Free. `store=false` impide el modo background y el multi-turno | [Interactions](https://ai.google.dev/gemini-api/docs/interactions) |
| Managed agents en **Gemini Enterprise Agent Platform** (antes Vertex AI) | Preview | Para empresas | [Blog Google](https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/) |
| **ADK** + Cloud Run o Agent Runtime (antes Agent Engine) | Framework open source; despliegue gestionado | Sin sesiones gestionadas, el estado se pierde cuando Cloud Run recicla la instancia | [ADK Cloud Run](https://google.github.io/adk-docs/deploy/cloud-run/), [Agent Platform deploy](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy) |
| Gemini API "clásica" con function calling y structured output | GA | Structured output con JSON Schema (subconjunto); combinable con herramientas, incluido function calling, en Gemini 3 (esto último en preview) | [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) |

**Veredicto:** "Gemini Managed Agents con antigravity-preview" **es real y está documentado**, pero es **preview**: "Features and schemas may change", sin versionado ni rollback de agentes ([custom agents](https://ai.google.dev/gemini-api/docs/custom-agents)).

**Precio:** pago por tokens a tarifa estándar; el cómputo del entorno no se cobra durante la preview ([pricing](https://ai.google.dev/gemini-api/docs/pricing)).
- Gemini 3.8 Flash cuesta US$ 0,75 de entrada y US$ 3,75 de salida por millón de tokens hasta el 31 de diciembre de 2026, y el doble desde el 1 de enero de 2027. Tiene tier gratuito.
- Google estima entre US$ 0,30 y US$ 1,30 por interacción típica, y hasta unos US$ 5 en flujos complejos de 3 a 5 millones de tokens ([Antigravity agent](https://ai.google.dev/gemini-api/docs/antigravity-agent)).
- No se encontraron números concretos de rate limit para el agente **[NV]**.

### 4.2 Por qué no es adecuado para "modificar facturas"

1. **No soporta salidas estructuradas** ("The Antigravity agent does not support structured outputs"). Tampoco acepta `temperature` ni `max_output_tokens` ([Antigravity agent](https://ai.google.dev/gemini-api/docs/antigravity-agent)). Un borrador de NC o ND necesita JSON validado contra esquema.
2. **Autonomía y superficie de riesgo.** La red de salida está abierta por defecto y "The agent may use any credential it has access to" ([Agents overview](https://ai.google.dev/gemini-api/docs/agents)). No hay un mecanismo nativo de aprobación humana. Lo más cercano es la pausa `requires_action` de las funciones personalizadas, que solo funciona en modo stateful, más *hooks* sobre código y filesystem ([Antigravity agent](https://ai.google.dev/gemini-api/docs/antigravity-agent)).
3. **Datos.** En el tier gratuito, el contenido "se usa para mejorar los productos" ([pricing](https://ai.google.dev/gemini-api/docs/pricing)). Las interacciones se guardan por defecto ([Interactions](https://ai.google.dev/gemini-api/docs/interactions)). Facturas, RUC y datos de conductores requieren tier de pago y una política de retención propia. Falta además la revisión de la Ley 29733 de datos personales **[NV]**.
4. **Costo y latencia** de 100 mil a 3 millones de tokens por interacción, frente a una tarea que es en esencia determinista: elegir el tipo de nota, calcular importes y aplicar plazos.
5. **Encaje normativo.** Por §1.2, el "cambio" correcto casi nunca es una edición. Es una decisión acotada entre unas pocas opciones legales (baja, NC con un código del catálogo, ND, factura nueva) con relojes. Eso es un árbol de reglas más una explicación, no un agente de código.

### 4.3 Diseño recomendado: "Correction Proposer" con humano en el loop

```text
Evento (rechazo POD, disputa de tarifa, penalidad, error de RUC, cambio de cuotas)
  → Motor de reglas (Postgres/TS, determinista):
      estado de la factura (borrador | emitida-rechazada | aceptada-no-entregada | aceptada-entregada | cedida en CAVALI)
      relojes: 3 días de envío de nota, 7 días de baja desde el CDR, plazo especial por error de adquirente
      importes: tarifa versionada, detracción 4 % sobre max(importe, VR), IGV
      → acciones legalmente posibles (lista cerrada)
  → Gemini (gemini-3.8-flash o 3.5-flash-lite) vía Interactions o generateContent desde una Edge Function:
      function calling: get_invoice, get_contract_clause, get_pod_case, list_allowed_actions
      structured output: CorrectionProposal {action, catalog_code, lines, amounts, rationale, cited_evidence[], confidence}
      el LLM elige y explica dentro de la lista cerrada; no calcula montos finales
  → Validación por esquema y por reglas (rechaza cualquier acción fuera de la lista o con importes que no cuadren)
  → Aprobación humana (rol facturación) con diff "factura original vs. efecto de la nota"
  → PSE/OSE API: emite la NC, ND o baja y recibe el CDR → evento inmutable en el expediente
```

- **Antes de emitir**, el agente sí puede "modificar": edita el **borrador** (líneas, OC/OS, glosas, partición por detracción) con trazabilidad.
- **Después de emitir**, solo **propone** documentos nuevos.
- Antes de ejecutar cualquier herramienta, el sistema aplica las reglas de la propuesta: "no emitir unilateralmente" y "no elegir tratamientos tributarios inciertos" (§3.9, §7).

**Alternativas según la etapa:**
- **MVP / hackathon:** Gemini con function calling y structured output desde una Supabase Edge Function. Alternativa estilo Luca: `UrlFetchApp` a la Gemini API desde Apps Script, con un adaptador único y presupuesto por pasada (`gas/shared/llm-runtime.js`).
- **Producción con orquestación multi-agente:** ADK en Cloud Run o Agent Runtime con sesiones gestionadas ([ADK](https://google.github.io/adk-docs/deploy/cloud-run/)).
- **Uso acotado del managed agent:** solo tareas *offline* sin emisión ni credenciales. Ejemplos: un informe de auditoría de un lote de expedientes, o el análisis exploratorio de un contrato largo con salida en texto que un humano revisa. Siempre con `tools` restringido, red en *allowlist* y `max_total_tokens`. Si se muestra en el demo, que no esté en el camino crítico del flujo en vivo.

---

## 5. Riesgos y preguntas abiertas

1. **Plazo de NC por error de adquirente o descripción.** Hay dos versiones: "15.º día hábil del mes siguiente" (orientación SUNAT) y "10 días hábiles" (gob.pe/cpe). Hay que confirmar la vigente en la RS 097-2012 consolidada **[2ria]**.
2. **Catálogo 10 (tipos de ND)** y sintaxis XMLDSig/UBL 2.1. Están en las guías de cpe.sunat.gob.pe, inaccesibles desde aquí **[2ria]**.
3. **D.S. 022-2025-MTC** (valores referenciales 2026). Solo se confirmó en fuentes secundarias; hay que conseguir el texto en El Peruano antes de cargar la tabla **[NV]**.
4. **Prórroga de no-sanción de la GRE-remitente después del 31 de agosto de 2026.** No se encontró ninguna; verificar en cpe.sunat.gob.pe/node/119 **[NV]**.
5. **Plataforma SUNAT de conformidad de factura** ([S6] de la propuesta) y una eventual ley de plazo máximo de pago a MYPE **[NV]**.
6. **Cuenta de detracciones del transportista.** No se verificó en fuente primaria el uso restringido de esos fondos ni su efecto en el flujo de caja que muestra el dashboard **[NV]**.
7. **Preview de Google.** `antigravity-preview-*` ya cambió una vez en 4 meses (de 05-2026 a 09-2026, con el 5 de octubre de 2026 como fecha de apagado del anterior según [AI Studio](https://aistudio.google.com/learn/managed-agents-updated-harness-files-credentials)). Riesgo de rotura el día del demo.
8. **Supabase Free se pausa** tras 7 días sin actividad: riesgo para la URL pública que revisa el jurado.
9. **Datos personales** (conductores, receptores, fotos y geolocalización): falta revisar la Ley 29733 y la retención **[NV]**.
10. **Datos de gonza sin verificar:** 90 días, US$ 2 000 por camión, 50 %/30 % de equipamiento e ingresos de Samsara. No usarlos como cifras en el pitch sin fuente.

---

## Fuentes

**SUNAT y normas**
- RS 000123-2022/SUNAT (GRE): https://www.sunat.gob.pe/legislacion/superin/2022/123-2022.pdf
- RS 000003-2023/SUNAT (plazo de 3 días): https://www.sunat.gob.pe/legislacion/superin/2023/000003-2023.pdf
- RS 193-2020/SUNAT y su Anexo 3 (catálogo 09): https://www.sunat.gob.pe/legislacion/superin/2020/193-2020.pdf · https://www.sunat.gob.pe/legislacion/superin/2020/anexo3-193-2020.pdf
- RS 117-2017/SUNAT (OSE, firma digital): https://www.sunat.gob.pe/legislacion/superin/2017/117-2017.pdf
- RSNATI 000031-2026 (no-sanción GRE): https://www.sunat.gob.pe/legislacion/superAdjunta/rsnati/2026/rsnati-000031-2026.pdf
- Informe SUNAT 000057-2025-7T0000: https://www.sunat.gob.pe/legislacion/oficios/2025/informe-oficios/i000057-2025-7T0000.pdf
- SUNAT, Operatividad (CDR, baja): https://orientacion.sunat.gob.pe/3529-operatividad
- SUNAT, Detracciones en transporte de bienes: https://orientacion.sunat.gob.pe/detracciones-en-el-transporte-de-bienes-por-via-terrestre
- SUNAT, FAQ Factura Negociable: https://orientacion.sunat.gob.pe/02-preguntas-frecuentes-factura-negociable
- Ley 29623: https://leyes.congreso.gob.pe/documentos/leyes/29623.pdf
- D.S. 026-2024-MTC (El Peruano): https://busquedas.elperuano.pe/dispositivo/NL/2357884-2
- SUNAT OSE (no se pudo abrir, 403): https://cpe.sunat.gob.pe/aliados/ose · https://cpe.sunat.gob.pe/padron-ose · https://cpe.sunat.gob.pe/guias-y-manuales

**MTC**
- Estadística, Servicios de carga (xlsx de empresas autorizadas 2016-2025 y ranking de flota 2025): https://www.gob.pe/institucion/mtc/informes-publicaciones/344890-estadistica-servicios-de-transporte-terrestre-por-carretera-servicios-de-carga
- Estadística, Parque automotor (xlsx de antigüedad de la flota de carga 2016-2025): https://www.gob.pe/institucion/mtc/informes-publicaciones/344892-estadistica-servicios-de-transporte-terrestre-por-carretera-parque-automotor

**Google**
- Cuotas de Apps Script: https://developers.google.com/apps-script/guides/services/quotas
- Utilities: https://developers.google.com/apps-script/reference/utilities/utilities
- XmlService: https://developers.google.com/apps-script/reference/xml-service/xml-service
- LockService: https://developers.google.com/apps-script/reference/lock/lock-service
- Límites de Google Sheets: https://support.google.com/drive/answer/37603
- Antigravity agent: https://ai.google.dev/gemini-api/docs/antigravity-agent
- Ficha `antigravity-preview-09-2026`: https://ai.google.dev/gemini-api/docs/models/antigravity-preview-09-2026
- Custom managed agents: https://ai.google.dev/gemini-api/docs/custom-agents
- Agents overview: https://ai.google.dev/gemini-api/docs/agents
- Interactions API: https://ai.google.dev/gemini-api/docs/interactions
- Pricing de la Gemini API: https://ai.google.dev/gemini-api/docs/pricing
- Structured output: https://ai.google.dev/gemini-api/docs/structured-output
- Blog de lanzamiento de Managed Agents: https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/
- Actualización en AI Studio: https://aistudio.google.com/learn/managed-agents-updated-harness-files-credentials
- ADK en Cloud Run: https://google.github.io/adk-docs/deploy/cloud-run/
- Agent Platform / Agent Runtime: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy

**Supabase**
- Límites de Edge Functions: https://supabase.com/docs/guides/functions/limits
- Pricing: https://supabase.com/pricing
- RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- pgaudit: https://supabase.com/docs/guides/database/extensions/pgaudit
- Vault: https://supabase.com/docs/guides/database/vault

**Secundarias (solo donde la primaria no fue accesible)**
- Greenter gre-api (flujo OAuth de la GRE): https://github.com/thegreenter/gre-api

**Nota de acceso:** `cpe.sunat.gob.pe` y algunas páginas de `gob.pe` devolvieron 403/418 a las herramientas de este entorno. Las afirmaciones que dependen de ellas están marcadas **[2ria]** o **[NV]**.
