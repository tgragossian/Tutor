# C1 shared interfaces

[C1 plan](README.md)

Every task's **Interfaces** block refers here. All new code lives under `src/mathtutor/help/`
or `src/mathtutor/retrieval/`; dataclasses are `frozen=True`.

```python
# help/config.py (Task 1)
ModelTariff(model_id: str, input_micros_per_mtok: int, output_micros_per_mtok: int)
HelpConfig(version, model, effort, deadline_s: float, max_calls: int, max_output_tokens: int,
           max_input_tokens: int, passages: int, field_caps: dict[str, int], guard: GuardLimits,
           admission: AdmissionLimits, retrieval: RetrievalParams, tariffs: dict[str, ModelTariff],
           prompt_version, schema_version, parser_version, guard_version)
load_help_config(path: Path) -> HelpConfig
worst_case_micros(cfg: HelpConfig, model: str) -> int

# help/latex_parse.py (Task 2) — pure Python, no SymPy
ParsedMath(tree: JsonValue, foreign: frozenset[str])      # foreign: symbols/functions ≠ variable
ParseRejected(reason: str)
parse_latex(src: str, *, variable: str = "x") -> ParsedMath | ParseRejected

# help/leak_guard.py (Task 3)
class LeakStatus(StrEnum): LEAK, NO_MATCH, UNCHECKED
Candidate(latex: str, origin: Literal["inline", "display", "equation_rhs", "decimal"])
GuardDecision = Literal["pass", "no_detected_math", "block"]
GuardResult(decision: GuardDecision, counts: dict[LeakStatus, int], reason: str)  # no LaTeX stored
extract_candidates(text: str, limits: GuardLimits) -> list[Candidate] | None   # None = too many
LeakGuard(pool: Pool, limits: GuardLimits, clock).check(text: str, answer: Answer, deadline: float) -> GuardResult

# retrieval/corpus.py, retrieval/bm25.py (Tasks 5–6)
class ChunkRole(StrEnum): DEFINITION, THEOREM, RULE, EXAMPLE, EXPLANATION, EXERCISE, ANSWER_KEY
Chunk(chunk_id, section, section_title, url, role: ChunkRole, text, content_hash, est_tokens: int)
Corpus(chunks: dict[str, Chunk], corpus_hash: str, edition: str); load_corpus(path: Path) -> Corpus
Hit(chunk_id: str, score: float)
Bm25Index.build(corpus: Corpus, params: RetrievalParams) -> Bm25Index;  .fingerprint: str
Bm25Index.search(query: str, k: int, *, boost_section: str | None, roles: frozenset[ChunkRole]) -> list[Hit]

# help/ledger.py (Task 8)
class HelpLimited(AppError)          # 429 "help_limited"
Ledger(sessions, cfg, clock)
  .admit(db, user_id: int, request_id: str, model: str) -> int          # entry id for call 1
  .reserve_call(request_id: str, user_id: int, call_no: int, model: str) -> int
  .settle(entry_id: int, input_tokens: int, output_tokens: int) -> int   # actual micros
  .mark_uncertain(entry_id: int) -> None
  .month_total(month: str) -> int                                        # settled+reserved+uncertain

# help/context.py (Task 9)
HelpType = Literal["hint", "feedback", "explain"]          # "question" arrives in C2
HelpContext(problem_id, topic, section, statement, answer_kind, attempts: list[AttemptLine],
            tries_used: int, hint_level: int, misconception_note: str | None, variable: str)
build_context(db, item: SessionItem, problem: Problem, hint_level: int, pool: Pool) -> HelpContext

# help/generator.py (Task 10)
GenerationRequest(model, effort, system: str, user: str, schema: dict, max_output_tokens: int, timeout_s: float)
GenerationResult(text: str | None, stop_reason: str, input_tokens: int | None,
                 output_tokens: int | None, model: str, provider_request_id: str | None, latency_ms: int)
GeneratorError(kind: Literal["timeout", "connection", "rate_limited", "api_error"], billed_unknown: bool)
class Generator(Protocol): def generate(self, req: GenerationRequest) -> GenerationResult
ClaudeGenerator(api_key: str); ScriptedGenerator(script: list[GenerationResult | GeneratorError])
HelpOutput(text: str, source_ids: list[str], abstain: bool)   # pydantic, extra="forbid"

# help/service.py (Task 11)
HelpIn(help_request_id: UUID, session_item_id: int, item_revision: int, help_type: HelpType, confusion: str | None)
class HelpStatus(StrEnum): DELIVERED, ABSTAINED, FALLBACK, UNAVAILABLE, LIMITED, STALE, PENDING
SourceRef(label: str, url: str, license: str)
HelpOutcome(request_id, status: HelpStatus, session_item_id, item_revision, help_seq: int,
            hint_level: int | None, html: str | None, sources: list[SourceRef])
HelpService(...).enabled -> bool;  .request_help(user_id: int, req: HelpIn) -> HelpOutcome
HelpService.availability(item_view: ItemView, user_id: int) -> HelpAvailability
```

Store (Task 7): `HelpRequestRow`, `UsageEntry`, `ItemHelpState`, `User.privacy_epoch` — see Task 7.
