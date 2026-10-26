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
3. **Delete the upload.** The file is deleted immediately after reading and never stored.
   Teacher handouts can carry names; only confirmed problem text is kept.
4. **Confirm.** Each problem is shown in an editable math field. The student confirms, fixes
   or drops it. Nothing is solved or graded before confirmation.
5. **Solve.** SymPy attempts each confirmed problem in the sandboxed pool with a timeout.
   - Solved, and the answer checker supports that type: **gradable**, with the full practice
     flow (tries, help, leak guard, reveal).
   - Not solved, or an unsupported type: **hints only**, labeled "Answers can't be checked
     for this problem." Help still cites the book; nothing is ever marked correct.

## Rules

- The reference answer counts only because SymPy computed it from the confirmed statement.
  Claude's reading is never treated as an answer.
- Own problems are private to their student (`user_problems`), never mixed into the reviewed
  bank, and excluded from bank statistics and evaluation sets unless separately reviewed.
- Students can delete own problems; "Clear history" removes them too.
- Upload reading counts toward the site-wide spend limit and the 10-per-day upload limit.
- Hints-only responses skip the leak guard (there is no answer to guard against) and are
  logged with that reason, so they are reported separately from guarded help.

## Gradable on day one

Derivatives only, because that is what the answer checker proves today. Limits, integrals and
other types become gradable as the checker expands in the later all-of-Calc-1 bank project;
until then they are hints-only but usable.

## Open details for the implementation plan

- How "differentiate f" and similar statements map to a SymPy task (a small typed task schema
  returned by the reader and edited in the confirm step).
- HEIC and multi-page PDF handling on the server without storing files (in-memory only).
- Upload size and type checks before any API call.
