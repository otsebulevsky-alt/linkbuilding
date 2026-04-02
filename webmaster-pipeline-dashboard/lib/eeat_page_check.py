"""Проверка EEAT на HTML страницы: логика как в weekly-outreach-sync.gs (apps-script-weekly-outreach-sync.md)."""

from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urlparse, urlunparse


def strip_tags_html(s: str) -> str:
    t = s or ""
    t = re.sub(r"<script[\s\S]*?</script>", " ", t, flags=re.I)
    t = re.sub(r"<style[\s\S]*?</style>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _contains_word(text_lower: str, word: str) -> bool:
    w = (word or "").strip().lower()
    if not w:
        return False
    if " " in w:
        return w in text_lower
    idx = 0
    while True:
        idx = text_lower.find(w, idx)
        if idx < 0:
            return False
        before = " " if idx == 0 else text_lower[idx - 1]
        after = " " if idx + len(w) >= len(text_lower) else text_lower[idx + len(w)]
        before_ok = not re.match(r"[0-9a-zа-яё]", before, re.I)
        after_ok = not re.match(r"[0-9a-zа-яё]", after, re.I)
        if before_ok and after_ok:
            return True
        idx += 1


def has_any_marker(text_lower: str, markers: list[str]) -> bool:
    for m in markers:
        if _contains_word(text_lower, m):
            return True
    return False


def has_author_link_in_html(html: str, markers: list[str]) -> bool:
    """Есть ли <a href="http..."> с текстом ссылки, где встречается маркер (как в GS)."""
    if not html or not markers:
        return False
    re_a = re.compile(
        r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
        re.I,
    )
    for m in re_a.finditer(html):
        href_raw = unescape((m.group(1) or "").strip())
        if not href_raw.lower().startswith(("http://", "https://")):
            continue
        link_text = strip_tags_html(m.group(2) or "").lower()
        if has_any_marker(link_text, markers):
            return True
    return False


def normalize_url_for_match(raw: str) -> str:
    """Сопоставление href с целевым URL: схема/хост в lower, www, хвостовой / у пути."""
    u = (raw or "").strip()
    if not u:
        return ""
    u = u.split("#", 1)[0].strip()
    try:
        p = urlparse(u)
    except ValueError:
        return u.lower()
    scheme = (p.scheme or "http").lower()
    netloc = (p.netloc or "").lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    q = p.query or ""
    return urlunparse((scheme, netloc, path, "", q, "")).lower()


def collect_hrefs_from_html(html: str) -> list[str]:
    out: list[str] = []
    re_h = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.I)
    for m in re_h.finditer(html or ""):
        h = unescape((m.group(1) or "").strip())
        if h.lower().startswith(("http://", "https://")):
            out.append(h)
    return out


def exact_target_url_on_page(html: str, target_url: str) -> bool:
    """Точное совпадение нормализованного URL размещения с одним из href на странице."""
    want = normalize_url_for_match(target_url)
    if not want:
        return False
    seen: set[str] = set()
    for h in collect_hrefs_from_html(html):
        n = normalize_url_for_match(h)
        if n and n not in seen:
            seen.add(n)
        if n == want:
            return True
    return False


def expected_author_page_url_on_page(html: str, expected_author_url: str) -> bool:
    """Колонка «Автор со ссылкой»: ожидаемый URL автора присутствует среди href (нормализованно)."""
    return exact_target_url_on_page(html, expected_author_url)


def normalize_anchor_text(s: str) -> str:
    """Трим, NBSP/thin space → пробел, схлопывание пробелов — как в ячейке таблицы."""
    t = (s or "").replace("\u00a0", " ").replace("\u2009", " ")
    return re.sub(r"\s+", " ", t).strip()


def verify_outgoing_link_and_anchor_pair(
    html: str,
    *,
    outgoing_url: str,
    anchor_text: str,
    anchor_case_insensitive: bool,
) -> dict[str, Any]:
    """На странице поста: один и тот же <a> с нормализованным href = outgoing и видимым текстом = anchor."""
    raw_out = (outgoing_url or "").strip()
    if not raw_out.lower().startswith(("http://", "https://")):
        return {
            "placement_pair_ok": False,
            "href_found": False,
            "detail": "outgoing_not_http",
        }
    want_h = normalize_url_for_match(raw_out)
    want_a = normalize_anchor_text(anchor_text)
    if not want_h or not want_a:
        return {
            "placement_pair_ok": False,
            "href_found": False,
            "detail": "empty_target_or_anchor",
        }
    re_a = re.compile(
        r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
        re.I,
    )
    href_found = False
    for m in re_a.finditer(html or ""):
        href_raw = unescape((m.group(1) or "").strip())
        if not href_raw.lower().startswith(("http://", "https://")):
            continue
        nh = normalize_url_for_match(href_raw)
        if nh != want_h:
            continue
        href_found = True
        inner = normalize_anchor_text(strip_tags_html(m.group(2) or ""))
        if anchor_case_insensitive:
            ok = inner.lower() == want_a.lower()
        else:
            ok = inner == want_a
        if ok:
            return {
                "placement_pair_ok": True,
                "href_found": True,
                "detail": "",
            }
    return {
        "placement_pair_ok": False,
        "href_found": href_found,
        "detail": "anchor_mismatch" if href_found else "href_not_found",
    }


def run_eeat_html_checks(html: str, markers: list[str]) -> dict[str, Any]:
    plain = strip_tags_html(html).lower()
    mention = has_any_marker(plain, markers) if markers else False
    author_link = has_author_link_in_html(html, markers) if markers else False
    return {
        "eeat_mention": mention,
        "eeat_author_link": author_link,
    }
