#!/bin/bash
set -e

BACKUP_DIR="/data/ocr_project/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$DATE"

mkdir -p "$BACKUP_PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/production.yml"

if [ -f "$SCRIPT_DIR/production.env" ]; then
    set -a
    source "$SCRIPT_DIR/production.env"
    set +a
fi

echo "开始备份..."
docker compose -f "$CONFIG_FILE" exec -T postgres pg_dump -U ${POSTGRES_USER:-postgres} ${POSTGRES_DB:-ocr_db} > "$BACKUP_PATH/database.sql"
tar -czf "$BACKUP_PATH/ocr_results.tar.gz" -C /data/ocr_project ocr_results
echo "备份完成: $BACKUP_PATH"
