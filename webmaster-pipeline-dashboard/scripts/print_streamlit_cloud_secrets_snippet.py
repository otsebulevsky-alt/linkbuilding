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
    print("# 2) Paste below (replace nothing if you use defaults), Save, Reboot app")
    print()
    print("GOOGLE_SERVICE_ACCOUNT_JSON = '''")
    print(raw)
    print("'''")
    print()
    print('LINKBUILDER_FILTER = "Олег"')
    print('LINKBUILDER_ALIASES = "Oleg,oleg"')
    print('TRADE_RESPONSIBLE_NAME = "Oleg Tsebulevskiy"')
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
