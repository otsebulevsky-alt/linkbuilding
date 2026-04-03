"""Кнопка «торг»: калькулятор за сегодня → email из «Сбор с ответов» → IMAP (тред) → SMTP-ответ со скидкой."""

from __future__ import annotations

import html as html_module
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from lib.config import AppConfig
from lib.mail_smtp import send_smtp_html
from lib.sheets_service import (
    a1_all_columns,
    get_sheet_title_by_gid,
    get_spreadsheet_values_rows,
    get_values_as_dataframe,
)

# Невидимые символы в ячейках Google Sheets (ZWSP, BOM, soft hyphen) ломают сравнение «Ответственный».
_HEADER_INVISIBLE_RE = re.compile(r"[\u200b-\u200d\ufeff\u00ad]")


def _clean_header_label(c: Any) -> str:
    s = _HEADER_INVISIBLE_RE.sub("", str(c or "").strip())
    s = unicodedata.normalize("NFKC", s)
    return " ".join(s.split())


def collect_responsible_needles(cfg: AppConfig) -> list[str]:
    """TRADE_RESPONSIBLE_NAME (можно несколько через |) + LINKBUILDER_FILTER + LINKBUILDER_ALIASES."""
    needles: list[str] = []
    raw = (cfg.trade_responsible_name or "").strip()
    if raw:
        for part in re.split(r"[|]", raw):
            p = part.strip()
            if len(p) >= 2:
                needles.append(p)
    lf = (cfg.linkbuilder_filter or "").strip()
    if len(lf) >= 2:
        needles.append(lf)
    for a in cfg.linkbuilder_aliases or []:
        p = (a or "").strip()
        if len(p) >= 2:
            needles.append(p)
    seen: set[str] = set()
    out: list[str] = []
    for n in needles:
        k = n.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(n)
    return out


def cell_matches_responsible(cell_val: str, needles: list[str]) -> bool:
    s = (cell_val or "").strip().lower()
    if not s or not needles:
        return False
    return any(n.lower() in s for n in needles)


def today_ddm_yyyy(tz_name: str) -> str:
    y, m, d = today_ymd(tz_name)
    return f"{d:02d}.{m:02d}.{y}"


def today_ymd(tz_name: str) -> tuple[int, int, int]:
    from zoneinfo import ZoneInfo

    name = (tz_name or "").strip() or "Europe/Moscow"
    try:
        tz = ZoneInfo(name)
    except Exception:
        tz = ZoneInfo("Europe/Moscow")
    now = datetime.now(tz)
    return (now.year, now.month, now.day)


def _valid_ymd(y: int, month: int, day: int) -> tuple[int, int, int] | None:
    try:
        dt = datetime(y, month, day)
    except ValueError:
        return None
    return (dt.year, dt.month, dt.day)


def parse_calc_trade_date_to_ymd(raw: Any) -> tuple[int, int, int] | None:
    """Дата торга из ячейки калькулятора → (год, месяц, день) для сравнения с «сегодня»."""
    if raw is None or isinstance(raw, bool):
        return None
    try:
        if pd.isna(raw):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(raw, str):
        s = raw.strip()
    else:
        s = str(raw).strip()

    def _from_serial(val: float) -> tuple[int, int, int] | None:
        if 25000 <= val <= 65000:
            epoch = datetime(1899, 12, 30)
            dt = epoch + timedelta(days=int(val))
            return (dt.year, dt.month, dt.day)
        return None

    if s:
        m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$", s)
        if m:
            return _valid_ymd(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        m2 = re.match(r"^(\d{4})-(\d{2})-(\d{2})\s*$", s)
        if m2:
            return _valid_ymd(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
        m3 = re.match(r"^(\d{4})[\s/.-]+(\d{1,2})[\s/.-]+(\d{1,2})\s*$", s)
        if m3:
            return _valid_ymd(int(m3.group(1)), int(m3.group(2)), int(m3.group(3)))
        m4 = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})\s*$", s)
        if m4:
            a, b, y = int(m4.group(1)), int(m4.group(2)), int(m4.group(3))
            if a > 12:
                return _valid_ymd(y, b, a)
            if b > 12:
                return _valid_ymd(y, a, b)
            return _valid_ymd(y, b, a)
        try:
            ser = float(s.replace(",", ".").strip())
            got = _from_serial(ser)
            if got is not None:
                return got
        except ValueError:
            pass
        return None

    try:
        n = float(raw)
    except (TypeError, ValueError):
        return None
    return _from_serial(n)


def normalize_domain_cell(v: Any) -> str:
    s = str(v or "").strip().lower()
    s = re.sub(r"^https?://", "", s, flags=re.I)
    s = s.split("/")[0].strip()
    s = s.split("?")[0].strip()
    if s.startswith("www."):
        s = s[4:]
    return s


def parse_price_number(raw: Any) -> float | None:
    s = str(raw or "").strip().replace("$", "").replace("\u00a0", " ").strip()
    if not s:
        return None
    s = re.sub(r"\s+", "", s)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts[-1]) <= 2 and parts[-1].isdigit():
            s = "".join(parts[:-1]) + "." + parts[-1]
        else:
            s = s.replace(",", "")
    try:
        v = float(s)
        return v if v > 0 else None
    except ValueError:
        return None


def _norm_header(c: Any) -> str:
    return _clean_header_label(c).lower()


def _column_names_for_header_probe(header_cells: list[Any]) -> list[str]:
    """Заголовки листа без построения DataFrame по всем строкам данных (для поиска строки шапки)."""
    return _make_unique_sheet_headers(header_cells)


def _header_match_key(label: Any) -> str:
    """Нормализация заголовка для сравнения (пробелы, NFKC, регистр, без ZWSP/BOM)."""
    return _clean_header_label(label).lower()


def resolve_calc_domain_col(df: pd.DataFrame) -> str | None:
    if df is None or not len(df.columns):
        return None
    norm_map = {_norm_header(c): c for c in df.columns}
    for key in ("домен", "domain", "site", "url", "website", "сайт"):
        if key in norm_map:
            return str(norm_map[key])
    return str(df.columns[0])


def resolve_calc_price_col(df: pd.DataFrame) -> str | None:
    if df is None or not len(df.columns):
        return None
    skip_if = (
        "гео",
        "балл",
        "score",
        "rd/ld",
        "стагнац",
        "ссылк",
        "links",
        "вывод",
        "referr",
    )
    # Только точные короткие шапки-метрики; подстрока «ld» ломала бы «sold», «golden» и т.д.
    metric_header_exact = frozenset(
        {
            "traffic",
            "dr",
            "ld",
            "rd",
            "rd/ld",
            "rd ld",
        }
    )
    for c in df.columns:
        cl = _norm_header(c)
        cln = _header_match_key(c)
        cln_nospace = cln.replace(" ", "")
        if any(x in cl or x in cln for x in skip_if):
            continue
        if cln_nospace in ("rd/ld", "rdld"):
            continue
        if cln in metric_header_exact and not (
            "цена" in cl or "price" in cln or "cost" in cln
        ):
            continue
        if "цена" in cl or "price" in cln or "cost" in cln:
            return str(c)
        if "$" in str(c) and ("usd" in cln or "цена" in cl or "price" in cln):
            return str(c)
    return None


def _fallback_responsible_col_telecom_layout(df: pd.DataFrame) -> str | None:
    """Калькулятор Telecomasia: Domain… колонка M (0-based 12) = ответственный; API иногда даёт `_c12` без текста."""
    cols = list(df.columns)
    if len(cols) < 13:
        return None
    if not resolve_calc_domain_col(df) or not resolve_calc_price_col(df):
        return None
    return str(cols[12])


def resolve_calc_responsible_col(df: pd.DataFrame, explicit_header: str = "") -> str | None:
    if df is None or not len(df.columns):
        return None
    ex = (explicit_header or "").strip()
    if ex:
        ex_key = _header_match_key(ex)
        for c in df.columns:
            if _clean_header_label(c) == _clean_header_label(ex):
                return str(c)
            if _norm_header(c) == ex_key:
                return str(c)
            if _header_match_key(c) == ex_key:
                return str(c)
        for c in df.columns:
            ck = _header_match_key(c)
            if ex_key and ex_key in ck:
                return str(c)
        for c in df.columns:
            if ex_key and ex_key in _norm_header(c):
                return str(c)
    for c in df.columns:
        cl = _norm_header(c)
        cln = _header_match_key(c)
        if (
            "ответствен" in cl
            or "ответствен" in cln
            or "responsible" in cln
            or "исполнитель" in cl
            or "исполнитель" in cln
            or "assignee" in cln
            or cln == "owner"
            or "owner" in cln
            or "менеджер" in cl
            or "менеджер" in cln
            or "linkbuilder" in cln
        ):
            return str(c)
    return _fallback_responsible_col_telecom_layout(df)


def _heuristic_calc_trade_date_col(df: pd.DataFrame) -> str | None:
    """Без точного COL_TRADE_DATE: комментарий Дениса, затем столбцы со словом «дата»."""
    for c in df.columns:
        cl = _norm_header(c)
        if "коммент" in cl and "денис" in cl:
            return str(c)
    candidates: list[str] = []
    for c in df.columns:
        cl = _norm_header(c)
        if "гео" in cl:
            continue
        if "коммент" in cl:
            continue
        if "дата" in cl:
            candidates.append(str(c))
    if len(candidates) == 1:
        return candidates[0]
    for c in candidates:
        if "торг" in _norm_header(c):
            return c
    for c in df.columns:
        cln = _header_match_key(c)
        if cln == "date" or cln.endswith(" date") or cln.startswith("date "):
            return str(c)
    return candidates[0] if candidates else None


def resolve_calc_trade_date_col(df: pd.DataFrame, explicit_header: str) -> str | None:
    if df is None or not len(df.columns):
        return None
    ex = (explicit_header or "").strip()
    if not ex:
        return _heuristic_calc_trade_date_col(df)
    ex_key = _header_match_key(ex)
    for c in df.columns:
        if str(c).strip() == ex or _norm_header(c) == ex.lower():
            return str(c)
        if _header_match_key(c) == ex_key:
            return str(c)
    for c in df.columns:
        ck = _header_match_key(c)
        if ex_key and ex_key in ck:
            return str(c)
    for c in df.columns:
        if ex.lower() in _norm_header(c):
            return str(c)
    return _heuristic_calc_trade_date_col(df)


def calc_trade_date_is_in_window(
    parsed: tuple[int, int, int],
    today: tuple[int, int, int],
    max_age_days: int,
) -> bool:
    """max_age_days <= 0 — только календарный сегодня; иначе от (сегодня − N) до сегодня включительно."""
    d_cell = date(parsed[0], parsed[1], parsed[2])
    d_today = date(today[0], today[1], today[2])
    if max_age_days <= 0:
        return d_cell == d_today
    if d_cell > d_today:
        return False
    return (d_today - d_cell).days <= max_age_days


def _make_unique_sheet_headers(raw: list[Any]) -> list[str]:
    cells = [_clean_header_label(c) if c is not None else "" for c in raw]
    seen: dict[str, int] = {}
    out: list[str] = []
    for i, h in enumerate(cells):
        base = h if h else f"_c{i}"
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.append(base if n == 0 else f"{base}__{n}")
    return out


def sheet_rows_to_calculator_dataframe(rows: list[list[Any]], header_row_index: int) -> pd.DataFrame:
    """Строит DataFrame: строка header_row_index — заголовки, ниже — данные."""
    if header_row_index < 0 or header_row_index >= len(rows):
        return pd.DataFrame()
    header = _make_unique_sheet_headers(rows[header_row_index])
    if not header:
        return pd.DataFrame()
    data_rows = rows[header_row_index + 1 :]
    max_len = len(header)
    normalized: list[list[Any]] = []
    for row in data_rows:
        r = list(row) + [""] * (max_len - len(row))
        normalized.append(r[:max_len])
    return pd.DataFrame(normalized, columns=header)


def trade_calculator_columns_ok(
    df: pd.DataFrame, col_trade_date: str, col_trade_responsible: str = ""
) -> bool:
    return bool(
        resolve_calc_domain_col(df)
        and resolve_calc_price_col(df)
        and resolve_calc_responsible_col(df, col_trade_responsible)
        and resolve_calc_trade_date_col(df, col_trade_date)
    )


def discover_calculator_dataframe_from_rows(
    rows: list[list[Any]], col_trade_date: str, col_trade_responsible: str = ""
) -> tuple[pd.DataFrame, int]:
    """Подбирает строку шапки по всему прочитанному диапазону (служебные строки сверху)."""
    if not rows:
        return pd.DataFrame(), -1
    for hi in range(len(rows)):
        if not any(str(c).strip() for c in rows[hi]):
            continue
        names = _column_names_for_header_probe(rows[hi])
        if not names:
            continue
        probe = pd.DataFrame(columns=names)
        if trade_calculator_columns_ok(probe, col_trade_date, col_trade_responsible):
            return sheet_rows_to_calculator_dataframe(rows, hi), hi
    return sheet_rows_to_calculator_dataframe(rows, 0), 0


def _pad_rows_to_max_width(rows: list[list[Any]]) -> list[list[Any]]:
    """Выравнивает длины строк: у API часто разная длина рядов — шапка не доходит до M, а данные длиннее."""
    if not rows:
        return rows
    m = max(len(r) for r in rows)
    return [list(r) + [""] * (m - len(r)) for r in rows]


def load_calculator_dataframe_for_trade(
    sheets_service: Any,
    spreadsheet_id: str,
    sheet_title: str,
    col_trade_date: str,
    col_trade_responsible: str = "",
) -> tuple[pd.DataFrame, int]:
    esc = sheet_title.replace("'", "''")
    # Было ZZ400 — строки ниже не попадали в «торг»; 10000 с запасом под длинные листы.
    rng = f"'{esc}'!A1:ZZ10000"
    rows = get_spreadsheet_values_rows(sheets_service, spreadsheet_id, rng)
    rows = _pad_rows_to_max_width(rows)
    return discover_calculator_dataframe_from_rows(
        rows, col_trade_date, col_trade_responsible
    )


def resolve_inbox_domain_col(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None
    for c in df.columns:
        cl = _norm_header(c)
        if cl in ("домен", "domain"):
            return str(c)
    return str(df.columns[0])


def resolve_inbox_email_col(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None
    # Не брать объединённый заголовок вроде «Цена после торг Почта» — там не полный текст ответа.
    for c in df.columns:
        cl = _norm_header(c)
        if not ("почт" in cl or cl == "email" or "e-mail" in cl):
            continue
        if "цена" in cl or "торг" in cl or "after" in cl:
            continue
        return str(c)
    # Fallback: колонка с «почт», даже если в заголовке ещё «цена» (лучше, чем None для старых листов).
    for c in df.columns:
        cl = _norm_header(c)
        if "почт" in cl or cl == "email" or "e-mail" in cl:
            return str(c)
    return None


def resolve_inbox_date_col(df: pd.DataFrame) -> str | None:
    """Колонка даты: «дата» / «date» (как в шапке «Сбор с ответов»); иначе второй столбец (B после «Домен»)."""
    if df is None or df.empty:
        return None
    norm_map = {_norm_header(c): str(c) for c in df.columns}
    for key in ("дата", "date"):
        if key in norm_map:
            return norm_map[key]
    if len(df.columns) > 1:
        return str(df.columns[1])
    return None


def resolve_inbox_price_col(df: pd.DataFrame) -> str | None:
    """Колонка «цена» в «Сбор с ответов»; не путать с «Цена после торг»."""
    if df is None or df.empty:
        return None
    for c in df.columns:
        cl = _norm_header(c)
        if "после" in cl or "торг" in cl:
            continue
        if "цена" in cl and "после" not in cl:
            return str(c)
        if cl in ("price", "cost"):
            return str(c)
    if len(df.columns) > 2:
        return str(df.columns[2])
    return None


def _parse_inbox_date_sort_key(raw: str) -> tuple:
    s = (raw or "").strip()
    if not s:
        return (0, 0, 0)
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return (y, mo, d)
    m2 = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m2:
        y, mo, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        return (y, mo, d)
    return (0, 0, 0)


def find_webmaster_email_in_inbox_log(df_inbox: pd.DataFrame, domain: str) -> str:
    dom_c = resolve_inbox_domain_col(df_inbox)
    mail_c = resolve_inbox_email_col(df_inbox)
    if not dom_c or not mail_c:
        return ""
    date_c = resolve_inbox_date_col(df_inbox)
    nd = normalize_domain_cell(domain)
    best: tuple[tuple[int, int, int], str] | None = None
    for _, row in df_inbox.iterrows():
        if normalize_domain_cell(row.get(dom_c, "")) != nd:
            continue
        mail = str(row.get(mail_c, "") or "").strip()
        if not mail or "@" not in mail:
            continue
        d_raw = str(row.get(date_c, "") or "").strip() if date_c else ""
        key = _parse_inbox_date_sort_key(d_raw)
        if best is None or key > best[0]:
            best = (key, mail)
    return best[1] if best else ""


def run_trade_bargain_round(
    *,
    sheets_service: Any,
    cfg: AppConfig,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    imap_host: str,
    imap_user: str,
    imap_password: str,
    imap_mailbox: str,
    imap_timeout_sec: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "errors": [],
        "today": "",
        "calc_sheet_title": "",
        "calc_trade_date_column": "",
        "trade_date_max_age_days": 0,
        "filter_stats": {},
        "needles": [],
        "rows_matched": 0,
        "domains_considered": 0,
        "sent": 0,
        "skipped": [],
        "smtp_errors": [],
    }
    needles = collect_responsible_needles(cfg)
    report["needles"] = needles
    if not needles:
        report["errors"].append(
            "Не заданы подстроки для колонки ответственного: укажите **TRADE_RESPONSIBLE_NAME** "
            "и/или **LINKBUILDER_FILTER** / **LINKBUILDER_ALIASES** в Secrets."
        )
        return report

    today_s = today_ddm_yyyy(cfg.trade_timezone)
    report["today"] = today_s
    today_tuple = today_ymd(cfg.trade_timezone)
    report["trade_date_max_age_days"] = int(cfg.trade_date_max_age_days)

    if not (smtp_user and smtp_password):
        report["errors"].append(
            "SMTP не настроен: нужны **GMAIL_SMTP_*** или **GMAIL_IMAP_*** (пароль приложения)."
        )
        return report

    if not (imap_user and imap_password):
        report["errors"].append(
            "IMAP не настроен: для ответа в тред нужны **GMAIL_IMAP_*** (или **GMAIL_SMTP_*** с тем же паролем приложения), "
            "как для **«Прочитать почту»** и **«отправить статьи»**."
        )
        return report

    # Ленивый импорт: иначе цикл trade_bargain ↔ mail_thread_lookup (там normalize_domain_cell).
    from lib.mail_thread_lookup import find_reply_context_for_peer

    title_calc = get_sheet_title_by_gid(
        sheets_service, cfg.spreadsheet_calculator_id, cfg.gid_calculator_tab_primary
    )
    if not title_calc:
        report["errors"].append(
            f"Калькулятор: не найден лист gid={cfg.gid_calculator_tab_primary}. Проверьте **GID_CALCULATOR_TAB_1**."
        )
        return report
    report["calc_sheet_title"] = title_calc

    df_calc, hdr_row_idx = load_calculator_dataframe_for_trade(
        sheets_service,
        cfg.spreadsheet_calculator_id,
        title_calc,
        cfg.col_trade_date,
        cfg.col_trade_responsible,
    )
    if df_calc.empty:
        report["errors"].append("Калькулятор: лист пуст, не прочитан API или нет строк под шапкой.")
        return report
    report["calc_header_row_1based"] = hdr_row_idx + 1 if hdr_row_idx >= 0 else 1

    col_dom = resolve_calc_domain_col(df_calc)
    col_price = resolve_calc_price_col(df_calc)
    col_resp = resolve_calc_responsible_col(df_calc, cfg.col_trade_responsible)
    col_date = resolve_calc_trade_date_col(df_calc, cfg.col_trade_date)
    if not col_dom or not col_price or not col_resp or not col_date:
        miss: list[str] = []
        if not col_dom:
            miss.append("домен")
        if not col_price:
            miss.append("цена")
        if not col_resp:
            miss.append("ответственный")
        if not col_date:
            miss.append("дата")
        report["errors"].append(
            f"Калькулятор **«{title_calc}»**: не сопоставлены колонки: **{', '.join(miss)}**. "
            f"Строка шапки (авто): **{report['calc_header_row_1based']}** (поиск по всему прочитанному диапазону, до **10000** строк). "
            f"Книга: **SPREADSHEET_CALCULATOR_ID** + **GID_CALCULATOR_TAB_1**. "
            f"Ожидаются заголовки вроде **Domain**, **Цена, $** / **Price** / **Cost**, **Ответственный**, "
            f"**Комментарий (Денис)** / **Date** — или задайте **COL_TRADE_DATE** / **COL_TRADE_RESPONSIBLE** в Secrets."
        )
        return report
    report["calc_trade_date_column"] = col_date

    title_inbox = get_sheet_title_by_gid(
        sheets_service, cfg.spreadsheet_inbox_log_id, cfg.gid_inbox_log
    )
    if not title_inbox:
        report["errors"].append(
            f"«Сбор с ответов»: не найден лист gid={cfg.gid_inbox_log}. Проверьте **GID_INBOX_LOG**."
        )
        return report

    df_inbox = get_values_as_dataframe(
        sheets_service, cfg.spreadsheet_inbox_log_id, a1_all_columns(title_inbox)
    )
    if df_inbox.empty:
        report["errors"].append("«Сбор с ответов»: лист пуст — неоткуда взять email вебмастера.")
        return report

    if not resolve_inbox_email_col(df_inbox):
        report["errors"].append("«Сбор с ответов»: не найдена колонка почты (ожидается заголовок вроде **Почта**).")
        return report

    stats: dict[str, int] = {
        "calc_data_rows": int(len(df_calc)),
        "skip_empty_date": 0,
        "skip_bad_date": 0,
        "skip_future_date": 0,
        "skip_old_date": 0,
        "skip_responsible": 0,
        "skip_empty_domain": 0,
        "skip_bad_price": 0,
        "passed_filters": 0,
    }

    # Последняя подходящая строка по домену перезаписывает предыдущие (низ листа = новее)
    by_domain: dict[str, dict[str, Any]] = {}
    for _, row in df_calc.iterrows():
        cell_date = row.get(col_date, "")
        parsed = parse_calc_trade_date_to_ymd(cell_date)
        if parsed is None:
            if not str(cell_date).strip():
                stats["skip_empty_date"] += 1
            else:
                stats["skip_bad_date"] += 1
            continue
        if not calc_trade_date_is_in_window(parsed, today_tuple, cfg.trade_date_max_age_days):
            d_cell = date(parsed[0], parsed[1], parsed[2])
            d_today = date(today_tuple[0], today_tuple[1], today_tuple[2])
            if d_cell > d_today:
                stats["skip_future_date"] += 1
            else:
                stats["skip_old_date"] += 1
            continue
        if not cell_matches_responsible(str(row.get(col_resp, "") or ""), needles):
            stats["skip_responsible"] += 1
            continue
        dom = str(row.get(col_dom, "") or "").strip()
        if not dom:
            stats["skip_empty_domain"] += 1
            continue
        price = parse_price_number(row.get(col_price))
        if price is None:
            stats["skip_bad_price"] += 1
            report["skipped"].append({"domain": dom, "reason": "bad_price"})
            continue
        stats["passed_filters"] += 1
        nd = normalize_domain_cell(dom)
        by_domain[nd] = {"domain": dom, "price": price}

    report["filter_stats"] = stats
    report["rows_matched"] = len(by_domain)
    if not by_domain:
        win = (
            f"только **{today_s}**"
            if cfg.trade_date_max_age_days <= 0
            else f"от **{today_s}** назад до **{cfg.trade_date_max_age_days}** календарных дней (вкл.)"
        )
        report["errors"].append(
            f"Нет строк калькулятора **«{title_calc}»**, где дата в **{col_date}** попадает в окно: {win} "
            f"(по **{cfg.trade_timezone}**), в **{col_resp}** есть подстрока из фильтра, домен и цена валидны. "
            f"Смотрите **диагностику фильтра** ниже. Форматы даты: **ДД.ММ.ГГГГ**, **ГГГГ-ММ-ДД**, **ГГГГ ММ ДД**. "
            f"**TRADE_DATE_MAX_AGE_DAYS** = **0** — только сегодня; иначе окно в днях. "
            f"**GID_CALCULATOR_TAB_1** должен указывать на лист с данными (например **Telecomasia**)."
        )
        return report

    discount = min(max(cfg.trade_discount_percent, 0.0), 0.95)

    for nd, pack in sorted(by_domain.items(), key=lambda x: x[0]):
        report["domains_considered"] += 1
        dom = pack["domain"]
        price = float(pack["price"])
        to_addr = find_webmaster_email_in_inbox_log(df_inbox, dom)
        if not to_addr:
            report["skipped"].append({"domain": dom, "reason": "no_email_in_inbox_log"})
            continue
        ctx = find_reply_context_for_peer(
            imap_host=imap_host,
            imap_user=imap_user,
            imap_password=imap_password,
            imap_mailbox=imap_mailbox,
            peer_email=to_addr,
            domain=dom,
            timeout_sec=max(60, int(imap_timeout_sec)),
        )
        if not ctx:
            report["skipped"].append({"domain": dom, "reason": "no_imap_thread"})
            continue
        new_price = round(price * (1.0 - discount), 2)
        pct = int(round(discount * 100))
        esc_dom = html_module.escape(dom)
        esc_price = html_module.escape(str(price))
        esc_new = html_module.escape(str(new_price))
        subj = ((ctx.get("subject") or "").strip() or "Re: ")[:998]
        body = (
            f"<p>Hello,</p>"
            f"<p>Thank you. We would really love to place our content with you "
            f"(<b>{esc_dom}</b>). "
            f"Could we agree on a small discount of <b>{pct}&nbsp;%</b>? "
            f"In that case the rate would be <b>{esc_new}</b> USD instead of <b>{esc_price}</b> USD. "
            f"We would be grateful for your reply.</p>"
            f"<p>Kind regards</p>"
            f"<p>—</p>"
            f"<p>Здравствуйте.</p>"
            f"<p>Спасибо вам. Нам бы очень хотелось разместиться у вас "
            f"(площадка <b>{esc_dom}</b>). "
            f"Не могли бы мы договориться о небольшой скидке <b>в {pct}&nbsp;%</b>? "
            f"Тогда ориентир — <b>{esc_new}</b> USD вместо <b>{esc_price}</b> USD. "
            f"Будем благодарны за ответ.</p>"
            f"<p>С уважением</p>"
        )
        try:
            send_smtp_html(
                host=smtp_host,
                port=int(smtp_port),
                user=smtp_user,
                password=smtp_password,
                to_addr=to_addr,
                subject=subj,
                html_body=body,
                use_tls=True,
                in_reply_to=ctx.get("message_id"),
                references=ctx.get("references"),
            )
            report["sent"] += 1
        except Exception as e:
            report["smtp_errors"].append(f"{dom} → {to_addr}: {e}")

    return report
