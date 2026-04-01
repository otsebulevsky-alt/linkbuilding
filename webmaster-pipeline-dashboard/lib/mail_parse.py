"""Extract domains and price hints from webmaster reply emails (subject + body)."""

from __future__ import annotations

import re
from email.message import Message
from urllib.parse import urlparse

# Hosts to ignore when scraping URLs from email bodies
_SKIP_NETLOCS = frozenset(
    {
        "mail.google.com",
        "accounts.google.com",
        "google.com",
        "www.google.com",
        "gmail.com",
        "www.gmail.com",
        "drive.google.com",
        "docs.google.com",
        "youtube.com",
        "www.youtube.com",
        "linkedin.com",
        "www.linkedin.com",
        "facebook.com",
        "www.facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "t.me",
        "telegram.me",
        "wa.me",
        "bit.ly",
        "tinyurl.com",
    }
)

_URL_RE = re.compile(r'https?://[^\s<>"\')\]]+', re.IGNORECASE)
# Host in subject: example.com, mayfair-london.co.uk
_SUBJ_HOST_CORE = (
    r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?"
    r"\.(?:[a-z]{2,}|com\.[a-z]{2}|co\.[a-z]{2})"
)
# "Content collaboration idea for marketingmedian.com"
# "Interest in collaborating with your website banglarrbhumi.com"
_SUBJECT_DOMAIN_RES: tuple[re.Pattern[str], ...] = (
    re.compile(rf"\bfor\s+({_SUBJ_HOST_CORE})\b", re.I),
    re.compile(rf"\byour\s+website\s+({_SUBJ_HOST_CORE})\b", re.I),
)
_PRICE_RES = (
    re.compile(r"\$\s*[\d,]+(?:\.\d{1,2})?", re.IGNORECASE),
    re.compile(r"€\s*[\d,]+(?:\.\d{1,2})?", re.IGNORECASE),
    re.compile(r"£\s*[\d,]+(?:\.\d{1,2})?", re.IGNORECASE),
    re.compile(r"[\d,]+(?:\.\d{1,2})?\s*(?:USD|usd|EUR|eur|GBP|gbp)\b", re.IGNORECASE),
    re.compile(r"\b(?:price|rate|cost|fee)\s*[:=]?\s*[\d,]+(?:\.\d{1,2})?\s*(?:USD|usd|\$)?", re.IGNORECASE),
)


def _normalize_host(raw: str) -> str | None:
    h = (raw or "").strip().lower()
    if not h or "." not in h:
        return None
    if h.startswith("www."):
        h = h[4:]
    if h.endswith("."):
        h = h[:-1]
    if h in _SKIP_NETLOCS or h.endswith(".google.com"):
        return None
    if len(h) < 4:
        return None
    return h


def domain_from_subject(subject: str) -> str | None:
    if not subject or not subject.strip():
        return None
    s = subject.strip()
    for rx in _SUBJECT_DOMAIN_RES:
        m = rx.search(s)
        if m:
            return _normalize_host(m.group(1))
    return None


def domains_from_urls_in_text(text: str) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(").,;]")
        try:
            p = urlparse(url)
        except Exception:
            continue
        host = _normalize_host(p.netloc or "")
        if not host or host in seen:
            continue
        seen.add(host)
        out.append(host)
    return out


def extract_all_domains(subject: str, body_text: str) -> list[str]:
    """Subject domain first, then URL hosts from body (unique, order preserved)."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(h: str | None) -> None:
        if not h or h in seen:
            return
        seen.add(h)
        ordered.append(h)

    add(domain_from_subject(subject))
    for h in domains_from_urls_in_text(body_text):
        add(h)
    return ordered


def extract_price_hint(text: str) -> str:
    """First plausible price fragment, or empty."""
    if not text:
        return ""
    for rx in _PRICE_RES:
        m = rx.search(text)
        if m:
            return m.group(0).strip()[:80]
    return ""


def message_body_text(msg: Message) -> str:
    """Plain + HTML (tags stripped) for parsing."""
    chunks: list[str] = []

    def decode_part(part) -> str:
        try:
            pl = part.get_payload(decode=True)
            if not pl:
                return ""
            return pl.decode("utf-8", errors="replace")
        except Exception:
            return ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                chunks.append(decode_part(part))
            elif ctype == "text/html":
                raw = decode_part(part)
                stripped = re.sub(r"<[^>]+>", " ", raw)
                stripped = re.sub(r"\s+", " ", stripped)
                chunks.append(stripped)
    else:
        ctype = msg.get_content_type()
        raw = decode_part(msg)
        if ctype == "text/html":
            raw = re.sub(r"<[^>]+>", " ", raw)
            raw = re.sub(r"\s+", " ", raw)
        chunks.append(raw)
    return "\n".join(c for c in chunks if c).strip()


def reply_date_iso(msg: Message) -> str:
    from datetime import datetime, timezone

    from email.utils import parsedate_to_datetime

    raw = msg.get("Date") or ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt:
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
