#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$ROOT/src:$ROOT/.vendor${PYTHONPATH:+:$PYTHONPATH}"
if [ "${1:-}" = "python" ] && ! command -v python >/dev/null 2>&1; then
  shift
  exec python3 "$@"
fi
exec "$@"
