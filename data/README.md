# data/: pipeline de datos de Fleet Intelligence

Convierte FEAD EMS dataset-2 (telemetría real de una flota en China, abril de 2020) en datos anónimos para la demo.
El repositorio solo contiene scripts y un fixture chico: nunca datos crudos (ADR 0006). FEAD no tiene licencia y sus
filas traen matrículas, IMEI y direcciones reales.

## Punta a punta

```bash
cd data && uv sync
uv run python -m fleetdata.pipeline \
  --archive /ruta/ems-dataset-2.tar.gz \      # se descarga ahí si no existe; siempre se verifica el SHA-256
  --alias-map /ruta/fuera-del-repo/alias.json \  # tabla privada {hash: "T01"…}; nunca entra al repo
  --out out                                    # ignorado por git
```

Lee el tar en streaming (15,5 GB descomprimidos, sin tocar disco). Tarda unos 20 minutos y necesita unos 3 GB de RAM.
Los tests (`uv run pytest`, o `make test-data`) usan un tar sintético con matrículas, IMEI y hashes falsos y no necesitan datos reales.

## Pasos

| Módulo | Qué hace |
|---|---|
| `download.py` | Descarga y verifica el SHA-256 del tar (valor fijado en el código). |
| `extract.py` | Filtra por hash de vehículo según la tabla de alias; los 28 para la línea base, 6 para la demo (T03, T04, T07, T22, T28, T09). |
| `anonymize.py` | hash a alias `T01…T28`; descarta IMEI, matrícula, hash y direcciones. Conserva lat/lon (ADR 0006). |
| `normalize.py` | Hora del evento en UTC (`ems_time` es hora local UTC+8), procedencia `fead_observed`, unidades corregidas del perfil (x7000 rpm, x7001 L/h, x7002 L, x7004 km/h, x7005 km). |
| `trips.py` | Viaje = recorrido entre estancias de 3 h o más en terminales; sentido por terminal de origen; pasada = recorrido de una celda H3 res. 6 en un viaje, con consumo = integral de x7001 y distancia GPS. |
| `baseline.py` | Línea base por (corredor, celda, sentido) con mediana, p90 y n de pasadas de los 28 vehículos en los días 1-12; con menos de 3 pasadas no hay línea base (ADR 0008, 0009). |
| `synthetic.py` | Fletes `F-101…` (1:1 con viaje), conductores y reportes guionados, con semilla fija. Procedencia `synthetic_demo`. |
| `fixture.py` | `data/fixtures/`: 30 min de T03 y de T07 (CSV), muestra de la línea base y la logística de esos vehículos. Se versiona. |
| `pii.py` | Detector de matrículas chinas, IMEI, hashes hex de 32/40/64 y texto chino. El pipeline falla si lo encuentra en la salida. |

## Salida (`out/`, no versionada)

`telemetry/<alias>.parquet` (los 6 vehículos de la demo, 19 días), `trips.csv`, `passes_demo.csv`, `baseline.csv`,
`freights.csv`, `drivers.csv`, `driver_reports.csv`. Esquema de telemetría: `alias, event_time (UTC), lat, lon, speed_kmh,
rpm, fuel_rate_lph, fuel_total_l, odometer_km, engine_on, provenance`.

## Procedencia de la logística sintética

Los fletes, conductores y reportes de `synthetic.py` son `synthetic_demo`. Un reporte del conductor escrito en vivo por
WhatsApp durante la demo es `human_reported` (CONTEXT.md), aunque su flete y su conductor sean sintéticos; los reportes
guionados que se precargan aquí son `synthetic_demo`. La línea base es `model_inferred` (calculada por el sistema).
