"""Google Sheets API — read ranges, resolve sheet by gid, optional append row."""

from __future__ import annotations

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


def get_sheet_title_by_gid(service, spreadsheet_id: str, gid: int) -> str | None:
    """Return sheet title for numeric sheetId (same as gid in URL). gid=0 — первая вкладка книги."""
    if gid < 0:
        return None
    try:
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
        sheets = meta.get("sheets", [])
        for sh in sheets:
            props = sh.get("properties") or {}
            if props.get("sheetId") == gid:
                return props.get("title")
        if gid == 0 and sheets:
            props0 = sheets[0].get("properties") or {}
            return props0.get("title")
    except HttpError:
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
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_a1, majorDimension="ROWS")
        .execute()
    )
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


def append_row(service, spreadsheet_id: str, sheet_title: str, row_values: list[Any]) -> None:
    escaped = sheet_title.replace("'", "''")
    range_a1 = f"'{escaped}'!A1"
    body = {"values": [row_values]}
    (
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
