# mcp · servidor MCP

Worker de Cloudflare. Adaptador delgado de la Domain API, sin lógica propia (ADR 0004). Dueño: Joseph.

## Correr

```sh
npm ci
npm run dev
```

## Tests

```sh
npm run typecheck   # regenera los tipos del Worker con `wrangler types`
npm test            # vitest dentro del runtime de Workers (@cloudflare/vitest-plugin)
```

## Tools

SDK: `createMcpHandler` de `agents/mcp/server` con `@modelcontextprotocol/server` v2 (sin estado, sin Durable Objects). Endpoint Streamable HTTP en `/mcp`; `/health` es público.

Siete adaptadores delgados de la Domain API (ADR 0004), que devuelven el sobre tal cual (procedencia, rango de tiempo, `updated_at`). Son un replay, nunca tiempo real.

| Tool | Entrada | Ruta de la Domain API |
|---|---|---|
| `get_fleet_overview` | - | `GET /v1/tools/get_fleet_overview` |
| `get_vehicle_status` | `alias` | `GET /v1/tools/get_vehicle_status` |
| `get_trip_status` | `trip_id` | `GET /v1/tools/get_trip_status` |
| `get_fuel_analysis` | `trip_id` | `GET /v1/tools/get_fuel_analysis` |
| `get_operational_bottlenecks` | `trip_id` | `GET /v1/tools/get_operational_bottlenecks` |
| `get_alerts` | - | `GET /v1/tools/get_alerts` |
| `control_replay` | `action` (play, pause, seek, set_speed), `speed?`, `to_event_time?` | `POST /v1/tools/control_replay` |

Un error de la Domain API (p. ej. 404 por alias desconocido) vuelve como resultado con `isError: true` y el `detail` original.

## Variables

| Nombre | Tipo | Uso |
|---|---|---|
| `DOMAIN_API_URL` | var en `wrangler.jsonc` | URL base de la Domain API (hoy un placeholder) |
| `MCP_API_KEY` | secreto | key que deben presentar los clientes MCP |
| `DOMAIN_API_KEY` | secreto | key de servicio que el Worker envía como `X-API-Key` a la Domain API |

`/mcp` exige `Authorization: Bearer <MCP_API_KEY>` o `X-API-Key: <MCP_API_KEY>`: 401 sin key o con key incorrecta, 503 si `MCP_API_KEY` no está configurada. En local, copia `.dev.vars.example` a `.dev.vars`.

## Desplegar

```sh
cd mcp
# 1. poner la URL real de la Domain API en vars.DOMAIN_API_URL de wrangler.jsonc
npx wrangler secret put MCP_API_KEY
npx wrangler secret put DOMAIN_API_KEY
npm run deploy
curl https://fleet-mcp.<subdominio>.workers.dev/health
```

## Conectar Claude Desktop

Con `mcp-remote` (en `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "fleet-intelligence": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://fleet-mcp.<subdominio>.workers.dev/mcp",
               "--header", "Authorization:${AUTH}"],
      "env": { "AUTH": "Bearer <MCP_API_KEY>" }
    }
  }
}
```

Reinicia Claude Desktop y pregunta, por ejemplo, "¿cómo está el vehículo T03?".

## Tests

Los tests usan un upstream simulado construido desde `../backend/openapi.json` (el `example` de cada respuesta 200 de `/v1/tools/*`, el mismo contrato que sirve Prism) y verifican la `X-API-Key` de servicio.
