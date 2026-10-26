# C design 4: own problems (C3)

[Milestone C design](README.md) · Previous: [guard and limits](03-guard-and-limits.md) · Next: [evaluation](05-evaluation-and-acceptance.md)

An option beside the reviewed bank: a student brings a problem from elsewhere, for example a
practice test their teacher handed out.

## Flow

1. **Bring it in.** On a "My problems" page the student types a problem in the math editor or
   uploads a photo or PDF: at most 10 MB and 5 pages; JPEG, PNG, HEIC or PDF.
2. **Read it.** Claude Haiku reads the upload and returns a structured list, one entry per
   problem: statement in LaTeX, guessed type (derivative, limit, integral, other) and the
   problem number on the sheet. Typed problems skip this step.
3. **Release local upload data.** Keep bytes/transcription transient until reading/confirmation
   ends: discard raw bytes when reading ends; expire unconfirmed text on a bounded deadline.
   Clean up on success, failure or cancellation. Do not persist raw files in the app,
   logs or backups. This is not a claim of deletion from provider systems or physical RAM/swap.
4. **Confirm.** Show editable statement AND interpreted task: operation, source expression,
   variable, derivative order and domain. The student confirms, fixes or drops it. Strip names
   and unrelated text. Nothing is solved or graded before confirmation; drafts are not durable.
5. **Solve.** A new bounded typed-task worker attempts supported confirmed problems.
   - Solved, and the answer checker supports that type: **gradable**, with the full practice
     flow (tries, help, leak guard, reveal).
   - Not solved, or an unsupported type: **hints only**, labeled "Answers can't be checked
     for this problem." Help still cites the book; nothing is ever marked correct.

## Rules

- Compute references from the confirmed executable task through allowlisted MathJSON, never
  from an LLM answer. Validate output kind, bounds and domain before creating a gradable item.
  The current grading pool is not a general solver; add explicit solve requests/results.
- Own problems are private to their student (`user_problems`), never mixed into the reviewed
  bank, and excluded from bank statistics and evaluation sets unless separately reviewed.
- Own-problem versions are immutable after attempts. Edits create a new version; deletion
  removes private statements, answers, attempts/help and invalidates pending work. See
  [state/accounting](06-state-and-accounting.md); B's hide-only history operation is insufficient.
- Upload reading counts toward the site-wide spend limit and the 10-per-day upload limit.
- Hints-only responses skip the leak guard (there is no answer to guard against) and are
  logged with that reason, so they are reported separately from guarded help.

## Gradable on day one

Restrict initial admission to explicit first derivatives of one real variable, within the
translator/checker's supported syntax and with provable domain/differentiability metadata.
Confirm the domain; do not silently use all reals for logs, radicals or singular expressions.
Unknown domains, unevaluated derivatives, parameters, implicit/multivariate problems and
unsupported output become hints-only. Limits/integrals remain hints-only until a later checker.
This is a narrower task subset than “every derivative”. Regression fixtures must cover its
boundary; comparing a computed answer with itself does not validate the transcription.

## Integration with practice and help

C3 needs an explicit owned-target contract: bank presentation versus confirmed private problem
ID/version. Never accept a client-supplied answer or make a private problem impersonate a bank ID.
Gradable private tasks use tries/reveal/revision rules through a new content-source adapter;
hints-only tasks have no answer submission, correctness verdict, tries or Reveal action.
Help loads their confirmed text server-side and logs `guard_skipped_no_reference` explicitly.
Use generic concept/question help when no reviewed confusion or misconception entry exists;
do not fabricate bank-topic metadata. Pin these C3 routes/schemas and store invariants in C-P3.

## Upload and privacy contract

- Authenticate/CSRF-check before parsing; use a narrowly scoped intake body cap. B's existing
  request-size bound stays in force elsewhere. Check actual MIME signature, not just extension.
- Bound raw bytes, pages, decoded pixels, extracted problems, encoded provider bytes and tokens.
  Reject malformed/password-protected documents. Decode/convert in a bounded isolated worker.
- HEIC requires conversion to a supported image format; PDF uses the document input path.
  Direct inline bytes avoid persistent provider Files API objects. No fetching user-supplied URLs.
- Verify multipart/proxy buffering and cancellation/crash cleanup; “in memory” cannot be assumed
  from endpoint code alone. Limit parallel decodes and measure them in the C3 host-sizing check.
- Explain hosted processing before upload. Local cleanup does not imply zero provider retention;
  [provider evidence](09-provider-evidence.md) records current public policy and its exceptions.
- C-P3 must pin executable schema, conversion/decode limits, retention/backup behavior and the
  bounded read/solve deadlines before implementation. API reading uses the same durable budget.
