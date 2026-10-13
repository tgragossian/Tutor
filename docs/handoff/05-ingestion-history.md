[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 153–188. Review findings remain unresolved.

### 4.2 Textbook and Exam Ingestion

Most source documents will be PDFs.

We cannot assume that original LaTeX source files or HTML versions are available.

**Preferred extraction service: Mathpix API.**

Investigate:

- Mathpix PDF conversion
- Mathpix Markdown output
- Batch document processing
- Mathematical notation preservation
- API cost and document retention policies

Proposed workflow:

1. Obtain a document with appropriate processing and reuse permissions.
2. Convert PDF to structured mathematical text using Mathpix.
3. Identify definitions, explanations, worked examples, exercises, and solutions.
4. Preserve original source locations.
5. Extract exercises into structured records.
6. Match available answers or solutions to exercises.
7. Validate mathematical extraction and answer correctness.
8. Store validated problem metadata in a database.
9. Index explanatory material for RAG.

Important: Mathpix handles mathematical OCR, not the entire exercise extraction, classification, matching, or correctness-verification process.

Use manual inspection and automated validation where necessary.

Ingestion should run as an offline or batch process, not during every student interaction.

**Do not bulk-download copyrighted materials or assume that publicly accessible PDFs are freely redistributable.** Track source licenses and permitted uses.

<!-- End preserved source. -->
