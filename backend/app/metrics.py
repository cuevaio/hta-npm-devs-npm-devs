"""Métricas históricas de un vehículo por día (hora de Lima) o por viaje.

Como el resto de la API, nunca revela lo que el replay todavía no reprodujo: solo cuentan las pasadas
terminadas, la telemetría ya reproducida y los fletes cuyo viaje ya llegó.
"""

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from .db import connect
from .freights import LIMA
from .fuel import IDLE_GAP_CAP_S, IDLE_SPEED_KMH, evaluar
from .schemas import MetricasPeriodo, VehicleMetrics

_EXISTS = "SELECT (EXISTS (SELECT 1 FROM trips WHERE alias = %(a)s) OR EXISTS (SELECT 1 FROM vehicles WHERE alias = %(a)s)) AS ok"

_FIRST_DAY = "SELECT min(t_start) AS t FROM trips WHERE alias = %s"

_PASSES = """
SELECT p.trip_id, p.t_start, p.km, p.liters, p.l_per_100km, t.corridor, t.sentido,
       b.n_passes, b.n_vehicles, b.median_l_per_100km, b.p90_l_per_100km, b.median_liters
FROM passes p
JOIN trips t ON t.trip_id = p.trip_id
LEFT JOIN baselines b ON b.corridor = p.corridor AND b.sentido = p.sentido AND b.h3_cell = p.h3_cell
WHERE p.alias = %(a)s AND p.t_start >= %(s)s AND p.t_end <= %(e)s
"""

_TRIPS_DONE = """
SELECT t.trip_id, t.t_end, t.corridor, t.sentido,
       coalesce(f.tarifa_pen, 0)::float AS tarifa, coalesce(f.fuel_cost_pen, 0)::float AS combustible
FROM trips t
LEFT JOIN freights f ON f.trip_id = t.trip_id
WHERE t.alias = %(a)s AND t.t_end >= %(s)s AND t.t_end <= %(e)s
"""

# Segundos en movimiento y en ralentí por día y viaje. Un hueco de telemetría no cuenta entero (tope por lectura).
_ENGINE = """
WITH r AS (
    SELECT event_time, speed_kmh, rpm, lead(event_time) OVER (ORDER BY event_time) AS nxt
    FROM telemetry_reading
    WHERE alias = %(a)s AND event_time >= %(s)s AND event_time < %(e)s
), s AS (
    SELECT event_time, speed_kmh, rpm, least(extract(epoch FROM nxt - event_time), %(cap)s) AS dt
    FROM r WHERE nxt IS NOT NULL
)
SELECT (s.event_time AT TIME ZONE 'America/Lima')::date AS dia, t.trip_id,
       coalesce(sum(dt) FILTER (WHERE speed_kmh > %(idle)s), 0) AS mov_s,
       coalesce(sum(dt) FILTER (WHERE speed_kmh <= %(idle)s AND rpm > 0), 0) AS idle_s
FROM s
LEFT JOIN trips t ON t.alias = %(a)s AND s.event_time >= t.t_start AND s.event_time < t.t_end
GROUP BY 1, 2
"""


def _dia(ts: datetime) -> str:
    return ts.astimezone(LIMA).date().isoformat()


class _Acum:
    def __init__(self):
        self.corredor = self.sentido = None
        self.viajes = self.tramos = self.con_base = self.sobre = 0
        self.km = self.litros = self.litros_validos = self.base = self.mov_s = self.idle_s = 0.0
        self.ingresos = self.combustible = 0.0

    def pasada(self, row: dict) -> None:
        valid, over = evaluar(row)
        self.tramos += 1
        self.km += row["km"]
        self.litros += row["liters"]
        if valid:
            self.con_base += 1
            self.litros_validos += row["liters"]
            self.base += row["median_liters"]
        self.sobre += over

    def sumar(self, o: "_Acum") -> None:
        for k in ("viajes", "tramos", "con_base", "sobre", "km", "litros", "litros_validos", "base",
                  "mov_s", "idle_s", "ingresos", "combustible"):
            setattr(self, k, getattr(self, k) + getattr(o, k))

    def modelo(self, clave: str) -> MetricasPeriodo:
        return MetricasPeriodo(
            clave=clave, corredor=self.corredor, sentido=self.sentido, viajes_finalizados=self.viajes,
            km=round(self.km, 1), litros=round(self.litros, 1),
            l_100km=round(self.litros / self.km * 100, 2) if self.km else None,
            tramos=self.tramos, tramos_con_linea_base=self.con_base, tramos_sobreconsumo=self.sobre,
            litros_linea_base=round(self.base, 1), exceso_l=round(self.litros_validos - self.base, 1),
            vs_pares_pct=round((self.litros_validos / self.base - 1) * 100, 1) if self.base else None,
            horas_en_movimiento=round(self.mov_s / 3600, 2), ralenti_h=round(self.idle_s / 3600, 2),
            ingresos_pen=round(self.ingresos, 2), combustible_pen=round(self.combustible, 2),
            margen_pen=round(self.ingresos - self.combustible, 2),
        )


def vehicle_metrics(
    database_url: str, alias: str, desde: date | None, hasta: date | None, agrupar_por: str
) -> tuple[VehicleMetrics, datetime, datetime, datetime] | None:
    """Devuelve (datos, inicio, fin, actualizado_en), o None si el vehículo es desconocido."""
    with connect(database_url, dict_rows=True) as conn:
        if not conn.execute(_EXISTS, {"a": alias}).fetchone()["ok"]:
            return None
        st = conn.execute("SELECT hora_replay, updated_at FROM replay_state").fetchone()
        hora = st["hora_replay"]
        if desde is None:
            first = conn.execute(_FIRST_DAY, (alias,)).fetchone()["t"]
            desde = (first or hora).astimezone(LIMA).date()
        hasta = min(hasta or hora.astimezone(LIMA).date(), hora.astimezone(LIMA).date())
        inicio = datetime.combine(desde, time(), LIMA)
        fin = max(inicio, min(datetime.combine(hasta + timedelta(days=1), time(), LIMA), hora))
        params = {"a": alias, "s": inicio, "e": fin, "cap": IDLE_GAP_CAP_S, "idle": IDLE_SPEED_KMH}
        passes = conn.execute(_PASSES, params).fetchall()
        done = conn.execute(_TRIPS_DONE, params).fetchall()
        engine = conn.execute(_ENGINE, params).fetchall()

    por_viaje = agrupar_por == "viaje"
    grupos: dict[str, _Acum] = defaultdict(_Acum)
    for p in passes:
        g = grupos[p["trip_id"] if por_viaje else _dia(p["t_start"])]
        g.pasada(p)
        if por_viaje:
            g.corredor, g.sentido = p["corridor"], p["sentido"]
    for t in done:
        g = grupos[t["trip_id"] if por_viaje else _dia(t["t_end"])]
        g.viajes += 1
        g.ingresos += t["tarifa"]
        g.combustible += t["combustible"]
        if por_viaje:
            g.corredor, g.sentido = t["corridor"], t["sentido"]
    for e in engine:
        if por_viaje and e["trip_id"] is None:
            continue
        g = grupos[e["trip_id"] if por_viaje else e["dia"].isoformat()]
        g.mov_s += float(e["mov_s"])
        g.idle_s += float(e["idle_s"])

    if not por_viaje:  # un día sin actividad también es un dato: barra en cero
        d = desde
        while d <= hasta:
            grupos[d.isoformat()]
            d += timedelta(days=1)

    total = _Acum()
    for g in grupos.values():
        total.sumar(g)
    filas = [g.modelo(k) for k, g in sorted(grupos.items())]  # días ISO y viajes T07-V01… ordenan solos
    data = VehicleMetrics(
        alias=alias, agrupar_por="viaje" if por_viaje else "dia", desde=desde.isoformat(), hasta=hasta.isoformat(),
        resumen=total.modelo("total"), filas=filas,
    )
    return data, inicio, fin, st["updated_at"]
