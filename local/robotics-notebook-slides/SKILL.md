---
name: robotics-notebook-slides
description: Create and update editable Google Slides for a robotics engineering notebook, especially VEX-style classroom documentation decks. Use when the user wants slide content generated from photos, build notes, or rough descriptions; when new slides must match the style of an existing Google Slides deck; when teacher comments on slides need to be reviewed and turned into proposed edits for approval; when operating the Slides API via the gws CLI (see openclaw skill gws-slides); or when a workflow needs to draft, revise, and keep a robotics notebook presentation compliant and organized.
---

# Robotics Notebook Slides

Create or revise a robotics notebook deck in Google Slides, preserve editability, match the existing deck style, and require user approval before applying changes.

## Companion skill: `gws-slides` (Google Slides API via CLI)

When **`gws`** is installed (`npm install -g @googleworkspace/cli`) and authenticated with **`gws auth login`**, use the **Clawhub / Workspace skill `gws-slides`** for Slides API operations: `gws slides presentations get`, `gws schema slides.presentations.batchUpdate`, and related commands. Full command patterns and token-saving tradeoffs live in `references/gws-slides-workflow.md`.

Use the **same Google Cloud OAuth project** you already configured for this workspace (Desktop client JSON + tokens under `.secrets/` as in `references/google-api-setup.md`); `gws` stores its own auth bundle but should be pointed at that **same** client/project during `gws auth setup`.

## VEX / engineering emphasis

Notebook slides should read like **design evidence**, not hype. Before drafting, skim `references/vex-engineering-notebook.md` and align content with: stated goal/constraints, design options and selection rationale, build notes, **test method + results** (never fabricated), iterations, and next steps. Prefer figures with captions and tight bullets so judges can scan quickly.

## Core workflow

1. Collect the minimum inputs:
   - Google Slides presentation ID or URL
   - goal for this round of edits
   - photos/screenshots or build notes
   - any teacher comments to address, if the task is comment-driven
2. Inspect the existing deck before drafting:
   - identify recurring layouts, title patterns, font sizes, color choices, image placement, and caption style
   - reuse the document's existing visual language instead of inventing a new one
3. Convert the user's rough description into notebook-ready content:
   - describe objective, process, decisions, tests, issues, iterations, and next steps
   - prefer concrete engineering detail over generic filler
   - keep wording school-appropriate and easy to edit later
4. Prepare a proposed change summary for approval:
   - which slides will be added or changed
   - what each slide will contain
   - which teacher comments will be addressed
5. Only after approval, apply the edits in Google Slides directly.
6. Report what changed and note anything still needing manual review.

## Notebook-content rules

Write like an engineering notebook, not like marketing copy.

Include useful content such as:
- date or work session context when available
- design goal or problem being solved
- build steps taken
- test results and observations
- problems encountered
- reasoning behind design decisions
- revisions and next steps

Avoid:
- fake precision
- invented measurements or results
- vague praise language
- long paragraphs when bullets or short captions work better

When the user provides limited detail, draft conservatively and clearly mark assumptions in the approval summary.

## Style matching rules

Before creating slides, inspect several existing slides in the target deck and infer:
- title format
- body text density
- whether slides use bullets, short paragraphs, tables, or captions
- image crop/aspect patterns
- use of bold, color accents, and section dividers
- whether dates, team roles, or reflection boxes recur

Match the deck's style closely unless the user asks for a redesign.

Prefer editable native slide elements:
- text boxes
- shapes
- lines
- tables
- inserted images with captions

Do not flatten text into images.

## Approval behavior

Always ask for approval before making Google Slides changes.

Approval summary should include:
- presentation being edited
- slide numbers to add or modify
- concise description of each change
- any assumptions or uncertain interpretations
- any teacher comments being addressed

If a teacher comment is ambiguous, ask one targeted follow-up before editing.

## Teacher comment handling

Treat teacher comments as revision requests, not as instructions to silently overwrite context.

Workflow:
1. Read unresolved or new comments.
2. Group them by slide and required action.
3. Draft the proposed fixes.
4. Ask the user for approval.
5. Apply the changes.
6. Mark handled items clearly in the final summary.

If a comment conflicts with prior slide content or seems incorrect, flag it instead of forcing a bad edit.

## Google integration guidance

Prefer this split:

- **Model (agent)**: turn photos/notes into structured slide plans, captions, and approval summaries; map teacher comments to proposed edits.
- **Deterministic tools**: **inspect and apply** via **`gws`** (see `references/gws-slides-workflow.md`) and/or Python under `scripts/` using OAuth files documented in `references/google-api-setup.md`.

Use Google APIs or a local automation script to:
- read presentation structure (`gws slides presentations get` or `scripts/robotics_slides.py inspect`)
- inspect slide/page elements for style patterns
- create slides and page elements (`presentations.batchUpdate` or existing apply scripts)
- update text and images
- read comments from the related Drive file when available through the chosen integration

Keep secrets out of the skill directory. Store credentials outside the skill and load them from a local secret source.

Read `references/google-api-setup.md` when setting up API access (OAuth JSON + optional `gws` CLI).
Read `references/gws-slides-workflow.md` when driving Slides through **`gws`**.
Read `references/implementation-plan.md` when building or extending the automation.

## Recommended implementation shape

Use a local script that accepts structured input such as:
- presentation ID
- mode: inspect, propose, apply, review-comments
- slide content payload
- optional image paths/URLs
- approval flag

Preferred capabilities:
1. Inspect deck style and summarize reusable patterns.
2. Generate a proposed slide plan from user notes and images.
3. Apply approved edits to Google Slides.
4. Read teacher comments and convert them into an approval-ready revision plan.

## Safety and quality

Do not fabricate notebook evidence.
Do not claim a test happened unless the user provided it.
Do not auto-apply comment-driven changes without approval.
Do not store Google credentials, refresh tokens, or cookies in the skill folder.

Before applying edits, verify:
- the target presentation ID is correct
- the slide plan matches the user's request
- images exist and are the intended ones
- changes remain editable in Google Slides

## Expected user prompts

- "Make slides for today’s robotics work from these images and notes."
- "Match the style of my existing notebook and add three slides about the pull-toy mechanism."
- "Check teacher comments on this deck and propose fixes for approval."
- "Apply the approved revisions to my robotics Google Slides notebook."
- "Use these build photos and make notebook slides that follow the same format as the existing deck."
