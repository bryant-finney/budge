---
name: comments-sparingly
description: Use comments sparingly in code and CI; make names, steps and structure explain themselves instead of long explanatory comments
metadata:
  type: feedback
---

# Comments sparingly

Be judicious with comments. A comment is not a substitute for clean, readable code, and CI
workflows count as code.

**Why:** On PR #32 (2026-10-28) the user asked for this to be remembered after the `ci-ok` job
went in with a seven-line comment block and a header comment that repeated what the YAML showed
([[required-checks-aggregator]]).

**How to apply:**

- Before writing a comment, see whether a clearer job or step name, a split step, or better
  structure says the same thing.
- Keep a comment only for what the code can't say: an external fact (for example, GitHub counts a
  skipped required check as passing), a non-obvious constraint, or a pointer to where something
  is enforced. Keep it to one line where you can.
- Put the rationale in the commit message, PR body or `rules.md` "Why" notes, not in the file.
