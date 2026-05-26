#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/opt/grocery-app/releases/current/compose.prod.yaml}"
ENV_FILE="${ENV_FILE:-/opt/grocery-app/shared/env/.env.prod}"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup-file.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

RESTORE_SQL="$(mktemp /tmp/grocery_restore.XXXXXX.sql)"
trap 'rm -f "$RESTORE_SQL"' EXIT

echo "Restoring from: $BACKUP_FILE"
gunzip -c "$BACKUP_FILE" > "$RESTORE_SQL"

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
  sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$RESTORE_SQL"

echo "Restore complete."
