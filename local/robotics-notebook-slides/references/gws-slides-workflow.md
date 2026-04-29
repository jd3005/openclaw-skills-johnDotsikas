# Google Slides via `gws` (pairs with `gws-slides` skill)

Use this workflow when the **`gws`** binary is available (`npm install -g @googleworkspace/cli`). It talks to the **same Google Cloud project and Slides/Drive APIs** you enabled for the Desktop OAuth JSON under `.secrets/`; authenticate once with **`gws auth setup`** then **`gws auth login`** so the CLI can call the APIs. You are not copying a second “API key” into the skill—reuse the **same GCP OAuth client project** you already set up for the Python helper.

## Why use `gws` here

- **Deterministic, script-shaped calls**: inspect schemas (`gws schema …`), `--dry-run` to validate URLs/params, structured JSON out—good for automation and fewer model-authored API mistakes.
- **Atomic updates**: `presentations.batchUpdate` applies validated requests together (see skill `gws-slides`).

## Prerequisites

- Install: `npm install -g @googleworkspace/cli` (check `gws --version`).
- Auth: `gws auth setup` then `gws auth login` (same Google account that can edit the notebook deck).

## Commands you will use often

Discovery (no API call, or dry-run only):

```bash
gws slides --help
gws schema slides.presentations.get
gws schema slides.presentations.batchUpdate
```

Fetch a deck (after login)—replace `PRESENTATION_ID` with the ID from the Slides URL:

```bash
gws slides presentations get --params '{"presentationId":"PRESENTATION_ID"}' --format json
```

Validate the HTTP shape without calling Google:

```bash
gws slides presentations get --params '{"presentationId":"PRESENTATION_ID"}' --dry-run
```

Build `batchUpdate` requests using schema output and the Slides API request format; prefer `--dry-run` first when experimenting.

## When to use Python scripts instead

- **Duplicating layout-heavy slides** or **bulk image placement**: a Python script using `googleapiclient` may be clearer than hand-authored batch JSON—run scripts from this skill’s `scripts/` with the same OAuth token files as documented in `google-api-setup.md`.

## When to use the model

- Turning photos and rough notes into **notebook wording**, **structured slide plans**, and **approval summaries**—then apply changes deterministically (`gws` or Python) after approval.
