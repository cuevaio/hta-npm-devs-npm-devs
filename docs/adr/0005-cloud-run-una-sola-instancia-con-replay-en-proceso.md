# Cloud Run corre con una sola instancia y el replay dentro del proceso

El replay necesita un proceso que siga vivo entre requests y un único estado (en curso, pausado, velocidad). Desplegamos el backend en Cloud Run con `min-instances=1`, `max-instances=1` y CPU siempre asignada (`--no-cpu-throttling`), y el replay corre como tarea asyncio dentro del mismo FastAPI. Con una sola instancia no hay que coordinar estado entre réplicas ni sufrir arranques en frío durante la demo.

## Consequences

- **No subir `max-instances`:** con dos instancias habría dos replays independientes y datos duplicados.
- El costo es fijo (aprox. USD 1–2 por día), aceptable para la duración del hackathon.
