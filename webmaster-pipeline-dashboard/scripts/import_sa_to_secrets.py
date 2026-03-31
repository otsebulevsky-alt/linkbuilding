"""One-off: copy GCP service account JSON into Streamlit secrets.toml (do not commit)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = Path(r"c:\project\start\private\env\service_account.json.json")
DST = ROOT / ".streamlit" / "secrets.toml"


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    raw = src.read_text(encoding="utf-8")
    json.loads(raw)
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(
        "GOOGLE_SERVICE_ACCOUNT_JSON = '''\n" + raw.strip() + "\n'''\n",
        encoding="utf-8",
    )
    print("OK", DST)


if __name__ == "__main__":
    main()
