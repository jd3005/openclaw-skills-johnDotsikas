#!/usr/bin/env python3
"""Gmail triage helper.

Version 1 goals:
- initialize local preference memory
- support OAuth credential/token paths
- fetch recent Gmail messages when dependencies and credentials are available
- score messages using simple rules
- support preference updates from command-line training flags

This script is intentionally conservative: read-only Gmail access and local JSON state.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


DEFAULT_PREFS = {
    "important_senders": [],
    "ignored_senders": [],
    "important_domains": [],
    "ignored_domains": [],
    "keyword_rules": {
        "important": [
            "assignment",
            "deadline",
            "due",
            "financial aid",
            "tuition",
            "bill",
            "payment",
            "security alert",
            "sign-in",
            "verify",
            "professor",
            "registrar",
            "canvas",
        ],
        "ignore": [
            "sale",
            "discount",
            "coupon",
            "newsletter",
            "unsubscribe",
            "limited time",
            "deal",
        ],
    },
    "category_weights": {
        "school": 3,
        "finance": 3,
        "security": 3,
        "deadlines": 3,
        "personal": 2,
        "newsletter": -2,
        "promotion": -3,
    },
}

CATEGORY_KEYWORDS = {
    "school": ["class", "course", "professor", "assignment", "canvas", "registrar", "student", "campus"],
    "finance": ["bill", "payment", "invoice", "tuition", "refund", "financial aid", "balance"],
    "security": ["security", "alert", "sign-in", "password", "verify", "verification", "login"],
    "deadlines": ["deadline", "due", "required", "expires", "urgent", "action required"],
    "newsletter": ["newsletter", "weekly update", "digest", "subscription"],
    "promotion": ["sale", "discount", "coupon", "deal", "shop", "offer"],
}


@dataclass
class MessageSummary:
    message_id: str
    thread_id: str
    sender: str
    subject: str
    snippet: str
    internal_ts: int | None
    labels: list[str]
    score: int
    categories: list[str]
    reasons: list[str]
    bucket: str


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")
        return json.loads(json.dumps(default))
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def extract_email_address(sender: str) -> tuple[str, str]:
    match = re.search(r"<([^>]+)>", sender)
    email = (match.group(1) if match else sender).strip().lower()
    domain = email.split("@", 1)[1] if "@" in email else ""
    return email, domain


def decode_header_value(payload_headers: list[dict[str, str]], name: str) -> str:
    for header in payload_headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def categorize(text: str) -> list[str]:
    text = text.lower()
    categories = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)
    if not categories:
        categories.append("personal")
    return categories


def score_message(msg: dict[str, Any], prefs: dict[str, Any]) -> MessageSummary:
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    sender = decode_header_value(headers, "From") or "Unknown sender"
    subject = decode_header_value(headers, "Subject") or "(no subject)"
    snippet = msg.get("snippet", "")
    labels = msg.get("labelIds", [])
    internal_ts = int(msg["internalDate"]) if msg.get("internalDate") else None

    sender_email, sender_domain = extract_email_address(sender)
    combined = " ".join([sender, subject, snippet]).lower()
    categories = categorize(combined)

    score = 0
    reasons: list[str] = []

    if sender_email in prefs.get("important_senders", []):
        score += 5
        reasons.append("important sender")
    if sender_email in prefs.get("ignored_senders", []):
        score -= 6
        reasons.append("ignored sender")
    if sender_domain and sender_domain in prefs.get("important_domains", []):
        score += 4
        reasons.append("important domain")
    if sender_domain and sender_domain in prefs.get("ignored_domains", []):
        score -= 5
        reasons.append("ignored domain")

    keyword_rules = prefs.get("keyword_rules", {})
    for keyword in keyword_rules.get("important", []):
        if keyword.lower() in combined:
            score += 2
            reasons.append(f'matched important keyword "{keyword}"')
    for keyword in keyword_rules.get("ignore", []):
        if keyword.lower() in combined:
            score -= 2
            reasons.append(f'matched ignore keyword "{keyword}"')

    category_weights = prefs.get("category_weights", {})
    for category in categories:
        score += int(category_weights.get(category, 0))
    if categories:
        reasons.append("categories: " + ", ".join(categories))

    if "IMPORTANT" in labels:
        score += 2
        reasons.append("gmail marked important")
    if "CATEGORY_PROMOTIONS" in labels:
        score -= 3
        reasons.append("gmail promotions label")

    if score >= 6:
        bucket = "important"
    elif score >= 2:
        bucket = "needs-attention"
    elif score <= -2:
        bucket = "promotional"
    else:
        bucket = "low-priority"

    return MessageSummary(
        message_id=msg.get("id", ""),
        thread_id=msg.get("threadId", ""),
        sender=sender,
        subject=subject,
        snippet=snippet,
        internal_ts=internal_ts,
        labels=labels,
        score=score,
        categories=categories,
        reasons=reasons,
        bucket=bucket,
    )


def format_digest(summaries: list[MessageSummary]) -> str:
    groups = {
        "important": "Important",
        "needs-attention": "Needs attention",
        "low-priority": "Low priority",
        "promotional": "Promotional / likely noise",
    }
    lines: list[str] = []
    for bucket, title in groups.items():
        items = [s for s in summaries if s.bucket == bucket]
        if not items:
            continue
        lines.append(f"{title}:")
        for item in items[:5]:
            reason = "; ".join(item.reasons[:2]) if item.reasons else "scored by default rules"
            lines.append(f"- {item.sender} — {item.subject} [{item.score}] ({reason})")
        lines.append("")
    return "\n".join(lines).strip()


def gmail_service(credentials_path: Path, token_path: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SystemExit(
            "Missing Google API dependencies. Install: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        ) from exc

    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise SystemExit(f"Missing OAuth client credentials file: {credentials_path}")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def fetch_messages(service, max_results: int, query: str | None) -> list[dict[str, Any]]:
    request = service.users().messages().list(userId="me", maxResults=max_results, q=query or "")
    response = request.execute()
    refs = response.get("messages", [])
    messages = []
    for ref in refs:
        full_msg = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        messages.append(full_msg)
    return messages


def train_preferences(prefs: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    changed = False

    def add_unique(path: list[str], value: str):
        nonlocal changed
        node = prefs
        for key in path[:-1]:
            node = node.setdefault(key, {})
        arr = node.setdefault(path[-1], [])
        if value not in arr:
            arr.append(value)
            changed = True

    for value in args.important_sender or []:
        add_unique(["important_senders"], value.lower())
    for value in args.ignore_sender or []:
        add_unique(["ignored_senders"], value.lower())
    for value in args.important_domain or []:
        add_unique(["important_domains"], value.lower())
    for value in args.ignore_domain or []:
        add_unique(["ignored_domains"], value.lower())
    for value in args.important_keyword or []:
        add_unique(["keyword_rules", "important"], value.lower())
    for value in args.ignore_keyword or []:
        add_unique(["keyword_rules", "ignore"], value.lower())

    if args.set_category_weight:
        for pair in args.set_category_weight:
            if "=" not in pair:
                raise SystemExit(f"Invalid category weight '{pair}', expected category=value")
            category, value = pair.split("=", 1)
            prefs.setdefault("category_weights", {})[category] = int(value)
            changed = True

    if changed:
        return prefs
    raise SystemExit("No training updates provided.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Gmail triage helper")
    parser.add_argument(
        "--prefs",
        default=str(Path(__file__).resolve().parent.parent / "data" / "preferences.json"),
        help="Path to preferences JSON",
    )
    parser.add_argument(
        "--credentials",
        default=str(Path(__file__).resolve().parent.parent / "data" / "credentials.json"),
        help="Path to Google OAuth client credentials JSON",
    )
    parser.add_argument(
        "--token",
        default=str(Path(__file__).resolve().parent.parent / "data" / "token.json"),
        help="Path to OAuth token JSON",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_cmd = subparsers.add_parser("init", help="Initialize preference storage")

    scan_cmd = subparsers.add_parser("scan", help="Fetch and rank recent Gmail messages")
    scan_cmd.add_argument("--max-results", type=int, default=15)
    scan_cmd.add_argument("--query", default="in:inbox newer_than:7d")

    train_cmd = subparsers.add_parser("train", help="Update preference memory")
    train_cmd.add_argument("--important-sender", action="append")
    train_cmd.add_argument("--ignore-sender", action="append")
    train_cmd.add_argument("--important-domain", action="append")
    train_cmd.add_argument("--ignore-domain", action="append")
    train_cmd.add_argument("--important-keyword", action="append")
    train_cmd.add_argument("--ignore-keyword", action="append")
    train_cmd.add_argument("--set-category-weight", action="append")

    subparsers.add_parser("show-prefs", help="Print current preference memory")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    prefs_path = Path(args.prefs)
    credentials_path = Path(args.credentials)
    token_path = Path(args.token)
    prefs = load_json(prefs_path, DEFAULT_PREFS)

    if args.command == "init":
        save_json(prefs_path, prefs)
        print(f"Initialized preferences at {prefs_path}")
        return 0

    if args.command == "show-prefs":
        print(json.dumps(prefs, indent=2))
        return 0

    if args.command == "train":
        prefs = train_preferences(prefs, args)
        save_json(prefs_path, prefs)
        print(json.dumps(prefs, indent=2))
        return 0

    if args.command == "scan":
        service = gmail_service(credentials_path, token_path)
        messages = fetch_messages(service, args.max_results, args.query)
        summaries = [score_message(message, prefs) for message in messages]
        summaries.sort(key=lambda item: item.score, reverse=True)
        print(format_digest(summaries))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
