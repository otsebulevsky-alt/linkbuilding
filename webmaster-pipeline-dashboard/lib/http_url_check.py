"""HTTP reachability check for publication URLs (stdlib only)."""

from __future__ import annotations

import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _close_http_error(e: BaseException) -> None:
    """Avoid ResourceWarning on discarded HTTPError (server body / temp file handle)."""
    if isinstance(e, HTTPError):
        try:
            e.close()
        except Exception:
            pass


def check_publication_url(url: str, *, timeout_sec: float = 20.0) -> dict[str, Any]:
    """
    HEAD first; on HTTPError from server, one GET retry (many sites block or mishandle HEAD).

    Returns: ok (2xx/3xx), status (int|None), final_url, error (str).
    """
    out: dict[str, Any] = {"ok": False, "status": None, "final_url": "", "error": ""}
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        out["error"] = "not_http"
        return out

    ctx = ssl.create_default_context()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; WebmasterPipelinePubCheck/1.0; +https://rantsports.com)"
    }

    def _open(method: str):
        req = Request(u, method=method, headers=headers)
        return urlopen(req, timeout=timeout_sec, context=ctx)

    resp = None
    try:
        try:
            resp = _open("HEAD")
        except HTTPError as head_err:
            _close_http_error(head_err)
            resp = _open("GET")
    except HTTPError as e:
        out["status"] = int(e.code) if e.code is not None else None
        out["final_url"] = getattr(e, "url", None) or u
        out["error"] = f"HTTP {e.code}"
        _close_http_error(e)
        return out
    except URLError as e:
        reason = e.reason
        out["error"] = str(reason) if reason is not None else "URLError"
        out["final_url"] = u
        return out
    except TimeoutError:
        out["error"] = "timeout"
        out["final_url"] = u
        return out
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        out["final_url"] = u
        return out

    if resp is None:
        out["error"] = "no_response"
        out["final_url"] = u
        return out

    try:
        code = resp.getcode()
        final = resp.geturl() or u
        out["status"] = int(code) if code is not None else None
        out["final_url"] = final
        out["ok"] = code is not None and 200 <= int(code) < 400
        if not out["ok"]:
            out["error"] = f"HTTP {code}"
    finally:
        try:
            resp.close()
        except Exception:
            pass

    return out


def fetch_publication_page(
    url: str,
    *,
    timeout_sec: float = 20.0,
    max_bytes: int = 1_500_000,
) -> dict[str, Any]:
    """
    GET HTML (до max_bytes) для EEAT / проверки ссылок на странице.
    Возвращает ok (2xx–3xx), status, final_url, body (str), error.
    """
    out: dict[str, Any] = {
        "ok": False,
        "status": None,
        "final_url": "",
        "body": "",
        "error": "",
    }
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        out["error"] = "not_http"
        return out

    ctx = ssl.create_default_context()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; WebmasterPipelinePubCheck/1.0; +https://rantsports.com)",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }

    try:
        req = Request(u, method="GET", headers=headers)
        with urlopen(req, timeout=timeout_sec, context=ctx) as resp:
            code = resp.getcode()
            final = resp.geturl() or u
            chunks: list[bytes] = []
            n = 0
            cap = max(50_000, min(max_bytes, 5_000_000))
            while n < cap:
                chunk = resp.read(min(65536, cap - n))
                if not chunk:
                    break
                chunks.append(chunk)
                n += len(chunk)
            body = b"".join(chunks).decode("utf-8", errors="replace")
        out["status"] = int(code) if code is not None else None
        out["final_url"] = final
        out["body"] = body
        out["ok"] = code is not None and 200 <= int(code) < 400
        if not out["ok"]:
            out["error"] = f"HTTP {code}"
    except HTTPError as e:
        out["status"] = int(e.code) if e.code is not None else None
        out["final_url"] = getattr(e, "url", None) or u
        out["error"] = f"HTTP {e.code}"
        _close_http_error(e)
    except URLError as e:
        reason = e.reason
        out["error"] = str(reason) if reason is not None else "URLError"
        out["final_url"] = u
    except TimeoutError:
        out["error"] = "timeout"
        out["final_url"] = u
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        out["final_url"] = u

    if not out.get("final_url"):
        out["final_url"] = u
    return out
