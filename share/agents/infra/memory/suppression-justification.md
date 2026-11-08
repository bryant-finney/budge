---
name: suppression-justification
description: Every inline linter suppression records its justification; yamllint directives reject trailing text, so the reason goes on the line above
metadata:
  type: feedback
---

# Justify every inline suppression

Every inline suppression comment records why it's there, for any linter.

**Why:** On PR #34 (2026-11-03) the owner asked for "a justification after the inline suppression
comment (in this case, because the line break makes it more difficult to read)" on the two
`line-length` exceptions in `compose.yaml`, and asked for the rule to be remembered.

**How to apply:**

- Put the reason after the directive on the same line when the linter allows it. Check first, by
  confirming the same line fails without the directive and passes with the justified form. A linter
  that rejects the text may report the original problem, or may ignore the directive silently.

- yamllint can't take it on the same line. Version 1.38.0 matches
  `^# yamllint disable-line( rule:\S+)*\s*$`, so any trailing text stops the suppression, and the
  directive only covers the next line, so nothing can sit between it and its target. Use this form:

  ```yaml
  # a line break makes the image URI harder to read
  # yamllint disable-line rule:line-length
  image: "..."
  ```

- This is a one-line exception to [[comments-sparingly]]: the reason is what the code can't say.
