# Un tramo es una celda H3 de resolución 6 recorrida en un sentido

La línea base compara vehículos que pasan por el mismo trecho del corredor (ADR 0002), así que necesitamos cortar los corredores en tramos comparables. Un tramo es una celda hexagonal H3 de resolución 6 (unos 6–7 km de recorrido) más el sentido del viaje (ida o vuelta según el terminal de origen). Los pares que siguen la misma carretera caen en las mismas celdas sin necesitar la geometría de la vía, y el corte tolera los huecos de GPS.

## Considered Options

- **Bloques de 10 km por odómetro desde el origen:** descartada; el odómetro de parte de la flota tiene resolución de 1 km y huecos.
- **Map-matching contra la red vial:** más preciso, pero no entra en el plazo.
- **Sentido por rumbo GPS:** descartado; falla en carreteras con curvas.

## Consequences

- El consumo de un tramo se mide integrando `x7001` (L/h) y sumando distancias GPS, no con `x7002` (resolución de 0,5 L) ni con el odómetro.
- Cambiar la resolución de H3 obliga a recalcular la línea base y las pasadas por tramo.
