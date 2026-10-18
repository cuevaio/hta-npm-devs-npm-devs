-- Capa comercial peruana de los fletes y totales observados por viaje (ADR 0012). Montos en soles.
ALTER TABLE freights
    ADD COLUMN client_ruc        text,
    ADD COLUMN tonnage_t         double precision,
    ADD COLUMN gre_remitente     text,
    ADD COLUMN gre_transportista text,
    ADD COLUMN tarifa_pen        numeric(12, 2),  -- sin IGV
    ADD COLUMN igv_pen           numeric(12, 2),
    ADD COLUMN total_pen         numeric(12, 2),
    ADD COLUMN detraccion_pen    numeric(12, 2),
    ADD COLUMN fuel_liters       double precision,  -- consumo observado del viaje completo
    ADD COLUMN fuel_cost_pen     numeric(12, 2);

ALTER TABLE trips
    ADD COLUMN km     double precision,
    ADD COLUMN liters double precision;
