# Cloud SQL con PostGIS es el único almacén; sin RAG ni grafo

Las consultas de la demo son hechos estructurados (posición, consumo por tramo, paradas, alertas) que SQL y PostGIS resuelven con exactitud, y los reportes de conductores son pocos y cortos. Usamos un solo Postgres 16 + PostGIS en Cloud SQL (`us-central1`, junto a Cloud Run) y descartamos para el MVP un vector store, GraphRAG o una base de grafos. Supabase quedó fuera porque el subconjunto de telemetría (0,8–1,3 GB) supera su plan gratuito de 500 MB.

## Consequences

- El contexto del agente se arma bajo demanda desde las tools, no desde una memoria vectorial.
- Si más adelante hay mucho texto libre, `pgvector` en la misma base es la primera opción a evaluar.
