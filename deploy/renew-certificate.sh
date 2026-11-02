#!/usr/bin/env bash
# Продление сертификата, запускается по cron раз в неделю. certbot
# продлевает его за месяц до окончания, nginx перечитывает новый файл.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker compose run --rm certbot renew --quiet
docker compose exec -T nginx nginx -s reload
