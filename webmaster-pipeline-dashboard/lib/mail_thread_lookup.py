"""Поиск последнего письма в переписке с вебмастером (IMAP) для ответа в тот же тред."""

from __future__ import annotations

import email
import imaplib
import re
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parseaddr

from lib.trade_bargain import normalize_domain_cell

# Имена вроде [Gmail]/Sent Mail по RFC 3501 — quoted string; иначе imaplib шлёт байты без кавычек
# и часть серверов отвечает BAD / обрывает команду по пробелу.
_ATOM_MAILBOX_RE = re.compile(r"^[A-Za-z0-9._\-%+]+$")


def _mailbox_arg_for_imap(logical_name: str) -> str:
    """Аргумент для IMAP SELECT/EXAMINE: INBOX / atom или \"...\" для имён с пробелами и скобками."""
    n = (logical_name or "").strip()
    if not n:
        return '""'
    if n.upper() == "INBOX":
        return n
    if _ATOM_MAILBOX_RE.fullmatch(n):
        return n
    inner = n.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{inner}"'


def _select_mailbox_examine(imap: imaplib.IMAP4_SSL, logical_name: str) -> tuple[bool, str]:
    """EXAMINE (readonly) с RFC-кавычками и запасными именами для Gmail Sent."""
    logical = (logical_name or "").strip()
    candidates: list[str] = []
    seen_log: set[str] = set()

    def add_logical(name: str) -> None:
        x = (name or "").strip()
        if not x or x in seen_log:
            return
        seen_log.add(x)
        candidates.append(x)

    add_logical(logical)
    low = logical.lower()
    if "sent" in low:
        if re.search(r"\[gmail\]", logical, re.I):
            add_logical(re.sub(r"(?i)\[gmail\]", "[Google Mail]", logical))
        if re.search(r"\[google mail\]", logical, re.I):
            add_logical(re.sub(r"(?i)\[google mail\]", "[Gmail]", logical))

    last_detail = ""
    for log in candidates:
        wire = _mailbox_arg_for_imap(log)
        try:
            typ, _ = imap.select(wire, readonly=True)
        except Exception as e:
            msg = str(e).replace("\r", " ").replace("\n", " ").strip()[:160]
            last_detail = f"{type(e).__name__}:{msg}"
            continue
        if typ == "OK":
            return True, ""
        last_detail = f"typ={typ}"

    return False, last_detail


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


def _normalize_addr_for_peer_compare(addr: str) -> str:
    """Сравнение peer: lower/strip; Gmail и googlemail.com — одна «каноническая» пара, без точек в local."""
    a = (addr or "").strip().lower()
    if "@" not in a:
        return a
    local, _, host = a.partition("@")
    if host in ("gmail.com", "googlemail.com"):
        return local.replace(".", "") + "@gmail.com"
    return a


def _peer_addresses_match(peer_email: str, candidate: str) -> bool:
    p = (peer_email or "").strip()
    c = (candidate or "").strip()
    if not p or not c:
        return False
    if p.lower() == c.lower():
        return True
    return _normalize_addr_for_peer_compare(p) == _normalize_addr_for_peer_compare(c)


def _all_header_addresses(msg: Message, *header_names: str) -> list[str]:
    """Все адреса из заголовков (getaddresses — несколько в одной строке)."""
    chunks: list[str] = []
    for name in header_names:
        v = msg.get(name)
        if v:
            chunks.append(_decode_mime(v))
    if not chunks:
        return []
    return [a.strip() for _, a in getaddresses(chunks) if (a or "").strip()]


def _header_peer_match(msg: Message, peer_email: str) -> bool:
    """Письмо с вебмастером: peer в From (все адреса), Sender, Reply-To, To, Cc, Delivered-To."""
    pl = (peer_email or "").strip()
    if not pl:
        return False
    for addr in _all_header_addresses(msg, "From"):
        if _peer_addresses_match(pl, addr):
            return True
    _, snd = parseaddr(_decode_mime(msg.get("Sender")))
    if _peer_addresses_match(pl, snd):
        return True
    _, rpto = parseaddr(_decode_mime(msg.get("Reply-To")))
    if _peer_addresses_match(pl, rpto):
        return True
    for addr in _all_header_addresses(msg, "To", "Cc", "Bcc", "Delivered-To", "X-Original-To", "Envelope-To"):
        if _peer_addresses_match(pl, addr):
            return True
    return False


def _message_ids_angle_bracketed(text: str) -> list[str]:
    return re.findall(r"<[^>\s]+>", (text or "").strip())


def _resolve_message_id_for_reply(msg: Message, raw_header: bytes | None = None) -> str:
    """Message-ID письма; если пусто — In-Reply-To, затем последний id из References, затем разбор сырого HEADER."""
    mid_raw = _decode_mime(msg.get("Message-ID")).strip()
    if mid_raw:
        return mid_raw
    irt = _decode_mime(msg.get("In-Reply-To")).strip()
    if irt:
        ids = _message_ids_angle_bracketed(irt)
        if ids:
            return ids[0]
        return irt.split()[0] if irt.split() else ""
    ref = _decode_mime(msg.get("References", "")).strip()
    ids = _message_ids_angle_bracketed(ref)
    if ids:
        return ids[-1]
    if raw_header:
        try:
            txt = raw_header.decode("utf-8", errors="replace")
        except Exception:
            txt = ""
        for line in txt.splitlines():
            if line.lower().startswith("message-id:"):
                rest = line.split(":", 1)[1].strip()
                found = _message_ids_angle_bracketed(rest)
                if found:
                    return found[0]
                return rest.strip()
    return ""


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


def _gmail_folders_with_list_flag(imap: imaplib.IMAP4_SSL, flag: bytes) -> list[str]:
    """Имена папок из IMAP LIST, где в флагах есть flag (например \\Sent, \\All)."""
    out: list[str] = []
    try:
        typ, rows = imap.list()
        if typ != "OK" or not rows:
            return []
        for row in rows:
            if not isinstance(row, (bytes, bytearray)):
                continue
            if flag not in row or b"\\Noselect" in row:
                continue
            name = _extract_last_quoted_mailbox_from_list_row(row)
            if name:
                out.append(name)
    except Exception:
        return []
    return out


def _mailboxes_for_thread_search(primary: str, imap: imaplib.IMAP4_SSL | None) -> list[str]:
    """INBOX (или IMAP_MAILBOX) → **Отправленные** (\\Sent) → **Вся почта** (\\All) из LIST.

    Торг: исходящее «мы → вебмастер» с доменом в теме часто лежит в **Sent**, а не во входящих;
    без этого X-GM-RAW во INBOX даёт 0–1 ложных UID, а \\All на части аккаунтов не открывается по SELECT.
    """
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
        for folder in _gmail_folders_with_list_flag(imap, b"\\Sent"):
            add(folder)
        for folder in _gmail_folders_with_list_flag(imap, b"\\All"):
            add(folder)
    return out


def _parse_uid_list_static(data) -> list[int]:
    if not data or not data[0]:
        return []
    chunk = data[0]
    if isinstance(chunk, bytes):
        chunk = chunk.decode("ascii", errors="replace")
    return [int(x) for x in str(chunk).split() if x.isdigit()]


def _iter_search_uid_batches(
    imap: imaplib.IMAP4_SSL,
    peer: str,
    dom: str,
    _parse_uid_list,
):
    """Несколько запросов подряд: не останавливаться на первом непустом UID-листе, если письмо не подошло.

    Иначе Gmail по `(peer+домен)` может вернуть 1 ложное совпадение — и широкий `from|to:peer` даже не пробуется.
    """
    for raw_q in (
        f"(from:{peer} OR to:{peer}) {dom}",
        f"(from:{peer} OR to:{peer}) subject:{dom}",
    ):
        uids = _gmail_raw_search_uids(imap, raw_q, _parse_uid_list)
        if uids:
            yield uids, False

    uids = _gmail_raw_search_uids(imap, f"from:{peer} OR to:{peer}", _parse_uid_list)
    if uids:
        yield uids, True

    # Только UID SEARCH: imap.search возвращает **порядковые номера**, а ниже UID FETCH —
    # иначе подставляются чужие письма и peer/Message-ID никогда не сходятся.
    try:
        typ, data = imap.uid("SEARCH", None, "TEXT", dom)
        if typ == "OK":
            uids = _parse_uid_list(data)
            if uids:
                yield uids, True
    except imaplib.IMAP4.error:
        pass


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
        mid_raw = _resolve_message_id_for_reply(msg, raw)
        if not mid_raw:
            continue
        mid_n = _normalize_msg_id(mid_raw)
        ref = _decode_mime(msg.get("References", "")).strip()
        if ref:
            references = ref if mid_n in ref else f"{ref} {mid_n}"
        else:
            references = mid_n
        return {
            "message_id": mid_n,
            "references": references,
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

    try:
        with imap_cm as imap:
            try:
                imap.login(imap_user, imap_password)
            except imaplib.IMAP4.error:
                return None, "imap_login_failed"

            meaningful: str | None = None
            extra_select_errors: list[str] = []

            # Только SEARCH/FETCH — пишем по SMTP, не через IMAP. Gmail помечает [Gmail]/Sent Mail и др. как
            # READ-ONLY; imap.select(..., readonly=False) тогда бросает IMAP4.readonly → ложный «select_error».
            for mbox in _mailboxes_for_thread_search(imap_mailbox, imap):
                ok_open, open_detail = _select_mailbox_examine(imap, mbox)
                if not ok_open:
                    extra_select_errors.append(
                        f"select_error:{mbox}" + (f" ({open_detail})" if open_detail else "")
                    )
                    continue

                batch_sizes: list[int] = []
                ctx_found: dict[str, str] | None = None
                for uids, domain_req in _iter_search_uid_batches(
                    imap, peer, dom, _parse_uid_list_static
                ):
                    if not uids:
                        continue
                    batch_sizes.append(len(uids))
                    ctx_found = _scan_uids_for_reply_context(
                        imap,
                        uids,
                        peer=peer,
                        dom=dom,
                        domain_required_in_headers=domain_req,
                        max_uids_to_scan=max_uids_to_scan,
                    )
                    if ctx_found:
                        return ctx_found, ""

                if not batch_sizes:
                    meaningful = f"imap_no_uids:{mbox}"
                else:
                    meaningful = (
                        f"imap_no_matching_thread:{mbox} "
                        f"search_uid_counts={'+'.join(str(x) for x in batch_sizes)}"
                    )
                continue

            if meaningful and extra_select_errors:
                return None, meaningful + " | " + "; ".join(extra_select_errors)
            if meaningful:
                return None, meaningful
            if extra_select_errors:
                return None, "imap_" + "; ".join(extra_select_errors)
            return None, "imap_unknown"
    except Exception:
        return None, "imap_exception"
