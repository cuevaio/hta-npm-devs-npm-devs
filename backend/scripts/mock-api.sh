#!/usr/bin/env bash
# Levanta un servidor simulado (Prism) del contrato en http://127.0.0.1:4010.
set -euo pipefail
exec npx -y @stoplight/prism-cli@5 mock -p "${PORT:-4010}" "$(cd "$(dirname "$0")/.." && pwd)/openapi.json"
