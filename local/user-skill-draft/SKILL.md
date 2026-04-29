---
name: user-skill-draft
description: Draft skill — replace this description with concrete capabilities and trigger phrases (what the skill does, when the agent should load it). Use when the user’s request matches those triggers after you customize this file.
---

# User skill draft

Customize this file, then rename the folder and update `name` / `description` in the frontmatter to match.

## Workflow

1. Read any inputs the user provides (files, links, constraints).
2. Apply the domain rules in [references/conventions.md](references/conventions.md) once you move real content there (optional).
3. Produce output in the format below unless the user specifies otherwise.

## Output format

- **Summary** — one short paragraph
- **Details** — bullets or numbered steps
- **Next actions** — only if something is still blocked

## Boundaries

- Stay inside the user’s stated scope.
- Do not assume secrets or credentials; ask or use configured tools only.

## Optional resources

- `scripts/` — put deterministic helpers here and run them with paths resolved from this skill directory
- `references/` — long specs; link from this file so the model loads them only when needed
