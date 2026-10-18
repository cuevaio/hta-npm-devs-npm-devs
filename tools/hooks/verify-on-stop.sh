#!/usr/bin/env bash
# Hook Stop del subagente `implementador`: no lo deja terminar con tests en
# rojo. Lee del último mensaje la línea `WORKTREE: <ruta>` y corre
# tools/verify-ticket.sh ahí. Salir con 2 bloquea la parada y le entrega
# stderr al subagente como siguiente instrucción.
set -uo pipefail

input=$(cat)
message=$(jq -r '.last_assistant_message // ""' <<<"$input")
worktree=$(grep -oP '^WORKTREE:\s*\K\S+' <<<"$message" | tail -1)
estado=$(grep -oP '^ESTADO:\s*\K\S+' <<<"$message" | tail -1)

if [ -z "$worktree" ]; then
  echo "Termina tu último mensaje con las líneas 'WORKTREE: <ruta absoluta>', 'TICKET: #<n>' y 'ESTADO: listo | bloqueado'." >&2
  exit 2
fi

# Un bloqueo declarado se le devuelve al orquestador tal cual; él decide.
if [ "$estado" = "bloqueado" ]; then
  exit 0
fi

if [ ! -d "$worktree" ]; then
  echo "El worktree '$worktree' no existe. Indica la ruta absoluta correcta en la línea WORKTREE." >&2
  exit 2
fi

if ! output=$("$CLAUDE_PROJECT_DIR/tools/verify-ticket.sh" "$worktree" 2>&1); then
  {
    echo "Los tests del worktree fallan; arréglalos antes de terminar (o termina con 'ESTADO: bloqueado' explicando por qué)."
    echo "--- últimas líneas de tools/verify-ticket.sh ---"
    tail -n 60 <<<"$output"
  } >&2
  exit 2
fi
exit 0
