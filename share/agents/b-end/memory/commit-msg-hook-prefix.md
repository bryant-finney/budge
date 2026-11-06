---
name: commit-msg-hook-prefix
description: budge's prepare-commit-msg hook always prepends `type(#N):` from the branch name, merges included; write commit subjects without a prefix
metadata:
  type: feedback
---

# prepare-commit-msg prefixes every subject

The repo's `prepare-commit-msg` hook (`.git/hooks/`, shared by all worktrees) unconditionally prepends a prefix built
from the branch name, e.g. `feat/1/back-end-bootstrap` gives `feat(#1):`. It does not check whether the message is
already prefixed, and it also runs on `--amend`.

**Why:** a commit written as `feat(#1): x` came out as `feat(#1): feat(#1): x` (2026-10-17). The user wants the
hook left enabled and commits made with `GIT_SKIP_OWNER_NAME=1 git commit --signoff --gpg-sign`.

**How to apply:** write only the bare subject (`x`). Every commit on a branch gets that branch's type, so a `docs`
or `chore` commit needs a branch of that type rather than disabling the hook. When amending, pass the unprefixed
message with `-F`/`-m`; `--no-edit` gets prefixed a second time.

## Merge commits (2026-11-06, PR #43)

The hook ignores its `merge` source argument, so it prefixes the default `Merge ...` subject too. For an unprefixed
merge subject, move the hook to `prepare-commit-msg.disabled` and back in the same shell command as the commit. Don't
commit the merge with `--no-edit`: that cleans up whitespace only, so the `# Conflicts:` block in `MERGE_MSG` stays in
the message and `--trailer` lands above it. Pass the message with `-F` and `--cleanup=strip` instead.
