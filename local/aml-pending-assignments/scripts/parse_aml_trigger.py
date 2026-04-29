#!/usr/bin/env python3
import json
import re
import sys


def fail(message: str) -> None:
    print(json.dumps({"ok": False, "error": message}))
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 2:
        fail("Pass the raw chat command as the first argument.")

    text = sys.argv[1].strip()
    result = {
        "ok": True,
        "target_mode": "assignment",
        "assignment_name": "",
        "post_author": "",
        "post_description": "",
        "response_text": "",
        "auto_generate": True,
        "dry_run": True,
        "headless": False,
        "keep_open": True,
    }

    patterns = [
        (r'^submit aml assignment:\s*"(?P<assignment>.+?)"\s+with\s+"(?P<text>.+)"$', "assignment-submit-custom"),
        (r'^do aml assignment:\s*"(?P<assignment>.+?)"\s+with\s+"(?P<text>.+)"$', "assignment-dry-custom"),
        (r'^submit aml assignment:\s*(?P<assignment>.+)$', "assignment-submit"),
        (r'^dry run aml assignment:\s*(?P<assignment>.+)$', "assignment-dry"),
        (r'^do aml assignment live:\s*(?P<assignment>.+)$', "assignment-live"),
        (r'^do aml assignment:\s*(?P<assignment>.+)$', "assignment-default"),
        (r'^reply to\s+(?P<person>.+?)\s+post\s+(?P<desc>.+?)\s+with\s+"(?P<text>.+)"$', "reply-custom"),
        (r'^reply to\s+(?P<person>.+?)\s+post\s+(?P<desc>.+)$', "reply-auto"),
    ]

    matched = None
    groups = None
    for pattern, kind in patterns:
        m = re.match(pattern, text, flags=re.IGNORECASE)
        if m:
            matched = kind
            groups = m.groupdict()
            break

    if not matched or groups is None:
        fail("Command did not match a known AML trigger phrase.")

    if matched.startswith("assignment"):
        result["assignment_name"] = (groups.get("assignment") or "").strip()
    else:
        result["target_mode"] = "reply"
        result["post_author"] = (groups.get("person") or "").strip()
        result["post_description"] = (groups.get("desc") or "").strip()

    if matched in {"assignment-submit", "assignment-submit-custom"}:
        result["dry_run"] = False
        result["keep_open"] = False
        result["headless"] = True

    if matched in {"assignment-submit-custom", "assignment-dry-custom", "reply-custom"}:
        result["auto_generate"] = False
        result["response_text"] = (groups.get("text") or "").strip()

    print(json.dumps(result))


if __name__ == "__main__":
    main()
