"""Удаление из листа «Сбор с ответов» строк, которые точно не ответы вебмастера."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from lib.mail_parse import is_automated_bounce_message, is_non_webmaster_platform_host
from lib.payment_match import is_our_payment_followup_template_only
from lib.sheets_service import (
    a1_all_columns,
    get_sheet_id_by_gid,
    get_sheet_title_by_gid,
    get_values_as_dataframe,
)
from lib.trade_bargain import normalize_domain_cell, resolve_inbox_domain_col, resolve_inbox_email_col


# Только адрес в ячейке «Почта» (без текста ответа) — не логируем как ответ вебмастера.
_EMAIL_ONLY_CELL_RE = re.compile(
    r"^[^\s@]+@[^\s@]+\.[^\s@]+\s*$",
    re.I,
)


def mail_cell_is_inbox_noise(cell: str) -> bool:
    """
    True — строку можно убрать из «Сбор с ответов»:
    - тело ячейки по сути только наш шаблон USDT/PayPal (часто «email + шаблон»);
    - или в ячейке только email без какого-либо текста ответа;
    - или текст отказа доставки / mailer-daemon (как в письме Mail Delivery Subsystem).
    """
    s = (cell or "").strip()
    if not s:
        return False
    if is_automated_bounce_message(from_header=s, from_addr="", subject="", body=s):
        return True
    if is_our_payment_followup_template_only(body=s):
        return True
    return bool(_EMAIL_ONLY_CELL_RE.match(s))


def inbox_log_row_is_removable_noise(
    row: pd.Series,
    *,
    mail_col: str,
    domain_col: str | None,
) -> bool:
    """Строка «Сбор с ответов» — шум по «Почте» или по «Домену» (github, slack, hunter, …)."""
    if mail_cell_is_inbox_noise(str(row.get(mail_col, "") or "")):
        return True
    if domain_col:
        dom = normalize_domain_cell(row.get(domain_col, ""))
        if dom and is_non_webmaster_platform_host(dom):
            return True
    return False


def _data_row_indices_to_delete_api_0based(
    df: pd.DataFrame, mail_col: str, domain_col: str | None
) -> list[int]:
    """Индексы строк листа для Sheets API (0-based; строка 0 — шапка)."""
    out: list[int] = []
    for pos, (_, row) in enumerate(df.iterrows()):
        if inbox_log_row_is_removable_noise(row, mail_col=mail_col, domain_col=domain_col):
            out.append(pos + 1)
    return out


def batch_delete_rows_by_zero_based_indices(
    service: Any,
    spreadsheet_id: str,
    sheet_id: int,
    row_indices_0based: list[int],
) -> None:
    """Удаляет строки; индексы — как в API (0 = первая строка листа). Снизу вверх."""
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


def remove_inbox_noise_rows(
    *,
    sheets_service: Any,
    spreadsheet_id: str,
    sheet_gid: int,
) -> dict[str, Any]:
    """
    Читает лист по gid, удаляет строки с шумом в колонке «Почта».
    Шапка (строка 1) не трогается.
    """
    report: dict[str, Any] = {
        "rows_deleted": 0,
        "candidates": 0,
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
        report["errors"].append(
            f"Не удалось получить sheetId для gid={sheet_gid}."
        )
        return report

    try:
        df = get_values_as_dataframe(sheets_service, spreadsheet_id, a1_all_columns(title))
        if df.empty:
            return report
        mail_col = resolve_inbox_email_col(df)
        if not mail_col:
            report["errors"].append(
                "Не найдена колонка «Почта» / email в первой строке листа."
            )
            return report
        domain_col = resolve_inbox_domain_col(df)

        to_del = _data_row_indices_to_delete_api_0based(df, mail_col, domain_col)
        report["candidates"] = len(to_del)
        if not to_del:
            return report

        batch_delete_rows_by_zero_based_indices(
            sheets_service, spreadsheet_id, sid, to_del
        )
        report["rows_deleted"] = len(to_del)
    except Exception as e:
        report["errors"].append(f"Очистка листа: {e}")
    return report
