"""Runtime configuration, read from ``MATHTUTOR_*`` environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MATHTUTOR_", extra="forbid", frozen=True)

    env: Literal["development", "test", "production"] = "development"
    secret_key: SecretStr | None = None
    content_path: Path = Path("content/compiled/problems.json")
    database_url: str = "sqlite:///data/mathtutor.db"
    # Verifier workers and each worker's address-space cap (RLIMIT_AS, Linux only); size these
    # from the host's measured memory (docs/ops/host.md).
    pool_size: int = Field(default=1, ge=1)
    pool_memory_mb: int = Field(default=384, ge=1)
    # Milestone C1 help. "scripted" drives tests only; "off" disables help.
    anthropic_api_key: SecretStr | None = None
    corpus_path: Path = Path("content/corpus/chunks.jsonl")
    confusions_path: Path = Path("content/help/confusions.json")
    help_generator: Literal["claude", "scripted", "off"] = "claude"
    guard_pool_memory_mb: int = Field(default=384, ge=1)
    help_config_path: Path = Path(__file__).parent / "help" / "help_config.json"

    @model_validator(mode="after")
    def _scripted_only_in_test(self) -> Self:
        if self.help_generator == "scripted" and self.env != "test":
            raise ValueError("MATHTUTOR_HELP_GENERATOR=scripted is allowed only when env is test")
        return self

    @model_validator(mode="after")
    def _production_needs_secret(self) -> Self:
        if self.env == "production":
            key = self.secret_key.get_secret_value() if self.secret_key else ""
            if len(key) < MIN_SECRET_LENGTH:
                raise ValueError(
                    f"MATHTUTOR_SECRET_KEY must be set and at least {MIN_SECRET_LENGTH} "
                    "characters in production"
                )
        return self
