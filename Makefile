# ════════════════════════════════════════════════════
# Makefile — удобные команды для управления сервисом
# Использование: make <команда>
# ════════════════════════════════════════════════════

.PHONY: help build up down restart logs shell db status dev dev-down dev-logs backup clean

# ── Цвета для вывода ────────────────────────────────
GREEN  = \033[0;32m
YELLOW = \033[1;33m
BLUE   = \033[0;34m
NC     = \033[0m

help: ## Показать список команд
	@echo ""
	@echo "$(BLUE)Сервис контроля лимитов Битрикс24$(NC)"
	@echo "────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ── ПРОДАКШН ────────────────────────────────────────
build: ## Пересобрать образ
	docker compose build --no-cache

up: ## Запустить сервис (продакшн)
	@mkdir -p db logs
	docker compose up -d
	@echo "$(GREEN)✓ Сервис запущен: http://localhost:8001$(NC)"

down: ## Остановить сервис
	docker compose down
	@echo "$(YELLOW)✓ Сервис остановлен$(NC)"

restart: ## Перезапустить сервис
	docker compose restart limit-service
	@echo "$(GREEN)✓ Сервис перезапущен$(NC)"

logs: ## Логи в реальном времени (Ctrl+C для выхода)
	docker compose logs -f limit-service

logs-tail: ## Последние 100 строк логов
	docker compose logs --tail=100 limit-service

status: ## Статус контейнеров
	@docker compose ps
	@echo ""
	@echo "$(BLUE)Healthcheck:$(NC)"
	@curl -s http://localhost:8001/health | python3 -m json.tool 2>/dev/null || echo "Сервис недоступен"

shell: ## Войти в контейнер (bash)
	docker compose exec limit-service /bin/bash || \
	docker compose exec limit-service /bin/sh

# ── РАЗРАБОТКА ───────────────────────────────────────
dev: ## Запустить в режиме разработки (hot-reload)
	@mkdir -p db-dev
	docker compose -f docker-compose.dev.yml up
	@echo "$(GREEN)✓ Dev-сервер: http://localhost:8001$(NC)"

dev-bg: ## Запустить dev в фоне
	@mkdir -p db-dev
	docker compose -f docker-compose.dev.yml up -d

dev-down: ## Остановить dev
	docker compose -f docker-compose.dev.yml down

dev-logs: ## Логи dev-сервера
	docker compose -f docker-compose.dev.yml logs -f

dev-shell: ## Войти в dev-контейнер
	docker compose -f docker-compose.dev.yml exec limit-service-dev /bin/sh

dev-rebuild: ## Пересобрать и перезапустить dev
	docker compose -f docker-compose.dev.yml down
	docker compose -f docker-compose.dev.yml build --no-cache
	docker compose -f docker-compose.dev.yml up

# ── БАЗА ДАННЫХ ──────────────────────────────────────
db: ## Открыть SQLite консоль
	@docker compose exec limit-service \
		python3 -c "import sqlite3; \
		conn = sqlite3.connect('/data/limits.db'); \
		[print(r) for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]; \
		conn.close(); print('Таблицы перечислены выше')"

db-shell: ## SQLite shell напрямую
	docker compose exec limit-service sqlite3 /data/limits.db

db-dump: ## Дамп базы данных
	@mkdir -p backups
	@FILENAME="backups/limits_$$(date +%Y%m%d_%H%M%S).db"; \
	docker compose cp limit-service:/data/limits.db $$FILENAME; \
	echo "$(GREEN)✓ Дамп сохранён: $$FILENAME$(NC)"

backup: db-dump ## Алиас для db-dump

# ── ОБСЛУЖИВАНИЕ ─────────────────────────────────────
update: ## Обновить код и перезапустить (без потери данных)
	git pull 2>/dev/null || true
	docker compose build
	docker compose up -d --force-recreate
	@echo "$(GREEN)✓ Обновление завершено$(NC)"

clean: ## Удалить остановленные контейнеры и неиспользуемые образы
	docker compose down
	docker image prune -f
	@echo "$(YELLOW)✓ Очистка завершена$(NC)"

clean-all: ## ОСТОРОЖНО: удалить ВСЁ включая данные
	@echo "$(YELLOW)Вы уверены? Это удалит ВСЕ данные! Введите YES:$(NC)"
	@read confirm; if [ "$$confirm" = "YES" ]; then \
		docker compose down -v; \
		rm -rf db db-dev logs; \
		docker image rm limit-service 2>/dev/null || true; \
		echo "$(GREEN)✓ Всё удалено$(NC)"; \
	else \
		echo "Отменено"; \
	fi

# ── ТЕСТИРОВАНИЕ ─────────────────────────────────────
test-webhook: ## Тест вебхука (требует .env с WEBHOOK_SECRET)
	@SECRET=$$(grep WEBHOOK_SECRET .env | cut -d= -f2); \
	curl -s -X POST http://localhost:8001/webhook/stage \
		-H "Content-Type: application/json" \
		-d "{\"element_id\": 999, \"stage_id\": \"TEST\", \"secret\": \"$$SECRET\"}" | \
		python3 -m json.tool

test-health: ## Проверить что сервис жив
	@curl -sf http://localhost:8001/health | python3 -m json.tool

test-stats: ## Получить статистику
	@curl -sf http://localhost:8001/api/stats | python3 -m json.tool

test-b24: ## Тест соединения с Битрикс24
	@curl -sf http://localhost:8001/api/bitrix/test | python3 -m json.tool
