# docs/dev · cómo nos repartimos el trabajo

Esta carpeta coordina al equipo: quién hace qué, en qué orden y cómo integramos el trabajo.

| Dónde | Qué es |
|---|---|
| [GitHub Issues](https://github.com/npm-devs/npm-devs/issues) | **Fuente de verdad de los tickets**: dueño, estado (labels de triage) y dependencias nativas (`blocked by`). |
| [`mapa-dependencias.md`](mapa-dependencias.md) | Vista general en Mermaid de los tickets y sus dependencias, con enlace a cada issue. |

El producto que construimos está descrito en [`docs/product/PRODUCT_CONTEXT_FLEET_INTELLIGENCE.md`](../product/PRODUCT_CONTEXT_FLEET_INTELLIGENCE.md). La investigación y las decisiones que lo respaldan viven en [`docs/research/`](../research/), en particular [`validacion-producto-decisiones.md`](../research/validacion-producto-decisiones.md).

## Equipo

| Persona | GitHub | Contacto | Responsabilidad | Carpetas |
|---|---|---|---|---|
| Joseph Robles | @JosephRobles23 | — | Grilling, mapa de dependencias, coordinación, harness de tests, infraestructura GCP, Zavu + agente + MCP + alertas, e2e | `mcp/`, `zavu/`, `e2e/` |
| Juan Montreuil | @JuanMontreuil08 | juanmontreuil71@gmail.com | Datos FEAD, replay, Domain API (FastAPI), línea base de combustible | `backend/`, `data/` |
| Lian Pinto | @KevinPinto123 | lianpinto2416@gmail.com | Dashboard | `dashboard/` |
| Ismael | @Ismaelrojas0112 | — | Landing page | `web/` |

> Desde el 2026-10-18 Joseph implementa todos los tickets con el orquestador; la tabla indica el área original de cada persona.

Regla de propiedad: **cada carpeta tiene un solo dueño** y nadie edita una carpeta ajena sin coordinarlo. `dashboard/` es de Lian y `web/` (landing) de Ismael. La ruta del webhook de reportes del conductor vive en `backend/` pero la implementa Joseph (#17), coordinando con Juan. El dashboard, el MCP y Zavu consumen el backend solo a través del contrato OpenAPI (#12).

## Flujo de trabajo: worktrees, sin PRs

Cada ticket tiene una rama y un worktree propios, así varias personas (o agentes) trabajan a la vez sin pisarse. **No abrimos PRs**: cada dev mergea su rama a `main` en local cuando los tests pasan.

```sh
# 1. Partir de main actualizado
git switch main && git pull

# 2. Tomar el ticket y crear su worktree (fuera de la carpeta del repo)
gh issue edit <n> --add-assignee @me
git worktree add ../npm-devs-<n> -b feat/<n>-<slug>
#   ej: git worktree add ../npm-devs-12 -b feat/12-replay-service

# 3. Trabajar ahí con commits chicos; correr los tests de la carpeta

# 4. Integrar en main (desde el repo principal)
git switch main && git pull
git merge feat/<n>-<slug>
<correr los tests>
git push
gh issue close <n> --comment "Mergeado en <sha>"

# 5. Limpiar
git worktree remove ../npm-devs-<n>
git branch -d feat/<n>-<slug>
```

Reglas:

1. **Un ticket = una rama = un worktree.**
2. Solo se empieza un ticket cuando todos sus bloqueos están cerrados en GitHub. Si hace falta empezar antes, se trabaja contra el **contrato** acordado (tipos, esquema, endpoint), nunca contra una rama ajena sin mergear.
3. **Nunca se mergea a `main` con tests en rojo.** Si `git pull` trae conflictos, los resuelve quien está integrando, antes del push.
4. Mergear seguido (al menos una vez por ticket terminado) para que nadie se aleje de `main`.
5. Los cambios a contratos compartidos (esquema de BD, `TelemetryEvent`, OpenAPI de la Domain API) van en su propio ticket y se avisa al equipo antes del merge.

## Implementar con el orquestador

Para avanzar tickets con agentes hay un orquestador (Opus 5.5) que planifica y verifica, y subagentes implementadores (Sonnet 5.5) que escriben el código.

```sh
tools/orquestar.sh                    # sesión con el orquestador como agente principal
tools/orquestar.sh "/orquestar 12 18" # trabaja esos tickets
tools/orquestar.sh "/orquestar"       # toma el frente de la spec #4 hasta agotarlo
```

| Pieza | Qué hace |
|---|---|
| `.claude/agents/orquestador.md` | Elige tickets `ready-for-agent` sin bloqueos, publica un plan como comentario en el issue, crea el worktree, delega, verifica el diff contra los criterios de aceptación, mergea a `main`, hace push y cierra el issue. Hasta 3 tickets en paralelo si tocan carpetas distintas. |
| `.claude/agents/implementador.md` | Implementa un ticket test-first (skill `tdd`) dentro de su worktree. No mergea, no hace push, no cierra issues. |
| `tools/hooks/verify-on-stop.sh` | Hook `Stop` del implementador: no lo deja terminar con tests en rojo. |
| `tools/verify-ticket.sh` | Corre los tests de las carpetas que cambió una rama. Lo usan el hook y el orquestador antes y después del merge. |

Los tickets `ready-for-human` (grilling, consola de GCP, Meta) no los toma el orquestador: los lista como pendientes. La primera vez que abras la sesión, Claude Code pide confiar en el workspace para activar los hooks del proyecto.

