# dashboard

React + Vite + TypeScript (ADR 0010), una sola página (D34). Consume solo las rutas públicas `/v1/*` de la Domain API: `/v1/fleet`, `/v1/trips/{trip_id}` y `/v1/replay`, con polling cada 2 s. Los tipos están en `src/api/types.ts` (generados del contrato `backend/openapi.json`).

Este ticket (#21) cubre: barra de estado del replay (solo lectura), lista de vehículos y viajes, mapa MapLibre con la posición actual de cada vehículo, procedencia y estados de carga, vacío, error y desactualizado. Alertas y consumo (#22) y controles del replay (#23) vienen después.

## Correr con el servidor simulado

```sh
npm ci
../backend/scripts/mock-api.sh     # Prism en http://127.0.0.1:4010 (otra terminal)
npm run dev
```

## Variables (build)

| Variable | Por defecto | Uso |
| --- | --- | --- |
| `VITE_API_URL` | `http://127.0.0.1:4010` | Base de la Domain API |
| `VITE_MAP_STYLE` | CARTO dark-matter | URL de estilo MapLibre; `empty` = estilo vacío local (tests) |

## Tests

```sh
npx playwright install chromium   # una vez
npm test
```

Playwright levanta el servidor simulado (Prism) y el build servido con `vite preview` (con `VITE_API_URL` apuntando al simulado y mapa vacío), y sobrescribe respuestas con `page.route` para los estados vacío, carga, error y desactualizado.

## Desplegar en Vercel (ADR 0011)

1. Importar el repo en Vercel con **Root Directory** `dashboard/` (usa `vercel.json`: Vite, salida `dist`, rewrite SPA).
2. Definir `VITE_API_URL` con la URL pública de la Domain API.
3. Agregar el dominio del dashboard a `CORS_ORIGINS` del backend (los previews `*.vercel.app` ya se permiten).
