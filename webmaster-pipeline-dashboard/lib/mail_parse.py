"""Extract domains and price hints from webmaster reply emails (subject + body)."""

from __future__ import annotations

import re
from email.message import Message
from urllib.parse import urlparse

# Hosts to ignore when scraping URLs from email bodies
_BOUNCE_FROM_LOCAL_PARTS = frozenset(
    {"mailer-daemon", "postmaster", "mail-daemon", "double-bounce"}
)

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

# Сервисы, трекеры, биржи ссылок, Slack, YouTrack и т.п. — не целевой «донор» в «Сбор с ответов».
_NON_WEBMASTER_HOST_ROOTS: frozenset[str] = frozenset(
    {
        "adsy.com",
        "ahrefs.com",
        "beginingrace.com",
        "collaborator.pro",
        "cs50.harvard.edu",
        "getmelinks.com",
        "github.blog",
        "github.com",
        "gogetlinks.net",
        "hunter.io",
        "icon-era.com",
        "intercom-mail.com",
        "linksposting.com",
        "miralinks.com",
        "openai.com",
        "paypal.com",
        "prposting.com",
        "presswhizz.com",
        "rotapost.ru",
        "sape.ru",
        "slack.com",
        "spamzilla.io",
        "tiktok.com",
        "track.customer.io",
        "twitch.tv",
        "unancor.com",
        "whitepress.com",
        "youtrack.rantsports.com",
    }
)


def is_non_webmaster_platform_host(host: str) -> bool:
    """
    True, если хост — известный сервис/трекер/биржа, а не сайт вебмастера для строки «Домен».
    Сопоставление по суффиксу: ``api.github.com`` → github.com.
    """
    h = (host or "").strip().lower().rstrip(".")
    if h.startswith("www."):
        h = h[4:]
    if not h or "." not in h:
        return False
    for root in _NON_WEBMASTER_HOST_ROOTS:
        if h == root or h.endswith("." + root):
            return True
    return False

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


def _normalize_host(raw: str, *, drop_platform_hosts: bool = True) -> str | None:
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
    if drop_platform_hosts and is_non_webmaster_platform_host(h):
        return None
    return h


def domain_from_subject(subject: str, *, drop_platform_hosts: bool = True) -> str | None:
    if not subject or not subject.strip():
        return None
    s = subject.strip()
    for rx in _SUBJECT_DOMAIN_RES:
        m = rx.search(s)
        if m:
            return _normalize_host(m.group(1), drop_platform_hosts=drop_platform_hosts)
    return None


def domains_from_urls_in_text(text: str, *, drop_platform_hosts: bool = True) -> list[str]:
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
        host = _normalize_host(p.netloc or "", drop_platform_hosts=drop_platform_hosts)
        if not host or host in seen:
            continue
        seen.add(host)
        out.append(host)
    return out


def _extract_domains_ordered(subject: str, body_text: str, *, drop_platform_hosts: bool) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(h: str | None) -> None:
        if not h or h in seen:
            return
        seen.add(h)
        ordered.append(h)

    add(domain_from_subject(subject, drop_platform_hosts=drop_platform_hosts))
    for h in domains_from_urls_in_text(body_text, drop_platform_hosts=drop_platform_hosts):
        add(h)
    return ordered


def extract_all_domains(subject: str, body_text: str) -> list[str]:
    """Subject domain first, then URL hosts from body (unique, order preserved). Без платформенного шума."""
    return _extract_domains_ordered(subject, body_text, drop_platform_hosts=True)


def extract_candidate_hosts(subject: str, body_text: str) -> list[str]:
    """Те же хосты, но **до** отсечения github/slack/hunter/… (для отличия «шум целиком» от «нет доменов»)."""
    return _extract_domains_ordered(subject, body_text, drop_platform_hosts=False)


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


_BUDGET_INQUIRY_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"what\s+is\s+your\s+budget", re.I),
    re.compile(r"what['\u2019]s\s+your\s+budget", re.I),
    re.compile(r"what\s+is\s+the\s+budget", re.I),
    re.compile(r"your\s+budget\s*\?", re.I),
    re.compile(r"\bwhat\s+budget\b", re.I),
    re.compile(r"какой\s+у\s+вас\s+бюджет", re.I),
    re.compile(r"какой\s+бюджет", re.I),
    re.compile(r"каков\s+бюджет", re.I),
    re.compile(r"ваш\s+бюджет\s*\?", re.I),
    re.compile(r"уточните\s+бюджет", re.I),
)


def is_budget_inquiry_message(*, subject: str, body: str) -> bool:
    """
    Вебмастер спрашивает бюджет — не слать автоответ про оплату; строку в таблице подсветить жёлтым.
    """
    blob = f"{subject or ''}\n{body or ''}"
    return any(rx.search(blob) for rx in _BUDGET_INQUIRY_RES)


def is_automated_bounce_message(
    *,
    from_header: str = "",
    from_addr: str = "",
    subject: str = "",
    body: str = "",
) -> bool:
    """
    Письмо от mailer-daemon / DSN / «Address not found» — не ответ вебмастера.
    Используется в синке IMAP и при очистке листа (полный текст ячейки «Почта» как body).
    """
    fa = (from_addr or "").strip().lower()
    if fa:
        local, _, _domain = fa.partition("@")
        if local in _BOUNCE_FROM_LOCAL_PARTS:
            return True
        if "mailer-daemon" in fa or "mail-daemon" in fa:
            return True

    fh = (from_header or "").lower()
    if "mail delivery subsystem" in fh or "mailer-daemon" in fh:
        return True

    subj_l = (subject or "").lower()
    for frag in (
        "undeliverable",
        "undelivered mail",
        "delivery status notification",
        "returned mail",
        "failure notice",
        "address not found",
        "delivery failure",
        "message not delivered",
        "could not be delivered",
    ):
        if frag in subj_l:
            return True

    blob = "\n".join((from_header, from_addr, subject, body)).lower()
    if "mailer-daemon@" in blob or "mail-daemon@" in blob:
        return True

    for frag in (
        "your message wasn't delivered",
        "your message was not delivered",
        "address not found",
        "couldn't be found or is unable to receive mail",
        "couldn't be found or is unable to receive email",
        "could not be found or is unable to receive mail",
        "could not be found or is unable to receive email",
        "the address couldn't be found",
        "the address could not be found",
        "mail delivery subsystem",
        "delivery status notification (failure)",
        "status: 5.0.0",
        "550 5.1.1",
    ):
        if frag in blob:
            return True
    return False


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
