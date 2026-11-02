#!/usr/bin/env bash
# Резервная копия сайта: дамп базы и загруженные фото и ролики.
# Копии шифруются и хранятся в репозитории restic на этом же сервере.
#   sudo /opt/keratin/deploy/backup.sh
#
# Хранится 7 ежедневных, 4 еженедельных и 6 ежемесячных копий.
# Исходники роликов по умолчанию не копируются (готовые ролики и обложки
# в копию входят), включить: BACKUP_VIDEO_SOURCES=1.
# Чтобы скачивать копии своим пользователем без sudo, задайте его группу:
# BACKUP_READER_GROUP=имя_группы. Файлы зашифрованы, без пароля они
# бесполезны.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGING_DIR=/var/lib/keratin-backup
export RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-/var/backups/keratin}"
export RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/root/.keratin-backup-password}"

fail() { echo "$1" >&2; exit 1; }

[[ $EUID -eq 0 ]] || fail "Запустите через sudo."
command -v restic >/dev/null || fail "Нет restic: sudo apt install restic"
[[ -s $RESTIC_PASSWORD_FILE ]] \
    || fail "Нет файла с паролем $RESTIC_PASSWORD_FILE, см. README.md."

cd "$PROJECT_DIR"
volume_path() {
    docker volume inspect --format '{{ .Mountpoint }}' "keratin_$1"
}

if ! restic cat config >/dev/null 2>&1; then
    echo "Создаю репозиторий $RESTIC_REPOSITORY"
    restic init
fi

install -d -m 700 "$STAGING_DIR"
trap 'rm -f "$STAGING_DIR/db.dump"' EXIT

echo "Дамп базы"
docker compose exec -T db \
    sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
    > "$STAGING_DIR/db.dump"

paths=("$STAGING_DIR/db.dump" "$(volume_path media)")
excludes=()
if [[ ${BACKUP_VIDEO_SOURCES:-0} == 1 ]]; then
    sources="$(volume_path private_media)"
    paths+=("$sources")
    excludes+=(--exclude "$sources/tmp")
fi

echo "Копирование"
restic backup --tag keratin "${excludes[@]}" "${paths[@]}"

echo "Удаление старых копий"
restic forget --tag keratin --prune \
    --keep-daily 7 --keep-weekly 4 --keep-monthly 6

if [[ -n ${BACKUP_READER_GROUP:-} ]]; then
    chgrp -R "$BACKUP_READER_GROUP" "$RESTIC_REPOSITORY"
    chmod -R g+rX "$RESTIC_REPOSITORY"
fi

restic snapshots --tag keratin --compact
