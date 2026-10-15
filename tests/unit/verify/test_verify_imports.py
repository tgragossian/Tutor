from __future__ import annotations

import subprocess
import sys

SCRIPT = """
import importlib, sys
for name in ("types", "structure", "precheck"):
    importlib.import_module(f"mathtutor.verify.{name}")
banned = ("sympy", "mpmath", "mathtutor.web", "mathtutor.store", "mathtutor.application")
bad = sorted(n for n in sys.modules if any(n == b or n.startswith(b + ".") for b in banned))
print(bad)
sys.exit(1 if bad else 0)
"""


def test_verify_imports() -> None:
    # The web process imports only these modules; sympy-using ones run in pool workers.
    result = subprocess.run(
        [sys.executable, "-I", "-c", SCRIPT], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
