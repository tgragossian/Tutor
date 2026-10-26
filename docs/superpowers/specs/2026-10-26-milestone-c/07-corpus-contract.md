# C design 7: reproducible corpus and grounded citations

[C design](README.md) · [Components](01-components.md) · [Review rationale](../../../reviews/2026-10-26-milestone-c/05-retrieval.md)

Review amendment, 2026-10-26. `tools/build_corpus` is a proposed tool, not an existing command.
Decision [0004 §1](../../../decisions/0004-rag-source-models-and-evaluation.md#1-openstax-text-in-retrieval)
owns the recorded source/licensing decision and conditions; this spec does not reinterpret it.

## Acquisition and offline build

- Acquire whole-book teaching pages against an explicit table-of-contents inventory. Save raw
  bytes and page metadata. Fail or report incomplete coverage; never label a partial crawl complete.
- Pin edition, canonical HTTPS URL, fetch date, raw-page hashes and extractor/schema versions.
  Record unavailable anchors/math and excluded content roles; inspect representative chapters.
- Build offline from that frozen snapshot. Normalize Unicode/whitespace, sort deterministically
  and preserve LaTeX with surrounding definitions, assumptions and example prerequisites.
- Chunk at mathematical boundaries, targeting 300–500 tokens with a separate hard ceiling.
  Split long examples into linked parts with context; do not split an equation from its conditions.
- IDs include book/section/anchor/part; detect collisions. A changed passage changes its content
  hash/corpus version even if its structural ID is stable. Logs identify `(corpus_hash, chunk_id)`.
- Separate volatile fetch timestamps from hashed build content. Record tokenizer/BM25 version,
  parameters, stopword/math normalization, sorted chunk order and canonical index fingerprint.
  Rebuilding the same raw snapshot with the same build config must reproduce the artifacts.

## Content roles and answer exposure

Definitions, theorems, rules, worked examples and explanatory text are retrieval candidates.
Exercise lists/answer keys are separately labeled and excluded from C1 help retrieval.
Whole-book coverage means teaching material across the book; it does not mean a graded bank.
Filter a known exact exercise/solution match before prompting; test equivalent near-matches.
Worked examples remain useful but are not inherently safe for every current problem.
No raw retrieved snippet or provider output is sent to the browser before validation.

Section links may lead to external pages containing worked answers. The guard governs text
delivered by this app, not the contents of an external textbook page the student opens.

## Retrieval contract

BM25 top 6 is the baseline. Include problem statement, topic, help intent and confusion/question;
for feedback add a bounded representation of the last wrong attempt or verified misconception.
Cap each field and total tokens; a long question must not crowd out the authoritative problem.
Section boosts are fixed in a versioned config and chosen on development queries only.
BM25 score is a ranking signal, not a calibrated probability that a question is supported.
Return no-context when nothing useful is available; do not invent a nearest section.

Test prose, equation and mixed queries across all chapters; include out-of-book negatives.
Maintain chunk-role and section coverage reports and inspect mathematical rendering after build.
Measure loaded index/RSS and mixed traffic; “tens of MB” remains an estimate until measured.

## Citation and display contract

- Require at least one unique source ID for a non-abstaining response; IDs must belong to this
  request's final retrieved set. A response with any unknown ID is invalid, not partly approved.
- Resolve title, section, anchor, licence and URL from versioned server metadata. Only canonical
  OpenStax HTTPS URLs are allowed. Link validity and semantic citation support are separate checks.
- After one shared repair opportunity, invalid citations yield a fixed abstention/section nudge;
  never strip IDs and retain claims that may have depended on them.
- Render a small safe Markdown subset and math only: no raw HTML, remote images, model links,
  embedded objects or trusted LaTeX commands. Source links are a separate server-rendered field.
- Retrieved instructions, student text and output are untrusted. Delimiters aid prompting;
  schema validation, no tool execution, ownership and escaping enforce the actual boundaries.
