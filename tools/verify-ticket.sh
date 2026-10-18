#!/usr/bin/env bash
# Corre los tests de las carpetas que cambió la rama actual respecto de main.
# Uso: tools/verify-ticket.sh [ruta-del-worktree]
# Sale con código distinto de cero si algún test falla. Instala dependencias
# faltantes antes de correr.
set -euo pipefail

cd "${1:-.}"
base=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main)
changed=$( { git diff --name-only "$base"; git diff --name-only; git ls-files --others --exclude-standard; } | sort -u)

targets=()
for d in backend mcp dashboard web; do
  if grep -q "^$d/" <<<"$changed"; then targets+=("$d"); fi
done
# El harness (Makefile, workflows) afecta a todas las carpetas.
if grep -qE '^(Makefile|\.github/workflows/)' <<<"$changed"; then
  targets=(backend mcp dashboard web)
fi

if [ ${#targets[@]} -eq 0 ]; then
  echo "verify-ticket: sin cambios en carpetas con tests (cambios: $(tr '\n' ' ' <<<"$changed"))"
  exit 0
fi

for d in "${targets[@]}"; do
  case $d in
    backend) [ -d backend/.venv ] || (cd backend && uv sync -q) ;;
    *) [ -d "$d/node_modules" ] || (cd "$d" && npm ci -s) ;;
  esac
  echo "verify-ticket: make test-$d"
  make --no-print-directory "test-$d"
done
echo "verify-ticket: OK (${targets[*]})"
