-- Geometría de la vía de cada corredor en sentido ida (OpenStreetMap vía OSRM, ADR 0012), para el mapa.
CREATE TABLE corridors (
    corridor        text PRIMARY KEY,
    via             text NOT NULL,
    origin_terminal text NOT NULL,
    dest_terminal   text NOT NULL,
    km              double precision NOT NULL,
    geom            geometry(LineString, 4326) NOT NULL
);
