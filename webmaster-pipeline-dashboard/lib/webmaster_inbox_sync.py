"""Sync unseen webmaster replies from Gmail IMAP into inbox log Google Sheet."""

from __future__ import annotations

import email
import html as html_module
import imaplib
from email.header import decode_header
from email.utils import parseaddr

from lib.mail_parse import (
    extract_all_domains,
    extract_price_hint,
    message_body_text,
    reply_date_iso,
)
from lib.payment_match import canonicals_from_reference_dataframe, payment_draft_for_message
from lib.mail_smtp import send_smtp_html
from lib.sheets_service import a1_all_columns, append_row, get_sheet_title_by_gid, get_values_as_dataframe


def _decode_mime(s: str | None) -> str:
    if not s:
        return ""
    out: list[str] = []
    for part, enc in decode_header(s):
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(part))
    return "".join(out)


def sync_unseen_webmasters_to_inbox_sheet(
    *,
    imap_host: str,
    imap_user: str,
    imap_password: str,
    imap_mailbox: str,
    sheets_service,
    spreadsheet_id: str,
    sheet_gid: int = 0,
    max_messages: int = 0,
    imap_timeout_sec: int = 900,
    payment_options_spreadsheet_id: str = "",
    payment_options_gid: int = 0,
    imap_newest_first: bool = True,
    auto_reply_payment_followup: bool = False,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_password: str = "",
) -> dict:
    """
    For each UNSEEN message: extract domains (subject + URLs in body), price hint, date, from;
    append one row per domain to the sheet (A–E как раньше; F — черновик про оплату при расхождении
    со справочником «Возможности оплаты» или если в ответе нет вариантов оплаты).
    Marks \\Seen only if at least one row was appended for that message.

    max_messages: if 0 or negative — обработать **все** непрочитанные, найденные SEARCH UNSEEN.
    if > 0 — только последние N по порядку номеров IMAP (обычно самые новые).
    """
    report: dict = {
        "emails_seen": 0,
        "rows_appended": 0,
        "emails_marked_read": 0,
        "skipped": [],
        "errors": [],
        "unseen_total": 0,
        "capped": False,
        "payment_followup_rows": 0,
        "payment_options_enabled": False,
        "payment_reference_empty": False,
        "payment_reply_sent": 0,
        "payment_reply_errors": [],
    }

    with imaplib.IMAP4_SSL(imap_host, timeout=max(60, imap_timeout_sec)) as imap:
        imap.login(imap_user, imap_password)
        typ, _ = imap.select(imap_mailbox)
        if typ != "OK":
            report["errors"].append(f"IMAP select {imap_mailbox!r}: {typ}")
            return report

        typ, data = imap.search(None, "UNSEEN")
        if typ != "OK" or not data or not data[0]:
            return report

        seq_nums = data[0].split()
        report["unseen_total"] = len(seq_nums)
        if max_messages > 0 and len(seq_nums) > max_messages:
            report["capped"] = True
            seq_nums = seq_nums[-max_messages:]
        if imap_newest_first and seq_nums:
            seq_nums = list(reversed(seq_nums))

        title = get_sheet_title_by_gid(sheets_service, spreadsheet_id, sheet_gid)
        if not title:
            report["errors"].append(
                f"Не найден лист gid={sheet_gid} в таблице {spreadsheet_id}. Проверьте доступ сервисного аккаунта (Editor)."
            )
            return report

        our_payment: set[str] = set()
        pid = (payment_options_spreadsheet_id or "").strip()
        if pid:
            report["payment_options_enabled"] = True
            pay_title = get_sheet_title_by_gid(sheets_service, pid, payment_options_gid)
            if pay_title:
                try:
                    df_pay = get_values_as_dataframe(
                        sheets_service, pid, a1_all_columns(pay_title)
                    )
                    our_payment = canonicals_from_reference_dataframe(df_pay)
                    report["payment_reference_empty"] = len(our_payment) == 0
                except Exception as e:
                    report["errors"].append(f"Справочник оплаты: не удалось прочитать лист — {e}")
                    report["payment_reference_empty"] = True
            else:
                report["errors"].append(
                    f"Справочник оплаты: лист gid={payment_options_gid} не найден в {pid}."
                )

        for num in seq_nums:
            report["emails_seen"] += 1
            typ, msg_data = imap.fetch(num, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                report["errors"].append(f"fetch seq={num!r}: {typ}")
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw)
            subj = _decode_mime(msg.get("Subject"))
            from_raw = _decode_mime(msg.get("From"))
            _, from_addr = parseaddr(from_raw)
            from_addr = (from_addr or from_raw or "").strip()
            body = message_body_text(msg)
            domains = extract_all_domains(subj, body)
            price = extract_price_hint(body) or extract_price_hint(subj)
            date_iso = reply_date_iso(msg)

            if not domains:
                report["skipped"].append(
                    {"seq": num.decode("ascii", errors="replace"), "subject": subj[:120], "reason": "no_domains"}
                )
                continue

            pay_draft = payment_draft_for_message(
                our_canonicals=our_payment, subject=subj, body=body
            )

            rows_ok = 0
            try:
                for dom in domains:
                    row = [dom, date_iso, price, "", from_addr, pay_draft]
                    append_row(sheets_service, spreadsheet_id, title, row)
                    if pay_draft:
                        report["payment_followup_rows"] += 1
                    rows_ok += 1
                    report["rows_appended"] += 1
            except Exception as e:
                report["errors"].append(
                    f"Sheets append seq={num.decode('ascii', errors='replace')}: {e}"
                )
                continue

            if (
                rows_ok > 0
                and auto_reply_payment_followup
                and pay_draft
                and from_addr
            ):
                if not (smtp_user and smtp_password):
                    report["payment_reply_errors"].append(
                        f"seq={num.decode('ascii', errors='replace')}: SMTP не настроен "
                        "(нужны GMAIL_SMTP_USER и GMAIL_SMTP_APP_PASSWORD)."
                    )
                else:
                    try:
                        subj_out = subj.strip()
                        if not subj_out.lower().startswith("re:"):
                            subj_out = f"Re: {subj_out}"
                        send_smtp_html(
                            host=smtp_host,
                            port=int(smtp_port),
                            user=smtp_user,
                            password=smtp_password,
                            to_addr=from_addr,
                            subject=subj_out[:998],
                            html_body=f"<p>{html_module.escape(pay_draft)}</p>",
                        )
                        report["payment_reply_sent"] += 1
                    except Exception as e:
                        report["payment_reply_errors"].append(
                            f"SMTP seq={num.decode('ascii', errors='replace')}: {e}"
                        )

            if rows_ok > 0:
                try:
                    seq = num.decode("ascii", errors="replace") if isinstance(num, bytes) else str(num)
                    imap.store(seq, "+FLAGS", "\\Seen")
                    report["emails_marked_read"] += 1
                except Exception as e:
                    report["errors"].append(
                        f"mark Seen seq={num.decode('ascii', errors='replace')}: {e}"
                    )

    return report
