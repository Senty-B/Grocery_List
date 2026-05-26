#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/grocery-app/shared/backups}"
COMPOSE_FILE="${COMPOSE_FILE:-/opt/grocery-app/releases/current/compose.prod.yaml}"
ENV_FILE="${ENV_FILE:-/opt/grocery-app/shared/env/.env.prod}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

DATE="$(date +%Y%m%d_%H%M%S)"
BACKUP_SQL="${BACKUP_DIR}/grocery_${DATE}.sql"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
  sh -c 'pg_dump --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > "$BACKUP_SQL"

gzip -f "$BACKUP_SQL"

find "$BACKUP_DIR" -name "grocery_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

echo "[$(date)] Backup complete: $(basename "${BACKUP_SQL}.gz")"
