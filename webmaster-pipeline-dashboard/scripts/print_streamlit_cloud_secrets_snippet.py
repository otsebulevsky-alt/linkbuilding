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


if __name__ == "__main__":
    main()
