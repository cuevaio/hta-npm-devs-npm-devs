#!/usr/bin/env bash
# Falla si la rama del worktree toca archivos fuera del alcance declarado.
# Uso: tools/check-scope.sh <worktree> <ruta>...
#   Cada <ruta> es una carpeta (termina en /) o un archivo exacto.
# Mira lo commiteado desde main, lo modificado y lo nuevo sin commitear.
set -euo pipefail

worktree=$1; shift
[ $# -gt 0 ] || { echo "check-scope: falta declarar el alcance"; exit 2; }
cd "$worktree"
base=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main)
changes=$( { git diff --name-status "$base"; git diff --name-status; \
             git ls-files --others --exclude-standard | sed 's/^/A\t/'; } | sort -u)

fuera=()
while IFS=$'\t' read -r status path rest; do
  [ -n "$path" ] || continue
  [ -n "${rest:-}" ] && path=$rest   # renombres: R<n>\tviejo\tnuevo
  ok=false
  for scope in "$@"; do
    if [[ "$scope" == */ && "$path" == "$scope"* ]] || [[ "$path" == "$scope" ]]; then ok=true; break; fi
  done
  $ok || fuera+=("$status $path")
done <<<"$changes"

if [ ${#fuera[@]} -gt 0 ]; then
  echo "check-scope: la rama toca ${#fuera[@]} archivo(s) fuera del alcance ($*):"
  printf '  %s\n' "${fuera[@]}" | head -40
  echo "Si un cambio es legítimo, amplía el alcance; si no, restáuralo con: git checkout $base -- <archivo>"
  exit 1
fi
echo "check-scope: OK ($*)"
