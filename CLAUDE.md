## Agent skills

### Issue tracker

Issues y specs viven en GitHub Issues de `npm-devs/npm-devs`, vía `gh`, con dependencias nativas entre issues. Sin PRs: las ramas se mergean a `main` en local (ver `docs/dev/README.md`). See `docs/agents/issue-tracker.md`.

### Triage labels

Labels por defecto: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: un `CONTEXT.md` en la raíz + `docs/adr/`. See `docs/agents/domain.md`.

## Tests

Cada carpeta (`backend/`, `mcp/`, `dashboard/`, `web/`, `e2e/`) tiene su capa de tests y su check en GitHub Actions; `make test` corre todas las que no necesitan URLs públicas.

- **Ningún ticket se cierra sin un test que cubra su criterio de aceptación.**
- **Nunca se mergea a `main` con tests en rojo.**
- Los tests verifican comportamiento externo (HTTP, lo que ve el usuario), no detalles internos. El punto de prueba principal es la Domain API por HTTP; MCP y Zavu se prueban contra el contrato OpenAPI.
