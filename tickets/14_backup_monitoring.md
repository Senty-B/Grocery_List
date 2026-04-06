# Ticket 14: Backup Strategy & Health Monitoring

**Phase:** 4 — DevOps & Deployment  
**Priority:** Medium  
**Dependencies:** Ticket 12  
**Estimated effort:** Small

---

## Why This Matters

The database contains all household data and user credentials. If it's lost, everything is lost. Daily backups are mandatory.

## Reference

- `Production_Cutover_Runbook.md` sections 9.2, 12

---

## Tasks

### 1. Create the backup script

`scripts/backup.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/grocery-app/shared/backups"
DATE=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="/opt/grocery-app/releases/current/compose.prod.yaml"
ENV_FILE="/opt/grocery-app/shared/env/.env.prod"

echo "[$(date)] Starting backup..."

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
  pg_dump -U grocery -d grocery \
  > "${BACKUP_DIR}/grocery_${DATE}.sql"

gzip "${BACKUP_DIR}/grocery_${DATE}.sql"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "[$(date)] Backup complete: grocery_${DATE}.sql.gz"
```

Make it executable: `chmod +x scripts/backup.sh`

### 2. Document cron setup

Add a cron job on the server (not inside Docker):

```bash
crontab -e
# Add this line for daily 3 AM backup:
0 3 * * * /opt/grocery-app/releases/current/scripts/backup.sh >> /opt/grocery-app/shared/logs/backup.log 2>&1
```

### 3. Document the restore procedure

Add to the backup script or a separate `scripts/restore.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_FILE="$1"
COMPOSE_FILE="/opt/grocery-app/releases/current/compose.prod.yaml"
ENV_FILE="/opt/grocery-app/shared/env/.env.prod"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./restore.sh <backup-file.sql.gz>"
  exit 1
fi

echo "Restoring from: $BACKUP_FILE"
gunzip -c "$BACKUP_FILE" > /tmp/restore.sql

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
  psql -U grocery -d grocery < /tmp/restore.sql

rm -f /tmp/restore.sql
echo "Restore complete."
```

### 4. Enhance the health check endpoint

Update the `/health` route to also verify database connectivity:

```python
@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return "OK", 200
    except Exception:
        return "Database unreachable", 503
```

---

## Acceptance Criteria

- [ ] Backup script runs without errors when invoked manually
- [ ] Backup file is compressed (`.gz`)
- [ ] Backups older than 7 days are automatically deleted
- [ ] Restore script can restore from a backup file
- [ ] `/health` returns `200` when DB is up and `503` when DB is down
- [ ] Cron job documentation is complete
