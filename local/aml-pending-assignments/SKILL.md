---
name: aml-pending-assignments
description: Logs into Headrick7 Moodle to check pending AML assignments and automate text submission by assignment name or specific URL. Use when the user asks to check AML pending work, open an AML assignment, or submit a prepared assignment response. Supports AI-powered response generation using OpenClaw agent and chat trigger phrases like "do aml assignment:" or "submit aml assignment:".
---

# AML Pending Assignments

Use this skill to check pending AML assignments and reply to course discussion posts from:
- `https://headrick7.com/login/index.php`

## Required Credentials

Set credentials in environment variables before running:

```bash
export AML_PORTAL_USER="atlasbot300@gmail.com"
export AML_PORTAL_PASS="atlasBot2026"
```

Optional:

```bash
# Defaults to AML
export AML_CLASS_KEYWORD="AML"

# Custom instructions for AI response generation
export AML_RESPONSE_INSTRUCTIONS="Write a 500-word essay analyzing the impact of technology on education"
```

Install dependencies once:

```bash
python3 -m pip install -r "skills/local/aml-pending-assignments/requirements.txt"
```

## Run

From repo root:

```bash
python3 "skills/local/aml-pending-assignments/scripts/check_aml_pending.py"
```

Trigger parser for chat phrases:

```bash
python3 "skills/local/aml-pending-assignments/scripts/parse_aml_trigger.py" 'do aml assignment: "Discussion 4" with "My exact response"'
```

## What This Script Does

1. Signs into Moodle using the login form token.
2. Pulls dashboard/course pages.
3. Finds AML-related items with pending-style keywords (`due`, `missing`, `overdue`, `todo`, `not submitted`).
4. Prints a concise report.

## Output Rules

- If pending assignments are found, list title/snippet/link.
- If AML content is found but no pending indicators exist, report that explicitly.
- If login fails, stop and print a clear error.

## Submit a Response to an Assignment or Reply to a Post

This supports text-entry assignments and text discussion replies (not file-upload-only forms).

You can target the assignment by name or by direct URL.

Set these variables:

```bash
export AML_PORTAL_USER="atlasbot300@gmail.com"
export AML_PORTAL_PASS="atlasBot2026"
export AML_ASSIGNMENT_NAME="Discussion 4"
export AML_AUTO_GENERATE="true"
```

Or use a direct URL fallback:

```bash
export AML_ASSIGNMENT_URL="https://headrick7.com/mod/assign/view.php?id=12345"
```

Optional manual text mode:

```bash
export AML_AUTO_GENERATE="false"
export AML_RESPONSE_TEXT="Your full assignment response text here"
```

Default execution behavior unless explicitly overridden:

```bash
export AML_HEADLESS="false"
export AML_DRY_RUN="true"
```

This means visible browser, dry run, and browser left open afterward.

Recommended first run (no submission - dry run mode):

```bash
export AML_DRY_RUN="true"
python3 "skills/local/aml-pending-assignments/scripts/submit_aml_assignment.py"
```

This will:
1. Analyze the assignment prompt from the page
2. Generate an AI response using your OpenClaw agent (OAuth configured)
3. Fill the response into the text field
4. Show you the result WITHOUT submitting (safe preview)

When auto-submission fails, you'll see:
- The extracted assignment prompt
- The generated AI response
- Browser window stays open for manual submission

Real submit with all output:

```bash
export AML_DRY_RUN="false"
python3 "skills/local/aml-pending-assignments/scripts/submit_aml_assignment.py"
```

If Playwright browser binaries are missing, install once:

```bash
python3 -m playwright install chromium
```

## Chat Trigger Phrases

Use these phrases from chat to invoke the skill behavior:

### Assignments
- `do aml assignment: <assignment name>`
- `do aml assignment live: <assignment name>`
- `dry run aml assignment: <assignment name>`
- `submit aml assignment: <assignment name>`
- `do aml assignment: "<assignment name>" with "<text i want submitted>"`
- `submit aml assignment: "<assignment name>" with "<text i want submitted>"`

### Discussion replies
- `reply to <person name> post <description of post content>`
- `reply to <person name> post <description of post content> with "<desired post content>"`

Behavior rules:
- Default unless specified otherwise: visible browser, dry run, leave browser open afterward.
- `live` means the same visible-browser dry-run behavior.
- `submit aml assignment:` performs a real submission using hidden browser unless later overridden.
- If `with "..."` is present, use that exact text and skip auto-generation.
- For reply flows, find the target post by person name plus post description, then open the reply editor and populate the response.
- If exactly one confident match exists, proceed automatically.
- If multiple plausible matches exist or confidence is low, stop and ask the user.
- Use `scripts/parse_aml_trigger.py` to convert a raw chat phrase into structured values before invoking `submit_aml_assignment.py`.

## AI Response Generation

When `AML_AUTO_GENERATE=true`:
- The script extracts the assignment title and prompt from the Moodle page
- Analyzes keywords to determine the response type (reflection, analysis, essay, etc.)
- Generates a contextually appropriate response
- Falls back to template response if OpenClaw is unavailable

### Custom Response Instructions

For more control over the AI response, set:

```bash
export AML_RESPONSE_INSTRUCTIONS="Write a detailed analysis comparing traditional vs online learning methods"
```

This overrides the automatic prompt analysis and generates a response based on your specific instructions.

## Reply Mode Variables

For discussion replies, use:

```bash
export AML_TARGET_MODE="reply"
export AML_POST_AUTHOR="Jane Doe"
export AML_POST_DESCRIPTION="the post about online learning being better than in-person"
```

Then run `submit_aml_assignment.py` with either auto-generation or manual `AML_RESPONSE_TEXT`.

### Assignment Types Detected

The script automatically detects different assignment types based on keywords:

- **Persuasive/Argumentative**: "argue", "position", "controversial", "opinion", "stance" → Generates passionate arguments on trivial topics
- **Discussion/Analysis**: "discuss", "explain", "describe" → Structured academic responses  
- **Comparative**: "compare", "contrast", "difference" → Side-by-side analysis
- **Evaluative**: "evaluate", "assess", "analyze" → Strengths/weaknesses analysis
- **Problem-Solving**: "problem", "solve", "solution" → Step-by-step solutions

### Debugging Output

The script shows detailed debugging information:
- Assignment title and extracted prompt
- Which HTML selectors found content on the page
- Detected response type based on keywords
- Generated response length
- Full response text when auto-submission fails
