"""
database.py — модели базы данных SQLite
"""
import logging
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, ForeignKey, UniqueConstraint, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/limits.db")
logger.info(f"[DB] DATABASE_URL = {DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    execution_options={"isolation_level": "SERIALIZABLE"},
    echo=os.getenv("DB_ECHO", "false").lower() == "true",  # SQL-запросы в лог при DB_ECHO=true
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    bitrix_department_value = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    limits = relationship("DepartmentLimit", back_populates="department", cascade="all, delete-orphan")
    transactions = relationship("LimitTransaction", back_populates="department")
    tracking = relationship("ElementTracking", back_populates="department")


class DepartmentLimit(Base):
    __tablename__ = "department_limits"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    year = Column(Integer, nullable=False)
    currency = Column(String(10), default="TJS", nullable=False)
    limit_amount = Column(Float, default=0.0, nullable=False)
    used_amount = Column(Float, default=0.0, nullable=False)
    reserved_amount = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    department = relationship("Department", back_populates="limits")
    __table_args__ = (UniqueConstraint("department_id", "year", "currency", name="uq_dept_year_currency"),)

    @property
    def available_amount(self):
        return max(0.0, self.limit_amount - self.used_amount - self.reserved_amount)

    @property
    def used_percent(self):
        if self.limit_amount <= 0:
            return 0
        return round((self.used_amount + self.reserved_amount) / self.limit_amount * 100, 1)


class LimitTransaction(Base):
    __tablename__ = "limit_transactions"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    year = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(50), nullable=False)
    bitrix_element_id = Column(Integer, nullable=True, index=True)
    bitrix_stage = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    department = relationship("Department", back_populates="transactions")
    TYPE_LABELS = {
        "reserve":       "🔒 Резерв",
        "release":       "🔓 Снятие резерва",
        "execute":       "✅ Исполнено",
        "manual_adjust": "✏️ Корректировка",
        "unplanned":     "⚠️ Внеплановый",
    }


class ElementTracking(Base):
    __tablename__ = "element_tracking"
    id = Column(Integer, primary_key=True, index=True)
    bitrix_element_id = Column(Integer, unique=True, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    year = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    last_stage = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    department = relationship("Department", back_populates="tracking")


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    logger.info("[DB] Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    logger.info("[DB] Таблицы готовы")
    db = SessionLocal()
    try:
        defaults = [
            ("stage_reserve",    "", "ID стадии резервирования (Одобренные)"),
            ("stage_execute",    "", "ID стадии исполнения (Исполненные)"),
            ("stage_release",    "", "ID стадии отклонения (Отклонённые)"),
            ("stage_unplanned",  "", "ID стадии внепланового расхода"),
            ("field_department", "", "Код поля Подразделение в смарт-процессе"),
        ]
        for key, val, desc in defaults:
            if not db.query(Setting).filter_by(key=key).first():
                db.add(Setting(key=key, value=val, description=desc))
        db.commit()
        logger.info("[DB] Настройки по умолчанию проверены")
    finally:
        db.close()


def seed_test_data():
    """
    Тестовые данные: реалистичные подразделения птицефабрики.
    Часть лимитов намеренно превышена — для демонстрации логики.
    """
    db = SessionLocal()
    try:
        if db.query(Department).count() > 0:
            logger.info("[SEED] Данные уже есть, пропускаем")
            return

        year = datetime.now().year
        logger.info(f"[SEED] Заполняем тестовые данные на {year} год...")

        # (название, bitrix_value, лимит TJS, использовано, зарезервировано, описание)
        departments_data = [
            ("Птицефабрика — основной цех",   "ptitsa_main",   8_000_000, 3_200_000, 800_000,  "Основное производство, содержание птицы"),
            ("Птицефабрика — ветеринария",     "ptitsa_vet",    3_500_000, 3_100_000, 600_000,  "Лекарства, вакцины, ветуслуги"),
            ("Птицефабрика — кормовой цех",    "ptitsa_feed",   6_000_000, 2_400_000, 500_000,  "Закупка и производство кормов"),
            ("Птицефабрика — инкубатор",       "ptitsa_incub",  2_000_000,   800_000, 100_000,  "Инкубационное яйцо, оборудование"),
            ("Птицефабрика — убойный цех",     "ptitsa_slaughter", 4_000_000, 1_600_000, 200_000, "Убой и первичная переработка"),
            ("Отдел снабжения",                "supply",        5_000_000, 1_750_000, 300_000,  "Закупки ТМЦ, логистика"),
            ("Финансовый отдел",               "finance",         800_000,   240_000,  60_000,  "Операционные расходы финансистов"),
            ("Административный отдел",         "admin",         1_200_000,   480_000, 120_000,  "Офисные, хозяйственные расходы"),
            ("Технический отдел",              "tech",          3_000_000,   900_000, 200_000,  "Ремонт, запчасти, обслуживание"),
            ("Отдел продаж",                   "sales",           900_000,   270_000,  80_000,  "Командировки, представительские"),
        ]

        for name, b_val, limit, used, reserved, desc in departments_data:
            dept = Department(name=name, bitrix_department_value=b_val, description=desc)
            db.add(dept)
            db.flush()
            db.add(DepartmentLimit(
                department_id=dept.id, year=year, currency="TJS",
                limit_amount=float(limit),
                used_amount=float(used),
                reserved_amount=float(reserved),
            ))
            # Тестовые транзакции (история)
            db.add(LimitTransaction(
                department_id=dept.id, year=year, currency="TJS",
                amount=float(limit), transaction_type="manual_adjust",
                note=f"Установлен начальный лимит на {year} год", created_by="admin",
            ))
            if used > 0:
                db.add(LimitTransaction(
                    department_id=dept.id, year=year, currency="TJS",
                    amount=float(used), transaction_type="execute",
                    note="Суммарные исполненные заявки (тестовые данные)", created_by="system",
                ))
            logger.info(f"[SEED]   + {name}: лимит={limit:,}, использ={used:,}, резерв={reserved:,}")

        # Несколько отделов имеют USD-лимиты (импортные препараты и т.д.)
        usd_data = [
            ("Птицефабрика — ветеринария", 50_000, 18_000, 5_000),
            ("Отдел снабжения",            30_000, 12_000, 2_000),
        ]
        for dept_bval, limit, used, reserved in usd_data:
            dept = db.query(Department).filter_by(bitrix_department_value=dept_bval).first()
            if dept:
                db.add(DepartmentLimit(
                    department_id=dept.id, year=year, currency="USD",
                    limit_amount=float(limit), used_amount=float(used), reserved_amount=float(reserved),
                ))
                logger.info(f"[SEED]   + {dept.name}: USD лимит={limit:,}")

        db.commit()
        logger.info(f"[SEED] ✓ Тестовые данные добавлены: {len(departments_data)} подразделений")

    except Exception as e:
        db.rollback()
        logger.error(f"[SEED] ✗ Ошибка: {e}", exc_info=True)
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
