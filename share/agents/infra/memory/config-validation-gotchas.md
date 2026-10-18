---
name: config-validation-gotchas
description: Intl.supportedValuesOf('timeZone') is CLDR-canonical (rejects Asia/Kolkata, UTC); Intl.DateTimeFormat over-accepts; Scheduler rate units; bootstrap.sh run is classifier-blocked
metadata:
  type: project
---

# Stack config validation gotchas

Found in the PR #21 review of `src/infrastructure/config.ts` (#13, 2026-10-18).

- **`Intl.supportedValuesOf('timeZone')` is not the IANA list.** It returns ICU/CLDR canonical
  IDs, which are often the pre-rename links (`Asia/Calcutta`, `Europe/Kiev`), and it omits `UTC`
  and all `Etc/*`. The fix was an explicit supplement (`IANA_ZONES_MISSING_FROM_ICU`), derived from
  the `Z` lines of `/usr/share/zoneinfo/tzdata.zi` minus that list. Regenerate it after a Node/ICU
  bump. A test checks that each entry is accepted by `Intl.DateTimeFormat` and is still missing
  from ICU's list.
- **`new Intl.DateTimeFormat(..., { timeZone })` alone accepts too much.** It matches
  case-insensitively and accepts offsets like `+05:30`. Python `zoneinfo` on Lambda (Linux,
  case-sensitive paths) rejects both. Use exact string membership for anything passed through to
  the back end.
- **Scheduler rate units.** The EventBridge Scheduler docs list only `minutes|hours|days`, while
  EventBridge *rules* require the singular unit for 1. `SCHEDULE_RATE_PATTERN` accepts either
  form for 1 and only the plural above 1. Whether Scheduler accepts `rate(1 hour)` hasn't been
  checked against AWS. Settle it on the first real `pulumi up` in milestone 4.
- **Don't run `bootstrap.sh` with non-help args in a session.** The auto-mode classifier blocks it
  as an IaC apply, even though it's a stub. Prove the exit-2 path by reading the `case`, and run
  only `--help` and shellcheck.

Related: [[pnpm-node-tooling-gotchas]].
