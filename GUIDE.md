# 📖 Инструкция по установке и настройке
## Сервис контроля лимитов для Битрикс24

---

## Архитектура решения

```
Сервер Битрикс24 (portal.farovon.tj)
│
├── Битрикс24 (PHP, порт 80/443)
│     └── Смарт-процесс ID=139
│           └── Роботы на стадиях → вызывают наш вебхук
│
├── Nginx (порт 443)
│     ├── / → Битрикс24
│     └── /limits/ → проксирует на порт 8001
│
└── Python FastAPI (порт 8001, systemd)
      └── SQLite база данных /opt/limit-service/limits.db
```

---

## ШАГ 1: Подключение к серверу

```bash
ssh root@ВАШ_IP_СЕРВЕРА
```

---

## ШАГ 2: Загрузка файлов

```bash
# Создаём папку
mkdir -p /opt/limit-service-install
cd /opt/limit-service-install

# Загружаем файлы (скопируйте все файлы из архива)
# ИЛИ создайте файлы вручную (содержимое в архиве)
```

**Структура файлов для загрузки:**
```
limit-service-install/
├── main.py
├── database.py
├── bitrix.py
├── requirements.txt
├── .env.example
├── install.sh
├── limit-service.service
├── nginx.conf
└── templates/
    └── index.html
```

---

## ШАГ 3: Запуск установщика

```bash
cd /opt/limit-service-install
chmod +x install.sh
sudo bash install.sh
```

Скрипт автоматически:
- Создаст `/opt/limit-service/`
- Создаст Python виртуальное окружение
- Установит зависимости
- Зарегистрирует systemd сервис
- Запустит сервис

---

## ШАГ 4: Настройка .env файла

```bash
nano /opt/limit-service/.env
```

**Заполните обязательные поля:**

```env
# 1. Ваш REST API вебхук из Битрикс24
# Создайте в: Битрикс24 → Настройки → Разработчикам → Входящий вебхук
# Выберите права: CRM (чтение/запись)
BITRIX_WEBHOOK_URL=https://portal.farovon.tj/rest/1/ВАШ_КЛЮЧ/

# 2. Код поля Подразделение (определяется в ШАГ 6)
FIELD_DEPARTMENT=UF_CRM_5_XXXXXXXXXX
```

**После изменения .env перезапустите сервис:**
```bash
systemctl restart limit-service
```

---

## ШАГ 5: Настройка Nginx

Откройте конфиг nginx для вашего домена:
```bash
# Обычно один из этих файлов:
nano /etc/nginx/sites-available/default
# ИЛИ
nano /etc/nginx/conf.d/bitrix.conf
# ИЛИ найдите через:
grep -r "portal.farovon.tj" /etc/nginx/
```

**Добавьте внутрь существующего блока `server { }`:**
```nginx
location /limits/ {
    proxy_pass         http://127.0.0.1:8001/;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
}

location /limits/webhook/ {
    proxy_pass         http://127.0.0.1:8001/webhook/;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
}
```

**Проверьте и перезапустите nginx:**
```bash
nginx -t          # проверка конфига
systemctl reload nginx
```

**Проверьте что сервис работает:**
```bash
curl https://portal.farovon.tj/limits/health
# Должен вернуть: {"status":"ok","service":"limit-service",...}
```

---

## ШАГ 6: Найти код поля «Подразделение»

1. Зайдите в Битрикс24
2. CRM → Смарт-процессы → Ваш смарт-процесс
3. Настройки (шестерёнка) → Поля
4. Найдите поле с названием «Подразделение» или «Отдел»
5. Нажмите на него — в URL будет `fieldId=XXX`
6. Или посмотрите код вида `UF_CRM_5_XXXXXXXXXX`
7. Вставьте код в `.env` в строку `FIELD_DEPARTMENT=`

**Если поля «Подразделение» нет — создайте его:**
- Тип: «Список» или «Привязка к пользователю»
- Рекомендуем тип «Список» с перечислением отделов

---

## ШАГ 7: Первоначальная настройка через веб-интерфейс

Откройте: `https://portal.farovon.tj/limits/`

### 7.1 Подразделения
- Перейдите в раздел **«Подразделения»**
- Добавьте ваши реальные подразделения
- В поле **«Значение в Б24»** укажите ТОЧНО то значение,
  которое будет в поле «Подразделение» в заявках Б24

### 7.2 Лимиты
- Перейдите в раздел **«Лимиты»**
- Нажмите «Установить лимит» для каждого подразделения
- Укажите год, валюту и сумму

### 7.3 Настройки стадий
- Перейдите в раздел **«Настройки»**
- Нажмите **«Тест соединения»** — должен вернуть ваше имя
- Нажмите **«Загрузить стадии из Б24»**
- Выберите соответствие стадий:
  - Резервирование → **«Одобренные»**
  - Исполнение → **«Исполненные»**
  - Отклонение → **«Отклонённые»**
  - Внеплановые расходы → **«Внеплановые расходы»** (создайте если нет)

---

## ШАГ 8: Создать стадию «Внеплановые расходы» в Б24

1. CRM → Смарт-процессы → Ваш процесс
2. Канбан → Добавить колонку (стадию)
3. Название: **«Внеплановые расходы»**
4. Вернитесь в настройки сервиса и выберите эту стадию

---

## ШАГ 9: Настройка роботов в Битрикс24

### Для стадии «Одобренные»:
1. CRM → Смарт-процессы → Автоматизация
2. Выберите стадию **«Одобренные»**
3. Добавить робота → **«Исходящий вебхук»**
4. Настройки:
   - **Адрес**: `https://portal.farovon.tj/limits/webhook/stage`
   - **Метод**: POST
   - **Тип кодирования**: JSON
   - **Параметры**:
     ```
     element_id = {=Document:ID}
     stage_id = {=Document:STAGE_ID}
     secret = ВАШ_WEBHOOK_SECRET_ИЗ_ENV
     ```
5. Сохранить

### Повторите для стадий «Исполненные» и «Отклонённые»

> ⚠️ **Важно**: значение `secret` должно совпадать с `WEBHOOK_SECRET` в вашем `.env` файле

---

## Логика работы (итоговая схема)

```
Сотрудник создаёт заявку → стадия «Новая»
         │
         ▼ Финансист одобряет
     Стадия «Одобренные»
         │
         ▼ Робот вызывает вебхук
    Сервис лимитов проверяет:
         │
         ├─ Лимит ЕСТЬ → Резервирует сумму
         │               → Комментарий в Б24: «Лимит подтверждён»
         │               → Продолжает работу в Б24
         │
         └─ Лимита НЕТ → Комментарий: «Лимит превышен»
                         → Переводит заявку в «Внеплановые расходы»
                         → Зам по финансам видит и решает

При стадии «Исполненные»:
    Резерв → Факт (списывается с лимита)

При стадии «Отклонённые»:
    Резерв снимается (лимит возвращается)
```

---

## Управление сервисом

```bash
# Статус
systemctl status limit-service

# Перезапуск (после изменения .env)
systemctl restart limit-service

# Логи в реальном времени
journalctl -u limit-service -f

# Логи последних 100 строк
journalctl -u limit-service -n 100

# Остановить
systemctl stop limit-service

# База данных (для ручной проверки)
sqlite3 /opt/limit-service/limits.db ".tables"
sqlite3 /opt/limit-service/limits.db "SELECT * FROM departments;"
```

---

## Устранение проблем

### Сервис не запускается
```bash
journalctl -u limit-service -n 50
# Проверьте .env файл, права на папку, python версию
```

### Вебхук не работает
```bash
# Проверьте что сервис слушает порт:
curl http://127.0.0.1:8001/health

# Проверьте nginx:
curl https://portal.farovon.tj/limits/health

# Тест вебхука вручную:
curl -X POST https://portal.farovon.tj/limits/webhook/stage \
  -H "Content-Type: application/json" \
  -d '{"element_id": 123, "stage_id": "TEST", "secret": "ВАШ_СЕКРЕТ"}'
```

### Стадии не загружаются
- Проверьте `BITRIX_WEBHOOK_URL` в `.env`
- Убедитесь что вебхук в Б24 имеет права на CRM
- Проверьте `BITRIX_ENTITY_TYPE_ID=139`

### Подразделение не определяется
- Убедитесь что `FIELD_DEPARTMENT` в `.env` — правильный код поля
- Проверьте что значение «Значение в Б24» в подразделении
  ТОЧНО совпадает со значением поля в заявке

---

## Обновление сервиса

```bash
# Скопируйте новые файлы в /opt/limit-service/
# Перезапустите:
systemctl restart limit-service
```
