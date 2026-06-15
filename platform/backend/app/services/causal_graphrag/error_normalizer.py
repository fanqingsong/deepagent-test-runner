"""
Error message normalization utilities.

Turns raw, noisy Playwright/LLM error strings into:
- a coarse `category` (Timeout, SelectorNotFound, Assertion, Navigation, ...)
- a stable `signature` (category + first extracted selector) used to group
  similar failures into the same graph node / failure community.
- the list of CSS/XPath/text selectors mentioned in the message.
"""

import re
from typing import List, Optional, Tuple

# Ordered (category, compiled pattern) - first match wins.
_CATEGORY_PATTERNS = [
    ("Timeout", re.compile(r"timeout|timed out|exceeded|deadline", re.IGNORECASE)),
    (
        "SelectorNotFound",
        re.compile(
            r"no element|not found|waiting for selector|locator.*resolved to 0|"
            r"element is not|no node found|unable to find",
            re.IGNORECASE,
        ),
    ),
    (
        "Assertion",
        re.compile(
            r"assert|expect|to be visible|to have text|tohavetext|tobevisible|"
            r"received.*expected|did not match",
            re.IGNORECASE,
        ),
    ),
    (
        "Navigation",
        re.compile(
            r"net::|err_|econnrefused|navigation|page\.goto|net_error|"
            r"dns|connection refused|ssl",
            re.IGNORECASE,
        ),
    ),
    ("Auth", re.compile(r"401|403|unauthor|forbidden|login failed|invalid credentials", re.IGNORECASE)),
    ("ServerError", re.compile(r"500|502|503|504|internal server error|bad gateway", re.IGNORECASE)),
    ("ScriptError", re.compile(r"syntaxerror|referenceerror|typeerror|is not a function|undefined", re.IGNORECASE)),
]

# Selector extraction patterns.
_SELECTOR_PATTERNS = [
    re.compile(r"""waiting for selector ["'`]([^"'`]+)["'`]""", re.IGNORECASE),
    re.compile(r"""locator\(\s*["'`]([^"'`]+)["'`]""", re.IGNORECASE),
    re.compile(r"""selector[:=]?\s*["'`]([^"'`]+)["'`]""", re.IGNORECASE),
    re.compile(r"""get_by_\w+\(\s*["'`]([^"'`]+)["'`]""", re.IGNORECASE),
    # Bare CSS id/class or xpath tokens. The lookbehind avoids matching method
    # calls like "page.click" / "locator.fill" as ".click" / ".fill".
    re.compile(r"(?<![\w)])(#[A-Za-z][\w\-]+)"),
    re.compile(r"(?<![\w)])(\.[A-Za-z][\w\-]{2,})"),
    re.compile(r"(//[A-Za-z@\[\]\w\-/'\"=\.\s]+)"),
    re.compile(r"""(\[[A-Za-z\-]+=['"][^'"\]]+['"]\])"""),
]


def categorize(error_message: Optional[str]) -> str:
    """Return a coarse category for an error message."""
    if not error_message:
        return "Unknown"
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(error_message):
            return category
    return "Other"


def extract_selectors(error_message: Optional[str], limit: int = 5) -> List[str]:
    """Extract up to `limit` distinct selectors mentioned in an error message."""
    if not error_message:
        return []
    found: List[str] = []
    seen = set()
    for pattern in _SELECTOR_PATTERNS:
        for match in pattern.findall(error_message):
            sel = match.strip()
            # Skip noise: too short, pure numbers, css-color-ish tokens.
            if len(sel) < 2 or sel in seen:
                continue
            if sel.startswith(".") and len(sel) <= 3:
                continue
            seen.add(sel)
            found.append(sel)
            if len(found) >= limit:
                return found
    return found


def normalize(error_message: Optional[str]) -> Tuple[str, str, List[str]]:
    """
    Normalize an error message.

    Returns:
        (category, signature, selectors)
    """
    category = categorize(error_message)
    selectors = extract_selectors(error_message)
    if selectors:
        signature = f"{category}::{selectors[0]}"
    elif error_message:
        # Use a trimmed, lower-cardinality fingerprint of the message.
        cleaned = re.sub(r"\d+", "N", error_message.strip())
        cleaned = re.sub(r"\s+", " ", cleaned)[:80]
        signature = f"{category}::{cleaned}"
    else:
        signature = f"{category}::no-message"
    return category, signature, selectors
