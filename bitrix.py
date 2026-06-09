"""
bitrix.py — клиент для работы с REST API Битрикс24
Обновлён с учётом анализа реального кода смарт-процесса:
  - categoryId = 38 → ENTITY_ID стадий = DYNAMIC_139_38
  - Валюта хранится как числовой ID из списка (LIST-поле)
"""
import httpx
import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

BITRIX_WEBHOOK_URL  = os.getenv("BITRIX_WEBHOOK_URL", "")
ENTITY_TYPE_ID      = int(os.getenv("BITRIX_ENTITY_TYPE_ID", "139"))
CATEGORY_ID         = int(os.getenv("BITRIX_CATEGORY_ID", "38"))   # setCategoryId(38)

# ── Коды полей (из реального кода смарт-процесса) ───────────────
FIELD_AMOUNT        = os.getenv("FIELD_AMOUNT",      "UF_CRM_5_1698135335")  # Сумма заявки
FIELD_CURRENCY      = os.getenv("FIELD_CURRENCY",    "UF_CRM_5_1698136041")  # Валюта (LIST-поле → числовой ID)
FIELD_DEPARTMENT    = os.getenv("FIELD_DEPARTMENT",  "")                     # Подразделение — заполнить после создания
FIELD_REQUEST_TYPE  = "UF_CRM_5_1718865244"  # Вид заявки
FIELD_APPROVER      = "UF_CRM_5_1713004245"  # Одобряющий руководитель
FIELD_RECIPIENT     = "UF_CRM_5_1696328690"  # Получатель денежных средств (Moneygiver)
FIELD_PURPOSE       = "UF_CRM_5_1713002952"  # Назначение
FIELD_CASHIER       = "UF_CRM_5_1696414797"  # Кассир

# ── Маппинг валют: значение в Б24 → код ISO ─────────────────────
CURRENCY_NAME_TO_CODE = {
    "сомони":            "TJS",
    "доллар сша":        "USD",
    "евро":              "EUR",
    "российский рубль":  "RUB",
    "тенге":             "KZT",
    "юань":              "CNY",
    "узбекский сум":     "UZS",
}


class BitrixClient:

    def __init__(self):
        self.webhook_url    = BITRIX_WEBHOOK_URL.rstrip("/")
        self.entity_type_id = ENTITY_TYPE_ID
        self.category_id    = CATEGORY_ID
        # Кэш: {enum_id: currency_code}
        self._currency_cache: Dict[str, str] = {}

    # ── Базовый вызов API ────────────────────────────────────────
    async def call(self, method: str, params: dict = None) -> Dict[str, Any]:
        if not self.webhook_url:
            raise ValueError("BITRIX_WEBHOOK_URL не задан в .env")
        url = f"{self.webhook_url}/{method}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=params or {})
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    logger.error(f"Bitrix API error [{method}]: {data}")
                return data
        except httpx.TimeoutException:
            logger.error(f"Timeout calling Bitrix: {method}")
            raise
        except Exception as e:
            logger.error(f"Bitrix exception [{method}]: {e}")
            raise

    # ── Получить элемент смарт-процесса ─────────────────────────
    async def get_element(self, element_id: int) -> Optional[Dict]:
        try:
            result = await self.call("crm.item.get", {
                "entityTypeId": self.entity_type_id,
                "id": element_id
            })
            return result.get("result", {}).get("item")
        except Exception as e:
            logger.error(f"get_element({element_id}): {e}")
            return None

    # ── Сменить стадию элемента ──────────────────────────────────
    async def update_stage(self, element_id: int, stage_id: str) -> bool:
        try:
            result = await self.call("crm.item.update", {
                "entityTypeId": self.entity_type_id,
                "id": element_id,
                "fields": {"stageId": stage_id}
            })
            return "result" in result
        except Exception as e:
            logger.error(f"update_stage({element_id}, {stage_id}): {e}")
            return False

    # ── Добавить комментарий в таймлайн ─────────────────────────
    async def add_comment(self, element_id: int, text: str) -> bool:
        try:
            result = await self.call("crm.timeline.comment.add", {
                "fields": {
                    "ENTITY_ID":   element_id,
                    "ENTITY_TYPE": f"dynamic_{self.entity_type_id}",
                    "COMMENT":     text
                }
            })
            return "result" in result
        except Exception as e:
            logger.error(f"add_comment({element_id}): {e}")
            return False

    # ── Получить стадии смарт-процесса ──────────────────────────
    async def get_stages(self) -> List[Dict]:
        """
        CategoryId = 38, поэтому ENTITY_ID = DYNAMIC_139_38.
        Пробуем несколько вариантов для надёжности.
        """
        candidates = [
            f"DYNAMIC_{self.entity_type_id}_STAGE_{self.category_id}",  # DYNAMIC_139_38 ← правильный
            f"DYNAMIC_{self.entity_type_id}_1",
            f"DYNAMIC_{self.entity_type_id}_0",
        ]
        for entity_id in candidates:
            try:
                result = await self.call("crm.status.list", {
                    "filter": {"ENTITY_ID": entity_id}
                })
                stages = result.get("result", [])
                if stages:
                    logger.info(f"Стадии найдены с ENTITY_ID={entity_id}: {len(stages)} шт.")
                    return stages
            except Exception as e:
                logger.warning(f"get_stages({entity_id}): {e}")
        return []

    # ── Получить поля смарт-процесса ────────────────────────────
    async def get_fields(self) -> Dict:
        try:
            result = await self.call("crm.item.fields", {
                "entityTypeId": self.entity_type_id
            })
            return result.get("result", {}).get("fields", {})
        except Exception as e:
            logger.error(f"get_fields: {e}")
            return {}

    # ── Загрузить значения LIST-поля валюты ──────────────────────
    async def load_currency_enum(self) -> Dict[str, str]:
        """
        Загружает справочник валют (UF_CRM_5_1698136041 — LIST-поле).
        Возвращает {enum_id: "TJS"/"USD"/...}
        """
        try:
            result = await self.call("user.field.list", {
                "filter": {"FIELD_NAME": FIELD_CURRENCY},
                "select": ["ID", "FIELD_NAME", "LIST"]
            })
            fields = result.get("result", [])
            mapping = {}
            for field in fields:
                for item in field.get("LIST", []):
                    enum_id = str(item.get("ID", ""))
                    val_name = item.get("VALUE", "").lower().strip()
                    iso_code = CURRENCY_NAME_TO_CODE.get(val_name, val_name.upper()[:3])
                    mapping[enum_id] = iso_code
            if mapping:
                self._currency_cache = mapping
                logger.info(f"Справочник валют загружен: {mapping}")
            return mapping
        except Exception as e:
            logger.error(f"load_currency_enum: {e}")
            return {}

    # ── Тест подключения ─────────────────────────────────────────
    async def test_connection(self) -> Dict:
        try:
            result = await self.call("profile")
            return {"ok": True, "user": result.get("result", {})}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Разрешить ID валюты → ISO-код ────────────────────────────
    async def resolve_currency(self, raw_value: Any) -> str:
        """
        Валюта в смарт-процессе — LIST-поле.
        raw_value может быть:
          - числовым ID элемента списка (например 52)
          - строкой "TJS"/"USD" (если где-то передаётся напрямую)
        """
        if raw_value is None:
            return "TJS"

        str_val = str(raw_value).strip()

        # Если уже ISO-код (3 буквы)
        if str_val.upper() in ("TJS", "USD", "EUR", "RUB", "KZT", "CNY", "UZS"):
            return str_val.upper()

        # Ищем в кэше
        if str_val in self._currency_cache:
            return self._currency_cache[str_val]

        # Кэш пуст — загружаем справочник
        if not self._currency_cache:
            await self.load_currency_enum()
            if str_val in self._currency_cache:
                return self._currency_cache[str_val]

        # Не нашли — возвращаем TJS по умолчанию с предупреждением
        logger.warning(f"Валюта не распознана: '{str_val}', используем TJS")
        return "TJS"

    # ── Извлечь сумму из элемента ────────────────────────────────
    def extract_amount(self, element: dict) -> Optional[float]:
        # Б24 возвращает поля в camelCase: UF_CRM_5_1698135335 → ufCrm5_1698135335
        camel = FIELD_AMOUNT.lower().replace("uf_crm_", "ufCrm").replace("_", "_")
        field_camel = "ufCrm" + FIELD_AMOUNT.replace("UF_CRM_", "").replace("_", "_").lower()
        # Проще — конвертируем напрямую
        field_camel = "ufCrm5_" + FIELD_AMOUNT.split("UF_CRM_5_")[-1]
        for field in [FIELD_AMOUNT, field_camel, "opportunity", "OPPORTUNITY"]:
            val = element.get(field)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
        return None

    # ── Извлечь сырое значение валюты ────────────────────────────
    def extract_department(self, element: dict, field_override: str = None) -> Optional[str]:
        field = field_override or FIELD_DEPARTMENT
        if field:
            field_camel = "ufCrm5_" + field.split("UF_CRM_5_")[-1]
            val = element.get(field) or element.get(field_camel)
            return str(val) if val else None
        return None

    # ── Извлечь подразделение ────────────────────────────────────
    def extract_department(self, element: dict, field_override: str = None) -> Optional[str]:
        field = field_override or FIELD_DEPARTMENT
        if field:
            val = element.get(field)
            return str(val) if val else None
        return None

    # ── Извлечь ID стадии ────────────────────────────────────────
    def extract_stage_id(self, element: dict) -> str:
        return element.get("stageId", "")

    # ── Получить список смарт-процессов ──────────────────────────
    async def get_entity_types(self) -> List[Dict]:
        """Полезно для отладки — список всех смарт-процессов"""
        try:
            result = await self.call("crm.type.list")
            return result.get("result", {}).get("types", [])
        except Exception as e:
            logger.error(f"get_entity_types: {e}")
            return []

    # ── Информация о смарт-процессе и категориях ─────────────────
    async def get_categories(self) -> List[Dict]:
        """Список категорий/воронок смарт-процесса"""
        try:
            result = await self.call("crm.category.list", {
                "entityTypeId": self.entity_type_id
            })
            return result.get("result", {}).get("categories", [])
        except Exception as e:
            logger.error(f"get_categories: {e}")
            return []


# Глобальный экземпляр клиента
bitrix = BitrixClient()
