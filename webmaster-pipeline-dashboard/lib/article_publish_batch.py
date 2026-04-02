"""Кнопка «отправить статьи»: строки «Жду публикации» в реестрах → почта из «Сбор с ответов» → SMTP."""

from __future__ import annotations

import html as html_module
from typing import Any

from lib.config import AppConfig
from lib.mail_smtp import send_smtp_html
from lib.sheets_service import (
    a1_all_columns,
    filter_by_linkbuilder,
    get_sheet_title_by_gid,
    get_values_as_dataframe,
    resolve_article_column,
    resolve_cost_column,
    resolve_donor_column,
    resolve_linkbuilder_column,
    resolve_status_column,
)
from lib.trade_bargain import find_webmaster_email_in_inbox_log, normalize_domain_cell


def is_google_docs_or_drive_url(raw: str) -> bool:
    """Ссылка на черновик в Google Docs / Drive (колонка Article/post в реестре)."""
    s = (raw or "").strip().lower()
    if not s.startswith("http"):
        return False
    return "docs.google.com" in s or "drive.google.com" in s


def build_article_publish_email_html(article_raw: str, cost_raw: str) -> str:
    """Двуязычное тело, как на вкладке «Жду публикации» (EN + RU)."""
    art = (article_raw or "").strip()
    cost = (cost_raw or "").strip()
    esc_art = html_module.escape(art)
    esc_cost = html_module.escape(cost)
    if art.lower().startswith("http"):
        art_html_en = f'<a href="{esc_art}">{esc_art}</a>'
        art_html_ru = art_html_en
    else:
        art_html_en = esc_art if art else "—"
        art_html_ru = esc_art if art else "—"
    if cost:
        fee_en = f"<b>{esc_cost}</b> USD (see internal calculator if needed)."
        fee_ru = f"<b>{esc_cost}</b> USD (уточните по калькулятору при необходимости)."
    else:
        fee_en = "as discussed."
        fee_ru = "по согласованию."
    return (
        f"<p>Hello,</p>"
        f"<p>Could you please publish our article? The text is in this Google Doc: {art_html_en}</p>"
        f"<p>Placement fee (gambling): {fee_en}</p>"
        f"<p>Best regards</p>"
        f"<p>—</p>"
        f"<p>Здравствуйте!</p>"
        f"<p>Пожалуйста, разместите нашу статью. Документ в Google Docs: {art_html_ru}</p>"
        f"<p>Сумма за размещение (гемблинг): {fee_ru}</p>"
        f"<p>С уважением</p>"
    )


def run_article_publish_batch(
    *,
    sheets_service: Any,
    cfg: AppConfig,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
) -> dict[str, Any]:
    """
    Строки: статус «Жду публикации» (колонка Status), в колонке Article/post — ссылка на **Google Docs/Drive**,
    домен из Website Donor → почта из «Сбор с ответов» → SMTP (новое письмо, не ответ в тред Gmail).
    """
    report: dict[str, Any] = {
        "errors": [],
        "wait_rows_total": 0,
        "queued": 0,
        "sent": 0,
        "skipped": [],
        "smtp_errors": [],
        "capped": False,
    }

    if not (smtp_user and smtp_password):
        report["errors"].append(
            "SMTP не настроен: нужны **GMAIL_SMTP_*** или **GMAIL_IMAP_*** (пароль приложения)."
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
        report["errors"].append(
            "«Сбор с ответов» пуст — сначала **«Прочитать почту»**, чтобы появились домены и почты вебмастеров."
        )
        return report

    registries: list[tuple[str, str, int]] = [
        ("TelecomAsia", cfg.spreadsheet_telecom_id, cfg.gid_telecom_registry),
        ("Реестр 2", cfg.spreadsheet_registry_2_id, cfg.gid_registry_2),
    ]

    tasks: list[dict[str, Any]] = []
    for reg_label, sid, gid in registries:
        title = get_sheet_title_by_gid(sheets_service, sid, gid)
        if not title:
            report["errors"].append(f"{reg_label}: не найден лист gid={gid}.")
            continue
        df = get_values_as_dataframe(sheets_service, sid, a1_all_columns(title))
        if df.empty:
            continue
        lb = resolve_linkbuilder_column(df, cfg.col_linkbuilder, [])
        st_col = resolve_status_column(df, cfg.col_status)
        col_donor = resolve_donor_column(df, cfg.col_website_donor)
        col_art = resolve_article_column(df, cfg.col_article_post)
        col_cost = resolve_cost_column(df, cfg.col_cost)
        if not st_col or not col_donor:
            report["errors"].append(f"{reg_label}: не найдены колонки статуса или Website Donor.")
            continue
        mine = filter_by_linkbuilder(df, lb, cfg.linkbuilder_filter, cfg.linkbuilder_aliases)
        wait_df = mine[mine[st_col].astype(str).str.strip() == cfg.status_wait_publish]
        report["wait_rows_total"] += len(wait_df)
        for idx, row in wait_df.iterrows():
            dom = str(row.get(col_donor, "") or "").strip()
            if not dom or not normalize_domain_cell(dom):
                tasks.append(
                    {
                        "registry": reg_label,
                        "domain": dom or "(пусто)",
                        "reason": "no_domain",
                        "art": "",
                        "cost": "",
                    }
                )
                continue
            art = str(row.get(col_art, "") or "").strip() if col_art else ""
            cost = str(row.get(col_cost, "") or "").strip() if col_cost else ""
            tasks.append(
                {
                    "registry": reg_label,
                    "domain": dom,
                    "reason": "",
                    "art": art,
                    "cost": cost,
                    "row_index": int(idx) if isinstance(idx, int) else str(idx),
                }
            )

    report["queued"] = len(tasks)
    if not tasks:
        if not report["errors"]:
            report["errors"].append("Нет строк «Жду публикации» в ваших строках обоих реестров.")
        return report

    max_send = cfg.article_publish_max_send
    sent = 0
    subj_base = "Article for publication / Статья для публикации"

    for t in tasks:
        if t.get("reason") == "no_domain":
            report["skipped"].append({"registry": t["registry"], "domain": t["domain"], "reason": "no_domain"})
            continue
        dom = t["domain"]
        if max_send > 0 and sent >= max_send:
            report["capped"] = True
            report["skipped"].append(
                {"registry": t["registry"], "domain": dom, "reason": f"cap_max_send_{max_send}"}
            )
            continue
        art = t.get("art") or ""
        if not art.strip():
            report["skipped"].append({"registry": t["registry"], "domain": dom, "reason": "no_article_link"})
            continue
        if not is_google_docs_or_drive_url(art):
            report["skipped"].append(
                {"registry": t["registry"], "domain": dom, "reason": "not_google_doc_url"}
            )
            continue
        to_addr = find_webmaster_email_in_inbox_log(df_inbox, dom)
        if not to_addr:
            report["skipped"].append({"registry": t["registry"], "domain": dom, "reason": "no_email_in_inbox_log"})
            continue
        body = build_article_publish_email_html(art, t.get("cost") or "")
        subj = f"{subj_base} — {dom}"[:998]
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
            )
            sent += 1
        except Exception as e:
            report["smtp_errors"].append(f"{t['registry']} {dom} → {to_addr}: {e}")

    report["sent"] = sent
    return report
