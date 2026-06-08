# 🖥️ Характеристики сервера и развёртывание в Docker

---

## Часть 1 — Рекомендуемые характеристики сервера

### Что фактически потребляет сервис

| Компонент | Потребление |
|---|---|
| Python FastAPI + uvicorn | ~50–80 МБ RAM |
| SQLite + кэш БД | ~10–30 МБ RAM |
| Nginx (уже есть на сервере Б24) | ~5–10 МБ |
| ОС + Docker daemon | ~200–300 МБ |

**Пиковая нагрузка:** одновременных пользователей — финансисты (3–5 человек) + роботы Б24 (до 20 вебхуков/мин в пиковые часы). Это очень низкая нагрузка.

---

### Минимальные характеристики (только для сервиса лимитов)

```
CPU:   1 ядро (любой x86_64)
RAM:   512 МБ
Диск:  10 ГБ SSD
ОС:    Ubuntu 22.04 LTS
Сеть:  100 Мбит/с (только локальная сеть)
```

---

### Рекомендуемые характеристики (с запасом на рост)

```
CPU:   2 ядра (2.0+ GHz, x86_64)
RAM:   2 ГБ (под Docker + ОС + запас)
Диск:  40 ГБ SSD
  └── ОС + Docker:     ~8 ГБ
  └── Образы Docker:   ~1 ГБ
  └── База данных:     ~1 ГБ (хватит на 5+ лет)
  └── Логи (ротация):  ~2 ГБ
  └── Резерв:          ~28 ГБ
ОС:   Ubuntu 22.04 LTS
Сеть: 100 Мбит/с (LAN до Битрикс24)
```

> 💡 **Если сервис живёт на том же сервере что и Битрикс24** — никаких отдельных характеристик не нужно. Б24 уже имеет значительно более мощное железо. Docker-контейнер просто займёт ~100 МБ RAM рядом с PHP.

---

### Почему НЕ нужен мощный сервер

- **SQLite** — нет отдельного сервера БД, нет накладных расходов
- **Один процесс uvicorn** (`--workers 1`) — SQLite не поддерживает параллельные записи
- **Пользователи** — только внутренние сотрудники, не публичный интернет
- **Трафик** — несколько десятков запросов в минуту максимум
- **Данные** — база данных через 3 года не превысит 100 МБ

---

## Часть 2 — Структура проекта

```
limit-service-docker/
│
├── 📄 Dockerfile              # Сборка образа
├── 📄 docker-compose.yml      # Продакшн запуск
├── 📄 docker-compose.dev.yml  # Dev режим (hot-reload)
├── 📄 Makefile                # Удобные команды
├── 📄 .dockerignore           # Что не копировать в образ
│
├── 📄 main.py                 # FastAPI приложение
├── 📄 database.py             # Модели SQLite
├── 📄 bitrix.py               # Клиент Битрикс24 API
├── 📄 requirements.txt        # Python зависимости
│
├── 📁 templates/
│   └── 📄 index.html          # Веб-интерфейс
│
├── 📄 .env.example            # Шаблон конфига продакшн
├── 📄 .env.dev                # Конфиг для разработки
│
├── 📁 db/                     # База данных prod (создаётся автоматически)
├── 📁 db-dev/                 # База данных dev (создаётся автоматически)
├── 📁 logs/                   # Логи (создаётся автоматически)
└── 📁 backups/                # Резервные копии БД
```

---

## Часть 3 — Установка Docker

### Шаг 1: Установить Docker на Ubuntu

```bash
# Подключитесь к серверу
ssh root@ВАШ_IP

# Обновите пакеты
apt update && apt upgrade -y

# Установите Docker одной командой (официальный скрипт)
curl -fsSL https://get.docker.com | bash

# Проверьте установку
docker --version
# → Docker version 25.x.x

# Docker Compose входит в состав Docker v2 (команда: docker compose)
docker compose version
# → Docker Compose version v2.x.x

# (Опционально) Добавьте текущего пользователя в группу docker
# чтобы не писать sudo перед каждой командой
usermod -aG docker $USER
newgrp docker
```

---

## Часть 4 — Первый запуск (Dev режим)

> Начинаем с dev режима — сразу видите изменения кода без пересборки образа.

### Шаг 2: Загрузите файлы на сервер

```bash
# Вариант А: через scp (с вашего ПК)
scp limit-service-docker.zip root@ВАШ_IP:/opt/
ssh root@ВАШ_IP "cd /opt && unzip limit-service-docker.zip && mv limit-service-docker limit-service"

# Вариант Б: прямо на сервере создать папку
mkdir -p /opt/limit-service
cd /opt/limit-service
# и скопируйте файлы любым удобным способом (WinSCP, FileZilla, nano)
```

### Шаг 3: Настройте конфиг

```bash
cd /opt/limit-service

# Создайте .env.dev на основе шаблона
cp .env.dev .env.dev.backup   # на всякий случай
nano .env.dev
```

В редакторе заполните:
```env
BITRIX_WEBHOOK_URL=https://portal.farovon.tj/rest/1/ВАШ_РЕАЛЬНЫЙ_КЛЮЧ/
FIELD_DEPARTMENT=UF_CRM_5_XXXXXXXXXX    ← ваш код поля
WEBHOOK_SECRET=dev-secret-12345         ← можно оставить для dev
```

Сохранить: `Ctrl+O` → `Enter` → `Ctrl+X`

### Шаг 4: Запустите в dev режиме

```bash
cd /opt/limit-service

# Создаём нужные папки
mkdir -p db-dev logs

# Запуск (логи идут прямо в терминал — удобно для отладки)
make dev

# ИЛИ без make:
docker compose -f docker-compose.dev.yml up
```

Вы увидите:
```
limit-service-dev  | INFO:     Инициализация БД...
limit-service-dev  | INFO:     Демо-данные добавлены
limit-service-dev  | INFO:     Сервис лимитов запущен ✓
limit-service-dev  | INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Шаг 5: Проверьте что работает

```bash
# В другом терминале (или откройте в браузере):
curl http://localhost:8001/health
# → {"status":"ok","service":"limit-service",...}

# Или с вашего ПК (если 8001 открыт в firewall):
# http://IP_СЕРВЕРА:8001/
```

---

## Часть 5 — Отладка (Debug)

### Просмотр логов

```bash
# Логи в реальном времени (dev режим уже показывает всё в терминале)
make dev-logs
# ИЛИ
docker compose -f docker-compose.dev.yml logs -f

# Только ошибки:
docker compose -f docker-compose.dev.yml logs -f | grep -i error

# Последние 50 строк:
docker compose -f docker-compose.dev.yml logs --tail=50
```

### Войти внутрь контейнера

```bash
make dev-shell
# ИЛИ
docker compose -f docker-compose.dev.yml exec limit-service-dev /bin/sh

# Внутри контейнера можно:
ls /app                          # список файлов
cat /app/main.py                 # посмотреть код
python3 -c "from database import *; init_db(); print('OK')"
sqlite3 /data/limits-dev.db ".tables"   # таблицы БД
sqlite3 /data/limits-dev.db "SELECT * FROM departments;"
exit                             # выйти
```

### Hot-reload — изменение кода без перезапуска

В dev режиме uvicorn следит за изменениями .py файлов.
Просто отредактируйте файл на сервере:

```bash
nano /opt/limit-service/main.py
# сохраните — контейнер автоматически перезагрузит код

# В логах увидите:
# WARNING:  StatReload detected changes in 'main.py'. Reloading...
# INFO:     Сервис лимитов запущен ✓
```

### Тестирование вебхука вручную

```bash
# Тест: что происходит при смене стадии элемента #123
make test-webhook

# ИЛИ полный curl:
curl -X POST http://localhost:8001/webhook/stage \
  -H "Content-Type: application/json" \
  -d '{
    "element_id": 123,
    "stage_id": "DYNAMIC_139_38:1",
    "secret": "dev-secret-12345"
  }'

# Тест соединения с Битрикс24:
make test-b24

# Загрузить стадии из Б24:
curl http://localhost:8001/api/bitrix/stages | python3 -m json.tool

# Загрузить справочник валют:
curl http://localhost:8001/api/bitrix/currencies | python3 -m json.tool
```

### FastAPI автодокументация (Swagger)

В dev режиме доступна интерактивная документация всех API:
```
http://IP_СЕРВЕРА:8001/docs       ← Swagger UI (можно тестировать прямо там)
http://IP_СЕРВЕРА:8001/redoc      ← ReDoc (красивая документация)
```

### Посмотреть базу данных

```bash
# Вариант 1: через make
make db-shell

# Вариант 2: напрямую
docker compose -f docker-compose.dev.yml exec limit-service-dev \
  sqlite3 /data/limits-dev.db

# Полезные команды SQLite:
.tables                                    # список таблиц
.schema departments                        # структура таблицы
SELECT * FROM departments;                 # все подразделения
SELECT * FROM department_limits;           # все лимиты
SELECT * FROM limit_transactions ORDER BY created_at DESC LIMIT 10;
SELECT * FROM element_tracking;           # отслеживание заявок Б24
.quit                                     # выход
```

---

## Часть 6 — Продакшн запуск

После того как протестировали в dev — переключаетесь на prod.

### Шаг 1: Создайте prod .env

```bash
cd /opt/limit-service
cp .env.example .env
nano .env
```

Заполните все поля (особенно `WEBHOOK_SECRET` — сложный, случайный).

### Шаг 2: Запустите продакшн

```bash
# Остановите dev если запущен
make dev-down

# Создайте папки
mkdir -p db logs

# Запустите продакшн (в фоне)
make up
# ИЛИ
docker compose up -d

# Проверьте статус
make status
```

### Шаг 3: Настройте Nginx

```bash
nano /etc/nginx/sites-available/default
# Добавьте блок из nginx.conf (см. файл nginx.conf)

nginx -t
systemctl reload nginx
```

### Шаг 4: Проверьте через браузер

```
https://portal.farovon.tj/limits/
```

---

## Часть 7 — Управление (шпаргалка)

```bash
# ── СТАТУС ──────────────────────────────────────────
make status                    # статус + healthcheck

# ── ЛОГИ ────────────────────────────────────────────
make logs                      # prod логи live
make dev-logs                  # dev логи live
make logs-tail                 # последние 100 строк

# ── УПРАВЛЕНИЕ ──────────────────────────────────────
make up                        # запустить prod
make down                      # остановить prod
make restart                   # перезапустить prod
make dev                       # запустить dev
make dev-down                  # остановить dev

# ── ОБНОВЛЕНИЕ КОДА ─────────────────────────────────
# В dev: просто сохраните файл — hot-reload сам сработает
# В prod:
docker compose build && docker compose up -d --force-recreate

# ── БАЗА ДАННЫХ ──────────────────────────────────────
make backup                    # сохранить дамп в ./backups/
make db-shell                  # SQLite консоль prod
make db                        # показать список таблиц

# ── ОЧИСТКА ─────────────────────────────────────────
make clean                     # удалить неиспользуемые образы
```

---

## Часть 8 — Типичные проблемы и решения

### «Port 8001 already in use»
```bash
lsof -i :8001          # кто занял порт
kill -9 PID            # убить процесс
```

### «Permission denied» на папку db/
```bash
chmod 777 /opt/limit-service/db
chmod 777 /opt/limit-service/db-dev
```

### Контейнер падает сразу после запуска
```bash
# Смотрим что произошло (даже если контейнер уже остановлен):
docker compose logs limit-service
# Чаще всего: ошибка в .env или отсутствует нужная переменная
```

### Вебхук не принимается (403)
```bash
# Проверьте что WEBHOOK_SECRET в .env совпадает с параметром в роботе Б24
grep WEBHOOK_SECRET /opt/limit-service/.env
```

### Стадии не загружаются из Б24
```bash
# Проверьте BITRIX_WEBHOOK_URL и BITRIX_CATEGORY_ID в .env
curl http://localhost:8001/api/bitrix/test
curl http://localhost:8001/api/bitrix/categories
```
