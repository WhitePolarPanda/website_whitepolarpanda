#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
if [ ! -x .venv/bin/python ]; then
  "${PYTHON:-python3.12}" -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
# Keep the previous preview flag as a compatibility alias.
if [ "$#" -ne 0 ] && [ "${1:-}" != "--review" ]; then
  echo "Usage: $0 [--review]" >&2
  exit 2
fi
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}"
