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

Ocho adaptadores delgados de la Domain API (ADR 0004), que devuelven el sobre tal cual (procedencia, rango de tiempo, `updated_at`). Son un replay, nunca tiempo real.

| Tool | Entrada | Ruta de la Domain API |
|---|---|---|
| `get_fleet_overview` | - | `GET /v1/tools/get_fleet_overview` |
| `get_vehicle_status` | `alias` | `GET /v1/tools/get_vehicle_status` |
| `get_trip_status` | `trip_id` | `GET /v1/tools/get_trip_status` |
| `get_fuel_analysis` | `trip_id` | `GET /v1/tools/get_fuel_analysis` |
| `get_operational_bottlenecks` | `trip_id` | `GET /v1/tools/get_operational_bottlenecks` |
| `get_alerts` | - | `GET /v1/tools/get_alerts` |
| `get_vehicle_metrics` | `alias`, `desde?`, `hasta?` (YYYY-MM-DD, hora de Lima), `agrupar_por?` (dia, viaje) | `GET /v1/tools/get_vehicle_metrics` |
| `control_replay` | `action` (play, pause, seek, set_speed), `speed?`, `to_event_time?` | `POST /v1/tools/control_replay` |

Un error de la Domain API (p. ej. 404 por alias desconocido) vuelve como resultado con `isError: true` y el `detail` original.

## Auth

`/mcp` acepta dos credenciales:

1. **OAuth 2.1** (`@cloudflare/workers-oauth-provider`). El Worker es servidor de autorización y recurso a la vez. Los clientes descubren todo desde el 401 (`/.well-known/oauth-protected-resource/mcp` y `/.well-known/oauth-authorization-server`). Se registran por DCR (`/oauth/register`) o CIMD, y usan PKCE S256. `/authorize` muestra una página de consentimiento y luego manda al usuario a iniciar sesión con GitHub. `/callback` solo emite el código si el login de GitHub está en `GITHUB_ALLOWED_USERS`; si no, devuelve `access_denied` al cliente. Tokens y grants viven en el KV `OAUTH_KV` (namespace `fleet-mcp-oauth`).
2. **API key estática**: `Authorization: Bearer <MCP_API_KEY>` o `X-API-Key`, para `mcp-remote`, los tests y el e2e. Si `MCP_API_KEY` no está configurada, este camino queda cerrado.

## Variables

| Nombre | Tipo | Uso |
|---|---|---|
| `DOMAIN_API_URL` | var en `wrangler.jsonc` | URL base de la Domain API |
| `PUBLIC_URL` | var en `wrangler.jsonc` | URL pública del Worker; emisor OAuth y recurso `${PUBLIC_URL}/mcp` |
| `GITHUB_ALLOWED_USERS` | var en `wrangler.jsonc` | logins de GitHub permitidos, separados por coma |
| `MCP_API_KEY` | secreto | key estática de los clientes MCP |
| `DOMAIN_API_KEY` | secreto | key de servicio que el Worker envía como `X-API-Key` a la Domain API |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | secretos | OAuth App de GitHub |

En local, copia `.dev.vars.example` a `.dev.vars`.

## Desplegar

La OAuth App de GitHub se crea en <https://github.com/settings/applications/new>:

- **Homepage URL**: `https://fleet-mcp.chif-of-staff.workers.dev`
- **Authorization callback URL**: `https://fleet-mcp.chif-of-staff.workers.dev/callback`

```sh
cd mcp
npx wrangler secret put MCP_API_KEY
npx wrangler secret put DOMAIN_API_KEY
npx wrangler secret put GITHUB_CLIENT_ID
npx wrangler secret put GITHUB_CLIENT_SECRET
npm run deploy
curl https://fleet-mcp.chif-of-staff.workers.dev/health
```

## Conectar Claude (OAuth)

En claude.ai o Claude Desktop, ve a *Settings → Connectors → Add custom connector*, pega `https://fleet-mcp.chif-of-staff.workers.dev/mcp`, deja vacíos los campos de OAuth Client ID y Secret, y conecta. Se abre la página de consentimiento y después GitHub.

## Conectar con la API key

Con `mcp-remote` (en `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "certera": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://fleet-mcp.chif-of-staff.workers.dev/mcp",
               "--header", "Authorization:${AUTH}"],
      "env": { "AUTH": "Bearer <MCP_API_KEY>" }
    }
  }
}
```

Reinicia Claude Desktop y pregunta, por ejemplo, "¿cómo está el vehículo T03?".

## Tests

Los tests usan un upstream simulado construido desde `../backend/openapi.json` (el `example` de cada respuesta 200 de `/v1/tools/*`, el mismo contrato que sirve Prism) y verifican la `X-API-Key` de servicio.
