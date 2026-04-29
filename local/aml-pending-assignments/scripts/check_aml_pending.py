#!/usr/bin/env python3
import difflib
import os
import re
import sys
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
try:
    from bs4 import BeautifulSoup
except ImportError as exc:
    print(
        "Error: missing dependency 'beautifulsoup4'. Install with: "
        "python3 -m pip install beautifulsoup4 requests",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


LOGIN_URL = "https://headrick7.com/login/index.php"
BASE_URL = "https://headrick7.com/"

PENDING_KEYWORDS = (
    "due",
    "overdue",
    "missing",
    "todo",
    "to do",
    "not submitted",
    "late",
    "pending",
    "open",
    "cut-off",
)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Error: required environment variable is missing: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def fetch_login_token(session: requests.Session) -> str:
    response = session.get(LOGIN_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.select_one('input[name="logintoken"]')
    return token_input.get("value", "") if token_input else ""


def login(session: requests.Session, username: str, password: str) -> None:
    token = fetch_login_token(session)
    payload = {
        "username": username,
        "password": password,
    }
    if token:
        payload["logintoken"] = token

    response = session.post(LOGIN_URL, data=payload, timeout=30, allow_redirects=True)
    response.raise_for_status()
    text = response.text.lower()
    bad_login = "invalid login" in text or "loginerrormessage" in text
    still_on_login = "login/index.php" in response.url.lower()
    if bad_login or still_on_login:
        raise RuntimeError("Login failed. Check AML_PORTAL_USER / AML_PORTAL_PASS.")


def gather_candidate_pages(session: requests.Session) -> List[str]:
    pages = [
        urljoin(BASE_URL, "my/"),
        urljoin(BASE_URL, "my/courses.php"),
        urljoin(BASE_URL, "calendar/view.php?view=upcoming"),
    ]
    discovered: List[str] = []
    for page_url in pages:
        try:
            response = session.get(page_url, timeout=30)
            if response.ok:
                discovered.append(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                for anchor in soup.select('a[href*="/course/view.php"], a[href*="/mod/assign/view.php"]'):
                    href = anchor.get("href")
                    if href:
                        discovered.append(urljoin(BASE_URL, href))
        except requests.RequestException:
            continue
    deduped: List[str] = []
    seen = set()
    for url in discovered:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def discover_aml_course_pages(
    session: requests.Session, discovered_pages: List[str], class_keyword: str
) -> List[str]:
    course_urls: List[str] = []
    keyword = class_keyword.lower()

    for page_url in discovered_pages:
        try:
            response = session.get(page_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.select('a[href*="/course/view.php"]'):
            label = clean_text(anchor.get_text(" ", strip=True))
            href = anchor.get("href", "")
            if not href:
                continue
            if keyword in label.lower():
                course_urls.append(urljoin(BASE_URL, href))

    deduped: List[str] = []
    seen = set()
    for url in course_urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def build_course_specific_pages(course_url: str) -> List[str]:
    # Moodle typically uses /course/view.php?id=<id>; derive assignment index page.
    course_id_match = re.search(r"[?&]id=(\d+)", course_url)
    pages = [course_url]
    if course_id_match:
        course_id = course_id_match.group(1)
        pages.append(urljoin(BASE_URL, f"mod/assign/index.php?id={course_id}"))
    return pages


def extract_pending_items(session: requests.Session, page_url: str, class_keyword: str) -> List[Dict[str, str]]:
    try:
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    items: List[Dict[str, str]] = []

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        label = clean_text(anchor.get_text(" ", strip=True))
        if not label:
            continue

        context_el = anchor.find_parent(["li", "tr", "div", "section", "article"])
        context_text = clean_text(context_el.get_text(" ", strip=True)) if context_el else label
        haystack = f"{label} {context_text}".lower()
        if class_keyword.lower() not in haystack:
            continue

        if not any(keyword in haystack for keyword in PENDING_KEYWORDS):
            continue

        item = {
            "title": label[:220],
            "snippet": context_text[:350],
            "url": urljoin(BASE_URL, href),
        }
        items.append(item)

    unique: List[Dict[str, str]] = []
    seen = set()
    for item in items:
        key = (item["title"], item["url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def extract_assignment_links(session: requests.Session, page_url: str) -> List[Dict[str, str]]:
    try:
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    items: List[Dict[str, str]] = []

    for anchor in soup.select('a[href*="/mod/assign/view.php"]'):
        href = anchor.get("href", "")
        label = clean_text(anchor.get_text(" ", strip=True))
        if not href or not label:
            continue
        context_el = anchor.find_parent(["li", "tr", "div", "section", "article"])
        context_text = clean_text(context_el.get_text(" ", strip=True)) if context_el else label
        items.append(
            {
                "title": label[:220],
                "snippet": context_text[:350],
                "url": urljoin(BASE_URL, href),
            }
        )

    unique: List[Dict[str, str]] = []
    seen = set()
    for item in items:
        key = (item["title"], item["url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def find_assignment_by_name(
    session: requests.Session,
    discovered_pages: List[str],
    class_keyword: str,
    assignment_name: str,
) -> Optional[Dict[str, str]]:
    aml_courses = discover_aml_course_pages(session, discovered_pages, class_keyword)
    search_pages = list(discovered_pages)
    for course_url in aml_courses:
        search_pages.extend(build_course_specific_pages(course_url))
    search_pages = list(dict.fromkeys(search_pages))

    candidates: List[Dict[str, str]] = []
    for page_url in search_pages:
        candidates.extend(extract_assignment_links(session, page_url))

    if not candidates:
        return None

    target = clean_text(assignment_name).lower()
    scored = []
    for item in candidates:
        title = item["title"].lower()
        snippet = item["snippet"].lower()
        score = max(
            difflib.SequenceMatcher(None, target, title).ratio(),
            difflib.SequenceMatcher(None, target, snippet).ratio(),
        )
        if target in title:
            score = max(score, 0.97)
        elif all(word in title for word in target.split() if word):
            score = max(score, 0.93)
        scored.append((score, item))

    scored.sort(key=lambda entry: entry[0], reverse=True)
    best_score, best_item = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    if best_score >= 0.90 and (best_score - second_score) >= 0.08:
        return best_item
    if best_score >= 0.97:
        return best_item
    return None


def main() -> None:
    username = get_required_env("AML_PORTAL_USER")
    password = get_required_env("AML_PORTAL_PASS")
    class_keyword = os.getenv("AML_CLASS_KEYWORD", "AML").strip() or "AML"
    assignment_name = os.getenv("AML_ASSIGNMENT_NAME", "").strip()

    with requests.Session() as session:
        session.headers.update(
            {"User-Agent": "aml-pending-checker/1.0 (+requests; educational use)"}
        )
        login(session, username, password)
        pages = gather_candidate_pages(session)

        if assignment_name:
            match = find_assignment_by_name(session, pages, class_keyword, assignment_name)
            if match:
                print(f"Confident match found: {match['title']}")
                print(f"Link: {match['url']}")
                if match.get("snippet"):
                    print(f"Snippet: {match['snippet']}")
                return
            print(f"No confident match found for assignment name: {assignment_name}")
            sys.exit(1)

        aml_courses = discover_aml_course_pages(session, pages, class_keyword)
        for course_url in aml_courses:
            pages.extend(build_course_specific_pages(course_url))

        # Keep calendar/upcoming view last so direct course pages are prioritized.
        pages = list(dict.fromkeys(pages))

        all_items: List[Dict[str, str]] = []
        for page in pages:
            all_items.extend(extract_pending_items(session, page, class_keyword))

    if not pages:
        print("Logged in, but no dashboard/course pages were discovered.")
        return

    if not all_items:
        print(f"No pending {class_keyword} assignments found from scanned pages.")
        print("If this seems wrong, open the course once in a browser and re-run.")
        return

    print(f"Pending {class_keyword} assignment signals:")
    for idx, item in enumerate(all_items, start=1):
        print(f"{idx}. {item['title']}")
        print(f"   Snippet: {item['snippet']}")
        print(f"   Link: {item['url']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
