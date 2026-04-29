# Implementation plan

## Phase 1

Build direct Google Slides editing with approval gating.

Capabilities:
- inspect a presentation (Python `inspect` and/or `gws slides presentations get`; see `gws-slides-workflow.md`)
- summarize style patterns from existing slides
- accept user-provided slide content payloads
- create new slides and editable text/image elements
- update existing slides after approval

## Phase 2

Add teacher-comment review.

Capabilities:
- fetch unresolved comments if API support is sufficient
- map comments to slide/page context
- produce an approval-ready revision plan
- apply approved fixes

## Suggested script shape

Create a Python script such as `scripts/robotics_slides.py` with commands like:
- `inspect --presentation <id>`
- `propose --presentation <id> --input <json>`
- `apply --presentation <id> --input <json> --approved`
- `review-comments --presentation <id>`

## Data model suggestion

Use JSON input with fields like:
- `goal`
- `slides` array
- `title`
- `body`
- `bullets`
- `speaker_notes` optional
- `image_paths`
- `target_position`
- `style_hint`
- `source_observations`

## Approval summary format

Return a compact structured summary before applying:
- target presentation
- add vs modify counts
- slide-by-slide summary
- assumptions
- open questions

## Practical note

Style matching will be approximate unless the script actively inspects page elements and clones recurring layouts. For best results, prefer:
- duplicating a representative existing slide when possible
- replacing placeholder text/images in the duplicate
- falling back to newly created layouts only when duplication is not suitable
