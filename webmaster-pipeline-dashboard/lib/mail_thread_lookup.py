"""Поиск последнего письма в переписке с вебмастером (IMAP) для ответа в тот же тред."""

from __future__ import annotations

import email
import imaplib
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parseaddr

from lib.trade_bargain import normalize_domain_cell


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


def _header_peer_match(msg: Message, peer_email: str) -> bool:
    """Письмо между нами и вебмастером (peer в From, Reply-To или To/Cc)."""
    pl = (peer_email or "").strip().lower()
    if not pl:
        return False
    _, f = parseaddr(_decode_mime(msg.get("From")))
    if f.strip().lower() == pl:
        return True
    _, rpto = parseaddr(_decode_mime(msg.get("Reply-To")))
    if rpto.strip().lower() == pl:
        return True
    for _, addr in getaddresses(
        [
            _decode_mime(msg.get("To")),
            _decode_mime(msg.get("Cc")),
            _decode_mime(msg.get("Delivered-To")),
        ]
    ):
        if addr.strip().lower() == pl:
            return True
    return False


def _normalize_msg_id(mid: str) -> str:
    s = (mid or "").strip()
    if not s:
        return ""
    if not s.startswith("<"):
        s = f"<{s}"
    if not s.endswith(">"):
        s = f"{s}>"
    return s


def _build_references(msg: Message) -> str:
    """References для ответа: старая цепочка + Message-ID текущего письма."""
    mid = _normalize_msg_id(_decode_mime(msg.get("Message-ID")))
    ref = _decode_mime(msg.get("References", "")).strip()
    if not mid:
        return ref
    if ref:
        if mid in ref:
            return ref
        return f"{ref} {mid}"
    return mid


def _reply_subject(original: str) -> str:
    o = _decode_mime(original).strip()
    if not o:
        return "Re: "
    if o.lower().startswith("re:"):
        return o
    return f"Re: {o}"


def find_reply_context_for_peer(
    *,
    imap_host: str,
    imap_user: str,
    imap_password: str,
    imap_mailbox: str,
    peer_email: str,
    domain: str,
    timeout_sec: int = 120,
    max_uids_to_scan: int = 150,
) -> dict[str, str] | None:
    """
    Последнее (по UID) письмо в ящике, где фигурируют peer и домен — для In-Reply-To / References.

    **domain** — как в реестре / «Сбор с ответов»; перед поиском приводится к виду host (как `normalize_domain_cell`).
    Возвращает: message_id, references, subject (уже с Re: при необходимости).
    Gmail: X-GM-RAW; иначе TEXT по домену + фильтр peer по заголовкам.
    """
    peer = (peer_email or "").strip()
    dom = normalize_domain_cell(domain)
    if not peer or not dom:
        return None

    try:
        imap_cm = imaplib.IMAP4_SSL(imap_host, timeout=max(60, timeout_sec))
    except OSError:
        return None

    try:
        with imap_cm as imap:
            try:
                imap.login(imap_user, imap_password)
            except imaplib.IMAP4.error:
                return None
            typ, _ = imap.select(imap_mailbox)
            if typ != "OK":
                return None

            def _parse_uid_list(data) -> list[int]:
                if not data or not data[0]:
                    return []
                chunk = data[0]
                if isinstance(chunk, bytes):
                    chunk = chunk.decode("ascii", errors="replace")
                return [int(x) for x in str(chunk).split() if x.isdigit()]

            uids: list[int] = []
            raw_q = f"(from:{peer} OR to:{peer}) {dom}"
            try:
                typ, data = imap.uid("SEARCH", None, "X-GM-RAW", raw_q)
                if typ == "OK":
                    uids = _parse_uid_list(data)
            except imaplib.IMAP4.error:
                uids = []

            if not uids:
                try:
                    typ, data = imap.search(None, "TEXT", dom)
                    if typ == "OK":
                        uids = _parse_uid_list(data)
                except imaplib.IMAP4.error:
                    uids = []

            if not uids:
                return None

            uids.sort(reverse=True)
            for uid in uids[:max_uids_to_scan]:
                try:
                    typ, msg_data = imap.uid("FETCH", str(uid), "(BODY.PEEK[HEADER])")
                except Exception:
                    continue
                if typ != "OK" or not msg_data:
                    continue
                raw: bytes | None = None
                for chunk in msg_data:
                    if isinstance(chunk, tuple) and len(chunk) >= 2:
                        cand = chunk[1]
                        if isinstance(cand, (bytes, bytearray)):
                            raw = bytes(cand)
                            break
                if raw is None:
                    continue
                try:
                    msg = email.message_from_bytes(raw)
                except Exception:
                    continue
                if not _header_peer_match(msg, peer):
                    continue
                subj = _decode_mime(msg.get("Subject"))
                mid_raw = _decode_mime(msg.get("Message-ID")).strip()
                if not mid_raw:
                    continue
                mid_n = _normalize_msg_id(mid_raw)
                refs = _build_references(msg)
                return {
                    "message_id": mid_n,
                    "references": refs,
                    "subject": _reply_subject(subj)[:998],
                }

            return None
    except Exception:
        return None
