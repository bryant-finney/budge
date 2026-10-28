#!/usr/bin/env python3
"""Copy the shared memory index into each agent's MEMORY.md and check every memory directory.

Exits 1 when it rewrites a file or finds a problem, so pre-commit and CI report the change.
"""

import re
import sys
from pathlib import Path

AGENTS = Path(__file__).resolve().parent
SHARED = AGENTS / "_memory"
INDEX = "MEMORY.md"

BEGIN = "<!-- shared-memory:begin (generated from share/agents/_memory/MEMORY.md; edit that file instead) -->"
END = "<!-- shared-memory:end -->"
BLOCK = re.compile(r"<!-- shared-memory:begin.*?-->.*?<!-- shared-memory:end -->", re.DOTALL)
ENTRY = re.compile(r"^- \[[^\]]+\]\((?P<target>[^)]+)\)")
NAME = re.compile(r"^name:\s*(?P<name>\S+)\s*$", re.MULTILINE)


def shared_entries(errors: list[str]) -> list[str]:
    lines = [line for line in (SHARED / INDEX).read_text().splitlines() if ENTRY.match(line)]
    targets = {m["target"] for line in lines if (m := ENTRY.match(line))}
    notes = {path.name for path in SHARED.glob("*.md")} - {INDEX}
    errors += [f"{SHARED / INDEX}: links missing note {target}" for target in sorted(targets - notes)]
    errors += [f"{SHARED / note}: not listed in {INDEX}" for note in sorted(notes - targets)]
    return [ENTRY.sub(lambda m: m[0].replace(f"({m['target']})", f"(../../_memory/{m['target']})"), line) for line in lines]


def check_unique_names(memory_dirs: list[Path], errors: list[str]) -> None:
    seen: dict[str, Path] = {}
    for directory in memory_dirs:
        for note in sorted(directory.glob("*.md")):
            if note.name == INDEX or not (match := NAME.search(note.read_text())):
                continue
            if (other := seen.setdefault(match["name"], note)) != note:
                errors.append(f"{note}: name {match['name']!r} is also used by {other}")


def main() -> int:
    errors: list[str] = []
    agent_dirs = sorted(AGENTS.glob("*/memory"))
    block = "\n".join([BEGIN, "", "Shared with every agent; these notes live in `share/agents/_memory/`.", "", *shared_entries(errors), "", END])
    check_unique_names([SHARED, *agent_dirs], errors)

    changed = False
    for index in (directory / INDEX for directory in agent_dirs):
        text = index.read_text()
        if not BLOCK.search(text):
            errors.append(f"{index}: missing the shared-memory begin/end markers")
            continue
        if (updated := BLOCK.sub(lambda _: block, text, count=1)) != text:
            index.write_text(updated)
            print(f"updated {index}")
            changed = True

    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors or changed else 0


if __name__ == "__main__":
    sys.exit(main())
