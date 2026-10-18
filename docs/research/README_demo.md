# Demo Hack the Andes (Lima): agente de WhatsApp para cobrar fletes (de la entrega al pago)

> **DATOS FICTICIOS - DEMO.** Todas las empresas, RUC (patrón `20999999xxx`), personas, DNI, licencias, placas, cuentas, correos (`.example`) y montos son inventados. Ningún documento tiene validez tributaria ni legal. Las fotos de entrega son **ilustraciones** generadas por código.

## 1. El caso

| Rol | Dato ficticio |
|---|---|
| Cliente / remitente | **DISTRIBUIDORA ANDINA DEL CENTRO S.A.C.** · RUC 20999999991 · Lurín, Lima |
| Transportista (MYPE) | **TRANSPORTES RUTA SIERRA E.I.R.L.** · RUC 20999999983 · Reg. MTC DEMO-15-000999-CNG |
| Destinatario | CD Huancayo del cliente · Av. Mariscal Castilla Ficticia 2580, El Tambo (ubigeo 120114) |
| Receptora en destino | Carmen Rosa Poma Sotelo (Jefa de Almacén) · DNI 99776655 |
| Unidad / conductor | Placa **F4X-982** (C3, camión de 3 ejes) · Wilfredo Quispe Huamán · DNI 99887766 · Lic. Q99887766 (A-IIIc) |
| Carga | 1,380 cajas de consumo masivo, 24 pallets, **18,000 kg** |
| Documentos clave | **OS-1042** (contrato marco CM-2026-007) · **GRE Remitente EG01-00004521** · GRE Transportista V001-00000318 (citada, no incluida) · **Factura E001-000123** |
| Tarifa | S/ 3,800.00 + IGV 18% (S/ 684.00) = **S/ 4,484.00** · crédito 30 días |

**El problema:** el cliente rechaza el cargo firmado (POD) y pide cambios de formato o documentos, y la factura y el pago se atrasan. El agente de WhatsApp del transportista recibe las fotos del conductor, revisa el POD contra la cláusula 3 de la OS, lo presenta, clasifica las observaciones del cliente (si son válidas o no pactadas), redacta las respuestas y hace seguimiento de los plazos de conformidad y pago.

### Cláusula 3 de la OS-1042: requisitos del POD (los 5 son obligatorios)
a) firma y nombre (y DNI) del receptor · b) **sello del almacén de destino** · c) **N° de OS** escrito en el cargo · d) fecha y hora de recepción · e) foto de la carga descargada.
**3.1:** cualquier cambio (formatos propios, fotos adicionales, otros documentos) **requiere una adenda escrita** firmada por ambas partes y solo aplica a servicios posteriores. La cláusula 3 también dice: *"No se exigirán formatos, documentos o evidencias adicionales a los aquí listados."*

## 2. Archivos

| Archivo | Qué es |
|---|---|
| `orden_servicio_OS-1042.pdf` | OS del cliente: tarifa, crédito 30 días, revisión del POD en 1 día hábil (2.3), cláusula 3 y 3.1 |
| `GRE_remitente_EG01-00004521.pdf` | Representación impresa de la GRE Remitente (en blanco, sin firmas) |
| `cargo_completo.png` | Foto del cargo firmado: firma, nombre, DNI, fecha/hora, OS-1042 y sello. **Cumple** |
| `cargo_sin_sello.png` | El mismo cargo **sin sello**. **No cumple la cláusula 3.b** |
| `foto_descarga.png` | Ilustración: 24 pallets descargados, con overlay 10/10/2026 14:21 (cumple 3.e) |
| `foto_camion_anden.png` | Ilustración: camión F4X-982 en el andén, 12:58 (evidencia extra) |
| `observacion_A_falta_sello.pdf` / `.eml` | Correo del cliente: falta el sello (observación **válida**) |
| `observacion_B_formato_nuevo.pdf` / `.eml` | Correo del cliente: exige el formato amarillo F-REC-07 y una foto en góndola (requisito **no pactado**) |
| `factura_E001-000123.pdf` | Factura electrónica del transportista: crédito, cuota, bloque SPOT 4% con valor referencial ilustrativo |
| `ground_truth.json` / `ground_truth.csv` | Campos estructurados de cada documento (para probar OCR/extracción) |
| `demo_estado.json` | Máquina de estados y timeline de los escenarios A y B |

## 3. Timeline (hora de Lima, UTC-5)

| Fecha y hora | Hito | Evidencia |
|---|---|---|
| Mié 07-oct-2026 10:15 | OS-1042 emitida | orden_servicio |
| Vie 09-oct-2026 18:42 | GRE EG01-00004521 emitida; salida de Lurín a las 22:00 | GRE |
| Sáb 10-oct-2026 12:58 | Llegada al CD Huancayo | foto_camion_anden |
| Sáb 10-oct-2026 14:21 | Carga descargada | foto_descarga |
| **Sáb 10-oct-2026 14:35** | **Entrega / firma del cargo** | cargo_* |
| Lun 12-oct-2026 09:10 | El agente presenta el POD al cliente | cargo + foto |
| Lun 12-oct-2026 16:45 (A) / 16:52 (B) | **Rechazo / observación** | observacion_A / observacion_B |
| A: Mar 13-oct 11:20 · B: Lun 12-oct 17:20 | A: re-presentación con sello · B: respuesta de defensa | cargo_completo / respuesta |
| A: Mar 13-oct 15:10 · B: Mar 13-oct 10:05 | POD aceptado | n/a |
| **Mar 13-oct-2026 17:30** | **Factura E001-000123 emitida** | factura |
| **Vie 23-oct-2026** | **Límite de conformidad**: 8 días hábiles desde la recepción de la factura (14, 15, 16, 19, 20, 21, 22, 23 oct). Si no hay disconformidad, se presume conformidad | n/a |
| **Jue 12-nov-2026** | **Límite de pago**: 30 días calendario desde la emisión (Ley 31362, proveedor MYPE) = vencimiento de la factura | n/a |
| Hoy, sáb 17-oct-2026 | Estado: `conformidad_pendiente` (faltan 5 días hábiles para la conformidad y 26 días para el pago) | demo_estado.json |

*Base legal referencial para el demo: la Ley 31362 regula el pago oportuno a proveedores MYPE (plazo máximo de 30 días calendario). La regla de 8 días hábiles para la conformidad viene del régimen de factura negociable (Ley 29623 y modificatorias). Hay que validarlo con un asesor antes de usarlo en producción.*

### Montos (deben coincidir en todos los documentos)
- Valor de venta S/ 3,800.00 · IGV S/ 684.00 · **Total S/ 4,484.00**
- SPOT 4% (código 027, transporte de carga). El **valor referencial es ILUSTRATIVO**: 18.00 TM × S/ 255.00/TM = **S/ 4,590.00**
- Base de la detracción = mayor entre el importe (4,484.00) y el valor referencial (4,590.00) = **S/ 4,590.00** → 4% = S/ 183.60 → **S/ 184.00** redondeado
- **Monto neto pendiente de pago: S/ 4,300.00** (1 cuota, vence el 12/11/2026)

## 4. Las dos versiones del demo

### Versión A: falta el sello pactado → corregir
1. El conductor envía `cargo_sin_sello.png` por WhatsApp. **Comportamiento ideal:** el agente detecta antes de presentar que falta el sello (3.b) y avisa al conductor de inmediato: *"Falta el sello del CD Huancayo. Pídeselo a la Sra. Carmen Poma antes de irte."*
2. Si ya se presentó, llega `observacion_A_falta_sello.pdf`. El agente la clasifica como **observación válida** (está en la cláusula 3.b) y **no discute**. Crea la tarea de conseguir el sello, coordina con el contacto del CD y vuelve a presentar `cargo_completo.png`.
3. Mensaje de re-presentación (borrador que aprueba el transportista):
   > Estimada Lucía: adjuntamos el cargo de la GRE EG01-00004521 con el sello de recepción del CD Huancayo, para la OS-1042. Con esto se cumplen los 5 requisitos de la cláusula 3. Agradeceremos su conformidad para emitir la factura. Saludos, Juan Carlos Rojas, Transportes Ruta Sierra.

### Versión B: requisito nuevo no pactado → el agente defiende con la OS
1. El POD presentado (`cargo_completo.png` + `foto_descarga.png`) **cumple** a)–e).
2. Llega `observacion_B_formato_nuevo.pdf`, que pide el formato F-REC-07 y una foto del producto en góndola. El agente lo clasifica como **requisito no pactado**: no está en la cláusula 3, la propia cláusula prohíbe exigir formatos adicionales y la 3.1 exige una adenda que no existe. Además, la "política interna" que menciona el cliente es del 01/10, anterior a la OS del 07/10, y no se incorporó.
3. Borrador de respuesta (el transportista lo aprueba antes de enviar):
   > Estimada Lucía: gracias por su revisión. El POD de la OS-1042 cumple los requisitos de la **cláusula 3** de la Orden de Servicio: (a) firma, nombre y DNI de la Sra. Carmen Poma, (b) sello del CD Huancayo, (c) OS-1042 consignada, (d) 10/10/2026 a las 14:35 y (e) foto de la carga descargada. El formato F-REC-07 y la foto en góndola no forman parte de los requisitos pactados. Según la **cláusula 3.1**, cualquier cambio requiere una adenda escrita y aplica solo a servicios posteriores. Le pedimos dar conformidad al POD para emitir la factura dentro del plazo. Con gusto evaluamos una adenda para los próximos servicios. Saludos, Juan Carlos Rojas.
4. El cliente acepta. Se emite la factura y empieza el seguimiento de plazos.

### Comportamiento esperado del agente (checklist de evaluación)
- Extrae la OS, la GRE, la placa, el receptor, la fecha y hora, y detecta si hay sello y firma en la imagen del cargo (ver `ground_truth.json`).
- Valida el POD contra la cláusula 3 **antes** de presentarlo y lista los requisitos faltantes.
- Clasifica cada observación como `observacion_valida` o `requisito_no_pactado` y cita la cláusula.
- Redacta las respuestas en tono cordial y firme. **Nunca envía sin la aprobación** del transportista.
- Después de la aceptación, arma los datos de la factura: montos, crédito, SPOT, base mayor y neto S/ 4,300.
- Recuerda los plazos: conformidad (23/10) y pago (12/11). Si vence la conformidad sin disconformidad, la marca como presunta. Si llega el 12/11 sin pago, sugiere un recordatorio citando la Ley 31362.

## 5. Ground truth (resumen; el detalle está en `ground_truth.json` y `ground_truth.csv`)

```json
{
  "orden_servicio_OS-1042.pdf": {"os": "OS-1042", "fecha": "07/10/2026", "contrato": "CM-2026-007", "valor_venta": 3800.00, "igv": 684.00, "total": 4484.00, "plazo_pago_dias": 30,
                                 "pod_requisitos": ["firma_nombre_receptor", "sello_almacen_destino", "numero_os", "fecha_hora_recepcion", "foto_carga_descargada"]},
  "GRE_remitente_EG01-00004521.pdf": {"serie_numero": "EG01-00004521", "fecha_emision": "09/10/2026", "motivo": "04", "placa": "F4X-982", "conductor_dni": "99887766", "peso_bruto_kg": 18000, "bultos": 1380},
  "cargo_completo.png": {"receptor": "Carmen Rosa Poma Sotelo", "dni": "99776655", "fecha": "10/10/2026", "hora": "14:35", "os": "OS-1042", "firma": true, "sello": true, "cumple": true},
  "cargo_sin_sello.png": {"receptor": "Carmen Rosa Poma Sotelo", "dni": "99776655", "fecha": "10/10/2026", "hora": "14:35", "os": "OS-1042", "firma": true, "sello": false, "cumple": false, "faltantes": ["sello_almacen_destino"]},
  "observacion_A_falta_sello.pdf": {"fecha": "12/10/2026 16:45", "clasificacion": "observacion_valida", "clausula": "3.b"},
  "observacion_B_formato_nuevo.pdf": {"fecha": "12/10/2026 16:52", "clasificacion": "requisito_no_pactado", "pide": ["F-REC-07", "foto_gondola"], "adenda": false},
  "factura_E001-000123.pdf": {"serie_numero": "E001-000123", "fecha": "13/10/2026", "vence": "12/11/2026", "total": 4484.00, "valor_ref_ilustrativo": 4590.00, "detraccion": 184.00, "neto": 4300.00}
}
```

```csv
documento,os,gre,placa,fecha_evento,firma,sello,cumple_pod,clasificacion,total
cargo_completo.png,OS-1042,EG01-00004521,F4X-982,10/10/2026 14:35,true,true,true,,
cargo_sin_sello.png,OS-1042,EG01-00004521,F4X-982,10/10/2026 14:35,true,false,false,,
observacion_A_falta_sello.pdf,OS-1042,EG01-00004521,,12/10/2026 16:45,,,,observacion_valida,
observacion_B_formato_nuevo.pdf,OS-1042,EG01-00004521,,12/10/2026 16:52,,,,requisito_no_pactado,
factura_E001-000123.pdf,OS-1042,EG01-00004521,F4X-982,13/10/2026 17:30,,,,,4484.00
```

## 6. Cómo regenerar
Los scripts están en `/workspace/chofex/src/` (`data.py` concentra todos los datos ficticios). Para regenerar:
`cd /workspace/chofex/src && ../.venv/bin/python gen_os.py ../demo_docs/orden_servicio_OS-1042.pdf && ../.venv/bin/python gen_gre.py ../demo_docs/GRE_remitente_EG01-00004521.pdf && ../.venv/bin/python gen_cargo.py && ../.venv/bin/python gen_fotos.py && ../.venv/bin/python gen_obs.py && ../.venv/bin/python gen_factura.py ../demo_docs/factura_E001-000123.pdf && ../.venv/bin/python gen_meta.py`
