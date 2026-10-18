# docs/dev · cómo nos repartimos el trabajo

Esta carpeta coordina al equipo: quién hace qué, en qué orden y en qué estado está cada issue.

| Archivo | Qué es |
|---|---|
| [`mapa-dependencias.md`](mapa-dependencias.md) | Issues, de qué depende cada uno y quién lo tiene. **Fuente de verdad del orden de trabajo.** |
| [`status.md`](status.md) | Estado actual de cada issue y bloqueos. Se actualiza en cada merge. |

El producto que construimos está descrito en [`docs/product/PRODUCT_CONTEXT_FLEET_INTELLIGENCE.md`](../product/PRODUCT_CONTEXT_FLEET_INTELLIGENCE.md). La investigación que respalda las decisiones vive en [`docs/research/`](../research/).

## Equipo

| Persona | Contacto | Responsabilidad |
|---|---|---|
| Joseph Robles | — | Grilling, mapa de dependencias, coordinación, infraestructura GCP, Zavu + agente + MCP + alertas |
| Juan Montreuil | juanmontreuil71@gmail.com | Datos FEAD + replay + backend FastAPI + línea base de combustible |
| Lian Pinto | lianpinto2416@gmail.com | Exclusivamente la web (`web/`) |

Regla de propiedad: **`web/` es de Lian.** Nadie más la edita sin coordinarlo, y Lian no toca código fuera de `web/`. La web consume el backend solo a través de los contratos de API que acordemos en el mapa.

## Flujo de trabajo con worktrees

Cada issue tiene una rama y un worktree propios, así varias personas (o agentes) trabajan a la vez sin pisarse.

```sh
# 1. Partir de main actualizado
git switch main && git pull

# 2. Crear el worktree del issue (fuera de la carpeta del repo)
git worktree add ../npm-devs-<id-issue> -b <tipo>/<id-issue>-<slug>
#   ej: git worktree add ../npm-devs-I03 -b feat/I03-replay-service

# 3. Trabajar ahí, abrir PR contra main

# 4. Al mergear, limpiar
git worktree remove ../npm-devs-<id-issue>
git branch -d <tipo>/<id-issue>-<slug>
```

Reglas:

1. **Un issue = una rama = un worktree = un PR.**
2. Solo se empieza un issue cuando todas sus dependencias están en `hecho` (mergeadas en `main`) según `status.md`. Si hace falta empezar antes, se trabaja contra el **contrato** acordado (tipos, esquema, endpoint), nunca contra una rama ajena sin mergear.
3. Al tomar un issue, se pone en `en curso` con tu nombre en `status.md`. Al mergear, se pasa a `hecho`.
4. Los cambios a contratos compartidos (esquema de BD, `TelemetryEvent`, endpoints de la Domain API) van en su propio issue y PR, y se avisa al equipo.
