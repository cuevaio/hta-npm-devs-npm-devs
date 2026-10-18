# Instructivo: cómo usar los documentos en la demo (Casos A y B)

> Todos los documentos son **ficticios** (marca "DATOS FICTICIOS - DEMO"). Sirven solo para la demo.

## 1. La historia en una frase
La empresa **Transportes Ruta Sierra** (MYPE) llevó 18 t de mercadería de Lurín (Lima) al CD Huancayo de su cliente **Distribuidora Andina del Centro** el **sábado 10-oct a las 14:35**. Para facturar y cobrar, el cliente tiene que aceptar el **cargo firmado** (la prueba de entrega o POD). El cliente lo rechaza, y el agente de WhatsApp ayuda al transportista a destrabarlo.

## 2. Qué es cada archivo (en el orden en que aparece)

| # | Archivo | Qué es | Para qué sirve en la demo |
|---|---|---|---|
| 1 | `orden_servicio_OS-1042.pdf` | El encargo del cliente: tarifa S/ 3,800 + IGV, crédito a 30 días y **cláusula 3** (los 5 requisitos del POD) | Es "lo pactado". Contra esto se valida todo |
| 2 | `GRE_remitente_EG01-00004521.pdf` | Guía de remisión en blanco, con la que sale el camión | Contexto: identifica la carga, la placa y el chofer |
| 3 | `foto_camion_anden.png`, `foto_descarga.png` | Fotos que manda el chofer al llegar y al descargar | La foto de descarga cumple el requisito 3.e |
| 4a | `cargo_sin_sello.png` | Guía firmada **sin sello** | Caso A: incompleto |
| 4b | `cargo_completo.png` | Guía firmada **con sello**, con todo | Caso B, y la corrección del caso A |
| 5a | `observacion_A_falta_sello.pdf` | Correo del cliente: "falta el sello" | Caso A: rechazo **válido** |
| 5b | `observacion_B_formato_nuevo.pdf` | Correo del cliente: "usen nuestro formato amarillo F-REC-07 + foto en góndola" | Caso B: rechazo **no pactado** |
| 6 | `factura_E001-000123.pdf` | Factura a crédito: S/ 4,484, detracción S/ 184, neto a cobrar S/ 4,300 | Se emite cuando el cliente acepta el POD |
| — | `ground_truth.json` / `.csv` | Los valores correctos de cada documento | Para comprobar que el OCR o la IA extraen bien los datos |
| — | `demo_estado.json` | Estados y línea de tiempo de A y B | Para el tablero o el semáforo en pantalla |
| — | `README_demo.md` | La explicación completa del caso | Referencia |

**Los 5 requisitos del POD (cláusula 3):** a) firma, nombre y DNI de quien recibe · b) sello del almacén · c) N° de OS escrito · d) fecha y hora · e) foto de la carga descargada.
**Cláusula 3.1:** cualquier cambio necesita una **adenda escrita** y solo vale para servicios futuros.

## 3. Paso previo (antes de mostrar los casos)
1. Cargar `orden_servicio_OS-1042.pdf` en el sistema. El agente extrae la tarifa, el plazo y los 5 requisitos y los muestra en pantalla.
2. (Opcional) Mostrar la GRE y las fotos del camión llegando.

## 4. CASO A: al cargo le falta el sello (el cliente tiene razón)
**Mensaje:** el agente evita rechazos porque detecta el error antes que el cliente.

| Paso | Qué haces | Archivo | Qué debe mostrar el agente |
|---|---|---|---|
| 1 | El "chofer" manda por WhatsApp la foto del cargo y de la descarga | `cargo_sin_sello.png` + `foto_descarga.png` | Lee: receptor Carmen Poma, DNI 99776655, 10/10 14:35, OS-1042, firma ✅, **sello ❌** |
| 2 | — | — | Responde al chofer al momento: *"Falta el sello del CD Huancayo. Pídeselo a la Sra. Carmen Poma antes de irte."* |
| 3 | (Variante) Si ya se presentó, llega el correo del cliente | `observacion_A_falta_sello.pdf` | Lo clasifica como **observación válida (cláusula 3.b)**. No discute y pide el sello |
| 4 | El chofer manda el cargo corregido | `cargo_completo.png` | Los 5 requisitos ✅. Prepara el reenvío al cliente (el transportista lo aprueba) |
| 5 | El cliente acepta | `factura_E001-000123.pdf` | Arma la factura y empieza a contar los plazos |

**Frase para el pitch:** "Sin el agente, este error se descubre 2 días después y el chofer ya está en otra ruta. Con el agente, se corrige en el mismo andén."

## 5. CASO B: el cliente pide algo que no estaba pactado (el transportista tiene razón)
**Mensaje:** el agente defiende al transportista con el contrato para que el cliente no pueda retrasar el pago.

| Paso | Qué haces | Archivo | Qué debe mostrar el agente |
|---|---|---|---|
| 1 | El chofer manda el cargo y la foto | `cargo_completo.png` + `foto_descarga.png` | Los 5 requisitos ✅. Presenta el POD al cliente (lun 12-oct 09:10) |
| 2 | Llega el rechazo del cliente | `observacion_B_formato_nuevo.pdf` | Compara con la OS: el formato F-REC-07 y la foto en góndola **no están en la cláusula 3**, la cláusula prohíbe pedir formatos adicionales y no hay adenda. Además, la "política interna" que cita el cliente es del 01/10, anterior a la OS del 07/10. Lo clasifica como **requisito no pactado** |
| 3 | — | — | Redacta una respuesta cordial y firme (ver abajo). **El transportista la aprueba antes de enviar** |
| 4 | El cliente acepta | `factura_E001-000123.pdf` | Emite la factura y empieza a contar los plazos |

**Respuesta del agente (caso B):**
> Estimada Lucía: gracias por su revisión. El POD de la OS-1042 cumple los requisitos de la cláusula 3 de la Orden de Servicio: (a) firma, nombre y DNI de la Sra. Carmen Poma, (b) sello del CD Huancayo, (c) OS-1042 consignada, (d) 10/10/2026 a las 14:35 y (e) foto de la carga descargada. El formato F-REC-07 y la foto en góndola no forman parte de los requisitos pactados. Según la cláusula 3.1, cualquier cambio requiere una adenda escrita y aplica solo a servicios posteriores. Le pedimos dar conformidad al POD para emitir la factura dentro del plazo. Con gusto evaluamos una adenda para los próximos servicios. Saludos, Juan Carlos Rojas.

**Frase para el pitch:** "Hoy el transportista rehace el documento las veces que el cliente pida, y su plata espera. Con el agente sabe en segundos si el pedido es válido o no, y responde con el contrato en la mano."

## 6. Cierre común (A y B): factura y plazos
- Factura E001-000123 emitida el **mar 13-oct 17:30**: S/ 4,484, detracción 4% S/ 184, **neto a cobrar S/ 4,300**.
- **Conformidad:** hasta el **vie 23-oct** (8 días hábiles). Si el cliente no responde, se presume la conformidad.
- **Pago:** hasta el **jue 12-nov** (30 días, Ley 31362 para MYPE). Si no paga, el agente sugiere un recordatorio citando la ley.
- En pantalla, la línea de estados: entregado → POD presentado → observado → corregido/defendido → aceptado → factura emitida → conformidad pendiente → pagado (`demo_estado.json`).

## 7. Consejos para presentar
- Empieza por el **caso B**: es el dolor que les contó Chofex y el más original. Usa el A como prueba de que el agente también corrige errores reales.
- Muestra siempre la cláusula citada en pantalla: es lo que da credibilidad.
- Recalca que el agente **nunca inventa sellos ni firmas** y **nunca envía sin aprobación** del transportista.
- Usa `ground_truth.json` para comprobar en vivo que los datos extraídos son correctos.
- Los montos y las leyes son referenciales: dilo si preguntan.
