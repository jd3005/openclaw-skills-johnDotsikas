# Google API setup

Use this checklist to set up direct Google Slides editing.

## What to enable

In Google Cloud Console, create a project for this automation and enable:
- Google Slides API
- Google Drive API

Drive API is useful for file lookup, permissions, and comment-related workflows around the presentation file.

## Recommended auth choice

For a personal school workflow, start with **Desktop app OAuth client**.

Why:
- easiest for one real user approving access in a browser
- works well for scripts run locally
- supports editable access to the user’s own Slides files

Avoid service accounts for the first version unless the deck is intentionally shared with that service account and the workflow is already understood.

## OAuth steps

1. Go to Google Cloud Console.
2. Create or select a project.
3. Enable Google Slides API.
4. Enable Google Drive API.
5. Open **APIs & Services -> OAuth consent screen**.
6. Configure the app:
   - user type: External is usually simplest
   - app name: something like `Atlas Robotics Slides`
   - support email: the Gmail you want to use for this workflow
   - add your own Google account as a test user if Google requires it
7. Open **Credentials**.
8. Create credentials -> **OAuth client ID**.
9. Application type -> **Desktop app**.
10. Download the client JSON file.

## Scopes to request

Start narrow but practical. Typical scopes:
- `https://www.googleapis.com/auth/presentations`
- `https://www.googleapis.com/auth/drive`

If later needed, narrow Drive usage once the exact comment/file workflow is stable.

## Local secret storage

Store the downloaded OAuth client JSON outside the skill folder, for example in:
- `/home/john/.openclaw/workspace/.secrets/google-slides-oauth-client.json`

Store generated tokens outside the skill folder too, for example:
- `/home/john/.openclaw/workspace/.secrets/google-slides-token.json`

Do not paste the JSON into chat.
Do not store tokens in `SKILL.md`, `MEMORY.md`, or other notes.

## First authorization run

The local script should:
1. load the OAuth client JSON
2. open a browser window for Google login/consent
3. ask the user to sign in with the Google account that owns or can edit the notebook deck
4. save the refresh/access token locally for future runs

## Presentation access requirements

The target Google Slides deck must be editable by the authorized Google account.

For each deck used by this automation:
- confirm the Google account can edit it manually
- keep the deck URL or presentation ID available

## Comment handling note

Google Slides comments may be exposed through Drive-related APIs or through alternate document metadata workflows depending on the exact setup. Validate comment retrieval early. If API comment access is incomplete, use a hybrid approach:
- direct Slides API for slide edits
- Drive/file metadata or browser automation for comment review

## Minimum test after setup

After auth is working, verify the script can:
1. read the presentation title
2. list slide IDs
3. create one test slide
4. insert a text box
5. update text
6. optionally insert an image
7. read enough file metadata to support comment workflow planning

## Optional: same Google Cloud project via `gws` (pairs with `gws-slides`)

The OpenClaw skill **`gws-slides`** uses the **`gws`** binary from [`@googleworkspace/cli`](https://www.npmjs.com/package/@googleworkspace/cli). It does **not** introduce a second type of secret inside this repo if you point it at the **same Google Cloud project** where Slides/Drive APIs are enabled and where your Desktop OAuth client was created.

1. Install: `npm install -g @googleworkspace/cli` (confirm `gws --version`).
2. Run **`gws auth setup`**, then **`gws auth login`**, using the same GCP project and Google account that own the notebook deck.
3. Sanity check (no specific deck ID required for the binary itself): `gws slides --help` prints subcommands; `gws schema slides.presentations.get` prints the API parameter schema; `gws slides presentations get --params '{"presentationId":"<id>"}' --dry-run` shows the resolved HTTP request without calling Google.

Prefer **`gws`** for schema inspection, `--dry-run` validation, and predictable JSON responses; keep **`scripts/robotics_slides.py` `inspect`** when you want a compact summary without learning `gws` flags. Details: `gws-slides-workflow.md` in this skill.
