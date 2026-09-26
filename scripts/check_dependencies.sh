#!/usr/bin/env bash
# Wrapper simples para rodar check_dependencies.py via cron.
# Uso no crontab, por exemplo:
#   */5 * * * * /caminho/para/assistente-voz/scripts/check_dependencies.sh >> /var/log/assistente-voz-health.log 2>&1
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

echo "[$(date --iso-8601=seconds)] check_dependencies.sh"
exec "$PYTHON" scripts/check_dependencies.py "$@"
