#!/bin/bash
# ════════════════════════════════════════════════════
# install.sh — установка сервиса лимитов Битрикс24
# Запуск: bash install.sh
# Требуется: Ubuntu 20.04+ с правами sudo
# ════════════════════════════════════════════════════

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SERVICE_DIR=/opt/limit-service
SERVICE_NAME=limit-service
SERVICE_PORT=8001

echo ""
echo "════════════════════════════════════════════════"
echo "  Установка сервиса контроля лимитов Б24"
echo "════════════════════════════════════════════════"
echo ""

# ── 1. Проверка ─────────────────────────────────────
info "Проверка системы..."
[[ $EUID -ne 0 ]] && error "Запустите скрипт с правами root: sudo bash install.sh"
command -v python3 >/dev/null 2>&1 || error "Python3 не установлен. Установите: apt install python3"
command -v pip3    >/dev/null 2>&1 || { warn "pip3 не найден, устанавливаем..."; apt-get install -y python3-pip; }
command -v nginx   >/dev/null 2>&1 || warn "nginx не найден — настройте вручную после установки"

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python версия: $PY_VER"

# ── 2. Директория ────────────────────────────────────
info "Создание директории $SERVICE_DIR..."
mkdir -p $SERVICE_DIR/templates
cp -r ./* $SERVICE_DIR/ 2>/dev/null || true
success "Файлы скопированы в $SERVICE_DIR"

# ── 3. Python venv ───────────────────────────────────
info "Создание виртуального окружения Python..."
python3 -m venv $SERVICE_DIR/venv || {
    warn "venv не найден, устанавливаем python3-venv..."
    apt-get install -y python3-venv
    python3 -m venv $SERVICE_DIR/venv
}
success "Виртуальное окружение создано"

# ── 4. Зависимости ───────────────────────────────────
info "Установка Python зависимостей..."
$SERVICE_DIR/venv/bin/pip install --upgrade pip -q
$SERVICE_DIR/venv/bin/pip install -r $SERVICE_DIR/requirements.txt -q
success "Зависимости установлены"

# ── 5. .env файл ─────────────────────────────────────
if [ ! -f "$SERVICE_DIR/.env" ]; then
    info "Создание .env файла..."
    cp $SERVICE_DIR/.env.example $SERVICE_DIR/.env
    
    # Генерируем случайный секрет
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/замените-на-случайную-строку-32-символа/$SECRET/g" $SERVICE_DIR/.env
    
    warn "ВАЖНО! Заполните $SERVICE_DIR/.env:"
    warn "  BITRIX_WEBHOOK_URL — ваш REST API вебхук из Б24"
    warn "  FIELD_DEPARTMENT   — код поля подразделения"
else
    success ".env уже существует, пропускаем"
fi

# ── 6. Права ─────────────────────────────────────────
info "Настройка прав доступа..."
chown -R www-data:www-data $SERVICE_DIR
chmod 600 $SERVICE_DIR/.env
success "Права настроены"

# ── 7. Systemd сервис ────────────────────────────────
info "Регистрация systemd сервиса..."
cp $SERVICE_DIR/limit-service.service /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload
systemctl enable $SERVICE_NAME
success "Сервис зарегистрирован в systemd"

# ── 8. Запуск ────────────────────────────────────────
info "Запуск сервиса..."
systemctl start $SERVICE_NAME
sleep 2
if systemctl is-active --quiet $SERVICE_NAME; then
    success "Сервис запущен!"
else
    error "Сервис не запустился. Проверьте: journalctl -u $SERVICE_NAME -n 50"
fi

# ── 9. Nginx ─────────────────────────────────────────
info "Настройка nginx..."
if command -v nginx >/dev/null 2>&1; then
    NGINX_CONF=$(nginx -t 2>&1 | grep "configuration file" | awk '{print $NF}' | tr -d ';' | head -1)
    NGINX_CONF=${NGINX_CONF:-/etc/nginx/nginx.conf}
    warn "Добавьте блок из $SERVICE_DIR/nginx.conf в ваш nginx конфиг"
    warn "Конфиг nginx: $NGINX_CONF"
    echo ""
    echo "─── Добавьте эти строки в server {} блок для portal.farovon.tj ───"
    cat $SERVICE_DIR/nginx.conf | grep -A 20 "location /limits/"
    echo "────────────────────────────────────────────────────────────────"
else
    warn "nginx не найден — настройте вручную"
fi

# ── Итог ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Установка завершена!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo "Проверка сервиса:"
echo "  curl http://localhost:$SERVICE_PORT/health"
echo ""
echo "После добавления nginx конфига:"
echo "  https://portal.farovon.tj/limits/"
echo ""
echo "Следующие шаги:"
echo "  1. Заполните $SERVICE_DIR/.env (BITRIX_WEBHOOK_URL, FIELD_DEPARTMENT)"
echo "  2. Добавьте блок из nginx.conf в конфиг nginx"
echo "  3. systemctl restart nginx"
echo "  4. Откройте https://portal.farovon.tj/limits/"
echo "  5. Настройте стадии в разделе Настройки"
echo "  6. Добавьте роботы в Битрикс24"
echo ""
echo "Управление сервисом:"
echo "  systemctl status  $SERVICE_NAME"
echo "  systemctl restart $SERVICE_NAME"
echo "  journalctl -u $SERVICE_NAME -f"
echo ""
