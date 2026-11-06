"""The evaluation runner's refusal: a fixed, user-readable reason; the CLI prints it and exits 2."""

from __future__ import annotations


class RunnerError(Exception):
    pass
