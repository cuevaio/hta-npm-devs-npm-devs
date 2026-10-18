# FEAD / EMS dataset-2: perfil verificado contra fuentes primarias

Fecha de investigación: 2026-10-18. Objetivo: validar las hipótesis de `docs/product/PRODUCT_CONTEXT_CERTERA.md` §6 y §8.

## Fuentes y convención de citas

- **[R]** Repo `Torreskai0722/FEAD`, commit `df6ea61` (2024-02-27, último push). Base de URL: `https://github.com/Torreskai0722/FEAD/blob/df6ea617bf1b27634d22a35faae0437909dc1d97/`. Cito como `[R] archivo:línea`.
- **[P]** Paper: Liu et al., *Fuel Rate Prediction for Heavy-Duty Trucks*, IEEE T-ITS 2023, `https://www.weisongshi.org/papers/liu23-fuel.pdf` (6,0 MB; el servidor devuelve 406 sin User-Agent de navegador). Cito como `[P] p.N, Tabla/sección`.
- **[D]** Diccionario de datos del propio repo: `[R] EMS/codes/秒级数据报文说明.xlsx` ("Descripción de los mensajes de datos **por segundo**"), Sheet1, cito como `[D] fila N`.
- **[GH]** API de GitHub: `gh api repos/Torreskai0722/FEAD` y `/issues`.
- **[S]** Perfilado propio de una muestra real de EMS dataset-2 (ver punto 1). Scripts en `/tmp/fead-scripts/profile.py` y `/tmp/fead-scripts/units.py`; salida en `/tmp/fead-scripts/profile_out.txt`.

---

## 1. Descarga, tamaño, formato, acceso: CONFIRMADO, con matices

| Hecho | Estado | Fuente |
|---|---|---|
| Enlace directo de Google Drive, id `15Awwj26PE0MIGRUW1CiCO2xkP3j8-z2o`, público, **sin registro ni formulario** | CONFIRMADO | [R] README.md:30. El antiguo enlace a Google Form está comentado en README.md:21-25 |
| Nombre del archivo: `2020-04-20 第二批数据.gz` ("segundo lote de datos") | CONFIRMADO | cabecera `content-disposition` de `drive.usercontent.google.com` |
| Tamaño comprimido: **1 506 792 176 B (~1,5 GB)**. EMS-1: 822 MB; IFM: 61 MB | CONFIRMADO | cabecera `content-length` |
| En realidad es un **tar.gz** (usuario `hive`) de archivos diarios `./ems_yingche_YYYYMMDD.txt`: texto **separado por tabulaciones**, sin cabecera, con una columna JSON | CONFIRMADO | [S]; los nombres coinciden con [R] EMS/codes/csv_load_ems_2.sql:71-179 (`ems_yingche_20200406.txt` … `20200419.txt`) |
| Tamaño descomprimido estimado **~20-25 GB** (ratio observado ~15:1: 60 MB → 938 MB) | Estimado | [S] |
| Hipótesis §6 "adquisición cada ~100 ms" | **CONTRADICE** | Ver abajo: 1 Hz |

**Muestra descargada.** Como pesa más de 500 MB, descargué solo los **primeros 60 MB** con una petición HTTP Range (`curl -r 0-62914559`, respuesta 206) en `/tmp/fead-sample/ems2_head.gz` y descomprimí ese prefijo (`ems2_head.raw`, 938 MB). Lo perfilé con `python -I` desde `/tmp/fead-scripts/`. La muestra tiene **1 582 402 filas** del 2020-04-01 completo y parte del 2020-04-02 [S].

Perfil de la muestra [S]:

- **Estructura:** las 1 582 402 filas tienen exactamente 24 campos; 0 fallos al parsear el JSON.
- **Camiones:** 28 `truckid` distintos en ~1,1 días. README y paper dicen 29 ([R] README.md:30; [P] p.4 Tabla III).
- **Rango temporal:** `ems_time` va de 2020-04-01 00:00:00 a 2020-04-02 23:59:59. **Rango completo del archivo NO VERIFICADO.** Indicios: el nombre del archivo es del 20/04/2020, el SQL carga del 06 al 19 de abril y el README dice "04/2020".
- **Frecuencia real:** las diferencias entre filas consecutivas del mismo camión son de **1 s en el 89 %** de los casos, con huecos de 2-8 s o más; no hay timestamps duplicados.
  - Resolución de `ems_time`: segundos. El JSON trae además `date` en milisegundos, pero es la hora de recepción.
  - **CONTRADICE** "cada 100 ms" ([R] README.md:17; [P] p.3 §II.B y Tabla I: "10 Hz"). El diccionario del repo se titula "por segundo" [D] fila 2.
- **Lat/lon:** presentes en el **99,90 %** de filas, todas dentro de China (lat 22,8-46,0; lon 103,0-126,8) y sin pares (0,0).
- **Datos de texto en chino:** columnas de dirección, ciudad y nombre de vía.
- **Matrículas reales en claro:** p. ej. `黑AU2730` (ver §4).

## 2. Columnas exactas, unidades y variable objetivo

### 2.1 Columnas posicionales (24, sin cabecera) [S]

Los nombres vienen de [R] EMS/codes/csv_load_ems_2.sql:45-64 y de [D] filas 22-32, pero el SQL no lista lat/lng/r_name/r_level y su orden no encaja del todo con los datos. Por eso, **los nombres de los campos 7 a 10 son inferidos**.

| # | Nombre (fuente) | Ejemplo | % nulo |
|---|---|---|---|
| 0 | `rowkey` (SQL) | `0000030955107011585694255000` (termina en epoch ms) | 0 |
| 1 | `ems_value` (SQL), **JSON de señales** | `{"x7000":"457","x7001":"7.90",…}` | 0 |
| 2 | `brake_pos` (SQL) | NULL | 80,5 |
| 3 | `torque` (SQL) | `33` | 5,2 |
| 4 | `tap_pos` (SQL) | `12` | 80,5 |
| 5 | `ems_time` (SQL), hora del evento, `YYYY-MM-DD HH:MM:SS`, sin zona horaria | | 0 |
| 6 | `imei` (SQL) | `107015590300000` | 0 |
| 7 | (inferido) sufijo del IMEI | `90300000` | 0 |
| 8 | `truckid` (SQL), hash de 32 hex | `77A23E4D…FA7A` | 0 |
| 9 | `itemid`? | `977` (constante) | 0 |
| 10 | (inferido) tipo de dispositivo | `E-Router-4G` (constante) | 0 |
| 11 | `truckno` (SQL), **matrícula** | `黑AU2730` | 0 |
| 12 | `orgcode` (SQL) | 3 valores distintos | 0 |
| 13-14 | `lat`, `lng` [D] filas 23-24 | `45.994545`, `126.615074` | 0,1 |
| 15 | `course`, rumbo 0-359° [D] fila 25 | | 0,1 |
| 16 | `triggertime` [D] fila 26 | va 11 s por detrás de `ems_time` (mediana; p95 = 89 s) | 0,1 |
| 17-20 | `province`, `city`, `county`, `address` [D] filas 27-30 | | 0,1-0,9 |
| 21 | `r_name`, nombre de vía (geocodificado con Tencent Maps) [D] fila 31 | 55 % "无名道路" (vía sin nombre) | 0,1 |
| 22 | `r_level`, categoría de vía [D] fila 32 | 其他道路 45 %, 高速 31 %, 乡镇村道 14 %… | 0,1 |
| 23 | `tdate` | `20200401` | 0 |

### 2.2 Señales dentro del JSON `ems_value`

Las columnas de unidades comparan tres fuentes: el diccionario del repo [D], el paper ([P] p.4 Tabla II) y la muestra [S].

| Clave | Significado [D] | Unidad según [D] | Unidad según [P] | Presencia [S] | Rango observado [S] y veredicto |
|---|---|---|---|---|---|
| x7000 | 转速 (régimen del motor) | "km/h" | "km/h" | 100 % | 403-2219, mediana 1069: son **rpm**. Las dos fuentes etiquetan mal la unidad |
| **x7001** | 瞬时油耗, **consumo instantáneo** | **L/h** | L/h | 99,99 % | 0-90,9, mediana 21,6; ceros en el 15,9 % de las filas |
| x7002 | 总油耗, consumo acumulado | "0,5 L" | L | 99,2 % | 27 459,5-84 485, sin decrementos. **Está en litros con resolución de 0,5 L**: su variación diaria coincide con la integral de x7001 (ratio 1,002; rango 0,996-1,004; n = 22 camiones) |
| x7003 | freno 1/0 | | | 100 % | binaria |
| x7004 | "EMS里程 0,1 km" | 0,1 km | km | 100 % | 0-121, mediana 79. **Correlación 0,989 con la velocidad GPS**: en la práctica es la **velocidad del vehículo en km/h**, no una distancia. CONTRADICE a [D] y a [P] |
| x7005 | 累计总里程, odómetro | (vacío) | "mile" | 99,7 % | Sube 1 190-1 900 por camión y día. Con velocidad media de ~79 km/h y operación de casi 24 h, eso **cuadra con km, no con millas** |
| x7006 | % de acelerador | | % | 100 % | 0-250: parece **crudo J1939 (0,4 %/bit)**, no 0-100 %. Unidad NO VERIFICADA |
| x7007 | temperatura del refrigerante | 1 °C con offset -100 | °C | 99,8 % | -56 a 94, mediana 21: el offset ya está aplicado de alguna forma, pero la escala real es dudosa. NO VERIFICADO |
| x006C | velocidad GPS | km/h | km/h | 91,2 % | 0-194,8, mediana 77,8 |
| x7035 | freno de mano | | | 100 % | binaria |
| x7091 | % de combustible en el tanque principal | 0,1 % | (no aparece) | **0 %** | **AUSENTE** en la muestra |
| x704F | % de carga o par motor | 0,01 | % | 94,8 % | 0-100 |
| x716D | posición del pedal de freno | 0,4 % | % | 19,5 % | solo en algunos camiones |
| x705F | marcha (campo reutilizado) | | | 19,5 % | -2 a 12 |
| x000B | fecha y hora | | | 100 % | igual a `ems_time` |
| x70EB, ems_type, x702C, x70EF | "desconocido" | | | | sin documentar |

### 2.3 Fuel rate y variable objetivo

- **Sí existe una señal de consumo instantáneo en EMS dataset-2:** `x7001`, en L/h, leída del bus CAN. **CONFIRMADO** ([D] fila 5; [P] p.4 Tabla II; [S] 99,99 % de presencia).
  - Precisión: resolución de 10 mL y error del 6,1-6,5 % ([R] README.md:13; [P] p.3 Tabla I: "6,3±0,2 %").
- **La variable objetivo del paper en EMS es `x7001`, fuel rate en L/h**, instantánea y por fila.
  - Paper: [P] p.3 §II.B ("analyzed with the label x7001") y p.4 Tabla V.
  - Código: [R] EMS/codes/fuel_cnn.py:59 (`label = float(d['x7001'])`), polynomial_feature.py:85 y fuel_lstm_updated.py:62.
- **En IFM** hay dos etiquetas ([P] p.4 Tabla VII):
  - `x8001`: caudal del medidor Ono Sokki, la "verdad de terreno".
  - `x8002`: fuel rate del CAN.
- **Consumo observado acumulado:** `x7002`, en litros, es fiable y cuadra con la integral de x7001 [S]. Sostiene la §8.1 "consumo observado", con la salvedad de que es una lectura del ECU (±~6 %) y no del medidor.

## 3. Identificador de camión y otras señales

| Pregunta | Estado | Evidencia |
|---|---|---|
| ID de camión estable por fila | **CONFIRMADO** | `truckid` (hash) presente al 100 %; relación 1:1 con `imei` y con la matrícula (0 hashes con más de un IMEI) [S]. El paper lo llama `vid` ([P] p.8 Tabla XIII-XIV, "vid-9964") |
| Lat/lon por fila | **CONFIRMADO** | 99,90 % [S] |
| Altitud | **NO ENCONTRADO** | no está en [D] ni en [S]. El paper la menciona solo como factor externo ([P] p.3 §II.A) |
| Velocidad del vehículo | **CONFIRMADO** | x006C (GPS, 91 %) y x7004 (de facto velocidad EMS, 100 %) [S] |
| Carga / peso | **NO ENCONTRADO** en EMS-2 | Solo existe en IFM: `combined_vehicle_weight_kg` ([P] p.4 Tabla II, x8009; [R] IFM/codes/dataset_ems_read.py:24-26) |
| Temperatura ambiente | **NO ENCONTRADO** | Solo hay temperatura del refrigerante (x7007), con escala dudosa |
| Ralentí | **Derivable, no explícito** | rpm (x7000) > 0 con velocidad = 0. La muestra no tiene filas con el motor apagado (rpm mínima 403), lo que sugiere que solo se registra con el motor encendido [S] |
| Códigos de falla (DTC) | **NO ENCONTRADO** en EMS-2 | IFM sí tiene `engine_DTC`, `brake_DTC`… (cabecera de `IFM-Dataset/vehicle_report.csv`, descargado en `/tmp/fead-sample/ifm/`) |
| Nivel de tanque | **NO ENCONTRADO** en la práctica | x7091 está en el diccionario pero con 0 % de presencia [S] |
| Contexto de vía | **CONFIRMADO** | categoría de vía (`r_level`) y nombre de vía (`r_name`) por fila |

## 4. Licencia y términos: NO ENCONTRADO (no hay licencia)

- El repo **no tiene archivo LICENSE**, y la API de GitHub devuelve `"license": null` [GH]. El README solo pide citar el paper ([R] README.md:33-44).
- El paper dice "We have open-sourced the dataset to the research community" ([P] p.2, lista de contribuciones), pero **sin licencia explícita**.
- Sin licencia rige el copyright por defecto: **no hay concesión de redistribución**. Usarlo localmente para un demo de investigación es defendible; **empaquetarlo o redistribuirlo, no**.
- **Riesgo adicional:** las filas incluyen **matrículas chinas reales** (columna 11), IMEI y direcciones exactas [S]. Para el demo hay que eliminar o hashear `truckno`, `imei` y `address`.
- No hay issues en el repo (0 en total) que aclaren los términos [GH].

## 5. ¿Se puede unir IFM con EMS dataset-2? CONTRADICE la unión (no es posible)

- IFM es **un único camión** ([R] README.md:31; [P] p.4 Tabla III).
- Sus archivos (`vehicle_report.csv`, `localization_result.csv`, `0x721_Ins_flow_rate.csv`, `0x18fef2fe_EngFuelRate.csv`) **no traen ID de vehículo**, solo timestamps en ns o segundos relativos [S, cabeceras del zip].
- Rango de IFM: **2020-05-27 05:17-07:43 UTC (unas 2,4 h)**, frente a **abril de 2020** en EMS-2. **No hay solapamiento temporal.**
  - El paper dice "one month of IFM data" ([P] p.3 §II.B), pero el zip publicado contiene unas 2,4 h: **discrepancia con el paper**.
- Esquema y frecuencias distintos: IFM tiene 57 columnas ROS/J1939 a ~100 Hz en `vehicle_report` y 20 Hz en el caudalímetro [S]; EMS-2 son claves x7xxx a 1 Hz.
- El propio código de IFM las alinea solo entre archivos IFM, con un `t0` fijo ([R] IFM/codes/dataset_ems_read.py:34-47).

## 6. Métricas y baselines del paper

Todo lo de esta sección sale de [P] pp.7-10.

**Métricas:**
- **R²** (Ec. 4) y una "**accuracy**" propia: 1 − mediana(|error|)/media(y) (Ec. 5), p.7.
- **No reporta MAE ni RMSE**, aunque el código calcula RMSE internamente ([R] EMS/codes/fuel_cnn.py:195).

**Protocolo de evaluación:**
- Normalización estándar más **5-fold CV sobre bloques contiguos** (`KFold(shuffle=False)`, [R] EMS/codes/fuel_cnn.py:110-117; [P] p.7).
- El 10 % del train se usa como validación.
- **No hay split por camión** y los modelos son **por camión y ruta** ("route matching", p.4-5).
- En LSTM, las ventanas solapadas pueden filtrar información entre folds.

**EMS, un camión y misma ruta ([P] p.8 Tabla XII):**
- G2 (rpm + acelerador + par):
  - LR R² 0,868
  - PR 0,922
  - MLP 0,913
  - CNN 0,922
  - **LSTM 0,952** (ventana de 10)
  - CNN-LSTM 0,915
- G3 sin acelerador: R² de 0,49 a 0,56, salvo LSTM, que llega a 0,947.

**Correlación con x7001 ([P] p.4 Tabla IV):**
- acelerador 0,937
- par 0,665
- rpm 0,530
- velocidad GPS 0,038

**Otros resultados:**
- Route matching: R² 0,908 → 0,922, con 8 veces menos filas ([P] p.8 Tabla XIII).
- IFM con AutoML: R² 0,998 ([P] p.10 Tablas XVI-XVII).
- VT-CPFM como baseline físico: R² 0,818 en el dataset VT ([P] p.7 Tabla X).

**Uso para nosotros:** un **baseline de "consumo esperado" basado en rpm, acelerador y par** debería rondar R² ≈ 0,87 (lineal) a 0,92 (polinómico), por camión. Hay que **añadir MAE/RMSE en L/h y un baseline ingenuo**, porque el paper no los da.

**Cuidado:** predecir x7001 a partir del acelerador y el par del mismo instante es casi un "sensor virtual" del ECU. Sirve para detectar desviaciones de la relación motor-consumo (inyección, sensor, manipulación), **no** para detectar consumo anómalo atribuible a ruta, carga o conducción.

---

## Implicaciones para el MVP

### Hipótesis que se sostienen

- **EMS-2 sirve para el replay de telemetría histórica.** Tiene ID estable por fila, timestamp de evento, lat/lon al 99,9 %, rpm, velocidad, acelerador, par, freno y, sobre todo, **consumo instantáneo (x7001, L/h) y acumulado (x7002, L)** coherentes entre sí. Sostiene la §6.1 y la §8 "consumo observado" (Nivel 0: L/100 km por tramo con x7002/x7005; ralentí derivado).
- La descarga es pública y gratuita, y no requiere registro.
- La separación `event_time` / `replayed_at` / `ingested_at` es viable: `ems_time` es la hora del evento y `triggertime` la del reporte.
- La advertencia de la §6.1 de "no unir IFM con EMS-2" queda **confirmada**.

### Hipótesis que se caen o se corrigen

- **"~100 ms"**: los datos reales van a **~1 Hz con huecos** → ajustar el replay y los umbrales. Ventaja: el volumen baja 10 veces.
- **Altitud, pendiente, temperatura ambiente, carga/peso, DTC y % de tanque: no están** en EMS-2. Las explicaciones del tipo "pendiente pronunciada" o la segmentación "por carga" de la §8 **no se pueden sostener con FEAD**. Habría que enriquecer la altitud desde lat/lon con un DEM externo, o eliminar esos factores.
- **Las unidades del diccionario y del paper no son fiables:** x7000 son rpm; x7004 es velocidad; x7005 está en km; x7006 parece crudo 0-250; x7007 es dudosa. **El mapeo a `TelemetryEvent` debe usar las unidades corregidas** de la sección 2.2.
- **Licencia:** no hay. **No redistribuir** el dataset ni incluirlo en un repo o imagen pública. Descargarlo en tiempo de setup y **anonimizar** matrícula, IMEI y dirección.
- Geografía: China (Heilongjiang → Guangdong) y textos en chino. Hace falta transliterar o traducir `r_level` y no presentarlo como Perú (ya previsto).
- Volumen: el archivo pesa 1,5 GB comprimido y ~20-25 GB descomprimido. Hay que leerlo en streaming con `tarfile` en modo `r|gz` y **sub-seleccionar unos pocos camiones y días** para el demo. No cargar los 26 M de filas.

### Recomendación

1. **Mantener FEAD EMS-2 como fuente P0**, usando un subconjunto: por ejemplo 3-5 camiones y 2-3 días, extraídos del prefijo de 60 MB, que ya trae día y medio de 28 camiones (unos 1,6 M filas).
   - Fijar el checksum del `.gz` y documentar el procedimiento de Range y streaming.
2. **Definir la detección de anomalías con dos señales:**
   - **(a)** residuo de x7001 frente a un modelo por camión basado en rpm, acelerador y par (sensor virtual, R² esperado ~0,9).
   - **(b)** L/100 km por tramo (x7002/x7005) frente a la mediana del camión, segmentada por categoría de vía y velocidad.
   - Reportar MAE/RMSE, hacer splits temporales y por camión, y añadir un baseline ingenuo.
3. Para el demo, inyectar anomalías sintéticas etiquetadas (fuga, ralentí prolongado, robo con caída de x7002 fuera de ruta) sobre el replay, marcadas como `synthetic_demo`, porque el dataset **no trae etiquetas de anomalía**.

### Plan B, si el dataset no sirve (descarga caída o rechazo por licencia o geografía)

- **IFM de FEAD (61 MB):** un camión, unas 2,4 h, con peso, DTC, aceleraciones y doble etiqueta de consumo. Sirve como demo de "sensor de alta fidelidad", pero no como flota.
- **Dataset VT (Wang & Rakha 2017), ya incluido en el repo** (`VT-Dataset/veh00{1,2,3}_all.csv`, ~8 MB): tres camiones con velocidad, rpm, **elevación** y fuel en g/s ([P] p.6 Tabla VIII). Se descarga sin coste, pero tampoco tiene licencia explícita.
- **Generador sintético calibrado** con las distribuciones medidas en [S] (rpm mediana 1069, x7001 mediana 21,6 L/h, unos 33 L/100 km). Siempre etiquetado `synthetic_demo`.

## Artefactos locales (fuera del repo, no versionados)

- `/tmp/fead-src/repo`: clon del repo.
- `/tmp/fead-paper/liu23.pdf` y `liu23.txt`: el paper y su texto extraído.
- `/tmp/fead-sample/ems2_head.gz`: prefijo de 60 MB de EMS-2. Su descompresión es `/tmp/fead-sample/ems2_head.raw`, de 938 MB.
- `/tmp/fead-sample/ifm/IFM-Dataset.zip`: el IFM completo.
- `/tmp/fead-scripts/`: scripts de perfilado y su salida.
