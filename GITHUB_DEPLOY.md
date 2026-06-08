# 🚀 Инструкция: GitHub → Сервер

## Полный путь: локально → GitHub → сервер → запуск

---

## ЧАСТЬ 1 — Подготовка GitHub

### Шаг 1.1 — Создать репозиторий

1. Зайдите на https://github.com
2. Нажмите **"New repository"** (зелёная кнопка)
3. Заполните:
   - **Repository name:** `limit-service`
   - **Description:** `Сервис контроля лимитов расходов для Битрикс24`
   - ⚫ **Private** — ОБЯЗАТЕЛЬНО приватный (там будут .env файлы с токенами)
   - ❌ НЕ ставьте галочки "Add README", "Add .gitignore" — у нас уже есть свои
4. Нажмите **"Create repository"**
5. Скопируйте URL репозитория:
   ```
   https://github.com/ВАШ_ЛОГИН/limit-service.git
   ```

---

### Шаг 1.2 — Создать Personal Access Token (PAT)

> PAT — это пароль для работы с GitHub через командную строку.
> Нужен один раз — потом сохраним на сервере навсегда.

1. GitHub → правый верхний угол → **ваш аватар → Settings**
2. Прокрутите вниз → **Developer settings** (самый низ левого меню)
3. **Personal access tokens → Tokens (classic)**
4. Нажмите **"Generate new token" → "Generate new token (classic)"**
5. Заполните:
   - **Note:** `limit-service-server` (описание для себя)
   - **Expiration:** `No expiration` (бессрочный — удобно для сервера)
   - Поставьте галочки:
     - ✅ **repo** (раскроется подменю — нужны все подпункты)
6. Нажмите **"Generate token"**
7. ⚠️ СКОПИРУЙТЕ токен СРАЗУ — GitHub покажет его только один раз!
   ```
   ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   Сохраните в надёжном месте (менеджер паролей, заметка).

---

## ЧАСТЬ 2 — Заливаем проект на GitHub (с вашего ПК)

### Шаг 2.1 — Установить Git (если нет)

**Windows:** скачайте с https://git-scm.com/download/win

**Ubuntu/Debian:**
```bash
sudo apt install git -y
```

### Шаг 2.2 — Настроить Git

```bash
git config --global user.name  "Ваше Имя"
git config --global user.email "ваш@email.com"
```

### Шаг 2.3 — Инициализировать репозиторий и залить

```bash
# Перейдите в папку с проектом
cd /путь/к/limit-service-docker

# Проверьте что .gitignore на месте
cat .gitignore   # должен увидеть список исключений

# Инициализируем git
git init

# Добавляем все файлы (кроме исключённых в .gitignore)
git add .

# Проверяем что добавилось (убеждаемся что .env НЕТ в списке!)
git status
# Должны быть: main.py, database.py, bitrix.py, Dockerfile, ...
# НЕ ДОЛЖНЫ быть: .env, *.db, db/, logs/

# Первый коммит
git commit -m "Initial commit: limit service v1.2.0"

# Указываем главную ветку
git branch -M main

# Подключаем GitHub репозиторий
git remote add origin https://github.com/ВАШ_ЛОГИН/limit-service.git

# Загружаем на GitHub
# При запросе логина — введите ваш GitHub логин
# При запросе пароля — вставьте PAT токен (не пароль GitHub!)
git push -u origin main
```

**Если всё прошло успешно**, зайдите на https://github.com/ВАШ_ЛОГИН/limit-service — увидите все файлы.

---

## ЧАСТЬ 3 — Настройка сервера

### Шаг 3.1 — Подключиться к серверу

```bash
ssh root@IP_ВАШЕГО_СЕРВЕРА
```

### Шаг 3.2 — Установить Git и Docker

```bash
# Обновить пакеты
apt update && apt upgrade -y

# Установить git
apt install git -y
git --version
# → git version 2.x.x

# Установить Docker (официальный скрипт)
curl -fsSL https://get.docker.com | bash
docker --version
# → Docker version 25.x.x

docker compose version
# → Docker Compose version v2.x.x
```

### Шаг 3.3 — Настроить Git на сервере

```bash
git config --global user.name  "Server"
git config --global user.email "server@farovon.tj"
```

---

## ЧАСТЬ 4 — Сохранить PAT токен НАВСЕГДА на сервере

> Это самый важный шаг — после него Git никогда не будет
> спрашивать пароль на этом сервере.

### Метод: ~/.git-credentials (рекомендуется)

```bash
# 1. Включаем хранилище учётных данных
git config --global credential.helper store

# 2. Записываем токен в файл
# ЗАМЕНИТЕ: ВАШ_ЛОГИН и ВАШ_PAT_ТОКЕН
echo "https://ВАШ_ЛОГИН:ВАШ_PAT_ТОКЕН@github.com" > ~/.git-credentials

# 3. Защищаем файл (только владелец может читать)
chmod 600 ~/.git-credentials

# 4. Проверяем что записалось правильно
cat ~/.git-credentials
# → https://ВАШ_ЛОГИН:ghp_xxxx...@github.com
```

### Проверка: клонируем без ввода пароля

```bash
# Тестовое клонирование (должно пройти без запроса пароля)
cd /tmp
git clone https://github.com/ВАШ_ЛОГИН/limit-service.git test-clone
# → Cloning into 'test-clone'...  (без запроса пароля!)
rm -rf /tmp/test-clone
echo "✓ Токен сохранён успешно"
```

---

## ЧАСТЬ 5 — Развёртывание на сервере

### Шаг 5.1 — Клонировать репозиторий

```bash
# Создаём рабочую директорию
mkdir -p /opt/services
cd /opt/services

# Клонируем проект
git clone https://github.com/ВАШ_ЛОГИН/limit-service.git
cd limit-service

# Проверяем структуру
ls -la
# Должны видеть: main.py, database.py, Dockerfile, docker-compose.yml ...
```

### Шаг 5.2 — Создать .env файл

```bash
# .env НЕ хранится в git — создаём вручную на сервере
cp .env.example .env
nano .env
```

Заполните в редакторе:
```env
# ── Битрикс24 ─────────────────────────────────
BITRIX_WEBHOOK_URL=https://portal.farovon.tj/rest/1/ВАШ_РЕАЛЬНЫЙ_КЛЮЧ/
BITRIX_ENTITY_TYPE_ID=139
BITRIX_CATEGORY_ID=38
FIELD_AMOUNT=UF_CRM_5_1698135335
FIELD_CURRENCY=UF_CRM_5_1698136041
FIELD_DEPARTMENT=UF_CRM_5_XXXXXXXXXX

# ── Безопасность ──────────────────────────────
WEBHOOK_SECRET=придумайте-сложную-строку-минимум-32-символа

# ── База данных ───────────────────────────────
DATABASE_URL=sqlite:////data/limits.db

# ── Логирование ───────────────────────────────
LOG_LEVEL=INFO
# LOG_LEVEL=DEBUG   ← раскомментируйте для отладки
# DB_ECHO=true      ← раскомментируйте чтобы видеть SQL запросы
```

Сохранить: `Ctrl+O` → `Enter` → `Ctrl+X`

### Шаг 5.3 — Создать нужные папки

```bash
mkdir -p db logs backups
```

### Шаг 5.4 — Собрать и запустить

```bash
# Сборка Docker образа (первый раз ~2-3 минуты)
docker compose build
# Увидите:
# [+] Building 45.3s (10/10) FINISHED
# => [internal] load build definition from Dockerfile
# => [1/5] FROM python:3.11-slim
# => [2/5] COPY requirements.txt .
# => [3/5] RUN pip install ...
# => Successfully built ...

# Запуск в фоне
docker compose up -d

# Проверяем статус (подождите 10-15 секунд)
docker compose ps
# Должны видеть: limit-service  running (healthy)
```

### Шаг 5.5 — Проверка запуска

```bash
# 1. Статус контейнера
docker compose ps

# 2. Логи запуска (самое важное!)
docker compose logs limit-service
# Должны увидеть:
# ============================================================
# [STARTUP] Сервис контроля лимитов стартует...
# [STARTUP] LOG_LEVEL        = INFO
# [STARTUP] DATABASE_URL      = sqlite:////data/limits.db
# [STARTUP] ENTITY_TYPE_ID    = 139
# ...
# [DB] Создание таблиц...
# [DB] Таблицы готовы
# [SEED] Заполняем тестовые данные на 2025 год...
# [SEED]   + Птицефабрика — основной цех: лимит=8,000,000, ...
# [SEED]   + Птицефабрика — ветеринария: лимит=3,500,000, ...
# ...
# [SEED] ✓ Тестовые данные добавлены: 10 подразделений
# [STARTUP] ✓ Сервис готов к работе
# ============================================================

# 3. Healthcheck
curl http://localhost:8001/health
# → {"status":"ok","service":"limit-service","version":"1.2.0",...}
```

### Шаг 5.6 — Настройка Nginx

```bash
# Найдите ваш nginx конфиг для portal.farovon.tj
grep -r "farovon.tj" /etc/nginx/ 2>/dev/null | grep -v ".swp"
# Покажет путь к конфигу

# Откройте найденный файл (пример пути):
nano /etc/nginx/sites-available/bitrix

# Добавьте ВНУТРЬ существующего server {} блока:
```
```nginx
    location /limits/ {
        proxy_pass         http://127.0.0.1:8001/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 30;
    }
    location /limits/webhook/ {
        proxy_pass         http://127.0.0.1:8001/webhook/;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }
```
```bash
# Проверьте конфиг и перезапустите
nginx -t
# → nginx: configuration file ... syntax is ok
# → nginx: configuration file ... test is successful

systemctl reload nginx

# Финальная проверка через домен
curl https://portal.farovon.tj/limits/health
# → {"status":"ok",...}
```

---

## ЧАСТЬ 6 — Обновление кода (рабочий процесс)

### Когда вносите правки — полный цикл:

```bash
# ── НА ВАШЕМ ПК ─────────────────────────────────────
# Вносите изменения в код
nano main.py  # или любой файл

# Коммит и пуш
git add .
git commit -m "Описание: что изменили"
git push

# ── НА СЕРВЕРЕ ───────────────────────────────────────
cd /opt/services/limit-service

# Скачиваем изменения
git pull
# → Updating abc1234..def5678
# → main.py | 5 ++---

# Пересобираем и перезапускаем (без потери данных!)
docker compose build
docker compose up -d --force-recreate

# Проверяем логи
docker compose logs -f limit-service --tail=50
```

### Быстрое обновление (если Dockerfile не менялся):

```bash
git pull && docker compose up -d --force-recreate --no-deps limit-service
```

---

## ЧАСТЬ 7 — Отладка: читаем логи

### Основные команды

```bash
# Все логи с начала запуска
docker compose logs limit-service

# Живые логи (Ctrl+C для выхода)
docker compose logs -f limit-service

# Только последние 100 строк
docker compose logs --tail=100 limit-service

# Фильтрация — только ошибки
docker compose logs limit-service 2>&1 | grep -E "ERROR|WARNING|✗"

# Фильтрация — только вебхуки
docker compose logs limit-service 2>&1 | grep "WEBHOOK"

# Фильтрация — только Битрикс24
docker compose logs limit-service 2>&1 | grep "B24"

# Логи с временными метками
docker compose logs -f --timestamps limit-service
```

### Включить DEBUG режим (видно всё):

```bash
# Меняем в .env:
nano .env
# LOG_LEVEL=DEBUG   ← раскомментируйте

# Перезапускаем
docker compose up -d --force-recreate

# Теперь в логах видно каждый HTTP запрос и ответ
```

### Включить SQL логи (видно все запросы к БД):

```bash
# В .env:
# DB_ECHO=true

docker compose up -d --force-recreate
# В логах появятся строки вида:
# SELECT departments.id, departments.name ...
```

### Войти внутрь контейнера для отладки:

```bash
docker compose exec limit-service /bin/sh

# Внутри:
python3 -c "from database import *; init_db(); print('DB OK')"
sqlite3 /data/limits.db ".tables"
sqlite3 /data/limits.db "SELECT name, used_amount, limit_amount FROM department_limits dl JOIN departments d ON d.id=dl.department_id;"
exit
```

### Тест вебхука вручную:

```bash
SECRET=$(grep WEBHOOK_SECRET /opt/services/limit-service/.env | cut -d= -f2)

curl -v -X POST http://localhost:8001/webhook/stage \
  -H "Content-Type: application/json" \
  -d "{\"element_id\": 9999, \"stage_id\": \"ТЕСТ\", \"secret\": \"$SECRET\"}"
```

---

## ЧАСТЬ 8 — Резервное копирование

```bash
# Бэкап базы данных
cp /opt/services/limit-service/db/limits.db \
   /opt/services/limit-service/backups/limits_$(date +%Y%m%d_%H%M%S).db

# Автоматический бэкап через cron (каждый день в 2:00 ночи)
crontab -e
# Добавьте строку:
0 2 * * * cp /opt/services/limit-service/db/limits.db \
  /opt/services/limit-service/backups/limits_$(date +\%Y\%m\%d).db
```

---

## Шпаргалка команд

```bash
# ── GITHUB ──────────────────────────────────────────
git status                    # что изменилось
git add . && git commit -m "..." && git push   # залить
git pull                      # скачать изменения

# ── СЕРВИС ──────────────────────────────────────────
docker compose up -d          # запустить
docker compose down           # остановить
docker compose restart        # перезапустить
docker compose ps             # статус

# ── ЛОГИ ────────────────────────────────────────────
docker compose logs -f limit-service             # живые логи
docker compose logs --tail=50 limit-service      # последние 50 строк
docker compose logs limit-service 2>&1 | grep ERROR

# ── ОБНОВЛЕНИЕ ──────────────────────────────────────
git pull && docker compose build && docker compose up -d --force-recreate

# ── БЭКАП ───────────────────────────────────────────
cp db/limits.db backups/limits_$(date +%Y%m%d).db
```
