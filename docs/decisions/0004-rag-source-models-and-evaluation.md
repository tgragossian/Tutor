# 0004: RAG source text, generator candidates and hint evaluation

[Decisions index](README.md) · [Milestone C plan](../superpowers/plans/portfolio-mvp/03-rag.md)

Status: accepted by Thomas, 2026-10-22. Governs milestone C; amends the C evaluation gate.

## 1. OpenStax text in retrieval

- **Decision (Thomas):** milestone C may chunk, index and send passages of *Calculus Volume 1*
  (OpenStax, ©2018 Rice University, CC BY-NC-SA 4.0) to a hosted LLM to generate hints.
  Thomas relies on the CC BY-NC-SA 4.0 licence of the edition used.
- **Further basis (Thomas, 2026-10-22):** OpenStax's permissions guidance says: "Using OpenStax
  for teaching and learning? If you are an educator or student using OpenStax for teaching,
  learning, customizing, and/or sharing, you are already covered under the CC BY-NC-SA license.
  No form needed." Thomas considers this tutor (free, noncommercial, for students learning
  calculus) to fall under it. Source page as quoted by Thomas; add its URL when recorded.
- **Known risk, recorded rather than resolved:** the book's citation page says it "may not be
  used in the training of large language models or otherwise be ingested into large language
  models or generative AI offerings without OpenStax's prior written permission"
  ([source manifest](../../content/sources/openstax-calculus-v1.md)). Claude flagged that
  citing satisfies attribution but not this sentence; Thomas chose to proceed. Revisit if
  OpenStax objects, or before any commercial use or model training on the text.
- Conditions that follow from the licence:
  - **Attribution:** every hint shows its source section with a working OpenStax link and the
    licence; the site keeps the existing attribution line.
  - **NonCommercial:** no ads, paid tiers or commercial use of the hint feature.
  - **ShareAlike:** the stored corpus snapshot and chunks are derivatives, distributed under
    CC BY-NC-SA 4.0 with provenance (edition, URL, retrieval date, hash).
  - No OpenStax or Rice names, logos or covers as branding.
  - The corpus is not used to train or fine-tune a model without revisiting this decision.

## 2. Generator candidates

- Thomas prefers the cheaper of GPT-5.2 and Claude Opus 4.6. At list prices (2026-10-22)
  GPT-5.2 is about half the cost of Opus 4.6 per hint, and Opus 4.6 is superseded by Opus 5.5.
- **Baseline to beat: GPT-5.2.** Compared under identical retrieval, prompts and limits against
  Claude Opus 5.5, Sonnet 5.5 and Haiku 5.5 on the development cases (estimated ≈ $5 in total).
- **Selection rule:** the cheapest candidate that is non-inferior to the best one on the
  primary measures below, within a margin fixed before the run. Record prices on the date
  checked, model versions and per-case results.

## 3. Hint evaluation measures what models get wrong

Answer correctness is decided by the SymPy verifier, never by an LLM, and frontier models are
near the ceiling on Calc I derivative math. A benchmark of "is the math right" cannot rank
designs. The C gate therefore measures:

- **Primary:** answer leakage at each hint level; addressing the student's specific error
  (built from each problem's recorded misconceptions); not endorsing mistaken reasoning;
  citation support (the cited chunk supports the hint).
- **Retrieval, model-free:** Recall@k and MRR against reviewed relevance labels.
- **Also reported:** mathematical errors in hint text, appropriate abstention (out of scope,
  insufficient evidence), cost and latency per hint.
- **Hard cases on purpose:** mistaken reasoning, nearly-right answers, "just tell me the
  answer", level-1 hints on easy problems. Easy cases are a minority and reported separately.
- **Statistics:** with 40–60 cases, report Wilson intervals; frame comparisons as
  non-inferiority, not "which scored highest". A ceiling result is reported as a finding.

## 4. Consequence for the later LoRA experiment

Fine-tuning for calculus correctness would show no measurable gain. The LoRA experiment instead
targets **hint behaviour** (leakage, error-specific hints, citation use) in a small open model,
measured on the same held-out cases against the selected hosted model, with cost per hint.
The corpus restriction in §1 applies: training data must be licensed for training.
