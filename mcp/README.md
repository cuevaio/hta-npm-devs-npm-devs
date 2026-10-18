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
