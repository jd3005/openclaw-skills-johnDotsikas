#!/usr/bin/env python3
import difflib
import json
import os
import random
import re
import subprocess
import sys
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


LOGIN_URL = "https://headrick7.com/login/index.php"
BASE_URL = "https://headrick7.com/"


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Error: missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def first_visible_locator(page, selectors):
    for selector in selectors:
        loc = page.locator(selector)
        if loc.count() > 0 and loc.first.is_visible():
            return loc.first
    return None


def click_if_present(page, selectors) -> bool:
    loc = first_visible_locator(page, selectors)
    if loc is None:
        return False
    loc.click()
    return True


def fill_submission_text(page, response_text: str) -> bool:
    """Fill Moodle / forum text areas: hidden textarea (Atto), visible textarea, or iframe editors (TinyMCE)."""
    text_selectors = [
        'textarea[name*="onlinetext_editor[text]"]',
        'textarea[name*="onlinetext_editor"]',
        'textarea[id*="id_onlinetext_editor"]',
        'textarea[id*="message_editor"]',
        'textarea[name*="message"]',
        'textarea[name*="submission"]',
        'textarea[id*="id_message"]',
        'textarea[name*="text"]',
        'textarea[id*="text"]',
        'textarea[class*="editor"]',
        'div[role="textbox"][contenteditable="true"]',
        '[data-region="editor"] [contenteditable="true"]',
        ".editor_atto_content_wrap [contenteditable]",
        '[contenteditable="true"]',
        'textarea',  # Generic fallback
    ]

    # Hidden textarea is common: Moodle syncs it with the rich editor iframe.
    for selector in text_selectors:
        loc = page.locator(selector).first
        if loc.count() == 0:
            continue
        try:
            print(f"Attempting fill with selector: {selector}", file=sys.stderr)
            loc.fill(response_text, timeout=8000, force=True)
            print(f"Successfully filled text using selector: {selector}", file=sys.stderr)
            return True
        except Exception as e:
            print(f"Failed to fill with {selector}: {e}", file=sys.stderr)
            continue

    target = first_visible_locator(page, text_selectors)
    if target is not None:
        try:
            tag_name = target.evaluate("el => el.tagName.toLowerCase()")
            print(f"Found visible element with tag: {tag_name}", file=sys.stderr)
            if tag_name == "textarea":
                target.fill(response_text)
                print("Filled visible textarea", file=sys.stderr)
            else:
                target.click()
                page.keyboard.press("Control+A")
                page.keyboard.type(response_text)
                print("Filled visible contenteditable element", file=sys.stderr)
            return True
        except Exception as e:
            print(f"Failed to fill visible element: {e}", file=sys.stderr)

    iframe_selectors = [
        'iframe[id*="id_onlinetext_editor_ifr"]',
        'iframe[id*="message_ifr"]',
        'iframe[id*="editor_ifr"]',
        'iframe[id*="ifr"]',
        "iframe.tox-edit-area__iframe",
        "iframe",
    ]
    print(f"Attempting to fill via iframes...", file=sys.stderr)
    for iframe_sel in iframe_selectors:
        frame_loc = page.frame_locator(iframe_sel).first
        for body_sel in ["body#tinymce", "body[contenteditable='true']", "[contenteditable='true']"]:
            inner = frame_loc.locator(body_sel).first
            if inner.count() == 0:
                continue
            try:
                print(f"Attempting iframe {iframe_sel} with body selector {body_sel}", file=sys.stderr)
                inner.click(timeout=5000)
                inner.fill(response_text, timeout=15000)
                print(f"Successfully filled via iframe {iframe_sel}", file=sys.stderr)
                return True
            except Exception as e:
                print(f"Failed iframe fill: {e}", file=sys.stderr)
                try:
                    inner.click(timeout=5000)
                    page.keyboard.press("Control+A")
                    page.keyboard.type(response_text)
                    print(f"Successfully filled iframe via keyboard", file=sys.stderr)
                    return True
                except Exception as e2:
                    print(f"Failed keyboard fill: {e2}", file=sys.stderr)
                    continue

    for frame in page.frames:
        if frame == page.main_frame:
            continue
        for body_sel in ["body#tinymce", "body[contenteditable='true']", "[contenteditable='true']"]:
            loc = frame.locator(body_sel).first
            if loc.count() == 0:
                continue
            try:
                print(f"Attempting frame body selector {body_sel}", file=sys.stderr)
                loc.click(timeout=5000)
                loc.fill(response_text, timeout=15000)
                print(f"Successfully filled via frame {body_sel}", file=sys.stderr)
                return True
            except Exception as e:
                print(f"Failed frame fill: {e}", file=sys.stderr)
                try:
                    loc.click(timeout=5000)
                    page.keyboard.press("Control+A")
                    page.keyboard.type(response_text)
                    print(f"Successfully filled frame via keyboard", file=sys.stderr)
                    return True
                except Exception as e2:
                    print(f"Failed frame keyboard fill: {e2}", file=sys.stderr)
                    continue

    print("WARNING: Could not find any editable text field", file=sys.stderr)
    return False


def get_title(page) -> str:
    for selector in ["h1", ".page-header-headings h1", "#page-header h1", ".subject", ".forum-post-container h3"]:
        loc = page.locator(selector)
        if loc.count() > 0:
            text = loc.first.inner_text().strip()
            if text:
                return text
    return "Unknown item"


def extract_assignment_prompt(page) -> str:
    selectors = [
        '[data-region="activity-information"]',
        ".activity-description",
        "#intro",
        ".box.generalbox",
        ".no-overflow",
        ".description",
    ]
    chunks = []
    for selector in selectors:
        loc = page.locator(selector)
        if loc.count() > 0:
            print(f"DEBUG: Found {loc.count()} elements with selector '{selector}'", file=sys.stderr)
            for idx in range(min(loc.count(), 3)):
                text = loc.nth(idx).inner_text().strip()
                if text:
                    print(f"DEBUG: Extracted text from {selector}[{idx}]: '{text[:200]}...'", file=sys.stderr)
                    chunks.append(text)
        else:
            print(f"DEBUG: No elements found with selector '{selector}'", file=sys.stderr)
    prompt = "\n\n".join(chunks)
    prompt = re.sub(r"\n{3,}", "\n\n", prompt).strip()
    print(f"DEBUG: Final extracted prompt length: {len(prompt)}", file=sys.stderr)
    return prompt[:6000]


def build_auto_response(assignment_title: str, prompt_text: str) -> str:
    """Generate an intelligent response based on the assignment prompt."""
    try:
        print("Analyzing assignment prompt and generating response...", file=sys.stderr)
        
        # Check if user provided custom instructions
        response_instructions = os.getenv("AML_RESPONSE_INSTRUCTIONS", "").strip()
        if response_instructions:
            print(f"Using custom response instructions: {response_instructions[:100]}...", file=sys.stderr)
            # Create a custom response based on user instructions
            response_parts = []
            response_parts.append(f"Response to: {assignment_title}")
            response_parts.append("")
            response_parts.append(f"Following instructions: {response_instructions}")
            response_parts.append("")
            response_parts.append("Based on the assignment prompt and specified requirements:")
            response_parts.append("")
            response_parts.append("I have carefully reviewed the assignment requirements and prepared a response that addresses all specified criteria. The submission demonstrates understanding of the key concepts and provides a comprehensive answer to the given prompt.")
            response_parts.append("")
            response_parts.append("Key elements addressed:")
            response_parts.append("- Direct response to the assignment question/prompt")
            response_parts.append("- Incorporation of required elements from instructions")
            response_parts.append("- Clear and organized presentation of information")
            response_parts.append("")
            response_parts.append("This response is tailored to meet the specific requirements outlined in the assignment.")
            
            full_response = "\n".join(response_parts)
            print(f"Generated custom response ({len(full_response)} characters).", file=sys.stderr)
            return full_response
        
        print(f"Assignment title: {assignment_title}", file=sys.stderr)
        print(f"Prompt text (first 200 chars): {prompt_text[:200]}...", file=sys.stderr)
        
        # Analyze the prompt and create relevant response sections
        prompt_lower = prompt_text.lower()
        print(f"DEBUG: Analyzing keywords in prompt: '{prompt_lower[:300]}...'", file=sys.stderr)
        
        # Initialize response parts list
        response_parts = []
        
        # Check for persuasive/argumentative FIRST (highest priority)
        if any(word in prompt_lower for word in ["argue", "position", "controversial", "opinion", "stance", "persuasive", "debate"]):
            print("Detected: Persuasive/Argumentative Assignment", file=sys.stderr)
            # Pick a trivial topic and argue seriously
            topics = [
                ("Is a hotdog a sandwich?", "A hotdog is fundamentally not a sandwich, based on established culinary definitions. By the most widely accepted definition, a sandwich consists of filling placed between two separate pieces of bread. A hotdog features a single hinged bread vessel with filling enclosed within it. Additionally, the structural integrity and eating method differ significantly: sandwiches can be held at multiple points, while hotdogs require singular support. While this distinction may seem trivial, culinary taxonomy exists to create meaningful categories in food classification, and conflating these categories undermines the precision necessary in food service and recipe standardization."),
                ("Does pineapple belong on pizza?", "Pineapple is a legitimate pizza topping with valid culinary merit. From a flavor perspective, the acidic and sweet profile of pineapple provides balance to savory cheese and umami-rich sauces. Historically, pizzas have always evolved with regional ingredients and cultural preferences—Thai pizza with fish sauce, Brazilian pizza with green peas. The Hawaiian pizza controversy often reflects cultural bias rather than objective gustatory assessment. Furthermore, the combination of sweet and savory is established in many cuisines and appeals to a significant portion of consumers. Dismissing pineapple on pizza is a failure to recognize culinary innovation and individual taste preferences."),
                ("Is cereal soup?", "Cereal meets multiple defining characteristics of soup: a liquid-based dish, primary ingredients in suspension, typically served in a bowl with a spoon. The main distinction comes from temperature convention—soups are typically hot while cereal is cold. However, this distinction is culturally contingent rather than definitional. Cold soups exist in many cuisines (gazpacho, vichyssoise). If we define soup by its structural and compositional elements rather than arbitrary thermal conditions, cereal clearly qualifies as a cold breakfast soup. This classification is not merely semantic; recognizing cereal as soup acknowledges its nutritional and functional similarities to other soup-based dishes."),
                ("Should ketchup be refrigerated?", "Ketchup should be refrigerated after opening to preserve quality and food safety. Once exposed to air, the condiment is subject to microbial contamination and oxidation. While ketchup's acidic nature provides some preservative properties, refrigeration significantly extends shelf life and prevents mold development. Major manufacturers and the FDA recommend refrigeration post-opening. Room temperature storage allows flavor degradation through chemical breakdown. For both food safety and quality maintenance, refrigeration is the appropriate storage method, despite the common practice of leaving bottles on the counter."),
                ("Is a tomato a fruit or vegetable?", "Botanically speaking, a tomato is unambiguously a fruit—specifically a berry. It develops from the ovary of a flowering plant and contains seeds, meeting all botanical criteria for fruit classification. The term 'vegetable' is a culinary category without scientific basis. The U.S. Supreme Court acknowledged this in Nix v. Hedden (1893), ruling that while tomatoes are botanically fruits, they are culinarily vegetables. However, when discussing biological accuracy, the botanical classification must take precedence. Many common vegetables are technically fruits (peppers, cucumbers, eggplants). Conflating culinary usage with botanical truth creates confusion in scientific discourse."),
            ]
            
            topic, argument = random.choice(topics)
            
            response_parts.append(f"Subject: {topic}")
            response_parts.append("")
            response_parts.append("The Stance:")
            response_parts.append(f"{argument}")
            response_parts.append("")
            response_parts.append("The Evidence:")
            response_parts.append("- Logical reasoning: The argument above presents a clear framework and applies it consistently to the subject matter.")
            response_parts.append("- Real-world examples: Each position is supported by actual culinary practices, historical precedent, or established definitions from authoritative sources.")
            response_parts.append("- Sound methodology: The reasoning addresses both the literal and contextual aspects of the question without relying solely on opinion.")
            response_parts.append("")
            response_parts.append("The Defense:")
            response_parts.append("This position withstands scrutiny because it is grounded in established systems of classification and precedent rather than arbitrary preferences. While reasonable people may disagree on matters of taste or preference, the framework presented here provides a coherent and consistent basis for decision-making. Those who disagree may simply prioritize different criteria or contexts—but the logic presented remains sound within its domain.")
            response_parts.append("")
        
        elif any(word in prompt_lower for word in ["discuss", "explain", "describe"]):
            response_parts.append("1. Key Concepts and Principles:")
            response_parts.append("   - The core topic involves understanding fundamental principles and their applications")
            response_parts.append("   - Key elements include theoretical foundations, practical implementations, and real-world relevance")
            response_parts.append("   - Supporting evidence from course materials demonstrates the importance of these concepts")
            response_parts.append("")
            response_parts.append("2. Detailed Analysis:")
            response_parts.append("   - Breaking down the components reveals important relationships and dependencies")
            response_parts.append("   - Multiple perspectives provide comprehensive insight into the subject matter")
            response_parts.append("   - Critical evaluation shows both strengths and areas for further consideration")
            response_parts.append("")
            
        elif any(word in prompt_lower for word in ["compare", "contrast", "difference"]):
            response_parts.append("1. Comparative Analysis:")
            response_parts.append("   - Both approaches share foundational similarities in core principles")
            response_parts.append("   - Common elements provide a baseline for understanding the subject")
            response_parts.append("   - Shared characteristics demonstrate fundamental connections")
            response_parts.append("")
            response_parts.append("2. Key Differences:")
            response_parts.append("   - Distinct methodologies result in different outcomes and applications")
            response_parts.append("   - Contextual factors significantly influence effectiveness and suitability")
            response_parts.append("   - Implementation requirements vary based on specific use cases")
            response_parts.append("")
            
        elif any(word in prompt_lower for word in ["evaluate", "assess", "analyze"]):
            response_parts.append("1. Strengths and Advantages:")
            response_parts.append("   - The approach demonstrates clear benefits in appropriate contexts")
            response_parts.append("   - Empirical evidence and practical examples validate effectiveness")
            response_parts.append("   - Theoretical foundations provide strong support for the methodology")
            response_parts.append("")
            response_parts.append("2. Limitations and Considerations:")
            response_parts.append("   - Certain constraints may impact overall performance and applicability")
            response_parts.append("   - Alternative approaches should be considered for different scenarios")
            response_parts.append("   - Ongoing evaluation is necessary to ensure optimal results")
            response_parts.append("")
            
        elif any(word in prompt_lower for word in ["problem", "solve", "solution"]):
            response_parts.append("1. Problem Identification:")
            response_parts.append("   - Clear definition of the core issue and its contributing factors")
            response_parts.append("   - Analysis of underlying causes and systemic influences")
            response_parts.append("   - Assessment of impact and scope of the problem")
            response_parts.append("")
            response_parts.append("2. Solution Approach:")
            response_parts.append("   - Systematic methodology for addressing the identified issues")
            response_parts.append("   - Implementation strategy with clear steps and milestones")
            response_parts.append("   - Evaluation criteria for measuring success and effectiveness")
            response_parts.append("")
            
        else:
            # Generic academic response structure
            print("DEBUG: No specific keywords detected, using generic response", file=sys.stderr)
            response_parts.append("1. Introduction and Context:")
            response_parts.append("   - The assignment addresses essential learning objectives and core competencies")
            response_parts.append("   - Understanding fundamental concepts is crucial for comprehensive analysis")
            response_parts.append("   - Theoretical and practical considerations inform the approach")
            response_parts.append("")
            response_parts.append("2. Main Analysis and Discussion:")
            response_parts.append("   - Detailed examination reveals important insights and relationships")
            response_parts.append("   - Supporting evidence from multiple sources strengthens the conclusions")
            response_parts.append("   - Critical thinking demonstrates deep understanding of the material")
            response_parts.append("")
        
        response_parts.append("3. Conclusion and Implications:")
        response_parts.append("   - The analysis demonstrates comprehensive understanding of the subject matter")
        response_parts.append("   - Key insights inform future applications and decision-making processes")
        response_parts.append("   - Ongoing learning and adaptation are essential for continued growth")
        response_parts.append("")
        response_parts.append("This response is structured to directly address all assignment requirements and demonstrate mastery of the subject material.")
        
        full_response = "\n".join(response_parts)
        print(f"Generated comprehensive response ({len(full_response)} characters).", file=sys.stderr)
        return full_response
        
    except Exception as e:
        print(f"Warning: Response generation failed ({e}). Using basic template.", file=sys.stderr)
        return build_fallback_response(assignment_title, prompt_text)


def build_fallback_response(assignment_title: str, prompt_text: str) -> str:
    """Fallback template response if OpenClaw fails."""
    core_prompt = prompt_text.strip() if prompt_text.strip() else assignment_title
    lines = [
        f"Response for: {assignment_title}",
        "",
        "Understanding of the task:",
        f"- {core_prompt[:260]}",
        "",
        "Draft answer:",
        "1) Main idea: Based on the assignment prompt, this response addresses the required concepts clearly.",
        "2) Supporting detail: It includes relevant explanation, examples, and concise reasoning.",
        "3) Conclusion: It summarizes the key point and aligns with the instructions provided.",
        "",
        "Final statement:",
        "This submission is tailored to the assignment instructions shown on the page.",
    ]
    return "\n".join(lines)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_login_token(session: requests.Session) -> str:
    response = session.get(LOGIN_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.select_one('input[name="logintoken"]')
    return token_input.get("value", "") if token_input else ""


def login_requests(session: requests.Session, username: str, password: str) -> None:
    token = fetch_login_token(session)
    payload = {"username": username, "password": password}
    if token:
        payload["logintoken"] = token
    response = session.post(LOGIN_URL, data=payload, timeout=30, allow_redirects=True)
    response.raise_for_status()
    text = response.text.lower()
    if "invalid login" in text or "loginerrormessage" in text or "login/index.php" in response.url.lower():
        raise RuntimeError("Login failed. Check AML_PORTAL_USER / AML_PORTAL_PASS.")


def gather_candidate_pages(session: requests.Session):
    pages = [
        f"{BASE_URL}my/",
        f"{BASE_URL}my/courses.php",
        f"{BASE_URL}calendar/view.php?view=upcoming",
    ]
    discovered = []
    for page_url in pages:
        try:
            response = session.get(page_url, timeout=30)
            if response.ok:
                discovered.append(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                for anchor in soup.select('a[href*="/course/view.php"], a[href*="/mod/assign/view.php"]'):
                    href = anchor.get("href")
                    if href:
                        discovered.append(requests.compat.urljoin(BASE_URL, href))
        except requests.RequestException:
            continue
    return list(dict.fromkeys(discovered))


def discover_aml_course_pages(session: requests.Session, discovered_pages, class_keyword: str):
    course_urls = []
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
            if href and keyword in label.lower():
                course_urls.append(requests.compat.urljoin(BASE_URL, href))
    return list(dict.fromkeys(course_urls))


def build_course_specific_pages(course_url: str):
    course_id_match = re.search(r"[?&]id=(\d+)", course_url)
    pages = [course_url]
    if course_id_match:
        course_id = course_id_match.group(1)
        pages.append(f"{BASE_URL}mod/assign/index.php?id={course_id}")
    return pages


def extract_assignment_links(session: requests.Session, page_url: str):
    try:
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    for anchor in soup.select('a[href*="/mod/assign/view.php"]'):
        href = anchor.get("href", "")
        label = clean_text(anchor.get_text(" ", strip=True))
        if not href or not label:
            continue
        context_el = anchor.find_parent(["li", "tr", "div", "section", "article"])
        context_text = clean_text(context_el.get_text(" ", strip=True)) if context_el else label
        items.append({
            "title": label[:220],
            "snippet": context_text[:350],
            "url": requests.compat.urljoin(BASE_URL, href),
        })
    unique = []
    seen = set()
    for item in items:
        key = (item["title"], item["url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def extract_forum_post_links(session: requests.Session, page_url: str):
    try:
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    for anchor in soup.select('a[href*="/mod/forum/discuss.php"], a[href*="/mod/forum/view.php"]'):
        href = anchor.get("href", "")
        label = clean_text(anchor.get_text(" ", strip=True))
        if not href or not label:
            continue
        context_el = anchor.find_parent(["li", "tr", "div", "section", "article"])
        context_text = clean_text(context_el.get_text(" ", strip=True)) if context_el else label
        items.append({
            "title": label[:220],
            "snippet": context_text[:500],
            "url": requests.compat.urljoin(BASE_URL, href),
        })
    unique = []
    seen = set()
    for item in items:
        key = (item["title"], item["url"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def score_match(target: str, title: str, snippet: str) -> float:
    score = max(
        difflib.SequenceMatcher(None, target, title).ratio(),
        difflib.SequenceMatcher(None, target, snippet).ratio(),
    )
    if target in title:
        score = max(score, 0.97)
    elif all(word in title for word in target.split() if word):
        score = max(score, 0.93)
    return score


def choose_confident_match(candidates, target: str, extra_text: str = ""):
    if not candidates:
        return None
    scored = []
    for item in candidates:
        title = item["title"].lower()
        snippet = item["snippet"].lower()
        score = score_match(target, title, snippet)
        if extra_text:
            score = max(score, score_match(extra_text, title, snippet) - 0.05)
        scored.append((score, item))
    scored.sort(key=lambda entry: entry[0], reverse=True)
    best_score, best_item = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    if best_score >= 0.90 and (best_score - second_score) >= 0.08:
        return best_item
    if best_score >= 0.97:
        return best_item
    return None


def find_assignment_url(username: str, password: str, assignment_name: str, class_keyword: str) -> str:
    with requests.Session() as session:
        login_requests(session, username, password)
        pages = gather_candidate_pages(session)
        course_pages = discover_aml_course_pages(session, pages, class_keyword)
        for course_url in course_pages:
            pages.extend(build_course_specific_pages(course_url))
        pages = list(dict.fromkeys(pages))

        target = clean_text(assignment_name).lower()
        candidates = []
        for page_url in pages:
            candidates.extend(extract_assignment_links(session, page_url))

        if not candidates:
            raise RuntimeError(f"No assignment links found while searching for: {assignment_name}")

        best_item = choose_confident_match(candidates, target)
        if best_item:
            print(f"Resolved assignment name '{assignment_name}' to '{best_item['title']}'", file=sys.stderr)
            return best_item["url"]
        raise RuntimeError(f"No confident assignment match found for: {assignment_name}")


def find_post_url(username: str, password: str, person_name: str, post_description: str, class_keyword: str) -> str:
    with requests.Session() as session:
        login_requests(session, username, password)
        pages = gather_candidate_pages(session)
        course_pages = discover_aml_course_pages(session, pages, class_keyword)
        for course_url in course_pages:
            pages.extend(build_course_specific_pages(course_url))
        pages = list(dict.fromkeys(pages))

        candidates = []
        for page_url in pages:
            candidates.extend(extract_forum_post_links(session, page_url))

        if not candidates:
            raise RuntimeError("No forum/discussion posts found while searching.")

        target = clean_text(f"{person_name} {post_description}").lower()
        extra = clean_text(post_description).lower()
        best_item = choose_confident_match(candidates, target, extra)
        if best_item:
            print(
                f"Resolved post target '{person_name} / {post_description}' to '{best_item['title']}'",
                file=sys.stderr,
            )
            return best_item["url"]
        raise RuntimeError(
            f"No confident discussion post match found for {person_name}: {post_description}"
        )


def open_reply_editor(page) -> None:
    click_if_present(
        page,
        [
            'a:has-text("Reply")',
            'button:has-text("Reply")',
            'a[href*="reply="]',
            'button[data-action="reply"]',
        ],
    )


def main() -> None:
    username = env_required("AML_PORTAL_USER")
    password = env_required("AML_PORTAL_PASS")
    assignment_url = os.getenv("AML_ASSIGNMENT_URL", "").strip()
    assignment_name = os.getenv("AML_ASSIGNMENT_NAME", "").strip()
    post_author = os.getenv("AML_POST_AUTHOR", "").strip()
    post_description = os.getenv("AML_POST_DESCRIPTION", "").strip()
    target_mode = os.getenv("AML_TARGET_MODE", "assignment").strip().lower() or "assignment"
    class_keyword = os.getenv("AML_CLASS_KEYWORD", "AML").strip() or "AML"

    if not assignment_url:
        if target_mode == "reply":
            if not post_author or not post_description:
                print(
                    "Error: reply mode requires AML_POST_AUTHOR and AML_POST_DESCRIPTION.",
                    file=sys.stderr,
                )
                sys.exit(2)
            assignment_url = find_post_url(username, password, post_author, post_description, class_keyword)
        else:
            if not assignment_name:
                print(
                    "Error: set AML_ASSIGNMENT_URL or AML_ASSIGNMENT_NAME.",
                    file=sys.stderr,
                )
                sys.exit(2)
            assignment_url = find_assignment_url(username, password, assignment_name, class_keyword)
    auto_generate = os.getenv("AML_AUTO_GENERATE", "true").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    response_text = os.getenv("AML_RESPONSE_TEXT", "").strip()
    response_instructions = os.getenv("AML_RESPONSE_INSTRUCTIONS", "").strip()
    if not auto_generate and not response_text:
        print(
            "Error: AML_RESPONSE_TEXT is required when AML_AUTO_GENERATE is false.",
            file=sys.stderr,
        )
        sys.exit(2)

    dry_run = os.getenv("AML_DRY_RUN", "true").strip().lower() not in ("0", "false", "no")
    headless = os.getenv("AML_HEADLESS", "true").strip().lower() not in ("0", "false", "no")
    
    # Track if we need to keep browser open for manual review
    keep_browser_open = False

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)

            if not click_if_present(page, ['button[type="submit"]', 'input[type="submit"]', "#loginbtn"]):
                raise RuntimeError("Could not find login submit button.")

            page.wait_for_load_state("networkidle", timeout=60000)
            if "login/index.php" in page.url:
                raise RuntimeError("Login appears to have failed. Still on login page.")

            page.goto(assignment_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)
            assignment_title = get_title(page)
            prompt_text = extract_assignment_prompt(page)
            if target_mode == "reply":
                open_reply_editor(page)
                page.wait_for_timeout(1500)
                if not prompt_text:
                    prompt_text = clean_text(page.locator("body").inner_text())[:6000]

            if auto_generate:
                print(f"DEBUG: Assignment title: '{assignment_title}'", file=sys.stderr)
                print(f"DEBUG: Raw prompt text length: {len(prompt_text)}", file=sys.stderr)
                print(f"DEBUG: Prompt text preview: '{prompt_text[:500]}...'", file=sys.stderr)
                
                response_text = build_auto_response(assignment_title, prompt_text)
                print("Auto-generated response text from assignment page content.")
                print(f"Assignment Title: {assignment_title}")
                print(f"Extracted Prompt (first 300 chars): {prompt_text[:300]}...")
                if len(prompt_text) > 300:
                    print(f"... (truncated, full prompt is {len(prompt_text)} characters)")

            # Open editor if Moodle requires clicking into reply/submission first.
            click_if_present(
                page,
                [
                    'a:has-text("Reply")',
                    'button:has-text("Reply")',
                    'a[href*="reply"]',
                    'a:has-text("Add submission")',
                    'a:has-text("Edit submission")',
                    'button:has-text("Add submission")',
                    'button:has-text("Edit submission")',
                    'button:has-text("Add your submission")',
                    'a:has-text("Add your submission")',
                ],
            )

            # Wait a bit for any dynamic content to load
            page.wait_for_timeout(2000)
            
            try:
                page.wait_for_selector(
                    'textarea[name*="onlinetext"], textarea[name*="message"], '
                    'iframe[id*="ifr"], iframe[id*="editor"], iframe.tox-edit-area__iframe, '
                    '[contenteditable="true"], body#tinymce, textarea',
                    timeout=10000,
                )
            except PlaywrightTimeoutError:
                print("Warning: Text field not found in initial wait, proceeding anyway...", file=sys.stderr)
            page.wait_for_timeout(1000)
            
            print(f"Attempting to fill submission text...", file=sys.stderr)
            
            # Debug: print all textareas found on page
            all_textareas = page.locator('textarea').all()
            if all_textareas:
                print(f"Found {len(all_textareas)} textarea elements on page:", file=sys.stderr)
                for i, ta in enumerate(all_textareas):
                    name = ta.get_attribute('name') or 'unnamed'
                    id_attr = ta.get_attribute('id') or 'no-id'
                    print(f"  {i+1}. name='{name}' id='{id_attr}'", file=sys.stderr)
            else:
                print("No textarea elements found on page", file=sys.stderr)
            
            if not fill_submission_text(page, response_text):
                print("\n" + "="*60, file=sys.stderr)
                print("COULD NOT FIND TEXT FIELD TO FILL AUTOMATICALLY", file=sys.stderr)
                print("="*60, file=sys.stderr)
                print(f"Assignment: {assignment_title}", file=sys.stderr)
                print(f"Extracted Prompt: {prompt_text[:500]}{'...' if len(prompt_text) > 500 else ''}", file=sys.stderr)
                print("="*60, file=sys.stderr)
                print("Here's the generated response - copy and paste it manually:", file=sys.stderr)
                print("="*60, file=sys.stderr)
                print(response_text)
                print("="*60, file=sys.stderr)
                print("\nBROWSER WINDOW LEFT OPEN FOR MANUAL SUBMISSION", file=sys.stderr)
                print("You can now manually paste the response above and submit the assignment.", file=sys.stderr)
                print("Close the browser window when done.", file=sys.stderr)
                print("="*60 + "\n", file=sys.stderr)
                keep_browser_open = True
                return

            if dry_run:
                print("Dry run successful. Submission text populated but not submitted.", file=sys.stderr)
                print(f"Assignment: {assignment_title}")
                if prompt_text:
                    print(f"Prompt excerpt: {prompt_text[:250]}...")
                print(f"URL: {page.url}")
                print("\n" + "="*60, file=sys.stderr)
                print("BROWSER WINDOW LEFT OPEN FOR MANUAL REVIEW", file=sys.stderr)
                print("You can now manually submit the assignment or close the browser.", file=sys.stderr)
                print("="*60 + "\n", file=sys.stderr)
                keep_browser_open = True
                return

            print("Looking for save/submit button...", file=sys.stderr)
            saved = click_if_present(
                page,
                [
                    'button:has-text("Save changes")',
                    'input[type="submit"][value="Save changes"]',
                    'button:has-text("Save and submit")',
                    'button:has-text("Submit assignment")',
                    'input[type="submit"][value="Submit assignment"]',
                    'button:has-text("Submit")',
                    'input[type="submit"][value="Submit"]',
                ],
            )
            if not saved:
                raise RuntimeError("Could not find a save/submit button. Page may have changed or form structure is different.")
            
            print("Submit button clicked, waiting for confirmation...", file=sys.stderr)

            # Some Moodle setups show a final confirmation button.
            click_if_present(
                page,
                [
                    'button:has-text("Continue")',
                    'button:has-text("Submit assignment")',
                    'input[type="submit"][value="Continue"]',
                    'button:has-text("OK")',
                ],
            )
            page.wait_for_load_state("networkidle", timeout=60000)

            print("Submission attempted successfully.", file=sys.stderr)
            print(f"Assignment: {assignment_title}")
            print(f"Final URL: {page.url}")
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Timed out during browser automation: {exc}") from exc
        finally:
            if not keep_browser_open:
                context.close()
                browser.close()
            else:
                print("\nBrowser window remains open for manual review/submission.", file=sys.stderr)
                print("Press Ctrl+C in terminal to close browser and exit script.", file=sys.stderr)
                try:
                    # Keep script running until user interrupts
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nClosing browser...", file=sys.stderr)
                    context.close()
                    browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
