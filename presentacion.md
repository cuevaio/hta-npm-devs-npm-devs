# Certera

> Señales claras. Decisiones certeras.

## Problema

Las plataformas de gestión de flotas calculan el consumo como si la carretera fuera plana. En los Andes un camión sube de 0 a 4 800 msnm en pocas horas, y sin ese contexto el gestor ve el gasto cuando ya no puede hacer nada: camiones sin diésel en zonas remotas, motores exigidos de más y alertas que nadie cree porque cualquier subida parece un problema.

## Solución

Certera es un agente de IA para flotas de transporte pesado en Perú. Cruza la telemetría de cada camión con la altitud y la pendiente de su ruta, detecta el sobreconsumo y avisa a la torre de control por WhatsApp con la evidencia. El chofer entra al circuito con sus reportes, y la IA de la empresa puede consultar la flota en lenguaje natural mediante un servidor MCP de solo lectura.

## Diferenciador

- **Compara con pares, no con promedios.** El consumo de cada camión se mide contra el de la flota que recorrió el mismo tramo en el mismo sentido, así que una subida a Ticlio no dispara falsas alarmas.
- **Explica, no es una caja negra.** Cada alerta separa hechos de hipótesis y declara de dónde sale cada dato.
- **Una persona en el circuito.** El reporte del chofer se cruza con los sensores antes de concluir nada.

## Impacto

*Estimación, sin validar con clientes.* Un camión varado cuesta entre **US$ 500 y 2 000** en grúa, reprogramación y penalidades. La meta de costo operativo es **menos de US$ 3 al mes por camión**, porque la IA solo razona cuando las reglas detectan una anomalía. Evitar un solo evento cubre la plataforma.
