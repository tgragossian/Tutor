"""The runtime image ships every data file the app loads (review C1-R1).

No Docker here: the test rebuilds the image's ``/app`` layout from the Dockerfile's ``COPY``
lines and its ``ENV`` paths, then loads help from that layout. The container smoke test checks
the real image (``tests/container/smoke.sh``).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from support.helpkit import CFG, ROOT

from mathtutor.help.generator import FixedHintGenerator
from mathtutor.settings import Settings
from mathtutor.web.app import _load_help

DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
RUNTIME = DOCKERFILE.rsplit("\nFROM ", 1)[1]  # the final stage only
DATA_FIELDS = ("content_path", "corpus_path", "confusions_path")


def _env() -> dict[str, str]:
    return dict(re.findall(r"(MATHTUTOR_[A-Z_]+)=(\S+)", RUNTIME))


def _copies() -> list[tuple[str, str]]:
    return re.findall(r"^COPY (content/\S*) (/app/\S*)$", RUNTIME, re.MULTILINE)


def test_every_data_path_is_set_and_copied() -> None:
    env = _env()
    copied = [dest for _, dest in _copies()]
    for field in DATA_FIELDS:
        path = env.get(f"MATHTUTOR_{field.upper()}")
        assert path is not None, f"the image does not set MATHTUTOR_{field.upper()}"
        assert any(path.startswith(dest) for dest in copied), f"{path} is not copied"


def test_image_layout_loads_help(tmp_path: Path) -> None:
    for source, dest in _copies():
        shutil.copytree(ROOT / source, tmp_path / dest.lstrip("/"), dirs_exist_ok=True)
    env = _env()

    def inside(field: str) -> Path:
        return tmp_path / env[f"MATHTUTOR_{field.upper()}"].lstrip("/")

    settings = Settings(
        env="test",
        help_generator="scripted",
        content_path=inside("content_path"),
        corpus_path=inside("corpus_path"),
        confusions_path=inside("confusions_path"),
    )
    assert _load_help(settings, CFG, FixedHintGenerator()) is not None
