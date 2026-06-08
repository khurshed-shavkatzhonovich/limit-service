"""
logging_config.py — централизованная настройка логирования
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR   = os.getenv("LOG_DIR", "/app/logs")


def setup_logging():
    """
    Настраивает логирование:
      - В stdout (всегда) — для docker logs
      - В файл с ротацией (если LOG_DIR доступен)
    Формат: дата | уровень | модуль | сообщение
    """
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # ── Stdout ────────────────────────────────────────
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(fmt)
    stdout_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    root.addHandler(stdout_handler)

    # ── Файл с ротацией ────────────────────────────────
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = os.path.join(LOG_DIR, "limit-service.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,   # 10 МБ
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.DEBUG)  # В файл пишем всё включая DEBUG
        root.addHandler(file_handler)
        logging.getLogger(__name__).info(f"[LOG] Файл лога: {log_file}")
    except Exception as e:
        logging.getLogger(__name__).warning(f"[LOG] Не удалось создать файл лога: {e}")

    # Приглушаем слишком болтливые библиотеки
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if os.getenv("DB_ECHO") == "true" else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        f"[LOG] Логирование настроено | уровень={LOG_LEVEL} | "
        f"время={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
