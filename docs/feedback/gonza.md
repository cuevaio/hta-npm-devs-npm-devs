# Feedback Gonza
### Contexto del Negocio de Transporte

- Transporte es un negocio de finanzas: alta inversión inicial, cobros a 90 días
- Camión cuesta \~$2,000, combustible \~200 litros por viaje
- Factoring necesario pero requiere mucho capital
- Realidad del parque vehicular en Perú: muchos microtransportistas, camiones viejos
- Estimado: \~50% de camiones sin tecnología moderna, solo \~30% bien equipados
- Estrategia de conductores: convenio con la Marina
- Oficiales que terminan carrera (\~50-60 años) se capacitan como conductores de tanque
- Se desvinculan de la Marina y pasan a trabajar con la empresa

### Cómo Funciona la Trazabilidad (Modelo Chopex)

- Tres pilares para dar estatus de un viaje:
1. GPS: ubicación, velocidad, paradas (minuto a minuto)
2. WhatsApp: contexto de la parada (comiendo, tráfico, baño)
3. ERP: viaje programado vs. realidad (conductor, horario, cliente)
- Estos tres pilares cubren \~80% de la operación; el 15-20% restante (cámaras, sensores) es útil pero no fundamental
- Chopex no vende hardware: se conecta a proveedores como Samsara, Mofi, Geotap vía API
- Samsara: empresa unicornio, factura $200M/año, documentación API pública con data de prueba disponible
- En algunos casos se solicita API/token al proveedor local; en otros se conectan directamente al OBD

### Pain Point Principal: Documentación y Liquidación

- Empresas de domésticos (y similares) acumulan documentos y reportes antes de liquidar
- Pagos quincenales, liquidación a fin de mes, documentos represados
- Las empresas grandes intencionalmente “patean” pagos con excusas documentarias
- Rechazan documentos por formato incorrecto (hoja azul vs. verde), horarios de recepción, revisiones lentas
- Ciclo real: presentación → revisión (días) → aprobación → factura → 30 días de crédito = 45-60 días efectivos
- Facturas electrónicas no resuelven el problema: el cliente igual exige impresión física con sello
- Este problema de liquidez afecta directamente al transportista

### Oportunidad: POD Customizable y Agéntico

- El POD (Proof of Delivery / evidencia) es el cuello de botella clave
- Si el POD es aceptado en el 90% de los casos, se libera liquidez inmediata al transportista
- Solución propuesta: dashboard que genere evidencia automáticamente según el formato del cliente
- El agente detecta el formato requerido y lo genera al instante, sin intervención manual
- Si hay cambio de formato, el ajuste es automático y se reanuda sin demora
- Validación cruzada: el chico de Discord también señaló la facturación como foco principal
- Cashflow es el “efecto wow”, pero la facturación/POD es el plato principal

### Conclusiones y Próximos Pasos

- Pain points confirmados que no estaban mapeados antes: documentación, POD, liquidez
- Foco del producto: facturación y evidencia customizable, no solo trazabilidad
- Más de 12 horas de trabajo por delante para aterrizar todo lo explorado
- La solución real no es solo un aplicativo de facturas: debe resolver el problema de fondo en la cadena de pagos

### Próximos Pasos

- **Aterrizar los pain points nuevos con lo ya mapeado**

Integrar los insights de documentación, POD y liquidez al modelo existente del producto.

- **Revisar documentación API de Samsara**

Explorar data de prueba disponible para casos de uso de trazabilidad.

- **Definir MVP centrado en POD customizable y agéntico**

El foco principal es facturación y evidencia, no cashflow como feature central.