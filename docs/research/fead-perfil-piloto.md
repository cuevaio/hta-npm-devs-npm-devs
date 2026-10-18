# FEAD EMS dataset-2: perfil de piloto (operación, geografía y consumo)

Fecha: 2026-10-18. Complementa `docs/research/fead-ems-dataset2-perfil.md`, que contiene el diccionario de columnas y las correcciones de unidades, y `docs/product/PRODUCT_CONTEXT_CERTERA.md` §6 y §8.

**Objetivo:** describir con los datos reales qué tipo de operación representa la flota, calcular métricas por camión y para la flota, y elegir camiones y ventanas para la demo de consumo anómalo.

## 0. Datos, método y convenciones

### Muestra analizada

Son dos peticiones HTTP Range consecutivas sobre el `.gz` público de 1 506 792 176 B:

| Tramo de bytes | Archivo local | SHA-256 |
|---|---|---|
| 0 – 62 914 559 | `/tmp/fead-sample/ems2_head.gz` | `b9dbb26e…be56` |
| 62 914 560 – 629 145 599 | `/tmp/fead-dl/part2.gz` | `bb093be1…530e` |

- En total son **600 MB comprimidos, el 40 % del archivo**.
- El tar contiene los miembros `ems_yingche_20200401.txt` a `…0409.txt`.
- El miembro del día 9 está truncado y, como las filas **no vienen ordenadas por tiempo** dentro de cada miembro, solo trae un submuestreo disperso de ese día. Por eso **se excluye el 2020-04-09** y el análisis cubre **8 días completos: del 2020-04-01 al 2020-04-08**.
- Filas usadas: **10 797 227**, de **28 camiones** [A].
  - Aparece un camión 29 con 472 filas (8 min, el 04-01). Se excluye de todas las métricas. El total de 29 coincide con el README y el paper.

### Anonimización

- Los camiones se etiquetan **T01..T28** por número de filas descendente.
- La tabla hash→alias vive solo en `/tmp/fead-pilot-work/anon_map_PRIVATE.json` (copia persistente en `~/Projects/fead/work/`, fuera del repo) y **no está en el repo**.
- No se publican matrículas, IMEI, `truckid` ni direcciones.
- De la matrícula solo uso el carácter de provincia.
- El `orgcode` se renombra O1/O2/O3.
- La geografía se reporta a nivel de provincia o ciudad (prefectura).

### Unidades

Siguen las correcciones del informe previo:

| Señal | Clave | Unidad corregida |
|---|---|---|
| rpm | `x7000` | rpm |
| Consumo instantáneo | `x7001` | L/h |
| Consumo acumulado | `x7002` | L, con resolución de 0,5 L |
| Velocidad | `x7004` | km/h (de facto) |
| Odómetro | `x7005` | km |
| Acelerador | `x7006` | crudo, 0–250 |
| Carga o par motor | `x704F` | % |

### Definiciones operativas (todas en `analyze.py`)

- **Peso temporal de una fila:** `dt = min(t_siguiente − t, 10 s)`. Solo hay filas con el motor encendido: la rpm mínima es 403, así que "horas de motor" equivale a tiempo con filas.
- **Detenido o ralentí:** `x7004 ≤ 1` y GPS `≤ 3` km/h (o nulo), con el motor encendido.
- **En movimiento:** `x7004 > 3`.
- **Parada:** intervalo de **10 min o más** entre dos muestras en movimiento. Incluye los huecos sin filas, que corresponden a motor apagado.
- **Parada larga o terminal:** parada de **3 h o más**.
- **Distancia y consumo:**
  - km = ∫`x7004`·dt, solo en huecos ≤ 60 s.
  - L = ∫`x7001`·dt.
  - L/100 km = L / km.
  - Contraste: Δ`x7002`/Δ`x7005` en pares consecutivos válidos (columna `L100_odo`).
- **Tramos de consumo:** bloques contiguos de 20 km (gap ≤ 60 s) con L/100 km, velocidad, acelerador y carga medios.
- **Hora:** `ems_time` tal como se publica, sin zona horaria. **Se asume la hora de China, UTC+8 [I].**

### Convención de citas

| Código | Script | Salida |
|---|---|---|
| [X] | `/tmp/fead-pilot-scripts/extract.py` | tsv compactos por camión en `/tmp/fead-pilot-work/trucks/` (solo el prefijo de 2 caracteres de la matrícula) |
| [A] | `/tmp/fead-pilot-scripts/analyze.py` | `/tmp/fead-pilot-work/fleet.json`, con métricas por camión |
| [Σ] | `/tmp/fead-pilot-scripts/summarize.py` | `/tmp/fead-pilot-work/summary.txt` |
| [G] | `/tmp/fead-pilot-scripts/fleetagg.py` | `/tmp/fead-pilot-work/fleetagg_out.txt`: agregados, grupos, paradas, O-D, candidatos |
| [C] | `/tmp/fead-pilot-scripts/corridors.py` | `/tmp/fead-pilot-work/corridors_out.txt`: tramos de viaje, pares, tramos de montaña, motor, ralentí |
| [Q] | `/tmp/fead-pilot-scripts/dq.py` | `/tmp/fead-pilot-work/dq_out.txt`: calidad de odómetro y carga |

Todo se ejecutó con `python3 -I` desde `/tmp/fead-pilot-scripts/`, solo con la biblioteca estándar, sin ejecutar nada de los directorios de datos.

Cada afirmación lleva una etiqueta: **[D] = dato medido**; **[I] = inferencia**, ya sea razonamiento o conocimiento externo no verificado con este dataset.

---

## 1. Resumen ejecutivo

| Métrica (28 camiones, 04-01..04-08) | Valor | Fuente |
|---|---|---|
| Distancia total / combustible total | **205 347 km / 66 661 L** | [G] línea `[FLOTA]` |
| **L/100 km de la flota (ΣL/Σkm)** | **32,5** | [G] |
| L/100 km por camión: mediana (P25–P75), rango, CV | **32,9** (31,1–33,4), 27,6–42,3, CV 9,5 % | [G] |
| km por camión y día de calendario (GPS haversine), mediana | **951** (P10 520, P90 1 125) | [G] |
| km por día **activo** (días con ≥ 200 km), mediana | **1 206** | [G] |
| Horas de motor por camión y día, mediana | **13,9 h** | [G] |
| Tiempo en movimiento sobre tiempo de motor, mediana | ~92 % | [Σ] columna `mov%` |
| Ralentí (% del tiempo de motor), mediana | **6,9 %** (4,0–16,7 %) | [G] |
| Consumo en ralentí, mediana por camión | **2,1 L/h** | [G] |
| Combustible quemado en ralentí sobre el total | **0,8 %** (520 L) | [G] |
| Velocidad en movimiento: mediana / P90 | **81 / ~92 km/h** | [G], [Σ] |
| Tiempo en movimiento por encima de 60 km/h | **83,6 %** | [G] `speed bins` |
| Tiempo de motor entre 22:00 y 06:00 | **30,3 %** (33,3 % si fuera uniforme) | [G] `hour-of-day` |
| Paradas ≥ 10 min por camión y día | **5,0**; mediana de 31 min y P90 de 312 min | [G] `stops` |
| Tramos terminal→terminal típicos | 1 280–3 500 km, en 19–56 h | [C] `TRIP LEGS` |

**Perfil [I, sustentado en datos]:** la flota hace **transporte troncal de larga distancia interprovincial ("line-haul") con tractocamiones pesados**.

- Opera punto a punto entre pocos hubs terminales a 1 300–3 500 km de distancia.
- Funciona prácticamente 24/7 en relevo, con todo indicando dos conductores.
- Circula casi siempre por autopista a 80–90 km/h y consume ~32 L/100 km.

**No es** distribución urbana, minería ni logística portuaria (ver §6).

---

## 2. Geografía

### 2.1 Cobertura

- Bounding box de la flota [D, código ad hoc sobre `fleet.json`, campo `bbox`]: lat **22,7°–46,0° N**, lon **103,0°–126,8° E**. Es casi toda la China oriental, de Heilongjiang a Guangdong y de Yunnan a Jiangsu.
- La flota pasa por 23 provincias.

Reparto del tiempo de motor por provincia [D, `provinces_h` sumado]:

| Provincia | % del tiempo de motor |
|---|---|
| Hunan | 15,1 |
| Guangdong | 13,1 |
| Henan | 10,2 |
| Hebei | 8,1 |
| Liaoning | 7,8 |
| Guizhou | 6,1 |
| Hubei | 6,1 |
| Jiangsu | 5,5 |
| Anhui | 5,1 |
| Jilin | 3,6 |
| Shaanxi | 3,2 |
| Yunnan | 2,6 |
| Chongqing | 2,5 |
| Heilongjiang | 2,3 |
| Resto | < 2 cada una |

Hunan y Henan pesan mucho porque son provincias **de paso** en el eje norte-sur. No son destinos.

### 2.2 Rutas recurrentes: clusters de paradas largas

Método [G] y [C]:
1. Tomar las paradas de 3 h o más, agrupadas por ciudad (prefectura).
2. Para cada camión, emparejar paradas largas consecutivas en ciudades distintas.
3. Medir la distancia del tramo como ∫velocidad entre el fin de una parada y el inicio de la siguiente.

Ciudades con más paradas de 3 h o más (candidatas a terminal) [D, G]:

| Ciudad | Paradas ≥ 3 h |
|---|---|
| Guangzhou | 41 |
| Wuxi | 37 |
| Harbin | 19 |
| Dongguan | 19 |
| Changchun | 14 |
| Kunming | 14 |
| Chengdu | 10 |
| Xianyang (área de Xi'an) | 8 |

Corredores recurrentes [D, C `TRIP LEGS` y `PEER COMPARISON`; G `recurrent O-D`]:

| Corredor (ida y vuelta) | Camiones | km por tramo (mediana) | h por tramo (mediana) | km/h medios, con paradas cortas |
|---|---|---|---|---|
| **Harbin ⇄ Guangzhou** | T01, T02, T03, T04, T07, T08 | 3 506 (G→H) / 3 422 (H→G) | 51 / 56 | 68 / 61 |
| **Changchun ⇄ Guangzhou** | T05, T16, T17, T18, T19 | 3 185 / 3 171 | 49 / 50 | 65 / 64 |
| **Wuxi ⇄ Kunming** | T06, T12, T14, T15 | 2 286 / 2 285 | 36 / 34 | 63 / 67 |
| **Wuxi ⇄ Xianyang** | T09, T20, T21 | 1 283 / 1 287 | 20 / 23 | 66 / 56 |
| **Dongguan ⇄ Chengdu** | T23, T24, T25, T28 | 1 852 / 1 828 | 33 / 30 | 57 / 61 |
| Harbin ⇄ Shanghai/Hangzhou | T10 | 2 317–2 603 | 37–43 | 60–66 |
| Guangzhou ⇄ Qingdao | T11 | 2 004–2 119 | 31–37 | 57–65 |
| Guangzhou ⇄ Xianyang | T13 | ~1 760 | 28 | 61–64 |
| Dongguan/Foshan ⇄ Kunming | T22, T26 | 1 493–1 708 | 30–34 | 49–53 |
| Guangzhou/Dongguan ⇄ Zhuzhou/Xiangtan/Changsha (regional) | T27 | 590–866 | 10–16 | 52–61 |

- La **repetibilidad** es alta [D]: el mismo corredor da ±1–2 % de km entre camiones. Por ejemplo, Changchun→Guangzhou mide entre 3 174 y 3 193 km en 5 camiones.
- Esto encaja con el "route matching" del paper. En la práctica, cada corredor es un **tramo comparable entre pares**.

### 2.3 ¿Urbano o carretera?

- La columna `r_level`, geocodificada por Tencent, asigna a los km de camiones con odómetro válido [D, G]:

| Categoría `r_level` | % de km |
|---|---|
| "otras vías" | 45,3 |
| autopista (高速) | 32,5 |
| camino rural o municipal | 12,3 |
| condado | 3,8 |
| provincial | 3,0 |
| nacional | 2,8 |
| vía rápida urbana | 0,0 |

- **La etiqueta no es fiable para separar urbano de carretera.** Los tramos de 20 km etiquetados "otras vías" tienen una velocidad media mediana de **81,3 km/h**, frente a 79,7 km/h en los de "autopista" [D, Q, última línea].
- **Clasificación por velocidad** [D, G]:
  - Solo el **6,3 %** del tiempo en movimiento transcurre a 3–30 km/h, y el 10,1 % a 30–60 km/h.
  - El **83,6 %** transcurre por encima de 60 km/h.
- **Conclusión [I]:** la operación es de **carretera e interurbana**. El componente urbano se limita a la entrada y salida de los terminales.
- Recomendación para el producto: derivar "urbano o carretera" de la velocidad, o de un mapa externo, y no de `r_level`.

---

## 3. Operación

### 3.1 Por camión

Los valores salen de [G] (primera tabla) y [Σ]. La distancia y el tiempo se reparten entre 8 días de calendario.

| T | Org | Prov. matrícula | km/día | h motor/día | % ralentí | L/h ralentí (med) | % noche (22–06) | v. mediana en mov. | L/100 km | L/100 (odo) | Días ≥ 200 km |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T01 | O1 | Heilongjiang | 1 269 | 17,7 | 5,8 | 1,6 | 33,1 | 82 | 32,1 | 32,7 | 8 |
| T02 | O1 | Heilongjiang | 1 153 | 16,6 | 6,4 | 1,6 | 34,6 | 80 | 33,0 | 33,6 | 8 |
| T03 | O1 | Heilongjiang | 1 285 | 17,4 | 6,7 | 1,85 | 33,4 | 85 | **35,2** | 35,8 | 8 |
| T04 | O1 | Heilongjiang | 925 | 16,2 | 10,2 | 1,8 | 30,0 | 81 | 33,2 | 33,7 | 6 |
| T05 | O1 | Heilongjiang | 1 066 | 16,6 | 4,1 | 2,1 | 33,6 | 80 | 31,8 | 32,4 | 7 |
| T06 | O1 | Heilongjiang | 1 113 | 15,4 | 4,0 | 2,8 | 34,0 | 81 | 33,2 | 33,8 | 8 |
| T07 | O1 | Heilongjiang | 1 078 | 15,0 | 6,7 | 1,85 | 34,6 | 83 | **35,2** | 35,8 | 7 |
| T08 | O1 | Heilongjiang | 1 110 | 14,7 | 4,5 | 2,2 | 32,7 | 87 | 32,9 | 33,4 | 6 |
| T09 | O1 | Heilongjiang | 985 | 15,2 | 7,7 | 2,0 | 24,9 | 78 | **27,6** | 28,0 | 8 |
| T10 | O1 | Heilongjiang | 952 | 14,2 | 7,0 | 1,75 | 29,8 | 80 | 31,5 | 32,1 | 6 |
| T11 | O2 | Guangdong | 996 | 14,5 | 4,4 | 1,9 | 27,5 | 82 | 28,2 | 28,3* | 8 |
| T12 | O1 | Heilongjiang | 891 | 14,2 | 10,6 | 1,75 | 29,1 | 83 | 32,5 | 33,1 | 6 |
| T13 | O2 | Guangdong | 958 | 13,8 | 4,8 | 1,95 | 35,8 | 81 | 29,1 | 27,9* | 7 |
| T14 | O1 | Heilongjiang | 1 051 | 14,1 | 4,9 | 2,55 | 30,7 | 83 | 33,3 | 33,8 | 7 |
| T15 | O1 | Heilongjiang | 966 | 13,5 | 5,0 | 2,5 | 37,2 | 81 | 32,9 | 33,5 | 7 |
| T16 | O1 | Heilongjiang | 994 | 14,0 | 4,4 | 2,5 | 30,4 | 82 | 31,4 | 32,0 | 5 |
| T17 | O1 | Heilongjiang | 938 | 13,1 | 6,4 | 1,8 | 30,6 | 83 | 33,0 | 33,6 | 6 |
| T18 | O1 | Heilongjiang | 950 | 12,9 | 4,6 | 1,95 | 27,7 | 83 | 32,9 | 33,5 | 6 |
| T19 | O1 | Heilongjiang | 793 | 12,6 | 10,3 | 2,3 | 31,5 | 77 | 29,6 | 30,2 | 5 |
| T20 | O1 | Heilongjiang | 815 | 12,2 | 9,3 | 2,35 | 24,6 | 81 | 30,1 | 30,7 | 5 |
| T21 | O1 | Heilongjiang | 807 | 12,2 | 7,8 | 2,1 | 18,7 | 80 | 29,1 | 29,6 | 5 |
| T22 | O2 | Guangdong | 671 | 12,3 | 13,5 | 2,1 | 31,2 | 73 | 33,1 | 33,4* | 6 |
| T23 | O3 | Fujian | 639 | 12,0 | 8,9 | 2,0 | 29,5 | 67 | 33,5 | 31,9 | 5 |
| T24 | O3 | Fujian | 581 | 10,8 | 10,4 | 2,2 | 27,8 | 68 | 37,5 | 35,7 | 6 |
| T25 | O3 | Fujian | 519 | 9,7 | 10,6 | 2,25 | 25,0 | 68 | 38,5 | 36,8 | 5 |
| T26 | O2 | Guangdong | 520 | 8,9 | **14,6** | 2,2 | 26,6 | 78 | 34,5 | 34,3* | 4 |
| T27 | O2 | Guangdong | 440 | 8,1 | **16,7** | 2,05 | 16,0 | 83 | 29,1 | 28,9* | 5 |
| T28 | O3 | Fujian | 476 | 7,8 | 8,5 | 2,2 | 35,9 | 74 | **42,3** | 40,2 | 4 (datos desde 04-03 18:02) |

\* En O2 el odómetro `x7005` tiene **resolución de 1 km** y le falta el 2,4–5,4 % de las filas. T13 además alterna saltos de +4,9 y −4,8 km, lo que sugiere dos fuentes intercaladas, y **no trae `x704F`** (carga) [D, Q]. Para estos camiones, la cifra válida es la de L/100 por integración de velocidad.

### 3.2 Turnos y ciclo de trabajo

- **Operación 24 h [D]:** el tiempo de motor por hora del día es casi plano. Va del **3,5 %** (00–01 h) al **4,8 %** (11–12 h), y el tramo de 22:00 a 06:00 concentra el **30,3 %** [G].
- **Relevo de conductores [I]:** los tramos de 3 400–3 500 km se hacen en **48–56 h**, con paradas intermedias de mediana 31 min [C, G]. Los días activos acumulan 18–23 h de motor, como T03 el 04-08 (23,2 h y 1 835 km) [Σ]. Eso no es compatible con un único conductor, y la explicación probable es una tripulación doble. El dataset no tiene datos de conductor.
- **Ciclo típico de O1 [D, C `per-truck sequence`]:**
  1. Unas 50 h de marcha.
  2. Parada larga de 8–18 h en el terminal (carga o descarga y descanso).
  3. Unas 50 h de regreso.
  - Por eso hay días de 1 400–1 800 km alternados con días de 150–400 km [Σ, PER-DAY].
- **Paradas ≥ 10 min [D, G]:** 1 113 paradas, 5,0 por camión y día.

| Duración | Nº | % del tiempo parado | % de esa parada con motor encendido |
|---|---|---|---|
| 10–30 min | 541 | 7,4 | 24 |
| 30–60 min | 207 | 6,6 | 16 |
| 1–3 h | 182 | 14,5 | 7 |
| 3–8 h | 109 | 24,0 | 4 |
| ≥ 8 h | 74 | 47,6 | 2,6 |

- **Implicación [D]:** en las paradas, el motor está apagado el **94 %** del tiempo (solo el 6,1 % del tiempo parado tiene filas). El ralentí prolongado es raro en esta flota (§5.2).

### 3.3 Velocidad

- Distribución del tiempo en movimiento, media de los camiones [D, G]:

| Banda | % del tiempo |
|---|---|
| 3–30 km/h | 6,3 |
| 30–60 km/h | 10,1 |
| 60–80 km/h | 36,2 |
| 80–90 km/h | 33,6 |
| > 90 km/h | 13,8 |

- O3 (Fujian, corredor Chengdu–Dongguan por Chongqing y Guizhou) es más lento: su mediana es de **67–74 km/h**, frente a 80–87 del resto [D, tabla §3.1]. Es coherente con un trazado más montañoso [I].

---

## 4. Consumo

### 4.1 Nivel y dispersión

- **Flota [D, G]:** **32,5 L/100 km** (ΣL/Σkm). La mediana por camión es **32,9**, con P25–P75 entre 31,1 y 33,4.
- **Coherencia entre métodos [D]:**
  - El L/100 por ∫`x7001`/∫velocidad difiere entre −1,4 y +1,9 L/100 km del método Δ`x7002`/Δ`x7005` (columnas `L100` y `L100_odo`, §3.1).
  - El odómetro concuerda con la velocidad integrada (`odo_valid` exige una relación de 0,95–1,05; la cumplen 23 de 28 camiones).
- **Por organización [D, G]:**

| Org | Camiones | L/100 km | CV entre camiones |
|---|---|---|---|
| O1 | 19 | 32,3 | **5,9 %** |
| O2 | 5 | 30,4 | 8,2 % |
| O3 | 4 | 37,6 | 8,3 % |

- **Outliers de flota** (Tukey, 1,5 × IQR) [D, G]:
  - Por debajo: **T09 (27,6)**.
  - Por encima: **T24 (37,5), T25 (38,5) y T28 (42,3)**.
  - Los altos son los tres de O3 en el corredor montañoso Dongguan–Chengdu: en parte es **efecto de ruta**, no de vehículo [I].
- **Comparación entre pares del mismo corredor** [D, C `PEER COMPARISON`]. Es la métrica relevante para la detección:

| Corredor | Mediana L/100 | Desvíos notables frente a la mediana |
|---|---|---|
| Harbin–Guangzhou | 33,1 | **T03 +6,3 %**, **T07 +6,3 %**, T01 −3,0 % |
| Changchun–Guangzhou | 31,8 | T17 +3,8 %, **T19 −6,9 %** |
| Wuxi–Kunming | 33,05 | todos dentro de ±1,7 % |
| Wuxi–Xianyang | 29,1 | T09 −5,2 %, T20 +3,4 % |
| Dongguan–Chengdu | 38,0 | **T28 +11,3 %**, **T23 −11,8 %** |

### 4.2 Ralentí

- **L/h en ralentí [D, G y §3.1]:** mediana de **2,1 L/h**, con un rango por camión de 1,6–2,8 L/h, a unas 700 rpm. Las rpm de ralentí de O2 y O3 son 550–600.
- **Peso del ralentí [D, G]:** el ralentí ocupa el **6,9 %** del tiempo de motor (mediana) y consume solo el **0,8 %** del combustible: 520 L de 66 661.
  - En esta flota, el ralentí es una palanca de ahorro pequeña.
  - Los camiones de O2 con más ralentí (T26 14,6 %, T27 16,7 %) llegan al 1,1 %.

### 4.3 Dónde se concentra el consumo alto: efecto de pendiente

Método: 9 848 tramos de 20 km [C].

- Solo el **4,3 %** supera 1,5 veces la mediana de su camión [D].
- Esos tramos se concentran en las ciudades de **Chenzhou y Zhuzhou (Hunan), Shaoguan y Qingyuan (Guangdong), Chongqing, Anshun, Tongren y Qianxinan (Guizhou) y Xi'an (Shaanxi)** [D, C `where`].

**Asimetría direccional, misma vía y mismos camiones** [D, C `DIRECTIONAL SECTIONS`]:

| Tramo | n | L/100 mediana | Acelerador crudo | Carga `x704F` | v. media |
|---|---|---|---|---|---|
| Shaoguan → Chenzhou (Nanling, hacia el norte) | 17 | **79,7** | 185 | 80 % | 64 km/h |
| Chenzhou → Shaoguan (hacia el sur) | 14 | **10,8** | 28 | 13 % | 74 km/h |
| Xi'an → Shangluo (Qinling, hacia el SE) | 10 | **64,0** | 154 | 76 % | 66 km/h |
| Shangluo → Xi'an | 11 | 49,5 | 127 | 65 % | 67 km/h |

- **Interpretación [I]:** el cruce de las montañas de Nanling en el corredor Pekín–Cantón (G4) tiene una subida neta hacia el norte. Una relación de 7:1 entre sentidos, con el acelerador a fondo y menor velocidad, es la firma de una **pendiente sostenida**.
- El dataset **no trae altitud**, así que la pendiente es una inferencia geográfica. Para afirmarla en el producto hay que enriquecer los datos con un modelo de elevación externo (DEM).
- **Consecuencia de diseño [I]:** un umbral "L/100 frente a la mediana del camión" marcaría como anómalos los 13 camiones que suben Nanling. La línea base tiene que ser **por tramo y sentido**, comparando con los pares que hacen ese mismo tramo (el route matching del paper), o incluir la pendiente.

---

## 5. Tipo de vehículo y carga (inferible)

- **Matrícula, solo provincia [D, A `plate_prov`]:**
  - O1: 19 camiones de **Heilongjiang**, con letra de ciudad A (Harbin).
  - O2: 5 de **Guangdong**, con letra A (Guangzhou).
  - O3: 4 de **Fujian**.
  - Cada `orgcode` se corresponde con una sola provincia de matrícula, lo que sugiere 3 empresas o filiales [I].
- **Firma del motor [D, C `ENGINE`]:**
  - rpm a 80 km/h: ~1 000 (T06 y T10 están en ~1 258, posiblemente con otra relación de transmisión [I]).
  - rpm p99,9: 1 400–1 900. Máximo absoluto: 2 219 [Σ].
  - `x7001` p99,9: mediana de 72,9 L/h; máximo de 95 L/h (T28).
- **Potencia implícita [I]:** 72,9 L/h × 0,835 kg/L ÷ 0,205 kg/kWh da **~300 kW (~400 CV)**, con un rango por camión de ~240–370 kW. Asume un consumo específico de 205 g/kWh, que es un supuesto externo. Encaja con motores diésel de 10–13 L de **tractocamión pesado**.
- **Consumo de ~32 L/100 km a ~80 km/h [D]:** coherente con un tractocamión y semirremolque cargado [I, referencia externa no verificada en este dataset].
- **Carga [D, Σ]:** el par o carga del motor `x704F` tiene mediana del 27–45 % y P90 del 68–99 %. **No hay peso** en EMS-2, así que la carga transportada (lleno o vacío, tipo de mercancía) **no se puede inferir con fiabilidad**.
  - T09 (27,6 L/100 km, carga mediana del 33 %) podría circular más ligero, pero esto es especulativo [I].
- **Tipo de mercancía:** desconocido. Los terminales están en grandes nodos logísticos e industriales del interior (Harbin, Changchun, Wuxi, Kunming, Chengdu, Xi'an) y del delta del río Perla (Guangzhou, Dongguan).
  - Encaja con carga general, de paquetería troncal o de autopartes, sin poder distinguir entre ellas [I].
  - **No presentar ningún tipo de mercancía como dato.**

---

## 6. Conclusión: ¿qué operación representa la flota?

**Transporte troncal de carga por carretera, de larga distancia e interprovincial (line-haul punto a punto), con tractocamiones pesados en relevo 24/7.**

| Hipótesis | Veredicto | Evidencia |
|---|---|---|
| **Larga distancia interurbana / troncal** | **Sí** | [D] Tramos de 1 280–3 500 km entre terminales fijos; 1 206 km por día activo; 84 % del tiempo en movimiento a más de 60 km/h; mediana de 81 km/h; 5 paradas por día; 30 % del motor de noche. [I] Tripulación doble |
| Distribución regional | Parcial y minoritaria | [D] T27 (tramos de 590–866 km, 16,7 % de ralentí) y los recorridos de O3 dentro de Guangdong (Dongguan–Huizhou–Qingyuan, 114–409 km a 25–37 km/h) |
| Distribución urbana / última milla | **No** | [D] Solo el 6,3 % del tiempo en movimiento por debajo de 30 km/h |
| Logística portuaria | **No** como perfil | [D] Los terminales dominantes están en el interior. Qingdao y Shanghai aparecen, pero son marginales (≤ 1 % del tiempo) |
| Minería | **No** | [D] Velocidades de autopista, ningún patrón de ciclos cortos de carga y descarga; bbox continental en vías pavimentadas |

---

## 7. Candidatos para la demo

Criterios de selección:
- Cobertura de 5 días o más con 12 h de datos o más [G `days>=12h`].
- Un episodio concreto y verificable.
- Al menos un camión de control.

Las ventanas usan `ems_time` (asumido UTC+8). Todas las cifras salen de [C], [G] y [Σ].

| # | Camión | Corredor | Por qué | Ventana sugerida | Cifras |
|---|---|---|---|---|---|
| 1 | **T03** | Harbin ⇄ Guangzhou | **Sobreconsumo frente a sus pares** más un **ralentí largo** | Ralentí: **04-04 01:53–02:46** (Harbin), al final de una parada de terminal de 17,8 h que empezó el 04-03 09:45, justo antes de salir hacia Guangzhou. Viaje: salida hacia las 04-04 03:30, llegada al terminal de Guangzhou el 04-06 11:43 (3 401 km, 56 h) | +6,3 % frente a la mediana del corredor (35,2 contra 33,1 L/100). Ralentí de 53,3 min, 3,14 L, 3,5 L/h a 700 rpm (1,7 veces la mediana de flota de 2,1 L/h). 7 días con ≥ 12 h |
| 2 | **T04** | Harbin ⇄ Guangzhou | **Ralentí acelerado** (rpm alta parado) | **04-07 19:39–20:09** (Harbin) | 30,7 min a **1 293 rpm** de media, **5,9 L/h**: 2,8 veces la mediana de ralentí de la flota. Causa desconocida (calentamiento, toma de fuerza, cabina) [I] |
| 3 | **T28** | Dongguan ⇄ Chengdu | **Outlier de flota** | Día **04-07** completo (22 h, 1 583 km GPS); tramo pico **04-07 08:30–08:48** (Chongqing, 90,5 L/100) | 42,3 L/100: +11,3 % frente a sus pares del corredor y el máximo de la flota. Cobertura solo desde 04-03 18:02 (3 días con ≥ 12 h) |
| 4 | **T22** | Kunming ⇄ Dongguan | **Ralentí prolongado repetido** más un caso de **calidad de datos** | **04-05 17:56–19:15** (Kunming); también 04-01 08:13 (39,6 min) y 04-07 18:12 en Dongguan (46,5 min) | 78,2 min, 3,08 L, 2,4 L/h. Ralentí del 13,5 % del tiempo de motor (el doble de la mediana). Odómetro a 1 km/paso: sirve para mostrar el fallback a velocidad integrada |
| 5 | **T09** (control) | Wuxi ⇄ Xianyang | **Camión eficiente** y caso de falso positivo evitado | Subida de Qinling **04-02 07:45–08:06** (Xi'an → Shangluo) | 27,6 L/100, el más bajo de la flota; 8 de 8 días activos. Su tramo a 67,5 L/100 está en la norma del tramo (mediana de 64,0) → **no** es una anomalía |

**Escenario adicional** de "falso positivo evitado": **T07 el 04-08 de 06:49 a 07:06**, subiendo Nanling hacia el norte. Consume 82,2 L/100, 2,4 veces su mediana, pero la mediana de ese tramo en ese sentido entre 13 camiones es 79,7. Con una línea base por tramo **no se alerta**; con una por camión, sí. Ilustra el diferenciador del producto: explicar en contexto.

**Advertencia:** los episodios son reales, pero **no hay etiquetas de anomalía**. Llamarlos "sobreconsumo" es una regla nuestra, no la verdad de terreno. Las anomalías inyectadas siguen siendo `synthetic_demo`, como dice el informe previo.

---

## 8. Cómo narrarlo ante un jurado peruano (sin atribuir los datos a Perú)

### Lo que se dice

> "La telemetría de motor y GPS es **real**: 28 tractocamiones de una flota de carga en **China**, abril de 2020, del dataset académico FEAD (Liu et al., IEEE T-ITS 2023). La **reproducimos como si llegara en vivo**. Los fletes, los conductores, los mensajes de WhatsApp y los nombres de los camiones son **sintéticos** y están marcados como tales."

### Por qué esta flota es relevante para Perú (analogía, no equivalencia)

Las analogías son inferencias de producto y no deben presentarse como datos:
- El perfil, troncal de larga distancia con tractocamión pesado, relevo y ~1 200 km por día activo, se parece al transporte por la **Panamericana Norte y Sur**, por ejemplo Lima–Piura o Lima–Arequipa.
- El efecto de pendiente de Nanling (79,7 frente a 10,8 L/100 según el sentido) es la versión "suave" de lo que pasaría en la **Carretera Central**.
- No hay que afirmar que las cifras se trasladan: los Andes superan los 4 000 m y la flota de FEAD no.

### Estructura sugerida

1. **"Una flota real"**: un mapa con los 5 corredores, rotulado "China, datos FEAD", con alias CAM-01..CAM-05 y sin matrículas.
2. **"Línea base inteligente"**: el caso de T07 en Nanling. Alerta ingenua frente a línea base por tramo; muestra que el sistema **no** alerta en una subida normal.
3. **"Anomalía real frente a pares"**: T03 o T28, que consumen 6–11 % más que sus pares en el mismo corredor. Alerta por WhatsApp con la evidencia (litros, km, ventana y procedencia `fead_observed`).
4. **"Ralentí"**: T04, con 5,9 L/h a 1 293 rpm detenido. El conductor responde por WhatsApp (mensaje **sintético**) y el sistema reclasifica el evento.
5. **"Mañana en Perú"**: los mismos `TelemetryProvider` con Samsara, Global GPS o un gateway J1939.

### Lo que **no** hay que hacer

- No reproyectar las trayectorias chinas sobre carreteras peruanas presentándolas como reales.
- Si se quiere un mapa de Perú, debe ir rotulado "**escenario simulado**", con un perfil de consumo derivado de FEAD.
- No convertir litros a soles peruanos como ahorro "observado".
- No mencionar matrículas, IMEI ni direcciones; tampoco atribuir una empresa o un tipo de mercancía.

---

## 9. Limitaciones

- **Cobertura:** 8 de unos 19–20 días. El rango completo del archivo sigue **sin verificar**. Al descargar el 40 % del archivo se llega al 09-abr, así que el total probablemente ronda el 19–20 de abril [I]. Puede haber variación semanal no capturada.
- **Hora local:** el UTC+8 es un supuesto. El perfil horario es casi plano, así que el supuesto afecta poco.
- **Paradas:** "parada" incluye los huecos sin filas. No se distingue entre motor apagado y pérdida de cobertura del dispositivo.
- **Ralentí:** usa `x7004 ≤ 1` con GPS `≤ 3`. Algunos episodios largos pueden partirse si hay huecos de más de 120 s.
- **Tramos de 20 km:** el L/100 en ventanas cortas está sujeto a la latencia de `x7001` y, si se usara `x7002`, a la cuantización de 0,5 L (~±3,5 % por tramo). Por eso los tramos usan la integral de `x7001`.
- **Errores de sensor:** `x7001` tiene un error de ±6 % según el paper. Es una lectura del ECU, no de un caudalímetro.

## 10. Reproducción

```bash
mkdir -p /tmp/fead-dl && curl -L -r 62914560-629145599 -o /tmp/fead-dl/part2.gz \
  "https://drive.usercontent.google.com/download?id=15Awwj26PE0MIGRUW1CiCO2xkP3j8-z2o&export=download&confirm=t"
cd /tmp/fead-pilot-scripts
python3 -I extract.py /tmp/fead-pilot-work/trucks /tmp/fead-sample/ems2_head.gz /tmp/fead-dl/part2.gz   # ~4 min
python3 -I analyze.py /tmp/fead-pilot-work/trucks /tmp/fead-pilot-work/fleet.json                        # ~5 min
python3 -I summarize.py  /tmp/fead-pilot-work/fleet.json > /tmp/fead-pilot-work/summary.txt
python3 -I fleetagg.py   /tmp/fead-pilot-work/fleet.json > /tmp/fead-pilot-work/fleetagg_out.txt
python3 -I corridors.py  /tmp/fead-pilot-work/fleet.json > /tmp/fead-pilot-work/corridors_out.txt
python3 -I dq.py /tmp/fead-pilot-work/fleet.json /tmp/fead-pilot-work/trucks /tmp/fead-pilot-work/anon_map_PRIVATE.json > /tmp/fead-pilot-work/dq_out.txt
```

Ningún dato crudo ni derivado con identificadores se guarda en el repo. Los tsv de `/tmp/fead-pilot-work/trucks/` conservan el `truckid` hash en el nombre del archivo y solo deben vivir fuera del repo.
