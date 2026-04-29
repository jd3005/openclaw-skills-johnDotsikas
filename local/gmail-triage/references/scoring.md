# Gmail Triage Scoring

## Goal
Produce a short, useful digest of recent Gmail messages while minimizing promotional noise.

## Primary signals

### Positive signals
- sender explicitly marked important
- domain explicitly marked important
- keywords related to school, finance, security, deadlines, or direct requests
- Gmail `IMPORTANT` label

### Negative signals
- sender explicitly ignored
- domain explicitly ignored
- promotional/newsletter keywords
- Gmail `CATEGORY_PROMOTIONS` label

## Default categories
- school
- finance
- security
- deadlines
- personal
- newsletter
- promotion

## Preference memory schema

```json
{
  "important_senders": [],
  "ignored_senders": [],
  "important_domains": [],
  "ignored_domains": [],
  "keyword_rules": {
    "important": [],
    "ignore": []
  },
  "category_weights": {
    "school": 3,
    "finance": 3,
    "security": 3,
    "deadlines": 3,
    "personal": 2,
    "newsletter": -2,
    "promotion": -3
  }
}
```

## Ranking buckets
- `important`: high-confidence messages the user should likely read first
- `needs-attention`: probably useful or actionable, but lower confidence
- `low-priority`: ordinary or ambiguous mail
- `promotional`: likely noise, newsletters, or marketing

## Training guidance
Prefer explicit and inspectable learning:
- add senders/domains when the user repeatedly confirms importance or irrelevance
- add keywords when the user emphasizes topics such as `tuition`, `assignment`, or `security alert`
- adjust category weights only when broad ranking behavior needs tuning
