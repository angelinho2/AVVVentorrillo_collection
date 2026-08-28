#!/bin/bash
# backup_avv.sh — Backup diario de la BD de AVV Ventorrillo
# Configurar en cron: 0 3 * * * /home/ubuntu/avvVento_collection/backup_avv.sh >> /var/log/avv_backup.log 2>&1

BACKUP_DIR="/home/ubuntu/avvVento_collection/backups"
COMPOSE_FILE="/home/ubuntu/avvVento_collection/docker-compose.yml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Iniciando backup..."

docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U avv_user -d avv_ventorrillo \
  | gzip > "$BACKUP_DIR/avv_backup_${TIMESTAMP}.sql.gz"

if [ $? -eq 0 ]; then
  echo "[$(date)] Backup completado: avv_backup_${TIMESTAMP}.sql.gz"
else
  echo "[$(date)] ERROR: falló el backup"
  exit 1
fi

# Eliminar backups de más de $KEEP_DAYS días
find "$BACKUP_DIR" -name "avv_backup_*.sql.gz" -mtime +${KEEP_DAYS} -delete
echo "[$(date)] Limpieza de backups antiguos completada"
