"""
bitrix.py — клиент для работы с REST API Битрикс24
Обновлён с учётом анализа реального кода смарт-процесса:
  - categoryId = 38 → ENTITY_ID стадий = DYNAMIC_139_STAGE_38
  - Валюта хранится как числовой ID из списка (LIST-поле)
  - Поля возвращаются в camelCase: UF_CRM_5_XXXXXX → ufCrm5_XXXXXX
"""
import httpx
import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "")
ENTITY_TYPE_ID     = int(os.getenv("BITRIX_ENTITY_TYPE_ID", "139"))
CATEGORY_ID        = int(os.getenv("BITRIX_CATEGORY_ID", "38"))

FIELD_AMOUNT       = os.getenv("FIELD_AMOUNT",     "UF_CRM_5_1698135335")
FIELD_CURRENCY     = os.getenv("FIELD_CURRENCY",   "UF_CRM_5_1698136041")
FIELD_DEPARTMENT   = os.getenv("FIELD_DEPARTMENT", "")

CURRENCY_NAME_TO_CODE = {
    "сомони":           "TJS",
    "доллар сша":       "USD",
    "евро":             "EUR",
    "российский рубль": "RUB",
    "тенге":            "KZT",
    "юань":             "CNY",
    "узбекский сум":    "UZS",
}


def _to_camel(field_code: str) -> str:
    """UF_CRM_5_1698135335 → ufCrm5_1698135335"""
    if "UF_CRM_5_" in field_code:
        return "ufCrm5_" + field_code.split("UF_CRM_5_")[-1]
    return field_code


class BitrixClient:

    def __init__(self):
        self.webhook_url    = BITRIX_WEBHOOK_URL.rstrip("/")
        self.entity_type_id = ENTITY_TYPE_ID
        self.category_id    = CATEGORY_ID
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
        candidates = [
            f"DYNAMIC_{self.entity_type_id}_STAGE_{self.category_id}",
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

    # ── Загрузить справочник валют ───────────────────────────────
    async def load_currency_enum(self) -> Dict[str, str]:
        try:
            result = await self.call("user.field.list", {
                "filter": {"FIELD_NAME": FIELD_CURRENCY},
                "select": ["ID", "FIELD_NAME", "LIST"]
            })
            fields = result.get("result", [])
            mapping = {}
            for field in fields:
                for item in field.get("LIST", []):
                    enum_id  = str(item.get("ID", ""))
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
        if raw_value is None:
            return "TJS"
        str_val = str(raw_value).strip()
        if str_val.upper() in ("TJS", "USD", "EUR", "RUB", "KZT", "CNY", "UZS"):
            return str_val.upper()
        if str_val in self._currency_cache:
            return self._currency_cache[str_val]
        if not self._currency_cache:
            await self.load_currency_enum()
            if str_val in self._currency_cache:
                return self._currency_cache[str_val]
        logger.warning(f"Валюта не распознана: '{str_val}', используем TJS")
        return "TJS"

    # ── Извлечь сумму из элемента ────────────────────────────────
    def extract_amount(self, element: dict) -> Optional[float]:
        for field in [FIELD_AMOUNT, _to_camel(FIELD_AMOUNT), "opportunity", "OPPORTUNITY"]:
            val = element.get(field)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
        return None

    # ── Извлечь сырое значение валюты ────────────────────────────
    def extract_currency_raw(self, element: dict) -> Any:
        for field in [FIELD_CURRENCY, _to_camel(FIELD_CURRENCY), "currencyId"]:
            val = element.get(field)
            if val is not None:
                return val
        return None

    # ── Извлечь подразделение ────────────────────────────────────
    def extract_department(self, element: dict, field_override: str = None) -> Optional[str]:
        field = field_override or FIELD_DEPARTMENT
        if field:
            for f in [field, _to_camel(field)]:
                val = element.get(f)
                if val:
                    return str(val)
        return None

    # ── Извлечь ID стадии ────────────────────────────────────────
    def extract_stage_id(self, element: dict) -> str:
        return element.get("stageId", "")

    # ── Список смарт-процессов (для отладки) ─────────────────────
    async def get_entity_types(self) -> List[Dict]:
        try:
            result = await self.call("crm.type.list")
            return result.get("result", {}).get("types", [])
        except Exception as e:
            logger.error(f"get_entity_types: {e}")
            return []

    # ── Категории смарт-процесса ─────────────────────────────────
    async def get_categories(self) -> List[Dict]:
        try:
            result = await self.call("crm.category.list", {
                "entityTypeId": self.entity_type_id
            })
            return result.get("result", {}).get("categories", [])
        except Exception as e:
            logger.error(f"get_categories: {e}")
            return []


bitrix = BitrixClient()