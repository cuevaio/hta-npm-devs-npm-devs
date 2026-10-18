# La telemetría es un replay de FEAD, no un proveedor en vivo

No tenemos acceso a Samsara, a un gateway OBD-II/J1939 ni a vehículos reales, y la demo tiene que ser reproducible sin credenciales comerciales. Por eso la única fuente de telemetría del MVP es el EMS dataset-2 de FEAD (29 tractocamiones, abril de 2020), reproducido por un servicio de replay que conserva la hora del evento original. Los proveedores en vivo quedan detrás de la misma interfaz para el futuro, pero no se implementan.

## Consequences

- Toda alerta refleja un escenario sobre datos históricos y debe decirlo; nunca se presenta como monitoreo en tiempo real.
- FEAD trae consumo instantáneo y acumulado, posición y señales de motor, pero no altitud, carga, temperatura ni códigos de falla. El mantenimiento predictivo queda fuera ([`fead-ems-dataset2-perfil.md`](../research/fead-ems-dataset2-perfil.md)).
