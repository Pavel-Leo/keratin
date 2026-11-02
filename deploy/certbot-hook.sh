#!/bin/sh
# Вызывается certbot после выпуска или продления сертификата.
# Ключ в /etc/letsencrypt читается только root, а nginx работает без прав
# root (пользователь 101), поэтому для него кладётся отдельная копия.
set -eu

NGINX_UID=101
target=/etc/letsencrypt/nginx

mkdir -p "$target"
chown "$NGINX_UID:$NGINX_UID" "$target"
chmod 700 "$target"

for name in fullchain.pem privkey.pem; do
    cp -L "$RENEWED_LINEAGE/$name" "$target/$name.new"
    chown "$NGINX_UID:$NGINX_UID" "$target/$name.new"
    chmod 600 "$target/$name.new"
    mv "$target/$name.new" "$target/$name"
done
