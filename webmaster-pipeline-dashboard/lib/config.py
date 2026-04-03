"""Load settings from Streamlit secrets or environment variables."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _env(key: str, default: str = "") -> str:
    v = os.environ.get(key)
    return (v or "").strip() if v is not None else default


def _env_int(key: str, default: int) -> int:
    raw = _env(key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = _env(key, "")
    if not raw:
        return default
    try:
        return float(raw.replace(",", ".").strip())
    except ValueError:
        return default


@dataclass
class AppConfig:
    # Canonical spreadsheet IDs (from implementation-notes / HACK-382)
    spreadsheet_inbox_log_id: str
    spreadsheet_telecom_id: str
    spreadsheet_registry_2_id: str
    spreadsheet_calculator_id: str
    spreadsheet_payment_options_id: str

    # Sheet gids (URL #gid=...) — used to resolve sheet title via API
    gid_telecom_registry: int
    gid_registry_2: int
    gid_calculator_tab_primary: int
    gid_calculator_tab_secondary: int
    gid_payment_options: int
    gid_inbox_log: int

    linkbuilder_filter: str
    status_prep_text: str
    status_wait_publish: str

    # Column header names (must match first row in Sheets)
    col_linkbuilder: str
    col_status: str
    col_article_post: str
    col_website_donor: str
    col_cost: str

    # Optional: IMAP folder / label search
    imap_mailbox: str
    # 0 = обработать все UNSEEN за один запуск; >0 = не больше N последних по порядку IMAP
    imap_sync_max_messages: int
    imap_sync_timeout_sec: int
    # UNSEEN: сначала более новые по номеру последовательности IMAP (как правило ближе к верху Gmail)
    imap_sync_newest_first: bool
    # После записи в таблицу: по умолчанию один раз на письмо отправить SMTP с текстом колонки F (логика оплаты)
    imap_auto_reply_payment_followup: bool

    # Extra substrings to match Linkbuilder column (e.g. Oleg vs Олег)
    linkbuilder_aliases: list[str]

    # «Торг»: подстрока для колонки ответственного в калькуляторе (или несколько через |). Пусто → только LINKBUILDER_*
    trade_responsible_name: str
    # Часовой пояс для «сегодня» (ДД.ММ.ГГГГ)
    trade_timezone: str
    # Точный заголовок столбца с датой торга в калькуляторе; пусто — эвристика по «дата» (без колонок «коммент»)
    col_trade_date: str
    # Точный заголовок столбца ответственного; пусто — эвристика «Ответственный» / Responsible и т.д.
    col_trade_responsible: str
    # Доля скидки (0.2 = минус 20 %)
    trade_discount_percent: float
    # «Торг»: 0 = дата только сегодня; N>0 = дата от (сегодня − N) до сегодня включительно
    trade_date_max_age_days: int

    # «Отправить статьи»: максимум писем за одно нажатие (0 = без лимита)
    article_publish_max_send: int

    # «Проверка публикаций»: HTTP + EEAT на странице + целевая ссылка + опционально Google CSE (индекс)
    publication_check_timeout_sec: int
    publication_check_max_rows: int
    publication_check_max_body_bytes: int
    publication_check_statuses: list[str]
    eeat_author_markers: list[str]
    col_author_with_link: str
    col_author_without_link: str
    # Колонка J — целевой URL; COL_PLACED_TARGET_URL в secrets остаётся алиасом, если COL_OUTGOING_LINK пусто
    col_outgoing_link: str
    # Колонка I — видимый текст ссылки (должен совпасть с тем же <a>, что и outgoing)
    col_anchor: str
    publication_check_anchor_case_insensitive: bool
    google_cse_api_key: str
    google_cse_cx: str


def _secrets_lookup_raw(secrets: Any, key: str) -> Any:
    """Streamlit versions differ: prefer __getitem__, then .get(), then attribute."""
    if secrets is None:
        return None
    try:
        return secrets[key]
    except Exception:
        pass
    try:
        return secrets.get(key)
    except Exception:
        pass
    try:
        return getattr(secrets, key, None)
    except Exception:
        return None
    return None


def _secrets_get(secrets: Any, key: str, default: str = "") -> str:
    try:
        if secrets is None:
            return default
        v = _secrets_lookup_raw(secrets, key)
        if v is None:
            v = default
        return str(v).strip() if v is not None else default
    except Exception:
        return default


def _secrets_get_float(secrets: Any, key: str, default: float) -> float:
    raw = _secrets_get(secrets, key, "")
    if not raw:
        return default
    try:
        return float(raw.replace(",", ".").strip())
    except ValueError:
        return default


def _secrets_get_int(secrets: Any, key: str, default: int) -> int:
    raw = _secrets_get(secrets, key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = _env(key, "")
    if not raw:
        return default
    low = raw.lower()
    if low in ("0", "false", "no", "off"):
        return False
    if low in ("1", "true", "yes", "on"):
        return True
    return default


def _secrets_get_bool(secrets: Any, key: str, default: bool) -> bool:
    raw = _secrets_get(secrets, key, "")
    if not raw:
        return default
    low = raw.lower()
    if low in ("0", "false", "no", "off"):
        return False
    if low in ("1", "true", "yes", "on"):
        return True
    return default


def _parse_list_csv(secrets: Any, key: str, default_items: list[str]) -> list[str]:
    raw = _secrets_get(secrets, key, "")
    if not raw:
        return list(default_items)
    parts = [p.strip() for p in re.split(r"[,;|]", raw) if p.strip()]
    return parts or list(default_items)


def load_config(secrets: Any | None = None) -> AppConfig:
    """secrets: streamlit.secrets or dict-like."""
    return AppConfig(
        spreadsheet_inbox_log_id=_secrets_get(
            secrets, "SPREADSHEET_INBOX_LOG_ID", _env("SPREADSHEET_INBOX_LOG_ID", "19dMDf3sxH8RuBI6hZwWwen_cm2A_UOQZdXVtcjMRllc")
        ),
        spreadsheet_telecom_id=_secrets_get(
            secrets, "SPREADSHEET_TELECOM_ASIA_ID", _env("SPREADSHEET_TELECOM_ASIA_ID", "1S5lk-ya4iWwq5znY_vebAuTqloyTlWTcsNuXydZXT00")
        ),
        spreadsheet_registry_2_id=_secrets_get(
            secrets, "SPREADSHEET_REGISTRY_2_ID", _env("SPREADSHEET_REGISTRY_2_ID", "1DaiRFqU2d_85cXr0fDmyhzIY4V9fm0zxh4KraZMOFnw")
        ),
        spreadsheet_calculator_id=_secrets_get(
            secrets, "SPREADSHEET_CALCULATOR_ID", _env("SPREADSHEET_CALCULATOR_ID", "1xrjeVD0Q94JI08v2gFvtv1NbiTAbq0fSjv-A-g5pPSs")
        ),
        spreadsheet_payment_options_id=_secrets_get(
            secrets,
            "SPREADSHEET_PAYMENT_OPTIONS_ID",
            _env("SPREADSHEET_PAYMENT_OPTIONS_ID", "17MoDWnMesQkpmI9bSZAF5LYQpjyM2itU0PpcaS-X240"),
        ),
        gid_telecom_registry=_secrets_get_int(secrets, "GID_TELECOM_REGISTRY", 728254189),
        gid_registry_2=_secrets_get_int(secrets, "GID_REGISTRY_2", 1088920242),
        gid_calculator_tab_primary=_secrets_get_int(secrets, "GID_CALCULATOR_TAB_1", 225938948),
        gid_calculator_tab_secondary=_secrets_get_int(secrets, "GID_CALCULATOR_TAB_2", 0),
        gid_payment_options=_secrets_get_int(secrets, "GID_PAYMENT_OPTIONS", 0),
        gid_inbox_log=_secrets_get_int(secrets, "GID_INBOX_LOG", 0),
        linkbuilder_filter=_secrets_get(secrets, "LINKBUILDER_FILTER", _env("LINKBUILDER_FILTER", "Олег")),
        status_prep_text=_secrets_get(secrets, "STATUS_PREP_TEXT", "Подготовка текста"),
        status_wait_publish=_secrets_get(secrets, "STATUS_WAIT_PUBLISH", "Жду публикации"),
        col_linkbuilder=_secrets_get(secrets, "COL_LINKBUILDER", "Linkbuilder"),
        col_status=_secrets_get(secrets, "COL_STATUS", "Status"),
        col_article_post=_secrets_get(secrets, "COL_ARTICLE_POST", "Article/post"),
        col_website_donor=_secrets_get(secrets, "COL_WEBSITE_DONOR", "Website Donor"),
        col_cost=_secrets_get(secrets, "COL_COST", "Cost $"),
        imap_mailbox=_secrets_get(secrets, "IMAP_MAILBOX", "INBOX"),
        imap_sync_max_messages=_secrets_get_int(
            secrets,
            "IMAP_SYNC_MAX_MESSAGES",
            _env_int("IMAP_SYNC_MAX_MESSAGES", 0),
        ),
        imap_sync_timeout_sec=max(
            60,
            _secrets_get_int(
                secrets,
                "IMAP_SYNC_TIMEOUT_SEC",
                _env_int("IMAP_SYNC_TIMEOUT_SEC", 900),
            ),
        ),
        imap_sync_newest_first=_secrets_get_bool(
            secrets,
            "IMAP_SYNC_NEWEST_FIRST",
            _env_bool("IMAP_SYNC_NEWEST_FIRST", True),
        ),
        imap_auto_reply_payment_followup=_secrets_get_bool(
            secrets,
            "IMAP_AUTO_REPLY_PAYMENT_FOLLOWUP",
            _env_bool("IMAP_AUTO_REPLY_PAYMENT_FOLLOWUP", True),
        ),
        linkbuilder_aliases=_parse_list_csv(
            secrets,
            "LINKBUILDER_ALIASES",
            ["Oleg", "oleg"],
        ),
        trade_responsible_name=_secrets_get(
            secrets,
            "TRADE_RESPONSIBLE_NAME",
            _env("TRADE_RESPONSIBLE_NAME", "Oleg Tsebulevskiy|Tsekhulevskiy|Tsebulovskiy"),
        ),
        trade_timezone=_secrets_get(secrets, "TRADE_TIMEZONE", _env("TRADE_TIMEZONE", "Europe/Moscow")),
        col_trade_date=_secrets_get(
            secrets,
            "COL_TRADE_DATE",
            _env("COL_TRADE_DATE", "Комментарий (Денис)"),
        ),
        col_trade_responsible=_secrets_get(
            secrets,
            "COL_TRADE_RESPONSIBLE",
            _env("COL_TRADE_RESPONSIBLE", "Ответственный"),
        ),
        trade_discount_percent=max(
            0.0,
            min(
                0.95,
                _secrets_get_float(
                    secrets,
                    "TRADE_DISCOUNT_PERCENT",
                    _env_float("TRADE_DISCOUNT_PERCENT", 0.2),
                ),
            ),
        ),
        trade_date_max_age_days=max(
            0,
            min(
                366,
                _secrets_get_int(
                    secrets,
                    "TRADE_DATE_MAX_AGE_DAYS",
                    _env_int("TRADE_DATE_MAX_AGE_DAYS", 30),
                ),
            ),
        ),
        article_publish_max_send=max(
            0,
            _secrets_get_int(
                secrets,
                "ARTICLE_PUBLISH_MAX_SEND",
                _env_int("ARTICLE_PUBLISH_MAX_SEND", 50),
            ),
        ),
        publication_check_timeout_sec=max(
            5,
            min(
                120,
                _secrets_get_int(
                    secrets,
                    "PUBLICATION_CHECK_TIMEOUT_SEC",
                    _env_int("PUBLICATION_CHECK_TIMEOUT_SEC", 25),
                ),
            ),
        ),
        publication_check_max_rows=max(
            0,
            _secrets_get_int(
                secrets,
                "PUBLICATION_CHECK_MAX_ROWS",
                _env_int("PUBLICATION_CHECK_MAX_ROWS", 150),
            ),
        ),
        publication_check_max_body_bytes=max(
            50_000,
            min(
                5_000_000,
                _secrets_get_int(
                    secrets,
                    "PUBLICATION_CHECK_MAX_BODY_BYTES",
                    _env_int("PUBLICATION_CHECK_MAX_BODY_BYTES", 1_500_000),
                ),
            ),
        ),
        publication_check_statuses=_parse_list_csv(
            secrets,
            "PUBLICATION_CHECK_STATUSES",
            ["Готово"],
        ),
        eeat_author_markers=_parse_list_csv(
            secrets,
            "EEAT_AUTHOR_MARKERS",
            ["алиса", "alisa", "metaratings", "авторы metaratings"],
        ),
        col_author_with_link=_secrets_get(secrets, "COL_AUTHOR_WITH_LINK", "Автор со ссылкой"),
        col_author_without_link=_secrets_get(secrets, "COL_AUTHOR_WITHOUT_LINK", "Автор без ссылки"),
        col_outgoing_link=(
            _secrets_get(secrets, "COL_OUTGOING_LINK", "")
            or _secrets_get(secrets, "COL_PLACED_TARGET_URL", "")
            or "Outgoing link"
        ),
        col_anchor=_secrets_get(secrets, "COL_ANCHOR", "Anchor"),
        publication_check_anchor_case_insensitive=_secrets_get_bool(
            secrets,
            "PUBLICATION_CHECK_ANCHOR_CASE_INSENSITIVE",
            _env_bool("PUBLICATION_CHECK_ANCHOR_CASE_INSENSITIVE", False),
        ),
        google_cse_api_key=_secrets_get(secrets, "GOOGLE_CSE_API_KEY", _env("GOOGLE_CSE_API_KEY", "")),
        google_cse_cx=_secrets_get(secrets, "GOOGLE_CSE_CX", _env("GOOGLE_CSE_CX", "")),
    )


def use_google_adc(secrets: Any | None) -> bool:
    """If true, use Application Default Credentials (no JSON key) — см. README."""
    raw = _secrets_get(secrets, "GOOGLE_USE_ADC", _env("GOOGLE_USE_ADC", ""))
    return raw.lower() in ("1", "true", "yes")


def _app_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_sa_from_json_file(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(data, dict) and data.get("type") == "service_account":
        return data
    return None


def _service_account_from_secrets_value(val: Any) -> dict | None:
    """Streamlit Secrets may expose JSON as a string (TOML) or as a parsed dict."""
    if val is None:
        return None
    if isinstance(val, dict):
        if val.get("type") == "service_account":
            return val
        return None
    if isinstance(val, str) and val.strip():
        try:
            data = json.loads(val)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict) and data.get("type") == "service_account":
            return data
    return None


def load_service_account_info(secrets: Any | None) -> dict | None:
    """Service account dict: env, Streamlit secrets, then file paths (see order below)."""
    env_inline = _env("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if env_inline:
        got = _service_account_from_secrets_value(env_inline)
        if got:
            return got

    if secrets is not None:
        inline = _secrets_lookup_raw(secrets, "GOOGLE_SERVICE_ACCOUNT_JSON")
        got = _service_account_from_secrets_value(inline)
        if got:
            return got

    raw = _secrets_get(secrets, "GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    file_hint = _secrets_get(secrets, "GOOGLE_SERVICE_ACCOUNT_FILE", _env("GOOGLE_SERVICE_ACCOUNT_FILE", ""))
    if file_hint:
        p = Path(file_hint)
        if not p.is_absolute():
            p = _app_root() / p
        got = _load_sa_from_json_file(p)
        if got:
            return got

    gac = _env("GOOGLE_APPLICATION_CREDENTIALS", "")
    if gac:
        got = _load_sa_from_json_file(Path(gac))
        if got:
            return got

    for rel in (
        ".streamlit/gcp-service-account.json",
        ".streamlit/service_account.json",
        ".streamlit/service_account.json.json",
    ):
        got = _load_sa_from_json_file(_app_root() / rel)
        if got:
            return got

    return None
