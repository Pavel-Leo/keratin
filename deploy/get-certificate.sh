#!/usr/bin/env bash
# Выпуск сертификата Let's Encrypt и переключение nginx на HTTPS.
#   sudo deploy/get-certificate.sh почта@example.ru example.ru www.example.ru
# Перед запуском домены должны указывать на этот сервер (A-записи),
# а сайт работать с NGINX_CONF=http.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fail() { echo "$1" >&2; exit 1; }

[[ $EUID -eq 0 ]] || fail "Запустите через sudo."
[[ $# -ge 2 ]] || fail "Укажите почту и хотя бы один домен."

email="$1"
shift
domains=()
for domain in "$@"; do
    domains+=(-d "$domain")
done

cd "$PROJECT_DIR"
docker compose run --rm certbot certonly \
    --webroot -w /var/www/certbot \
    --cert-name keratin "${domains[@]}" \
    --email "$email" --agree-tos --no-eff-email \
    --deploy-hook "sh /hook.sh"

if grep -q '^NGINX_CONF=' .env; then
    sed -i 's/^NGINX_CONF=.*/NGINX_CONF=https/' .env
else
    echo 'NGINX_CONF=https' >> .env
fi
docker compose up -d nginx

echo "Готово: https://$1"
