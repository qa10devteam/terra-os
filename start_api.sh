#!/usr/bin/env bash
# Terra-OS API — trwały skrypt startowy
# Python 3.12 (.venv) + poprawny PYTHONPATH
#
# Namespace packages:
#   services.api.*  → services/api/services/api/
#   services.ai.*   → services/ai/
#   services.ingestion.* → services/ingestion/
# Działa dzięki namespace package (brak __init__.py w services/api/services/)

set -e
TERRA_ROOT="$(cd "$(dirname "$0")" && pwd)"

export PYTHONPATH="\
${TERRA_ROOT}/services/api:\
${TERRA_ROOT}:\
${TERRA_ROOT}/packages/db:\
${TERRA_ROOT}/packages/shared:\
${TERRA_ROOT}/packages/vendor"

exec "${TERRA_ROOT}/.venv/bin/uvicorn" services.api.main:app \
  --host "${HOST:-127.0.0.1}" \
  --port "${PORT:-8765}" \
  --workers "${WORKERS:-1}" \
  "$@"
