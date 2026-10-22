"""tools/load/measure.sh keeps the burst's exit status (review B-R4), using stub commands."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

STUBS = {
    "sudo": 'exec "$@"\n',
    "docker": "exit 0\n",
    "free": 'echo "Mem: 909 551 47 2 443 358"\n',
    "sleep": "exit 0\n",
}


def _run(tmp_path: Path, burst_exit: int) -> subprocess.CompletedProcess[str]:
    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name, body in {**STUBS, "python3": f"exit {burst_exit}\n"}.items():
        path = stubs / name
        path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8", newline="\n")
        path.chmod(0o755)
    env = {**os.environ, "PATH": f"{stubs.as_posix()}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(
        [BASH or "bash", "tools/load/measure.sh", "http://example.invalid"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.skipif(BASH is None or os.name == "nt", reason="needs a POSIX bash with PATH stubs")
@pytest.mark.parametrize("burst_exit", [0, 1])
def test_measure_returns_the_burst_exit_status(tmp_path: Path, burst_exit: int) -> None:
    result = _run(tmp_path, burst_exit)
    assert result.returncode == burst_exit, result.stderr
    assert "== after" in result.stdout  # memory is still reported for a failed run
    assert ("do not use these numbers" in result.stderr) == (burst_exit != 0)
