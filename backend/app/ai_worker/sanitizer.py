"""
Nexus Mail — Email Sanitizer
Cleans raw email bodies before sending to the AI pipeline.

ARCHITECTURE FIX (Inbox Zero Analysis):
Inbox Zero strips tracking pixels, excess CSS, HTML formatting, and normalizes
to clean text before sending to the LLM — "fiercely optimizing token usage."

Our old approach: Pass raw body_text or body_html directly to the AI.
HTML emails waste massive tokens on CSS, tracking pixels, and formatting.

Impact: Can reduce token consumption by 40-70% on HTML-heavy emails.
"""

import re
from html import unescape


def sanitize_email_body(body_text: str = "", body_html: str = "") -> str:
    """
    Clean and normalize email content for AI processing.
    Returns clean text optimized for LLM token efficiency.

    Priority: body_text > cleaned body_html
    """
    # Prefer plain text if available and substantial
    if body_text and len(body_text.strip()) > 50:
        return _clean_plain_text(body_text)

    # Fall back to cleaning HTML
    if body_html:
        return _html_to_clean_text(body_html)

    # Last resort
    return body_text.strip() if body_text else ""


def _html_to_clean_text(html: str) -> str:
    """Convert HTML email to clean text, stripping all noise."""

    # Remove tracking pixels (1x1 images, zero-width images)
    html = re.sub(
        r'<img[^>]*(?:width\s*=\s*["\']?[01]["\']?|height\s*=\s*["\']?[01]["\']?)[^>]*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )

    # Remove all tracking pixel images (common patterns)
    html = re.sub(
        r'<img[^>]*(?:track|pixel|beacon|open|wf\.gif|\.gif\?)[^>]*/?>',
        "",
        html,
        flags=re.IGNORECASE,
    )

    # Remove <style> blocks entirely
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove <script> blocks
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

    # Remove hidden elements
    html = re.sub(
        r'<[^>]*(?:display\s*:\s*none|visibility\s*:\s*hidden)[^>]*>.*?</[^>]*>',
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Convert <br>, <br/>, <br /> to newlines
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)

    # Convert </p>, </div>, </tr>, </li> to newlines
    html = re.sub(r"</(?:p|div|tr|li|h[1-6])>", "\n", html, flags=re.IGNORECASE)

    # Convert <li> to bullet points
    html = re.sub(r"<li[^>]*>", "• ", html, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", html)

    # Decode HTML entities
    text = unescape(text)

    # Clean up whitespace
    return _normalize_whitespace(text)


def _clean_plain_text(text: str) -> str:
    """Clean plain text email content."""

    # Remove email signature separators and everything after
    # Common patterns: "-- ", "___", "---", "Sent from my iPhone"
    sig_patterns = [
        r"\n-- \n.*$",
        r"\n_{3,}\n.*$",
        r"\n-{3,}\n.*$",
        r"\nSent from my (?:iPhone|iPad|Galaxy|Pixel).*$",
        r"\nGet Outlook for .*$",
    ]
    for pattern in sig_patterns:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)

    return _normalize_whitespace(text)


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace for consistent, token-efficient output."""

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces to single space
    text = re.sub(r" {2,}", " ", text)

    # Collapse 3+ newlines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]

    # Remove completely empty lines at the start and end
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    text = "\n".join(lines)

    # Truncate to a reasonable length for the AI (saves tokens on very long emails)
    max_chars = 4000  # ~1000 tokens
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... email truncated for processing ...]"

    return text.strip()
