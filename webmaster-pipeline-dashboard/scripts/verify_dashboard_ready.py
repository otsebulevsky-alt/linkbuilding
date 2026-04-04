"""Quick checks: SA JSON exists, unit tests pass. Run from webmaster-pipeline-dashboard/.

Usage:
  py scripts/verify_dashboard_ready.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = ROOT / ".streamlit" / "gcp-service-account.json"


def main() -> int:
    ok = True
    if not KEY.is_file():
        print("MISSING:", KEY)
        ok = False
    else:
        print("OK: service account JSON at .streamlit/gcp-service-account.json")

    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
