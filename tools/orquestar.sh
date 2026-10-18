#!/usr/bin/env bash
# Abre una sesión de Claude Code cuyo hilo principal es el agente `orquestador`.
# El modelo se pasa explícito porque una variable ANTHROPIC_MODEL del entorno
# podría imponer otro.
# Uso: tools/orquestar.sh                 → sesión interactiva
#      tools/orquestar.sh "/orquestar 12" → arranca con esa instrucción
set -euo pipefail
cd "$(dirname "$0")/.."
exec claude --agent orquestador --model claude-opus-5-5 "$@"
