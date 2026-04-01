"""Sync unseen webmaster replies from Gmail IMAP into inbox log Google Sheet."""

from __future__ import annotations

import email
import imaplib
from email.header import decode_header
from email.utils import parseaddr

from lib.mail_parse import (
    extract_all_domains,
    extract_price_hint,
    message_body_text,
    reply_date_iso,
)
from lib.sheets_service import append_row, get_sheet_title_by_gid


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
    limit: int = 40,
) -> dict:
    """
    For each UNSEEN message: extract domains (subject + URLs in body), price hint, date, from;
    append one row per domain to the sheet (columns A–E: Домен, дата, цена, Цена после торг, Почта).
    Marks \\Seen only if at least one row was appended for that message.
    """
    report: dict = {
        "emails_seen": 0,
        "rows_appended": 0,
        "emails_marked_read": 0,
        "skipped": [],
        "errors": [],
    }

    with imaplib.IMAP4_SSL(imap_host, timeout=120) as imap:
        imap.login(imap_user, imap_password)
        typ, _ = imap.select(imap_mailbox)
        if typ != "OK":
            report["errors"].append(f"IMAP select {imap_mailbox!r}: {typ}")
            return report

        typ, data = imap.search(None, "UNSEEN")
        if typ != "OK" or not data or not data[0]:
            return report

        seq_nums = data[0].split()
        if len(seq_nums) > limit:
            seq_nums = seq_nums[-limit:]

        title = get_sheet_title_by_gid(sheets_service, spreadsheet_id, sheet_gid)
        if not title:
            report["errors"].append(
                f"Не найден лист gid={sheet_gid} в таблице {spreadsheet_id}. Проверьте доступ сервисного аккаунта (Editor)."
            )
            return report

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

            rows_ok = 0
            try:
                for dom in domains:
                    row = [dom, date_iso, price, "", from_addr]
                    append_row(sheets_service, spreadsheet_id, title, row)
                    rows_ok += 1
                    report["rows_appended"] += 1
            except Exception as e:
                report["errors"].append(
                    f"Sheets append seq={num.decode('ascii', errors='replace')}: {e}"
                )
                continue

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
