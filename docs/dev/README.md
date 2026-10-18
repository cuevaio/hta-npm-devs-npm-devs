# docs/dev · cómo nos repartimos el trabajo

Esta carpeta coordina al equipo: quién hace qué, en qué orden y cómo integramos el trabajo.

| Dónde | Qué es |
|---|---|
| [GitHub Issues](https://github.com/npm-devs/npm-devs/issues) | **Fuente de verdad de los tickets**: dueño, estado (labels de triage) y dependencias nativas (`blocked by`). |
| [`mapa-dependencias.md`](mapa-dependencias.md) | Vista general en Mermaid de los tickets y sus dependencias, con enlace a cada issue. |

El producto que construimos está descrito en [`docs/product/PRODUCT_CONTEXT_FLEET_INTELLIGENCE.md`](../product/PRODUCT_CONTEXT_FLEET_INTELLIGENCE.md). La investigación y las decisiones que lo respaldan viven en [`docs/research/`](../research/), en particular [`validacion-producto-decisiones.md`](../research/validacion-producto-decisiones.md).

## Equipo

| Persona | Contacto | Responsabilidad |
|---|---|---|
| Joseph Robles | — | Grilling, mapa de dependencias, coordinación, infraestructura GCP, Zavu + agente + MCP + alertas |
| Juan Montreuil | juanmontreuil71@gmail.com | Datos FEAD + replay + backend FastAPI + línea base de combustible |
| Lian Pinto | lianpinto2416@gmail.com | Exclusivamente la web (`web/`) |

Regla de propiedad: **`web/` es de Lian.** Nadie más la edita sin coordinarlo, y Lian no toca código fuera de `web/`. La web consume el backend solo a través de los contratos de API que acordemos en el mapa.

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
