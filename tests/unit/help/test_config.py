import json
import re
from pathlib import Path

import pytest

from mathtutor.help import messages
from mathtutor.help.config import HelpConfig, load_help_config, worst_case_micros
from mathtutor.settings import Settings

CONFIG_PATH = Path(__file__).parents[3] / "src" / "mathtutor" / "help" / "help_config.json"


def test_config_values() -> None:
    cfg = load_help_config(CONFIG_PATH)
    assert cfg.version == "c1-1"
    assert cfg.model == "claude-haiku-5-5"
    assert cfg.effort == "low"
    assert cfg.deadline_s == 15.0
    assert cfg.max_calls == 2
    assert cfg.max_output_tokens == 1000
    assert cfg.max_input_tokens == 8000
    assert cfg.passages == 6
    assert cfg.max_output_chars == 2000
    assert cfg.max_source_ids == 6
    assert cfg.field_caps == {
        "statement": 1500,
        "attempt_latex": 400,
        "misconception_note": 300,
        "confusion_text": 300,
    }
    g = cfg.guard
    assert (g.max_candidates, g.max_candidate_bytes, g.max_nodes, g.max_depth) == (20, 400, 200, 24)
    assert (g.budget_s, g.pool_deadline_s, g.queue_max, g.queue_wait_s) == (5.0, 2.0, 4, 1.0)
    a = cfg.admission
    assert (a.per_hour, a.per_day, a.concurrency) == (30, 150, 4)
    assert a.month_budget_micros == 15_000_000
    assert a.uncertain_after_s == 120
    r = cfg.retrieval
    assert (r.k1, r.b, r.section_boost) == (1.2, 0.75, 1.3)
    assert r.roles == ["definition", "theorem", "rule", "example", "explanation"]
    assert (r.query_max_bytes, r.question_max_bytes) == (1200, 500)
    assert cfg.tariffs["claude-haiku-5-5"].input_micros_per_mtok == 100_000
    assert cfg.tariffs["claude-haiku-5-5"].output_micros_per_mtok == 500_000
    assert cfg.tariffs["claude-sonnet-5-5"].input_micros_per_mtok == 2_000_000
    assert cfg.tariffs["claude-sonnet-5-5"].output_micros_per_mtok == 10_000_000
    assert (cfg.prompt_version, cfg.schema_version) == ("v1", "1")
    assert (cfg.parser_version, cfg.guard_version, cfg.tariff_version) == ("1", "1", "2026-10-26")


def test_worst_case_haiku() -> None:
    cfg = load_help_config(CONFIG_PATH)
    assert worst_case_micros(cfg, "claude-haiku-5-5") == 1_300
    assert worst_case_micros(cfg, "claude-sonnet-5-5") == 26_000


def test_worst_case_unknown_model() -> None:
    with pytest.raises(ValueError):
        worst_case_micros(load_help_config(CONFIG_PATH), "nope")


def test_unknown_key_rejected(tmp_path: Path) -> None:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data["surprise"] = 1
    p = tmp_path / "c.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_help_config(p)
    assert isinstance(load_help_config(CONFIG_PATH), HelpConfig)


def test_scripted_only_in_test_env() -> None:
    with pytest.raises(ValueError):
        Settings(env="production", help_generator="scripted", secret_key="x" * 40)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Settings(env="development", help_generator="scripted")
    assert Settings(env="test", help_generator="scripted").help_generator == "scripted"


def test_settings_defaults() -> None:
    s = Settings()
    assert s.anthropic_api_key is None
    assert s.corpus_path == Path("content/corpus/chunks.jsonl")
    assert s.help_generator == "claude"
    assert s.guard_pool_memory_mb == 384
    assert s.help_config_path.is_file()
    assert load_help_config(s.help_config_path).version == "c1-1"


def test_messages_us_spelling() -> None:
    assert messages.UNAVAILABLE == "Hints are unavailable right now."
    assert messages.LIMITED == "You've reached the help limit for now."
    assert messages.ABSTAIN == "I can't answer that from the textbook."
    assert messages.NUDGE == "Here's a nudge without the answer: re-read {section}."
    for name in ("UNAVAILABLE", "LIMITED", "ABSTAIN", "NUDGE"):
        assert not re.search(r"licence|colour|behaviour", getattr(messages, name), re.I)
