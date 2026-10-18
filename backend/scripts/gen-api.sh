#!/usr/bin/env bash
# Exporta el OpenAPI y regenera los tipos TS de mcp/, zavu/ y dashboard/.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/export_openapi.py
for out in ../mcp/src/api/types.ts ../zavu/api/types.ts ../dashboard/src/api/types.ts; do
  mkdir -p "$(dirname "$out")"
  npx -y openapi-typescript@7 openapi.json -o "$out"
done
