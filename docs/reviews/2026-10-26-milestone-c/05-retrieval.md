# C-R7/C-R8: corpus and document authority

[Review](README.md) · [Corpus contract](../../superpowers/specs/2026-10-26-milestone-c/07-corpus-contract.md)

## Corpus findings

Fetching the live book again is not a reproducible rebuild. Save raw pages, a canonical
page list, extractor/tokenizer versions and hashes; separate source acquisition from an
offline deterministic build. Otherwise a changed page, timestamp or ordering changes IDs
and silently invalidates relevance labels and logs.

Section/example labels alone need not be unique across the whole book. Namespace chunks by
book/section/anchor/part and keep content hashes plus a corpus version. Track coverage and
reject silent missing pages. A hash proves identity, not that math survived HTML extraction.

The corpus includes whole-book teaching material, not a graded bank. Distinguish prose,
theorems and worked examples from exercises and answer-key blocks. An exact worked solution
matching the current problem can leak via context or a displayed snippet. Use content roles,
match exclusions and no raw snippet display; retain the external source link for attribution.
An external textbook page may itself contain answers and is outside the response guard.

BM25 can miss notation or paraphrases. Pin tokenization and section-boost strength; evaluate
word-only, equation-bearing and mixed queries across the book. Scores are not calibrated
confidence values. A valid source ID only proves membership; human judgments must assess
whether the chunk supports the response.

The existing OpenStax decision is preserved, including its recorded permissions risk.
This review makes no new legal determination or claim of permission.

## Documentation findings

The C overview said small corpus, C1-only buttons and below-reveal guarding; the new spec
said whole book, C2 text and guard at every level. Active indexes still treated B hours as a
closure gate despite the 2026-10-26 handoff. The spec's “later projects, in order” put the
new bank ahead of LoRA, contradicting decision 0005's C → LoRA → D/E → expansion sequence.

Corrected active summaries to link one contract per topic. Automated-bank placement remains
C-O4; do not silently override the accepted LoRA order. Original handoff pages and dated B
reviews remain historical. Provider versions/prices are execution evidence, not folklore.
