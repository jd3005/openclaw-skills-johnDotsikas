---
name: gmail-triage
description: Read-only Gmail inbox triage via OAuth with local preference learning. Use when the user wants to scan Gmail for important messages, identify urgent or school/account/security-related email, suppress promotional noise, summarize recent inbox activity, or update learned sender/domain/keyword importance rules from feedback such as "this sender matters" or "ignore emails like this".
---

# Gmail Triage

Use this skill to check a Gmail inbox, rank recent messages by importance, and improve ranking over time using local preferences.

## Quick workflow

1. Ensure Gmail OAuth credentials are available before attempting API access.
2. Load or initialize local preference memory.
3. Fetch recent inbox messages from Gmail.
4. Score each message using sender, domain, keyword, and heuristic category signals.
5. Return a compact digest grouped by importance.
6. When the user gives feedback, update the preference memory rather than relying on unstored conversational memory.

## Output format

Keep replies compact and easy to skim.

Use these sections when relevant:
- **Important**
- **Needs attention**
- **Low priority**
- **Promotional / likely noise**

For each listed email, include:
- sender
- subject
- short reason it was ranked that way
- timestamp if useful for urgency

Avoid dumping too many messages at once. Prefer the top few items per section.

## Triage guidance

Boost messages when they match signals like:
- school, professor, registrar, financial aid, billing, assignment, deadline
- account/security alerts, password resets, sign-in notices, verification messages
- direct personal communication or explicit requests for action
- payment failures, invoices, due dates, missing documents, urgent wording
- senders or domains marked important in local preferences

Down-rank messages when they match signals like:
- promotions, discounts, coupons, shopping campaigns
- newsletters, mailing lists, routine announcements
- no-reply bulk notifications with low user value
- senders or domains marked ignored in local preferences

When uncertain, place a message in **Needs attention** instead of hiding it.

## Learning rules

Use explicit user feedback to update local preference memory.

Supported preference types:
- important senders
- ignored senders
- important domains
- ignored domains
- important keywords
- ignored keywords
- category weights

Examples of feedback to translate into stored rules:
- "always treat this sender as important"
- "ignore this sender"
- "emails about tuition are important"
- "messages like this are low priority"
- "professor emails matter"

Prefer inspectable local rules over opaque learning.

## Safety and scope

Keep version 1 read-only.
Do not delete, archive, label, reply to, or send email unless the skill is explicitly expanded later.
Store OAuth tokens and learned preferences locally and treat them as sensitive.

## Resources

### scripts/
- `gmail_triage.py`: OAuth setup, inbox scan, scoring, and preference training.

### references/
- `scoring.md`: scoring model and preference schema details.
