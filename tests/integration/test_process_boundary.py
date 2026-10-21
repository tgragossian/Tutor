"""The web process never imports SymPy or mpmath, even with the real pool running."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from support.webapp import ROOT

SCRIPT = """
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from mathtutor.settings import Settings
from mathtutor.store.db import upgrade
from mathtutor.web.app import create_app

url = "sqlite:///" + Path(sys.argv[1]).as_posix()
upgrade(url)
settings = Settings(env="test", content_path=Path(sys.argv[2]), database_url=url)
with TestClient(create_app(settings)) as client:
    ready = client.get("/readyz")
    assert ready.status_code == 200, ready.text
bad = sorted(n for n in sys.modules if n.split(".")[0] in ("sympy", "mpmath")
             or n == "mathtutor.verify.check")
print(bad)
sys.exit(1 if bad else 0)
"""


def test_web_process_has_no_sympy(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            SCRIPT,
            str(tmp_path / "boundary.db"),
            str(ROOT / "content" / "compiled" / "problems.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
