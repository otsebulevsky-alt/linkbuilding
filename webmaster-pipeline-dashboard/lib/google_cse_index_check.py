"""Проверка «в индексе Google» через Custom Search JSON API (опционально).

Нужны GOOGLE_CSE_API_KEY и GOOGLE_CSE_CX в Secrets; CSE с включённым поиском по всему вебу.
Эвристика: в выдаче по запросу с точным URL есть результат с тем же нормализованным link.
"""

from __future__ import annotations

import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from lib.eeat_page_check import normalize_url_for_match


def check_article_url_in_google_index(
    article_url: str,
    *,
    api_key: str,
    cx: str,
    timeout_sec: float = 20.0,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "indexed": None,
        "error": "",
        "raw_total": None,
        "matched_link": "",
    }
    key = (api_key or "").strip()
    cxe = (cx or "").strip()
    u = (article_url or "").strip()
    if not key or not cxe:
        out["error"] = "no_cse_credentials"
        return out
    if not u.startswith(("http://", "https://")):
        out["error"] = "bad_article_url"
        return out

    target = normalize_url_for_match(u)
    # Запрос в кавычках — кандидат на точное совпадение с URL материала
    q = f'"{u}"'
    params = urlencode({"key": key, "cx": cxe, "q": q, "num": "10"})
    api = f"https://www.googleapis.com/customsearch/v1?{params}"
    ctx = ssl.create_default_context()
    req = Request(
        api,
        method="GET",
        headers={"User-Agent": "WebmasterPipelineIndexCheck/1.0"},
    )
    try:
        with urlopen(req, timeout=timeout_sec, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
    except HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            body = ""
        out["error"] = f"HTTP {e.code} {body}"
        return out
    except URLError as e:
        out["error"] = str(e.reason) if e.reason else "URLError"
        return out
    except (json.JSONDecodeError, TimeoutError, OSError) as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out

    err = data.get("error")
    if err:
        out["error"] = str(err.get("message") or err)[:400]
        return out

    searches = data.get("searchInformation") or {}
    out["raw_total"] = searches.get("totalResults")
    items = data.get("items") or []
    for it in items:
        link = (it.get("link") or "").strip()
        if not link:
            continue
        if normalize_url_for_match(link) == target:
            out["indexed"] = True
            out["matched_link"] = link[:500]
            return out

    out["indexed"] = False
    return out
