# Fleet Intelligence

Inteligencia operacional para flotas de transporte troncal de larga distancia: explica qué pasa con cada vehículo en su corredor, detecta sobreconsumo de combustible frente a sus pares y avisa al gestor de flota por WhatsApp.

## Language

### Personas

**Gestor de flota**:
Persona que supervisa la operación de la flota, recibe alertas y consulta el estado de vehículos y viajes.
_Avoid_: Operador, coordinador, usuario

**Conductor**:
Persona que maneja un vehículo durante un viaje y puede enviar reportes por WhatsApp.
_Avoid_: Chofer, operador

No hay otros roles: el despachador se funde con el gestor de flota y no existe analista de mantenimiento.

### Flota y operación

**Vehículo**:
Tractocamión de la flota, identificado por un alias anónimo (`T01`…`T28`). Su estado no equivale al estado de una entrega.
_Avoid_: Camión (en código y docs), unidad, truck

**Viaje**:
Recorrido de un vehículo por un corredor en un sentido, con un conductor. La telemetría pertenece al viaje.
_Avoid_: Trip, traslado, recorrido

**Flete**:
Encargo comercial (carga, cliente, origen y destino) que cumple un viaje. En la demo es siempre sintético y cada flete tiene exactamente un viaje.
_Avoid_: Shipment, envío, pedido, carga (como entidad)

**Corredor**:
Ruta interprovincial fija y recurrente entre dos terminales, que varios vehículos recorren en ambos sentidos.
_Avoid_: Ruta, línea

**Sentido**:
Dirección en que un vehículo recorre un corredor (ida o vuelta). El consumo de un mismo corredor cambia mucho según el sentido.
_Avoid_: Dirección, rumbo

**Tramo**:
Trecho de unos 10 km de un corredor, recorrido en un sentido. Es la unidad de comparación del consumo.
_Avoid_: Segmento, celda, sección

**Parada**:
Vehículo detenido durante 10 minutos o más.
_Avoid_: Detención, stop

**Cuello de botella**:
Tiempo perdido en un viaje por paradas sin explicar o por ralentí prolongado, ordenado por impacto. Una parada explicada por el conductor deja de serlo, pero sigue visible.
_Avoid_: Retraso, demora, tramo lento

**Reporte del conductor**:
Mensaje de WhatsApp de un conductor, guardado con su texto original y asociado a un viaje. Su procedencia es `human_reported` aunque el viaje sea sintético.
_Avoid_: Reporte humano, mensaje, evento del conductor

**Ralentí**:
Motor encendido con el vehículo detenido.
_Avoid_: Idle, motor en vacío

### Datos y procedencia

**Procedencia**:
Origen de un dato: `fead_observed` (telemetría real de FEAD), `synthetic_demo` (fabricado para la demo), `human_reported` (escrito por una persona), `external_enrichment` (fuente externa) o `model_inferred` (calculado por el sistema). Toda respuesta la declara.
_Avoid_: Fuente, origen

**Replay**:
Reproducción controlada de telemetría histórica de FEAD como si llegara en vivo. Nunca es monitoreo en tiempo real.
_Avoid_: Streaming, simulación, tiempo real

**Hora del evento**:
Momento en que ocurrió la lectura original en el vehículo. Se distingue de la **hora de replay** (cuándo se reemitió) y de la **hora de ingesta** (cuándo la recibió el sistema).
_Avoid_: Timestamp (sin calificar)

### Combustible y alertas

**Consumo observado**:
Combustible que el vehículo realmente gastó según su telemetría, en litros o L/100 km.
_Avoid_: Consumo real (sin calificar), gasto

**Pares**:
Vehículos de la flota que recorrieron el mismo tramo del mismo corredor en el mismo sentido.
_Avoid_: Flota (como referencia de comparación), benchmark

**Línea base**:
Consumo esperado para un tramo y sentido de un corredor, calculado a partir de sus pares. Nunca es por vehículo.
_Avoid_: Promedio, consumo esperado del camión, baseline del vehículo

**Sobreconsumo**:
Consumo observado por encima de la línea base de un tramo más allá de un umbral.
_Avoid_: Consumo anómalo, exceso, desperdicio

**Anomalía**:
Hallazgo registrado por el sistema, con su evidencia, que puede agrupar varios tramos con sobreconsumo de un mismo viaje.
_Avoid_: Incidente, evento, desviación

**Alerta**:
Aviso enviado al gestor de flota por una anomalía, según una política anti-spam. Si existe un reporte del conductor relacionado, lo incluye; nunca decide por el gestor.
_Avoid_: Notificación, aviso, alarma
