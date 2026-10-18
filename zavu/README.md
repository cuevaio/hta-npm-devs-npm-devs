# Zavu · agente Certera

Zavu Function con el agente de WhatsApp del gestor de flota (`defineAgent`, español, solo WhatsApp, sin voz) y las 6 tools de lectura de la Domain API: `get_fleet_overview`, `get_vehicle_status`, `get_trip_status`, `get_fuel_analysis`, `get_operational_bottlenecks`, `get_alerts`. `control_replay` no está aquí (solo MCP).

Cada tool hace un único `fetch` a `GET ${DOMAIN_API_URL}/v1/tools/<tool>` con `X-API-Key` y devuelve el sobre tal cual (ADR 0004). Si falta configuración o la API responde 4xx/5xx, devuelve `{ error, status, detail }` y el agente dice que no tiene el dato. El prompt limita el agente a la flota, separa Hechos de Hipótesis, declara procedencia y hora (UTC+8) y aclara que es un replay.

## Requisitos

- Node 18+ (probado con 22)
- Acceso al proyecto de Zavu (`.zavu/config.json`, no editar) y sesión iniciada: `npx zavudev login`

## Variables

| Variable | Qué es |
|---|---|
| `SENDER_ID` | Sender de Zavu del agente |
| `DOMAIN_API_URL` | URL base de la Domain API, sin `/v1` |
| `DOMAIN_API_KEY` | API key de servicio (`X-API-Key`) |
| `GEMINI_API_KEY` | API key propia de Google para el modelo `gemini-4-argon` (proveedor `google`); sin ella el agente no se registra |

## Tests

```sh
npm ci
npm run typecheck
npm test   # levanta Prism desde ../backend/openapi.json en el puerto 4011 y lo apaga al final
```

## Desplegar

```sh
npx zavudev fn secrets set SENDER_ID <senderId>
npx zavudev fn secrets set DOMAIN_API_URL <url>
npx zavudev fn secrets set DOMAIN_API_KEY <clave>
npx zavudev fn secrets set GEMINI_API_KEY -   # lee la key de stdin
npx zavudev deploy
```

Para apuntar a Cloud Run cuando exista el tracer, usa su URL como `DOMAIN_API_URL` y la API key real como `DOMAIN_API_KEY`, y vuelve a ejecutar `fn secrets set`. Con el simulado, basta una URL pública de Prism (`backend/scripts/mock-api.sh`).

## Archivos

| Archivo | Qué es |
|---|---|
| `index.ts` | `defineAgent` y un `defineTool` por tool |
| `prompt.ts` | Prompt del agente |
| `tools.ts` | `TOOL_DEFS` y `callDomainApi` (módulos importados por ruta relativa: Zavu solo despliega lo que `index.ts` importa, nunca `../`) |
| `test/` | vitest contra Prism |
| `.zavu/config.json` | Vincula la carpeta con la función. **No borrar ni editar** |
