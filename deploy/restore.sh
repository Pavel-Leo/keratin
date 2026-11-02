#!/usr/bin/env bash
# Восстановление сайта из копии restic: база и загруженные файлы.
#   sudo deploy/restore.sh            последняя копия
#   sudo deploy/restore.sh 1a2b3c4d   конкретная копия
# Список копий: sudo restic -r /var/backups/keratin snapshots
# Текущие база и файлы сайта заменяются содержимым копии.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGING_DIR=/var/lib/keratin-backup
export RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-/var/backups/keratin}"
export RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/root/.keratin-backup-password}"
SNAPSHOT="${1:-latest}"

fail() { echo "$1" >&2; exit 1; }

[[ $EUID -eq 0 ]] || fail "Запустите через sudo."
command -v restic >/dev/null || fail "Нет restic: sudo apt install restic"

cd "$PROJECT_DIR"
volume_path() {
    docker volume inspect --format '{{ .Mountpoint }}' "keratin_$1"
}

read -r -p "База и файлы сайта будут заменены копией $SNAPSHOT. Продолжить? [y/N] " answer
[[ $answer == [yY] ]] || fail "Отменено."

RESTORE_DIR="$(mktemp -d)"
trap 'rm -rf "$RESTORE_DIR"' EXIT
restic restore "$SNAPSHOT" --tag keratin --target "$RESTORE_DIR"

dump="$RESTORE_DIR$STAGING_DIR/db.dump"
[[ -s $dump ]] || fail "В копии нет дампа базы."

replace_volume() {
    local target source
    target="$(volume_path "$1")"
    source="$RESTORE_DIR$target"
    [[ -d $source ]] || return 0
    echo "Файлы: $1"
    find "$target" -mindepth 1 -delete
    cp -a "$source/." "$target/"
}

echo "Остановка сайта"
docker compose stop web worker

echo "База"
docker compose exec -T db \
    sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' \
    < "$dump"

replace_volume media
replace_volume private_media

echo "Запуск сайта"
docker compose up -d web worker
