# La telemetría de la demo es sintética, sobre corredores reales de Perú

Reemplaza a [0001](0001-telemetria-por-replay-de-fead.md) y a [0006](0006-datos-de-china-sin-reproyectar-ni-redistribuir.md).

El producto se vende a flotas peruanas y una demo en corredores de China obligaba a explicarlo todo como analogía. Reproyectar las trayectorias de FEAD sobre la Panamericana se descartó: era fabricar datos con apariencia de reales, el consumo medido no calzaba con el terreno nuevo y entre el 15 % y el 90 % de las lecturas de cada vehículo caían fuera de los corredores. En su lugar, `data/fleetdata/peru.py` genera una flota de 28 tractocamiones que recorren cuatro corredores reales (Lima–Arequipa, Lima–Huancayo por Ticlio, Lima–Piura y Arequipa–Juliaca) con un modelo físico de consumo (`fisica.py`): masa, pendiente, curvas, altitud y resistencia aerodinámica. La geometría viene de OpenStreetMap (OSRM) y la altitud de SRTM 90 m. Las dos se descargan una vez y se versionan en `rutas_peru.json`. El modelo se calibró con lo medido en FEAD: unos 33 L/100 km en llano y una mediana de 21,6 L/h.

## Consequences

- Toda la telemetría, los viajes, los fletes, los conductores y los reportes precargados son `synthetic_demo`. La línea base sigue siendo `model_inferred`. La demo nunca dice "telemetría real". El aviso pasa a ser "flota simulada sobre carreteras reales de Perú".
- Los casos de la demo están guionados en `GUIONES`: sobreconsumo de T07, ralentí de T04, parada sin explicar de T28 y subida a Ticlio de T22. Son deterministas con la semilla, y los tests los verifican.
- La capa comercial es peruana: toneladas, tarifa en S/ por t-km, IGV, detracción del 4 % sobre S/ 400, GRE y RUC ficticios con dígito verificador inválido. Las tarifas y el precio del diésel son supuestos de la demo y están marcados en el código.
- Al no haber datos de terceros, el repositorio puede versionar la salida completa si hace falta. El pipeline de FEAD queda solo como referencia de calibración.
- Por ahora se conservan las fechas (abril de 2020) y el corte de días a las 16:00 UTC del replay para no mover el contrato del backend. Pasar a hora de Lima es un cambio aparte.
