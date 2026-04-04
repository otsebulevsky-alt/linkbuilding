"""Print a TOML snippet for Streamlit Community Cloud -> Settings -> Secrets.

Reads local service account JSON (default: .streamlit/gcp-service-account.json).
Output: stdout only. Do not paste the printed JSON into public chats.

Usage:
  py scripts/print_streamlit_cloud_secrets_snippet.py
  py scripts/print_streamlit_cloud_secrets_snippet.py path/to/key.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / ".streamlit" / "gcp-service-account.json"


def main() -> None:
    src = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_JSON
    if not src.is_file():
        sys.stderr.write(
            f"File not found: {src}\n"
            "Usage: py scripts/print_streamlit_cloud_secrets_snippet.py [path-to-sa.json]\n"
        )
        sys.exit(1)
    raw = src.read_text(encoding="utf-8").strip()
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("type") != "service_account":
        sys.stderr.write("Not a Google service account JSON (expected type=service_account).\n")
        sys.exit(1)

    print("# 1) share.streamlit.io -> your app -> Manage app (or ...) -> Settings -> Secrets")
    print("# 2) Paste below (merge with existing Secrets if any), Save, Reboot app")
    print()
    print("# --- Process env: fewer Cloud crashes after «Processed dependencies» ---")
    print('PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"')
    print('MALLOC_ARENA_MAX = "2"')
    print('PYTHONMALLOC = "malloc"')
    print('OMP_NUM_THREADS = "1"')
    print('OPENBLAS_NUM_THREADS = "1"')
    print()
    print("GOOGLE_SERVICE_ACCOUNT_JSON = '''")
    print(raw)
    print("'''")
    print()
    try:
        ce = str(data.get("client_email") or "").strip()
    except Exception:
        ce = ""
    if ce:
        print(f"# Share all required spreadsheets with this address (Viewer or Editor): {ce}")
    print()
    print("# Google Sheets — канон HACK-382 (в ID калькулятора: ...Q94JI08... = буква I, не J108)")
    print('SPREADSHEET_INBOX_LOG_ID = "19dMDf3sxH8RuBI6hZwWwen_cm2A_UOQZdXVtcjMRllc"')
    print('SPREADSHEET_TELECOM_ASIA_ID = "1S5lk-ya4iWwq5znY_vebAuTqloyTlWTcsNuXydZXT00"')
    print('SPREADSHEET_REGISTRY_2_ID = "1DaiRFqU2d_85cXr0fDmyhzIY4V9fm0zxh4KraZMOFnw"')
    print('SPREADSHEET_CALCULATOR_ID = "1xrjeVD0Q94JI08v2gFvtv1NbiTAbq0fSjv-A-g5pPSs"')
    print('SPREADSHEET_PAYMENT_OPTIONS_ID = "17MoDWnMesQkpmI9bSZAF5LYQpjyM2itU0PpcaS-X240"')
    print('GID_INBOX_LOG = "0"')
    print('GID_TELECOM_REGISTRY = "728254189"')
    print('GID_REGISTRY_2 = "1088920242"')
    print('GID_CALCULATOR_TAB_1 = "225938948"')
    print('GID_CALCULATOR_TAB_2 = "0"')
    print('GID_PAYMENT_OPTIONS = "0"')
    print()
    print('LINKBUILDER_FILTER = "Олег"')
    print('LINKBUILDER_ALIASES = "Oleg,oleg"')
    print('TRADE_RESPONSIBLE_NAME = "Oleg Tsebulevskiy|Tsekhulevskiy|Tsebulovskiy"')
    print('COL_TRADE_DATE = "Комментарий (Денис)"')
    print('# COL_TRADE_RESPONSIBLE = "Ответственный"  # если авто-поиск колонки не сработал')
    print('ARTICLE_PUBLISH_MAX_SEND = "50"')
    print('# PUBLICATION_CHECK_TIMEOUT_SEC = "25"')
    print('# PUBLICATION_CHECK_MAX_ROWS = "150"')
    print('# PUBLICATION_CHECK_STATUSES = "Готово"')
    print('# COL_ANCHOR = "Anchor"')
    print('# COL_OUTGOING_LINK = "Outgoing link"')
    print('# COL_PLACED_TARGET_URL = ""  # если COL_OUTGOING_LINK пусто — имя колонки URL')
    print('# PUBLICATION_CHECK_ANCHOR_CASE_INSENSITIVE = "false"')
    print('# GOOGLE_CSE_API_KEY = ""')
    print('# GOOGLE_CSE_CX = ""')
    print()
    print("# --- Mail (replace APP_PASSWORD with your Google App Password, 16 chars) ---")
    print('GMAIL_SMTP_USER = "o.tsebulevsky@rantsports.com"')
    print('GMAIL_SMTP_APP_PASSWORD = "APP_PASSWORD"')
    print('GMAIL_SMTP_HOST = "smtp.gmail.com"')
    print('GMAIL_SMTP_PORT = "587"')
    print('GMAIL_IMAP_USER = "o.tsebulevsky@rantsports.com"')
    print('GMAIL_IMAP_APP_PASSWORD = "APP_PASSWORD"')
    print('IMAP_MAILBOX = "INBOX"')


if __name__ == "__main__":
    main()
