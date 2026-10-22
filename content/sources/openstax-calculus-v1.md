# Source: OpenStax Calculus Volume 1

[Content index](../README.md)

## Book

- **Title:** Calculus Volume 1
- **Authors:** Gilbert Strang and Edwin "Jed" Herman
- **Publisher:** OpenStax, Houston, Texas
- **Edition:** the edition published 30 March 2016, per the book's citation page (web version read on 2026-10-13)
- **Base URL:** https://openstax.org/books/calculus-volume-1/pages/1-introduction
- **Answer key used for checks:** https://openstax.org/books/calculus-volume-1/pages/chapter-3

Sections used in milestone A:

| Topic id | Section | URL |
|---|---|---|
| `derivatives.basic_rules` | 3.3 Differentiation Rules | https://openstax.org/books/calculus-volume-1/pages/3-3-differentiation-rules |
| `derivatives.trig` | 3.5 Derivatives of Trigonometric Functions | https://openstax.org/books/calculus-volume-1/pages/3-5-derivatives-of-trigonometric-functions |
| `derivatives.chain_rule` | 3.6 The Chain Rule | https://openstax.org/books/calculus-volume-1/pages/3-6-the-chain-rule |

## Licence

- **`CC BY-NC-SA 4.0`**: [Creative Commons Attribution-NonCommercial-ShareAlike 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
- This is the string every problem's `source.license` carries; the schema accepts no other.
- The OpenStax and Rice University names, logos and book covers are trademarks outside the licence. Do not use them as branding.
- The "Citation/Attribution" box at the bottom of each book page (e.g. [1 Introduction](https://openstax.org/books/calculus-volume-1/pages/1-introduction), checked 2026-10-22) says it "may not be used in the training of large language models or otherwise be ingested into large language models or generative AI offerings without OpenStax's prior written permission". Check this before any pipeline that feeds the book's text to an LLM.
- **Decision (Thomas, 2026-10-21):** transcribing exercises with an assistant is acceptable. The licence page of the edition used (©2018 Rice University, CC BY-NC-SA 4.0) does not mention LLMs, and the attribution line it requires is shown on every page. Revisit before milestone C feeds book text into RAG.
- **Decision (Thomas, 2026-10-22):** milestone C may send book passages to a hosted LLM for hints, relying on the CC licence; the sentence above is a recorded known risk. Conditions: [decision 0004](../../docs/decisions/0004-rag-source-models-and-evaluation.md).

## Attribution shown in the UI

> Problems from *Calculus Volume 1* by Gilbert Strang and Edwin "Jed" Herman, OpenStax, licensed under CC BY-NC-SA 4.0. Download for free at https://openstax.org/details/books/calculus-volume-1.

Each problem view also links its own section URL (`source.url`) and names the exercise number when there is one.

## Adapted items

- Problems with `source.adapted: true` (and `exercise: null`) are written by the author, modelled on the cited section.
- They are derivative works of the original and are distributed under the same licence, `CC BY-NC-SA 4.0`.
- Transcribed exercises that grade only one part of a multi-part exercise say so in `review.notes`.
