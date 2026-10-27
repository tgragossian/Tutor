"""Versioned configuration for Claude-written help (values pinned in the C1 plan)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_CONFIG_PATH = Path(__file__).with_name("help_config.json")
MAX_CALLS = 2


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTariff(_Frozen):
    model_id: str
    input_micros_per_mtok: int
    output_micros_per_mtok: int


class GuardLimits(_Frozen):
    max_candidates: int
    max_candidate_bytes: int
    max_nodes: int
    max_depth: int
    budget_s: float
    pool_deadline_s: float
    queue_max: int
    queue_wait_s: float


class AdmissionLimits(_Frozen):
    per_hour: int
    per_day: int
    concurrency: int
    month_budget_micros: int
    uncertain_after_s: int


class RetrievalParams(_Frozen):
    k1: float
    b: float
    section_boost: float
    roles: list[str]
    query_max_bytes: int
    question_max_bytes: int


class HelpConfig(_Frozen):
    version: str
    model: str
    effort: str
    deadline_s: float
    max_calls: int = Field(ge=1, le=MAX_CALLS)  # spec 06: at most two calls per request
    max_output_tokens: int
    max_input_tokens: int
    passages: int
    max_output_chars: int
    max_source_ids: int
    field_caps: dict[str, int]
    guard: GuardLimits
    admission: AdmissionLimits
    retrieval: RetrievalParams
    tariffs: dict[str, ModelTariff]
    prompt_version: str
    schema_version: str
    parser_version: str
    guard_version: str
    tariff_version: str


def load_help_config(path: Path) -> HelpConfig:
    """Load and validate a help config; unknown keys raise ``ValueError``."""
    return HelpConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))


def worst_case_micros(cfg: HelpConfig, model: str) -> int:
    """Upper bound in micro-USD for one call: full input plus full output, rounded up."""
    tariff = cfg.tariffs.get(model)
    if tariff is None:
        raise ValueError(f"no tariff for model {model!r}")
    numerator = (
        cfg.max_input_tokens * tariff.input_micros_per_mtok
        + cfg.max_output_tokens * tariff.output_micros_per_mtok
    )
    return -(-numerator // 1_000_000)
