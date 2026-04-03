"""Google Sheets API — read ranges, resolve sheet by gid, optional append row."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES_RW = ["https://www.googleapis.com/auth/spreadsheets"]


def build_sheets_service_adc():
    """Application Default Credentials (локально: gcloud auth application-default login)."""
    try:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError
    except ImportError:
        return None
    try:
        creds, _ = google.auth.default(scopes=SCOPES_RW)
    except DefaultCredentialsError:
        return None
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _creds(service_account_info: dict | None):
    if not service_account_info:
        return None
    return service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES_RW)


def build_sheets_service(service_account_info: dict | None):
    creds = _creds(service_account_info)
    if not creds:
        return None
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _int_sheet_id(val: Any) -> int | None:
    """sheetId из API — int; на всякий случай приводим из str/float."""
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        try:
            return int(float(val))
        except (TypeError, ValueError):
            return None


def _norm_calc_tab_title(title: str) -> str:
    s = unicodedata.normalize("NFKC", (title or "").strip().lower())
    return re.sub(r"\s+", "", s)


# Имена вкладки калькулятора (после «Создать копию» gid меняется — ищем по названию).
_CALC_TAB_TITLE_ALIASES = frozenset(
    {
        "telecomasia",
        "telecomesia",
        "телекомазия",
    }
)


def get_sheet_title_by_gid(service, spreadsheet_id: str, gid: int) -> str | None:
    """Return sheet title for numeric sheetId (same as gid in URL). gid=0 — первая вкладка книги."""
    if service is None:
        return None
    if gid < 0:
        return None
    try:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
        sheets = meta.get("sheets", [])
        want = int(gid)
        for sh in sheets:
            props = sh.get("properties") or {}
            sid = _int_sheet_id(props.get("sheetId"))
            if sid is not None and sid == want:
                t = props.get("title")
                return str(t) if t is not None else None
        if want == 0 and sheets:
            props0 = sheets[0].get("properties") or {}
            t0 = props0.get("title")
            return str(t0) if t0 is not None else None
    except HttpError:
        return None
    except Exception:
        # SSL, timeouts, google.auth refresh errors — do not crash Streamlit UI
        return None
    return None


def resolve_calculator_sheet_title(
    service: Any,
    spreadsheet_id: str,
    gid: int,
) -> tuple[str | None, str]:
    """(title, err_html). err пустой при успехе. Отличает 403/404 от «gid не в этой книге»; fallback по имени вкладки."""
    if service is None:
        return None, "Клиент Google Sheets не инициализирован (проверьте **GOOGLE_SERVICE_ACCOUNT_JSON** и **Reboot app**)."
    if not spreadsheet_id or not str(spreadsheet_id).strip():
        return None, "Не задан **SPREADSHEET_CALCULATOR_ID** (книга калькулятора)."
    if gid < 0:
        return None, "Некорректный **GID_CALCULATOR_TAB_1**."
    try:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
    except HttpError as e:
        status = getattr(getattr(e, "resp", None), "status", None)
        if status == 403:
            return None, (
                "Нет доступа к книге калькулятора (**403**). Откройте таблицу в Google Sheets → **Настроить доступ** "
                "и добавьте **client_email** из **GOOGLE_SERVICE_ACCOUNT_JSON** (роль **Читатель** или выше). "
                "Проверьте, что **SPREADSHEET_CALCULATOR_ID** в Secrets совпадает с ID в URL книги."
            )
        if status == 404:
            return None, (
                "Книга не найдена (**404**). Проверьте **SPREADSHEET_CALCULATOR_ID** в Secrets — ID из URL "
                "`/spreadsheets/d/<ID>/edit`."
            )
        return None, f"Google Sheets API: HTTP **{status}** при чтении книги калькулятора."
    except Exception:
        return None, "Не удалось прочитать метаданные книги (сеть / SSL / таймаут). Повторите позже."

    sheets = meta.get("sheets") or []
    if not sheets:
        return None, "В книге калькулятора нет ни одной вкладки."

    want = int(gid)
    for sh in sheets:
        props = sh.get("properties") or {}
        sid = _int_sheet_id(props.get("sheetId"))
        if sid is not None and sid == want:
            t = props.get("title")
            return (str(t) if t is not None else None) or None, ""

    if want == 0:
        props0 = (sheets[0].get("properties") or {})
        t0 = props0.get("title")
        return (str(t0) if t0 is not None else None) or None, ""

    matches: list[str] = []
    for sh in sheets:
        props = sh.get("properties") or {}
        title = str(props.get("title") or "")
        nt = _norm_calc_tab_title(title)
        if nt in _CALC_TAB_TITLE_ALIASES or ("telecom" in nt and "asia" in nt):
            matches.append(title)

    if len(matches) == 1:
        return matches[0], ""

    titles_preview = ", ".join(
        str((s.get("properties") or {}).get("title") or "?") for s in sheets[:18]
    )
    if len(matches) > 1:
        return None, (
            f"Лист с **gid={gid}** в этой книге не найден (после копирования файла gid меняется). "
            f"Несколько вкладок похожи на калькулятор: **{', '.join(matches)}** — уточните **GID_CALCULATOR_TAB_1** "
            f"в URL нужной вкладки. Все вкладки: {titles_preview}"
        )

    return None, (
        f"В книге **нет** вкладки с **sheetId={gid}** (как в URL `gid=`). "
        f"Часто **SPREADSHEET_CALCULATOR_ID** в Streamlit Secrets указывает на **другую** книгу, чем в браузере, "
        f"или таблицу копировали (новый gid). Откройте нужную вкладку и скопируйте **gid** из URL. "
        f"Вкладки в этой книге: **{titles_preview}**"
    )


def get_sheet_id_by_gid(service, spreadsheet_id: str, gid: int) -> int | None:
    """Numeric sheetId для batchUpdate (совпадает с #gid= в URL)."""
    if service is None:
        return None
    if gid < 0:
        return None
    try:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
        sheets = meta.get("sheets", [])
        want = int(gid)
        for sh in sheets:
            props = sh.get("properties") or {}
            sid = _int_sheet_id(props.get("sheetId"))
            if sid is not None and sid == want:
                return sid
        if want == 0 and sheets:
            return _int_sheet_id((sheets[0].get("properties") or {}).get("sheetId"))
    except HttpError:
        return None
    except Exception:
        return None
    return None


def a1_all_columns(sheet_title: str) -> str:
    escaped = sheet_title.replace("'", "''")
    return f"'{escaped}'!A:ZZ"


def resolve_linkbuilder_column(df: pd.DataFrame, primary: str, synonyms: list[str] | None = None) -> str | None:
    """Match header: exact (case-insensitive), then synonyms, then column containing link+build."""
    if df.empty or not len(df.columns):
        return None
    syn = [primary] + (synonyms or [])
    norm_map = {str(c).strip().lower(): c for c in df.columns}
    for want in syn:
        w = want.strip().lower()
        if w in norm_map:
            return norm_map[w]
    for c in df.columns:
        cl = str(c).strip().lower()
        if "link" in cl and "build" in cl:
            return str(c)
    return None


def resolve_status_column(df: pd.DataFrame, primary: str) -> str | None:
    if df.empty:
        return None
    norm_map = {str(c).strip().lower(): c for c in df.columns}
    for want in (primary, "Status", "Статус", "status"):
        w = want.strip().lower()
        if w in norm_map:
            return norm_map[w]
    for c in df.columns:
        if "status" in str(c).strip().lower() or "статус" in str(c).strip().lower():
            return str(c)
    return None


def resolve_article_column(df: pd.DataFrame, primary: str) -> str | None:
    if df.empty:
        return None
    norm_map = {str(c).strip().lower(): c for c in df.columns}
    w = primary.strip().lower()
    if w in norm_map:
        return norm_map[w]
    for c in df.columns:
        cl = str(c).strip().lower()
        if "article" in cl and "post" in cl:
            return str(c)
    return None


def resolve_donor_column(df: pd.DataFrame, primary: str) -> str | None:
    if df.empty:
        return None
    norm_map = {str(c).strip().lower(): c for c in df.columns}
    w = primary.strip().lower()
    if w in norm_map:
        return norm_map[w]
    for c in df.columns:
        cl = str(c).strip().lower()
        if "website" in cl and "donor" in cl:
            return str(c)
    return None


def resolve_cost_column(df: pd.DataFrame, primary: str) -> str | None:
    if df.empty:
        return None
    norm_map = {str(c).strip().lower(): c for c in df.columns}
    w = primary.strip().lower()
    if w in norm_map:
        return norm_map[w]
    for c in df.columns:
        if "cost" in str(c).strip().lower():
            return str(c)
    return None


def get_values_as_dataframe(service, spreadsheet_id: str, range_a1: str) -> pd.DataFrame:
    """First row = header."""
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_a1, majorDimension="ROWS")
            .execute()
        )
    except HttpError:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    rows = result.get("values") or []
    if not rows:
        return pd.DataFrame()
    header = [str(c).strip() for c in rows[0]]
    data = rows[1:]
    max_len = len(header)
    normalized = []
    for row in data:
        r = list(row) + [""] * (max_len - len(row))
        normalized.append(r[:max_len])
    return pd.DataFrame(normalized, columns=header)


def get_spreadsheet_values_rows(service: Any, spreadsheet_id: str, range_a1: str) -> list[list[Any]]:
    """Сырые строки листа (majorDimension=ROWS). Пустой список при ошибке API."""
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_a1, majorDimension="ROWS")
            .execute()
        )
    except HttpError:
        return []
    except Exception:
        return []
    return result.get("values") or []


def filter_by_linkbuilder(
    df: pd.DataFrame,
    col_linkbuilder: str | None,
    linkbuilder: str,
    extra_aliases: list[str] | None = None,
) -> pd.DataFrame:
    if df.empty or not col_linkbuilder or col_linkbuilder not in df.columns:
        return pd.DataFrame(columns=df.columns)
    s = df[col_linkbuilder].astype(str).str.strip()
    needles: list[str] = [linkbuilder.strip()]
    if extra_aliases:
        needles.extend(x.strip() for x in extra_aliases if x and x.strip())
    seen: set[str] = set()
    uniq: list[str] = []
    for n in needles:
        if n.lower() not in seen:
            seen.add(n.lower())
            uniq.append(n)
    mask = pd.Series(False, index=df.index)
    for n in uniq:
        mask = mask | s.str.contains(n, case=False, regex=False, na=False)
    return df.loc[mask].copy()


def count_by_status(df: pd.DataFrame, col_status: str) -> dict[str, int]:
    if df.empty or col_status not in df.columns:
        return {}
    vc = df[col_status].astype(str).str.strip()
    vc = vc[vc != ""]
    return vc.value_counts().to_dict()


def parse_append_updated_range_start_row_0based(updated_range: str | None) -> int | None:
    """Из ответа values.append `updates.updatedRange` («Лист»!A12:F12) → 0-based индекс первой строки."""
    if not updated_range:
        return None
    part = updated_range.split("!", 1)[-1]
    left = part.split(":")[0].strip()
    digits = "".join(ch for ch in left if ch.isdigit())
    if not digits:
        return None
    return int(digits) - 1


def append_row(
    service, spreadsheet_id: str, sheet_title: str, row_values: list[Any]
) -> str | None:
    """
    Добавляет строку; возвращает updates.updatedRange из ответа API (для подсветки строки) или None.
    """
    escaped = sheet_title.replace("'", "''")
    range_a1 = f"'{escaped}'!A1"
    body = {"values": [row_values]}
    resp = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    return (resp.get("updates") or {}).get("updatedRange")


def batch_format_rows_background(
    service: Any,
    spreadsheet_id: str,
    sheet_id: int,
    row_indices_0based: list[int],
    end_column_exclusive: int,
    color: dict[str, float],
    *,
    chunk: int = 200,
) -> None:
    """Заливка фона для целых строк (0-based индекс строки листа; 0 = шапка)."""
    unique = sorted({r for r in row_indices_0based if r >= 1})
    if not unique:
        return
    requests: list[dict[str, Any]] = []
    for r in unique:
        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": r,
                        "endRowIndex": r + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": max(1, end_column_exclusive),
                    },
                    "cell": {"userEnteredFormat": {"backgroundColor": color}},
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        )
    for i in range(0, len(requests), chunk):
        (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests[i : i + chunk]},
            )
            .execute()
        )
