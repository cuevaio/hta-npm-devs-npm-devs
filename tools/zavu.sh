#!/usr/bin/env bash
# Atajo al CLI de Zavu con la versión fijada. Uso: tools/zavu.sh login
set -euo pipefail
cd "$(dirname "$0")/../zavu"
exec npx -y zavudev@0.14.1 "$@"
