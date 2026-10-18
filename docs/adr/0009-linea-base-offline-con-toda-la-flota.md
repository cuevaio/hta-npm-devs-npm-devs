# La línea base se calcula offline con toda la flota; a la base solo llega el agregado

La telemetría cruda a 1 Hz solo se carga para los 6 camiones de la demo, pero con 6 camiones casi ningún tramo tendría pares suficientes. La línea base se calcula en `data/` con los 28 camiones de FEAD en los días 1–12 y a Cloud SQL solo llega la tabla agregada por tramo (mediana, p90 y número de pasadas). Un tramo con menos de 3 pasadas de pares no tiene línea base: el sistema no lo juzga y lo dice.

## Consequences

- La base desplegada no contiene telemetría cruda de los otros 22 camiones, solo estadísticos por tramo.
- Recalcular la línea base es un paso offline del pipeline de datos, no algo que haga la Domain API.
