#!/bin/bash
set -euo pipefail

BACKUP_DIR="/home/ubuntu/backups"
DB_NAME="${POSTGRES_DB:-terraos}"
DB_USER="${POSTGRES_USER:-terraos}"
DB_HOST="${POSTGRES_HOST:-127.0.0.1}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/terraos_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup of ${DB_NAME}..."
pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"
echo "[$(date)] Backup saved: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Keep only last 7 backups
cd "$BACKUP_DIR"
ls -t terraos_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
echo "[$(date)] Cleanup done. Backups retained: $(ls terraos_*.sql.gz | wc -l)"

# Optional S3 upload
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    echo "[$(date)] Uploading to s3://${BACKUP_S3_BUCKET}/..."
    aws s3 cp "$BACKUP_FILE" "s3://${BACKUP_S3_BUCKET}/daily/$(basename "$BACKUP_FILE")"
    echo "[$(date)] S3 upload complete."
fi
