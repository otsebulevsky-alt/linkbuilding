"""Кнопка «торг»: строки калькулятора за сегодня (ДД.ММ.ГГГГ) + ответственный → email из «Сбор с ответов» → SMTP −20%."""

from __future__ import annotations

import html as html_module
import re
from datetime import datetime
from typing import Any

import pandas as pd

from lib.config import AppConfig
from lib.mail_smtp import send_smtp_html
from lib.sheets_service import a1_all_columns, get_sheet_title_by_gid, get_values_as_dataframe


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
    from zoneinfo import ZoneInfo

    name = (tz_name or "").strip() or "Europe/Moscow"
    try:
        tz = ZoneInfo(name)
    except Exception:
        tz = ZoneInfo("Europe/Moscow")
    return datetime.now(tz).strftime("%d.%m.%Y")


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
    return str(c or "").strip().lower()


def resolve_calc_domain_col(df: pd.DataFrame) -> str | None:
    if df is None or df.empty or not len(df.columns):
        return None
    norm_map = {_norm_header(c): c for c in df.columns}
    for key in ("домен", "domain", "site"):
        if key in norm_map:
            return str(norm_map[key])
    return str(df.columns[0])


def resolve_calc_price_col(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None
    for c in df.columns:
        cl = _norm_header(c)
        if "гео" in cl:
            continue
        if "цена" in cl or ("price" in cl and "$" in str(c)):
            return str(c)
        if cl == "cost $" or ("cost" in cl and "$" in str(c)):
            return str(c)
    return None


def resolve_calc_responsible_col(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None
    for c in df.columns:
        cl = _norm_header(c)
        if "ответствен" in cl or "responsible" in cl:
            return str(c)
    return None


def resolve_calc_trade_date_col(df: pd.DataFrame, explicit_header: str) -> str | None:
    if df is None or df.empty:
        return None
    ex = (explicit_header or "").strip()
    if ex:
        for c in df.columns:
            if str(c).strip() == ex or _norm_header(c) == ex.lower():
                return str(c)
        for c in df.columns:
            if ex.lower() in _norm_header(c):
                return str(c)
    candidates: list[str] = []
    for c in df.columns:
        cl = _norm_header(c)
        if "гео" in cl:
            continue
        if "дата" in cl:
            candidates.append(str(c))
    if len(candidates) == 1:
        return candidates[0]
    for c in candidates:
        if "торг" in _norm_header(c):
            return c
    return candidates[0] if candidates else None


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
    for c in df.columns:
        cl = _norm_header(c)
        if "почт" in cl or cl == "email" or "e-mail" in cl:
            return str(c)
    return None


def resolve_inbox_date_col(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None
    for c in df.columns:
        if _norm_header(c) == "дата":
            return str(c)
    if len(df.columns) > 1:
        return str(df.columns[1])
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
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "errors": [],
        "today": "",
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

    if not (smtp_user and smtp_password):
        report["errors"].append(
            "SMTP не настроен: нужны **GMAIL_SMTP_*** или **GMAIL_IMAP_*** (пароль приложения)."
        )
        return report

    title_calc = get_sheet_title_by_gid(
        sheets_service, cfg.spreadsheet_calculator_id, cfg.gid_calculator_tab_primary
    )
    if not title_calc:
        report["errors"].append(
            f"Калькулятор: не найден лист gid={cfg.gid_calculator_tab_primary}. Проверьте **GID_CALCULATOR_TAB_1**."
        )
        return report

    df_calc = get_values_as_dataframe(
        sheets_service, cfg.spreadsheet_calculator_id, a1_all_columns(title_calc)
    )
    if df_calc.empty:
        report["errors"].append("Калькулятор: лист пуст или не прочитан.")
        return report

    col_dom = resolve_calc_domain_col(df_calc)
    col_price = resolve_calc_price_col(df_calc)
    col_resp = resolve_calc_responsible_col(df_calc)
    col_date = resolve_calc_trade_date_col(df_calc, cfg.col_trade_date)
    if not col_dom or not col_price or not col_resp or not col_date:
        report["errors"].append(
            "Калькулятор: не удалось сопоставить колонки (домен / цена / ответственный / дата). "
            "Задайте **COL_TRADE_DATE** = точный заголовок столбца с датой **ДД.ММ.ГГГГ**."
        )
        return report

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

    # Последняя подходящая строка по домену перезаписывает предыдущие (низ листа = новее)
    by_domain: dict[str, dict[str, Any]] = {}
    for _, row in df_calc.iterrows():
        d_raw = str(row.get(col_date, "") or "").strip()
        if d_raw != today_s:
            continue
        if not cell_matches_responsible(str(row.get(col_resp, "") or ""), needles):
            continue
        dom = str(row.get(col_dom, "") or "").strip()
        if not dom:
            continue
        price = parse_price_number(row.get(col_price))
        if price is None:
            report["skipped"].append({"domain": dom, "reason": "bad_price"})
            continue
        nd = normalize_domain_cell(dom)
        by_domain[nd] = {"domain": dom, "price": price}

    report["rows_matched"] = len(by_domain)
    if not by_domain:
        report["errors"].append(
            f"Нет строк за **{today_s}** с вашим именем в «{col_resp}». "
            f"Проверьте дату в таблице и **TRADE_RESPONSIBLE_NAME** / linkbuilder-фильтр."
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
        new_price = round(price * (1.0 - discount), 2)
        pct = int(round(discount * 100))
        esc_dom = html_module.escape(dom)
        esc_price = html_module.escape(str(price))
        esc_new = html_module.escape(str(new_price))
        subj = f"Re: {dom} — pricing / согласование цены"
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
                subject=subj[:998],
                html_body=body,
                use_tls=True,
            )
            report["sent"] += 1
        except Exception as e:
            report["smtp_errors"].append(f"{dom} → {to_addr}: {e}")

    return report
