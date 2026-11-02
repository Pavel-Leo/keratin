#!/usr/bin/env bash
# Проверка сервера перед установкой сайта. Ничего не меняет, только читает.
#   sudo bash deploy/diagnose.sh
# Вывод можно целиком прислать разработчику.

section() { printf '\n== %s\n' "$1"; }

section "Система"
grep PRETTY_NAME /etc/os-release
uname -r
echo "Ядер: $(nproc)"
free -h
df -h /

section "Кто слушает порты 80 и 443 (TCP и UDP)"
ss -tulpn | awk 'NR == 1 || $5 ~ /:(80|443)$/'

section "Все открытые порты"
ss -tulpn

section "Docker"
if command -v docker >/dev/null; then
    docker --version
    docker compose version 2>/dev/null \
        || echo "Плагин docker compose не установлен (см. DEPLOY.md, шаг 2)"
    docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
else
    echo "Docker не установлен"
fi

section "Похожие на VPN службы"
systemctl list-units --type=service --state=running --no-pager \
    | grep -Ei 'xray|v2ray|sing-box|openvpn|wg-quick|wireguard|outline|shadowsocks|amnezia|hysteria|marzban|x-ui|ocserv|ipsec|strongswan' \
    || echo "не найдено среди служб systemd"

section "Межсетевой экран"
if command -v ufw >/dev/null; then
    ufw status verbose
else
    echo "ufw не установлен"
fi
if command -v nft >/dev/null; then
    nft list ruleset | head -n 60
fi
iptables -S 2>/dev/null | head -n 40

section "restic"
command -v restic >/dev/null && restic version || echo "restic не установлен"
