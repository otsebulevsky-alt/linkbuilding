"""Поиск последнего письма в переписке с вебмастером (IMAP) для ответа в тот же тред."""

from __future__ import annotations

import email
import imaplib
import re
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


def _headers_mention_domain(msg: Message, dom: str) -> bool:
    """Домен есть в Subject / From / To / Cc / Reply-To / References / In-Reply-To (как в типичных outreach-тредах)."""
    d = (dom or "").strip().lower()
    if not d:
        return False
    variants = {d}
    if d.startswith("www."):
        variants.add(d[4:])
    else:
        variants.add("www." + d)
    blob = " ".join(
        [
            _decode_mime(msg.get("Subject")),
            _decode_mime(msg.get("From")),
            _decode_mime(msg.get("To")),
            _decode_mime(msg.get("Cc")),
            _decode_mime(msg.get("Reply-To")),
            _decode_mime(msg.get("References")),
            _decode_mime(msg.get("In-Reply-To")),
        ]
    ).lower()
    return any(v in blob for v in variants)


def _gmail_raw_search_uids(imap: imaplib.IMAP4_SSL, raw_q: str, parse_uids) -> list[int]:
    try:
        typ, data = imap.uid("SEARCH", None, "X-GM-RAW", raw_q)
        if typ == "OK":
            return parse_uids(data)
    except imaplib.IMAP4.error:
        pass
    return []


def _unescape_imap_quoted_inner(inner: bytes) -> bytes:
    return inner.replace(b"\\\"", b'"').replace(b"\\\\", b"\\")


def _extract_last_quoted_mailbox_from_list_row(row: bytes) -> str | None:
    """Имя ящика из строки LIST — последнее поле в кавычках (modified UTF-7 не портим через utf-8 decode всей строки)."""
    matches = list(re.finditer(rb'"((?:[^"\\]|\\.)*)"', row))
    if not matches:
        return None
    inner = _unescape_imap_quoted_inner(matches[-1].group(1))
    if not inner.strip():
        return None
    try:
        return inner.decode("ascii")
    except UnicodeDecodeError:
        return inner.decode("latin-1", errors="replace")


def _gmail_all_mail_folders_from_list(imap: imaplib.IMAP4_SSL) -> list[str]:
    """Все папки с \\All (Gmail «Вся почта» — имя зависит от языка UI, не использовать хардкод [Gmail]/All Mail)."""
    out: list[str] = []
    try:
        typ, rows = imap.list()
        if typ != "OK" or not rows:
            return []
        for row in rows:
            if not isinstance(row, (bytes, bytearray)):
                continue
            if b"\\All" not in row or b"\\Noselect" in row:
                continue
            name = _extract_last_quoted_mailbox_from_list_row(row)
            if name:
                out.append(name)
    except Exception:
        return []
    return out


def _mailboxes_for_thread_search(primary: str, imap: imaplib.IMAP4_SSL | None) -> list[str]:
    """Сначала выбранный ящик (обычно INBOX), затем папки \\All из LIST — без англ. хардкода (на ru-Gmail его нет)."""
    out: list[str] = []
    seen: set[str] = set()
    p = (primary or "").strip() or "INBOX"

    def add(name: str) -> None:
        n = name.strip()
        if not n:
            return
        key = n.casefold()
        if key in seen:
            return
        seen.add(key)
        out.append(n)

    add(p)
    if imap is not None:
        for folder in _gmail_all_mail_folders_from_list(imap):
            add(folder)
    return out


def _parse_uid_list_static(data) -> list[int]:
    if not data or not data[0]:
        return []
    chunk = data[0]
    if isinstance(chunk, bytes):
        chunk = chunk.decode("ascii", errors="replace")
    return [int(x) for x in str(chunk).split() if x.isdigit()]


def _collect_search_uids(
    imap: imaplib.IMAP4_SSL, peer: str, dom: str, _parse_uid_list
) -> tuple[list[int], bool]:
    strict_queries = (
        f"(from:{peer} OR to:{peer}) {dom}",
        f"(from:{peer} OR to:{peer}) subject:{dom}",
    )
    uids: list[int] = []
    domain_required_in_headers = False
    for raw_q in strict_queries:
        uids = _gmail_raw_search_uids(imap, raw_q, _parse_uid_list)
        if uids:
            return uids, domain_required_in_headers

    uids = _gmail_raw_search_uids(imap, f"from:{peer} OR to:{peer}", _parse_uid_list)
    domain_required_in_headers = bool(uids)
    if uids:
        return uids, domain_required_in_headers

    try:
        typ, data = imap.search(None, "TEXT", dom)
        if typ == "OK":
            uids = _parse_uid_list(data)
            domain_required_in_headers = True
    except imaplib.IMAP4.error:
        uids = []
    return uids, domain_required_in_headers


def _scan_uids_for_reply_context(
    imap: imaplib.IMAP4_SSL,
    uids: list[int],
    *,
    peer: str,
    dom: str,
    domain_required_in_headers: bool,
    max_uids_to_scan: int,
) -> dict[str, str] | None:
    uids = sorted(set(uids), reverse=True)
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
        if domain_required_in_headers and not _headers_mention_domain(msg, dom):
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


def find_reply_context_for_peer(
    *,
    imap_host: str,
    imap_user: str,
    imap_password: str,
    imap_mailbox: str,
    peer_email: str,
    domain: str,
    timeout_sec: int = 120,
    max_uids_to_scan: int = 400,
) -> tuple[dict[str, str] | None, str]:
    """
    (context | None, diagnostic). context — message_id, references, subject.
    diagnostic пустая строка при успехе; иначе короткий код для отчёта UI (например imap_no_uids:INBOX).
    """
    peer = (peer_email or "").strip()
    dom = normalize_domain_cell(domain)
    if not peer or not dom:
        return None, "bad_peer_or_domain"

    try:
        imap_cm = imaplib.IMAP4_SSL(imap_host, timeout=max(60, timeout_sec))
    except OSError:
        return None, "imap_connect_failed"

    last_hint = "imap_unknown"
    try:
        with imap_cm as imap:
            try:
                imap.login(imap_user, imap_password)
            except imaplib.IMAP4.error:
                return None, "imap_login_failed"

            meaningful: str | None = None
            extra_select_errors: list[str] = []

            for mbox in _mailboxes_for_thread_search(imap_mailbox, imap):
                try:
                    typ, _ = imap.select(mbox)
                except Exception:
                    extra_select_errors.append(f"select_error:{mbox}")
                    continue
                if typ != "OK":
                    extra_select_errors.append(f"select_failed:{mbox}")
                    continue

                uids, domain_req = _collect_search_uids(imap, peer, dom, _parse_uid_list_static)
                if not uids:
                    meaningful = f"imap_no_uids:{mbox}"
                    continue

                ctx = _scan_uids_for_reply_context(
                    imap,
                    uids,
                    peer=peer,
                    dom=dom,
                    domain_required_in_headers=domain_req,
                    max_uids_to_scan=max_uids_to_scan,
                )
                if ctx:
                    return ctx, ""
                meaningful = f"imap_no_matching_thread:{mbox} uids={len(uids)}"

            if meaningful and extra_select_errors:
                return None, meaningful + " | " + "; ".join(extra_select_errors)
            if meaningful:
                return None, meaningful
            if extra_select_errors:
                return None, "imap_" + "; ".join(extra_select_errors)
            return None, "imap_unknown"
    except Exception:
        return None, "imap_exception"
