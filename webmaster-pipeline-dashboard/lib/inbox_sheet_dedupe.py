"""Дедупликация строк «Сбор с ответов» и подсветка цены (мин — зелёный, макс — красный)."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import pandas as pd

from lib.sheets_service import (
    a1_all_columns,
    get_sheet_id_by_gid,
    get_sheet_title_by_gid,
    get_values_as_dataframe,
)
from lib.trade_bargain import (
    normalize_domain_cell,
    parse_price_number,
    resolve_inbox_domain_col,
    resolve_inbox_price_col,
)

_COLOR_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
_COLOR_GREEN = {"red": 0.78, "green": 0.94, "blue": 0.80}
_COLOR_RED = {"red": 0.96, "green": 0.80, "blue": 0.80}

_FLOAT_EPS = 1e-6


def batch_delete_rows_by_zero_based_indices(
    service: Any,
    spreadsheet_id: str,
    sheet_id: int,
    row_indices_0based: list[int],
) -> None:
    """Удаляет строки; индексы — как в Sheets API (0 = первая строка листа). Снизу вверх."""
    unique = sorted({i for i in row_indices_0based if i > 0}, reverse=True)
    if not unique:
        return
    requests = [
        {
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": idx,
                    "endIndex": idx + 1,
                }
            }
        }
        for idx in unique
    ]
    (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
        .execute()
    )


def _norm_sig_cell(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v).strip().lower())


def exact_duplicate_sheet_rows_to_delete(df: pd.DataFrame) -> list[int]:
    """
    Строки для удаления (0-based индекс **строки листа**, строка 0 = шапка).
    Полные дубликаты по всем ячейкам: остаётся **верхняя** строка (меньший индекс).
    """
    if df.empty:
        return []
    cols = [str(c) for c in df.columns]
    groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for pos, (_, row) in enumerate(df.iterrows()):
        sig = tuple(_norm_sig_cell(row.get(c)) for c in cols)
        groups[sig].append(pos + 1)
    to_del: list[int] = []
    for _sig, api_rows in groups.items():
        if len(api_rows) <= 1:
            continue
        sorted_rows = sorted(api_rows)
        to_del.extend(sorted_rows[1:])
    return to_del


def _price_highlight_for_sheet_rows(df: pd.DataFrame, domain_col: str, price_col: str) -> dict[int, str]:
    """
    api_row_0based (строка листа) -> 'green' | 'red' | 'clear'.
    Только при ≥2 строках с тем же доменом и различимых числовых ценах.
    """
    out: dict[int, str] = {}
    if df.empty or not domain_col or not price_col:
        return out
    by_dom: dict[str, list[tuple[int, float | None]]] = defaultdict(list)
    for pos, (_, row) in enumerate(df.iterrows()):
        dom = normalize_domain_cell(row.get(domain_col, ""))
        if not dom:
            continue
        api_row = pos + 1
        p = parse_price_number(row.get(price_col, ""))
        by_dom[dom].append((api_row, p))

    for _dom, rows in by_dom.items():
        if len(rows) < 2:
            for api_row, _p in rows:
                out[api_row] = "clear"
            continue
        parsed = [p for _r, p in rows if p is not None]
        if len(parsed) < 2:
            for api_row, _p in rows:
                out[api_row] = "clear"
            continue
        lo, hi = min(parsed), max(parsed)
        if abs(lo - hi) < _FLOAT_EPS:
            for api_row, _p in rows:
                out[api_row] = "clear"
            continue
        for api_row, p in rows:
            if p is None:
                out[api_row] = "clear"
            elif abs(p - lo) < _FLOAT_EPS:
                out[api_row] = "green"
            elif abs(p - hi) < _FLOAT_EPS:
                out[api_row] = "red"
            else:
                out[api_row] = "clear"
    return out


def _repeat_cell_background(
    sheet_id: int,
    row_0based: int,
    start_col: int,
    end_col: int,
    color: dict[str, float],
) -> dict[str, Any]:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_0based,
                "endRowIndex": row_0based + 1,
                "startColumnIndex": start_col,
                "endColumnIndex": end_col,
            },
            "cell": {"userEnteredFormat": {"backgroundColor": color}},
            "fields": "userEnteredFormat.backgroundColor",
        }
    }


def _batch_update_chunks(service: Any, spreadsheet_id: str, requests: list[dict], chunk: int = 400) -> None:
    for i in range(0, len(requests), chunk):
        chunk_req = requests[i : i + chunk]
        (
            service.spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": chunk_req})
            .execute()
        )


def dedupe_and_highlight_inbox_sheet(
    *,
    sheets_service: Any,
    spreadsheet_id: str,
    sheet_gid: int,
) -> dict[str, Any]:
    """
    1) Удаляет полные дубликаты строк (все столбцы совпадают), оставляет верхнюю копию.
    2) Сбрасывает фон данных (белый), затем для каждого домена с ≥2 строками и разными ценами:
       минимальная цена — зелёный фон строки, максимальная — красный, промежуточные — белый.
    """
    report: dict[str, Any] = {
        "duplicates_removed": 0,
        "rows_formatted": 0,
        "errors": [],
        "sheet_title": "",
    }
    title = get_sheet_title_by_gid(sheets_service, spreadsheet_id, sheet_gid)
    if not title:
        report["errors"].append(
            f"Не найден лист gid={sheet_gid} в таблице {spreadsheet_id} (проверьте GID_INBOX_LOG и доступ)."
        )
        return report
    report["sheet_title"] = title

    sid = get_sheet_id_by_gid(sheets_service, spreadsheet_id, sheet_gid)
    if sid is None:
        report["errors"].append(f"Не удалось получить sheetId для gid={sheet_gid}.")
        return report

    try:
        df = get_values_as_dataframe(sheets_service, spreadsheet_id, a1_all_columns(title))
        if df.empty:
            return report

        domain_col = resolve_inbox_domain_col(df)
        price_col = resolve_inbox_price_col(df)
        if not domain_col or not price_col:
            report["errors"].append(
                "Не найдены колонки «Домен» и/или «цена» для дедупа и подсветки."
            )
            return report

        ncols = len(df.columns)
        to_del = exact_duplicate_sheet_rows_to_delete(df)
        if to_del:
            batch_delete_rows_by_zero_based_indices(sheets_service, spreadsheet_id, sid, to_del)
            report["duplicates_removed"] = len(to_del)
            df = get_values_as_dataframe(sheets_service, spreadsheet_id, a1_all_columns(title))
            if df.empty:
                return report

        n_data = len(df)
        requests: list[dict[str, Any]] = []
        if n_data > 0:
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sid,
                            "startRowIndex": 1,
                            "endRowIndex": 1 + n_data,
                            "startColumnIndex": 0,
                            "endColumnIndex": ncols,
                        },
                        "cell": {"userEnteredFormat": {"backgroundColor": _COLOR_WHITE}},
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
            )

        highlights = _price_highlight_for_sheet_rows(df, domain_col, price_col)
        color_map = {"green": _COLOR_GREEN, "red": _COLOR_RED, "clear": _COLOR_WHITE}
        for api_row, kind in sorted(highlights.items()):
            if kind not in ("green", "red"):
                continue
            requests.append(
                _repeat_cell_background(sid, api_row, 0, ncols, color_map[kind])
            )
            report["rows_formatted"] += 1

        if requests:
            _batch_update_chunks(sheets_service, spreadsheet_id, requests)
    except Exception as e:
        report["errors"].append(f"Дедуп / подсветка: {e}")
    return report
