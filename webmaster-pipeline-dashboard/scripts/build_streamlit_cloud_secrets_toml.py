"""Build one TOML file for Streamlit Community Cloud -> Settings -> Secrets.

NEVER paste this .py into Secrets — only the generated .toml (TOML format, not raw JSON).

Usage:
  py scripts/build_streamlit_cloud_secrets_toml.py
  py scripts/build_streamlit_cloud_secrets_toml.py --clipboard   # Windows: copy file to clipboard

Reads:  .streamlit/gcp-service-account.json
Writes: .streamlit/generated-for-streamlit-cloud-secrets.toml (gitignored)

Replace xxxx in GMAIL_* with your Google App Password before Save on Streamlit.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = ROOT / ".streamlit" / "gcp-service-account.json"
OUT = ROOT / ".streamlit" / "generated-for-streamlit-cloud-secrets.toml"

# [REF: lib/config.py + hack-382 implementation-notes] Q94 + JI + 08 = letter I, not digit 1
_CALC_ID = "1xrjeVD0Q94JI08v2gFvtv1NbiTAbq0fSjv-A-g5pPSs"


def _copy_file_to_clipboard_windows(file_path: Path) -> bool:
    if platform.system() != "Windows":
        return False
    lp = str(file_path.resolve()).replace("'", "''")
    ps = f"Get-Content -LiteralPath '{lp}' -Raw -Encoding UTF8 | Set-Clipboard"
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _build_lines(ce: str, raw_json: str) -> list[str]:
    return [
        "# =============================================================================",
        "# Streamlit Cloud -> App -> Settings -> Secrets: paste ALL of this file.",
        "# Format is TOML (KEY = \"value\"). Do NOT paste only { ... } JSON without the line:",
        "#   GOOGLE_SERVICE_ACCOUNT_JSON = ''' ... '''",
        "# =============================================================================",
        f"# Service account email (share all spreadsheets with this address): {ce}",
        "",
        "# --- Process stability (Cloud) ---",
        'PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"',
        'MALLOC_ARENA_MAX = "2"',
        'PYTHONMALLOC = "malloc"',
        'OMP_NUM_THREADS = "1"',
        'OPENBLAS_NUM_THREADS = "1"',
        "",
        "# --- Google service account (required for all 4 buttons + Sheets) ---",
        "GOOGLE_SERVICE_ACCOUNT_JSON = '''",
        raw_json,
        "'''",
        "",
        "# --- Books + gids (HACK-382 canon; SPREADSHEET_CALCULATOR_ID must contain ...JI08... letter I) ---",
        'SPREADSHEET_INBOX_LOG_ID = "19dMDf3sxH8RuBI6hZwWwen_cm2A_UOQZdXVtcjMRllc"',
        'SPREADSHEET_TELECOM_ASIA_ID = "1S5lk-ya4iWwq5znY_vebAuTqloyTlWTcsNuXydZXT00"',
        'SPREADSHEET_REGISTRY_2_ID = "1DaiRFqU2d_85cXr0fDmyhzIY4V9fm0zxh4KraZMOFnw"',
        f'SPREADSHEET_CALCULATOR_ID = "{_CALC_ID}"',
        'SPREADSHEET_PAYMENT_OPTIONS_ID = "17MoDWnMesQkpmI9bSZAF5LYQpjyM2itU0PpcaS-X240"',
        'GID_INBOX_LOG = "0"',
        'GID_TELECOM_REGISTRY = "728254189"',
        'GID_REGISTRY_2 = "1088920242"',
        'GID_CALCULATOR_TAB_1 = "225938948"',
        'GID_CALCULATOR_TAB_2 = "0"',
        'GID_PAYMENT_OPTIONS = "0"',
        "",
        "# --- Linkbuilder + trade (button: trade) ---",
        'LINKBUILDER_FILTER = "Олег"',
        'LINKBUILDER_ALIASES = "Oleg,oleg"',
        'TRADE_RESPONSIBLE_NAME = "Oleg Tsebulevskiy|Tsekhulevskiy|Tsebulovskiy"',
        'COL_TRADE_DATE = "Комментарий (Денис)"',
        'COL_TRADE_RESPONSIBLE = "Ответственный"',
        'TRADE_TIMEZONE = "Europe/Moscow"',
        'TRADE_DATE_MAX_AGE_DAYS = "30"',
        'TRADE_DISCOUNT_PERCENT = "0.2"',
        "",
        "# --- Mail (buttons: read mail, trade, send articles) ---",
        "# Replace xxxx with Google App Password (16 chars). Or use panel 'Change mail' per session.",
        'GMAIL_SMTP_USER = "o.tsebulevsky@rantsports.com"',
        'GMAIL_SMTP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"',
        'GMAIL_SMTP_HOST = "smtp.gmail.com"',
        'GMAIL_SMTP_PORT = "587"',
        'GMAIL_IMAP_USER = "o.tsebulevsky@rantsports.com"',
        'GMAIL_IMAP_APP_PASSWORD = "xxxx xxxx xxxx xxxx"',
        'IMAP_MAILBOX = "INBOX"',
        'IMAP_SYNC_TIMEOUT_SEC = "900"',
        'IMAP_AUTO_REPLY_PAYMENT_FOLLOWUP = "true"',
        "",
        "# --- Send articles (button) ---",
        'ARTICLE_PUBLISH_MAX_SEND = "50"',
        "",
        "# --- Publication check (button) ---",
        'PUBLICATION_CHECK_TIMEOUT_SEC = "25"',
        'PUBLICATION_CHECK_MAX_ROWS = "150"',
        'PUBLICATION_CHECK_MAX_BODY_BYTES = "1500000"',
        'PUBLICATION_CHECK_STATUSES = "Готово"',
        'PUBLICATION_CHECK_ANCHOR_CASE_INSENSITIVE = "false"',
        'COL_ANCHOR = "Anchor"',
        'COL_OUTGOING_LINK = "Outgoing link"',
        'COL_AUTHOR_WITH_LINK = "Автор со ссылкой"',
        'COL_AUTHOR_WITHOUT_LINK = "Автор без ссылки"',
        'EEAT_AUTHOR_MARKERS = "алиса,alisa,metaratings,авторы metaratings"',
        "# Optional Google CSE (index check); leave unset to use code defaults (empty):",
        "# GOOGLE_CSE_API_KEY = \"\"",
        "# GOOGLE_CSE_CX = \"\"",
        "",
    ]


def main() -> None:
    want_clipboard = "--clipboard" in sys.argv or "-c" in sys.argv

    if not KEY.is_file():
        sys.stderr.write(
            f"Missing service account JSON: {KEY}\n"
            "Put your key file there (Google Cloud -> Service account -> Keys -> JSON).\n"
        )
        sys.exit(1)
    raw = KEY.read_text(encoding="utf-8").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Invalid JSON in {KEY}: {e}\n")
        sys.exit(1)
    if not isinstance(data, dict) or data.get("type") != "service_account":
        sys.stderr.write(f"Not a service account JSON: {KEY}\n")
        sys.exit(1)

    ce = str(data.get("client_email") or "").strip()
    lines = _build_lines(ce, raw)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote: {OUT}")

    if want_clipboard:
        if _copy_file_to_clipboard_windows(OUT):
            print("Clipboard: OK (Windows) — open Streamlit Secrets and Ctrl+V, then Save, Reboot.")
        else:
            print("Clipboard: skipped (not Windows or PowerShell failed). Open the .toml file and copy manually.")
    else:
        print("Tip: py scripts/build_streamlit_cloud_secrets_toml.py --clipboard  (Windows: copy to clipboard)")
        print("Then: share.streamlit.io -> your app -> Settings -> Secrets -> paste -> Save -> Reboot app.")


if __name__ == "__main__":
    main()
