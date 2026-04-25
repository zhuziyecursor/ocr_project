#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/production.yml"

if [ -f "$SCRIPT_DIR/production.env" ]; then
    set -a
    source "$SCRIPT_DIR/production.env"
    set +a
fi

case "$1" in
  start)
    echo "启动服务..."
    docker compose -f "$CONFIG_FILE" up -d
    ;;
  stop)
    echo "停止服务..."
    docker compose -f "$CONFIG_FILE" down
    ;;
  restart)
    echo "重启服务..."
    docker compose -f "$CONFIG_FILE" restart
    ;;
  logs)
    echo "查看日志..."
    docker compose -f "$CONFIG_FILE" logs -f "$2"
    ;;
  status)
    echo "服务状态:"
    docker compose -f "$CONFIG_FILE" ps
    curl -sf http://localhost:8200/health && echo "Backend: OK" || echo "Backend: FAIL"
    ;;
  rebuild)
    echo "重新构建..."
    docker compose -f "$CONFIG_FILE" build --no-cache
    docker compose -f "$CONFIG_FILE" up -d
    ;;
  backup)
    echo "备份数据..."
    BACKUP_DIR="/data/ocr_project/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    docker compose -f "$CONFIG_FILE" exec -T postgres pg_dump -U postgres ocr_db > "$BACKUP_DIR/database.sql"
    tar -czf "$BACKUP_DIR/ocr_results.tar.gz" -C /data/ocr_project ocr_results
    echo "备份完成: $BACKUP_DIR"
    ;;
  *)
    echo "用法: $0 {start|stop|restart|logs|status|rebuild|backup}"
    exit 1
    ;;
esac
