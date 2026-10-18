---
description: Implementa tickets del MVP con el ciclo del orquestador (plan → implementador → tests → merge)
argument-hint: "[números de issue, o vacío para tomar el frente]"
disable-model-invocation: true
---

Ejecuta el ciclo descrito en tu definición de `orquestador` (`.claude/agents/orquestador.md`).

Tickets pedidos: $ARGUMENTS

- Si hay números, trabaja solo esos tickets, en el orden que permitan sus dependencias.
- Si está vacío, calcula el frente de la spec #4 y avanza ticket por ticket hasta que no quede ninguno `ready-for-agent` desbloqueado.

Al terminar, resume: tickets cerrados con su commit, tickets en curso, bloqueos y pendientes `ready-for-human`.
