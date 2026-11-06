"""Fixed student-facing help messages (US spelling)."""

UNAVAILABLE = "Help is unavailable right now."
LIMITED = "You've reached the help limit for now."
ABSTAIN = "I can't answer that from the textbook."
NUDGE = "Here's a nudge without the answer: re-read {section}."
# Spec D6a: one hint per attempt; a repeat Hint click gets one of these, with no model call.
TRY_FIRST = (
    "You've already had a hint for getting started. Try an answer, even a partial one, and I "
    "can help with what you wrote. If a step is unclear, use Explain this."
)
TRY_AGAIN = (
    "You've already had a hint for this answer. Try again with it in mind, and I can help with "
    "what you change. If the method is unclear, use Explain this."
)

# Error messages for rejected help requests (the web layer shows them as-is).
ID_REUSED = "This help request ID was already used for a different request."
UNKNOWN_HELP_TYPE = "Unknown help type."
CHOOSE_CONFUSION = "Choose what you're confused about."
CONFUSION_ONLY_EXPLAIN = "Only an explanation request takes a confusion."
PROBLEM_CHANGED = "This problem changed. Reload it."
HELP_CLOSED = "Help isn't available for this problem now."
FEEDBACK_NEEDS_WRONG = "Feedback needs an incorrect answer to look at."
PROBLEM_NOT_FOUND = "Problem not found."
USER_NOT_FOUND = "User not found."
NOT_YOUR_PROBLEM = "This is not your problem."
DATABASE_BUSY = "The database is busy. Please try again."
