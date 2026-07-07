#!/bin/bash
# Faza 65 — Automated PostgreSQL backup
# Cron: 0 2 * * * /home/ubuntu/terra-os/scripts/backup.sh >> /var/log/terraos_backup.log 2>&1

set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/terraos

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup terraos_${DATE}.sql.gz"
sudo -u postgres pg_dump terraos | gzip > "${BACKUP_DIR}/terraos_${DATE}.sql.gz"

# Keep only last 7 days
find "$BACKUP_DIR" -name '*.sql.gz' -mtime +7 -delete

echo "[$(date)] Backup completed: terraos_${DATE}.sql.gz ($(du -h "${BACKUP_DIR}/terraos_${DATE}.sql.gz" | cut -f1))"
