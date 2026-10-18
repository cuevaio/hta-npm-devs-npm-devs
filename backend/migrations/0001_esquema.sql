-- Esquema inicial (D33). Tiempos en UTC; las posiciones en PostGIS.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE vehicles (
    alias text PRIMARY KEY  -- T01…T28 (ADR 0006)
);

CREATE TABLE drivers (
    driver_id  text PRIMARY KEY,
    name       text NOT NULL,
    provenance text NOT NULL DEFAULT 'synthetic_demo'
);

CREATE TABLE trips (
    trip_id         text PRIMARY KEY,
    alias           text NOT NULL REFERENCES vehicles (alias),
    corridor        text NOT NULL,
    sentido         text NOT NULL CHECK (sentido IN ('ida', 'vuelta')),
    origin_terminal text NOT NULL,
    dest_terminal   text NOT NULL,
    t_start         timestamptz NOT NULL,
    t_end           timestamptz NOT NULL,
    provenance      text NOT NULL DEFAULT 'synthetic_demo'
);
CREATE INDEX trips_alias_t_start ON trips (alias, t_start);

-- 1:1 con el viaje: trip_id es la clave primaria.
CREATE TABLE freights (
    trip_id           text PRIMARY KEY REFERENCES trips (trip_id),
    freight_id        text NOT NULL UNIQUE,
    alias             text NOT NULL REFERENCES vehicles (alias),
    driver_id         text NOT NULL REFERENCES drivers (driver_id),
    client            text NOT NULL,
    cargo             text NOT NULL,
    corridor          text NOT NULL,
    sentido           text NOT NULL,
    origin_terminal   text NOT NULL,
    dest_terminal     text NOT NULL,
    planned_departure timestamptz NOT NULL,
    provenance        text NOT NULL DEFAULT 'synthetic_demo'
);

CREATE TABLE driver_reports (
    report_id   text PRIMARY KEY,
    trip_id     text NOT NULL REFERENCES trips (trip_id),
    driver_id   text NOT NULL REFERENCES drivers (driver_id),
    reported_at timestamptz NOT NULL,
    text        text NOT NULL,
    provenance  text NOT NULL
);

-- Telemetría por reproducir (días 13-19). El replay la copia a telemetry_reading.
CREATE TABLE telemetry_source (
    alias         text NOT NULL,
    event_time    timestamptz NOT NULL,
    lat           double precision NOT NULL,
    lon           double precision NOT NULL,
    speed_kmh     double precision,
    rpm           double precision,
    fuel_rate_lph double precision,
    fuel_total_l  double precision,
    odometer_km   double precision,
    engine_on     boolean,
    provenance    text NOT NULL DEFAULT 'fead_observed'
);
CREATE INDEX telemetry_source_alias_event_time ON telemetry_source (alias, event_time);
CREATE INDEX telemetry_source_event_time ON telemetry_source (event_time);

-- Lecturas visibles: la historia (replayed_at nulo) y lo ya reproducido.
CREATE TABLE telemetry_reading (
    alias         text NOT NULL,
    event_time    timestamptz NOT NULL,  -- hora del evento
    replayed_at   timestamptz,           -- hora de replay (nula en la historia)
    ingested_at   timestamptz NOT NULL DEFAULT now(),  -- hora de ingesta
    lat           double precision NOT NULL,
    lon           double precision NOT NULL,
    geom          geography(Point, 4326) GENERATED ALWAYS AS
                  (ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography) STORED,
    speed_kmh     double precision,
    rpm           double precision,
    fuel_rate_lph double precision,
    fuel_total_l  double precision,
    odometer_km   double precision,
    engine_on     boolean,
    provenance    text NOT NULL DEFAULT 'fead_observed'
);
CREATE INDEX telemetry_reading_alias_event_time ON telemetry_reading (alias, event_time);
CREATE INDEX telemetry_reading_event_time ON telemetry_reading (event_time) WHERE replayed_at IS NOT NULL;

-- Estado único del replay (ADR 0005).
CREATE TABLE replay_state (
    id           boolean PRIMARY KEY DEFAULT true CHECK (id),
    estado       text NOT NULL DEFAULT 'paused' CHECK (estado IN ('playing', 'paused')),
    velocidad    double precision NOT NULL DEFAULT 1 CHECK (velocidad > 0),
    hora_replay  timestamptz NOT NULL,
    inicio       timestamptz NOT NULL,
    fin          timestamptz NOT NULL,
    last_tick_at timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);
-- Día 13 a día 19 en hora local UTC+8.
INSERT INTO replay_state (hora_replay, inicio, fin)
VALUES ('2020-04-12T16:00:00Z', '2020-04-12T16:00:00Z', '2020-04-19T16:00:00Z');
