"""List recent unread messages via IMAP (Gmail + app password)."""

from __future__ import annotations

import email
import imaplib
from email.header import decode_header
from email.utils import parseaddr


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


def fetch_unread_summaries(
    *,
    host: str,
    user: str,
    password: str,
    mailbox: str,
    limit: int = 25,
) -> list[dict[str, str]]:
    """
    Returns list of {uid, subject, from_addr, date, snippet_preview}.
    """
    out: list[dict[str, str]] = []
    with imaplib.IMAP4_SSL(host, timeout=60) as imap:
        imap.login(user, password)
        typ, _ = imap.select(mailbox)
        if typ != "OK":
            return out
        typ, data = imap.search(None, "UNSEEN")
        if typ != "OK" or not data or not data[0]:
            return out
        uids = data[0].split()
        uids = uids[-limit:] if len(uids) > limit else uids
        for uid in reversed(uids):
            typ, msg_data = imap.fetch(uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw)
            subj = _decode_mime(msg.get("Subject"))
            from_raw = _decode_mime(msg.get("From"))
            _, addr = parseaddr(from_raw)
            date = msg.get("Date") or ""
            body_preview = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                body_preview = payload.decode("utf-8", errors="replace")[:500]
                        except Exception:
                            pass
                        break
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_preview = payload.decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass
            out.append(
                {
                    "uid": uid.decode("ascii", errors="replace"),
                    "subject": subj,
                    "from_addr": addr or from_raw,
                    "date": date,
                    "snippet_preview": body_preview.replace("\n", " ")[:400],
                }
            )
    return out
