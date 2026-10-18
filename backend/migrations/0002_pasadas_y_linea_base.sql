-- Pasadas por tramo (celda H3 res. 6 + sentido, ADR 0008) y línea base offline (ADR 0009). Tiempos en UTC.
CREATE TABLE passes (
    trip_id       text NOT NULL REFERENCES trips (trip_id),
    alias         text NOT NULL,
    corridor      text NOT NULL,
    sentido       text NOT NULL CHECK (sentido IN ('ida', 'vuelta')),
    h3_cell       text NOT NULL,
    t_start       timestamptz NOT NULL,
    t_end         timestamptz NOT NULL,
    day           integer,
    km            double precision NOT NULL,
    liters        double precision NOT NULL,
    l_per_100km   double precision,
    in_baseline   boolean NOT NULL DEFAULT false
);
CREATE INDEX passes_trip_t_start ON passes (trip_id, t_start);
CREATE INDEX passes_segment ON passes (corridor, sentido, h3_cell);

CREATE TABLE baselines (
    corridor           text NOT NULL,
    sentido            text NOT NULL CHECK (sentido IN ('ida', 'vuelta')),
    h3_cell            text NOT NULL,
    n_passes           integer NOT NULL,
    n_vehicles         integer NOT NULL,
    median_l_per_100km double precision NOT NULL,
    p90_l_per_100km    double precision NOT NULL,
    median_liters      double precision NOT NULL,
    p90_liters         double precision NOT NULL,
    median_km          double precision NOT NULL,
    provenance         text NOT NULL DEFAULT 'model_inferred',
    PRIMARY KEY (corridor, sentido, h3_cell)
);
