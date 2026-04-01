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

    # Extra substrings to match Linkbuilder column (e.g. Oleg vs Олег)
    linkbuilder_aliases: list[str]


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


def _secrets_get_int(secrets: Any, key: str, default: int) -> int:
    raw = _secrets_get(secrets, key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
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
        linkbuilder_aliases=_parse_list_csv(
            secrets,
            "LINKBUILDER_ALIASES",
            ["Oleg", "oleg"],
        ),
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
