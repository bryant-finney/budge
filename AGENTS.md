# Codex project guidance

Use the shared role instructions and memory for the layer being changed, even when working without
a subagent. Paths below are relative to the repository root.

| Agent   | Scope                                                 | Role instructions                   | Memory index                                  |
| ------- | ----------------------------------------------------- | ----------------------------------- | --------------------------------------------- |
| `b-end` | `src/back-end/`, Python dependencies and tests        | [Role](share/agents/b-end/AGENT.md) | [Memory](share/agents/b-end/memory/MEMORY.md) |
| `f-end` | `src/front-end/`, TypeScript, UI and UX               | [Role](share/agents/f-end/AGENT.md) | [Memory](share/agents/f-end/memory/MEMORY.md) |
| `infra` | `src/infrastructure/`, workflows, local stack and AWS | [Role](share/agents/infra/AGENT.md) | [Memory](share/agents/infra/memory/MEMORY.md) |

Read the applicable role and memory index before starting work, then consult relevant linked notes.
Follow the shared role's memory guidance subject to higher-priority session instructions. Keep shared
knowledge in `share/agents/<name>/memory/`; the `.codex/agent-memory/` links point to those same files.

When delegating, use the matching custom agent in `.codex/agents/`, give it explicit file ownership,
and tell it to preserve other agents' edits. Coordinate API and infrastructure changes across layers.

Codex discovers repository skills in `.agents/skills/`. For GitHub rulesets and merge settings, use
[apply-repo-rules](.agents/skills/apply-repo-rules/SKILL.md). Claude's `allowed-tools` field does not
grant permissions in Codex; follow the session's approval policy and the skill's explicit requirements.
The front-end role uses `dataviz` when the session provides it; otherwise follow its shared chart and
accessibility guidance.

`.codex/config.toml` enables multi-agent tools and native Codex memory generation and recall. Native
Codex memories remain managed by Codex separately from the shared role memory files. Start a new Codex
session after changing this setup so agent and skill discovery refreshes. Project config requires a
trusted checkout, as described in the [Codex configuration docs](https://learn.chatgpt.com/docs/config-file/config-basics).

Run relevant checks and `pre-commit run --files <changed files>` before reporting completion. Use the
`gh:commit` skill whenever creating commits.
