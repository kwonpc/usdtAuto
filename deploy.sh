#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

echo "[deploy] pulling latest source"
git pull

if [[ ! -f config_bak.yml ]]; then
  echo "[deploy] config_bak.yml not found" >&2
  exit 1
fi

echo "[deploy] restoring config.yml from config_bak.yml"
cp config_bak.yml config.yml

echo "[deploy] ensuring runtime directories exist"
mkdir -p data logs

echo "[deploy] rebuilding and starting containers"
compose up -d --build

echo "[deploy] current containers"
compose ps
