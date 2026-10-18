-- Altitud de cada lectura, en msnm (ADR 0012). La flota de Perú la toma de SRTM sobre la ruta;
-- el pipeline de FEAD no la trae, así que la columna admite nulos.
ALTER TABLE telemetry_source  ADD COLUMN alt_m double precision;
ALTER TABLE telemetry_reading ADD COLUMN alt_m double precision;
