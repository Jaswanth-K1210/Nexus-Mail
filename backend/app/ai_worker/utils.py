import re

def sanitize_for_prompt(text: str, max_length: int = 3000) -> str:
    """
    Sanitizes user-controlled input for LLM prompts.
    1. Strips lines starting with SYSTEM:, INSTRUCTION:, IGNORE PREVIOUS
    2. Truncates to max_length at word boundary
    3. Removes markdown formatting that could confuse LLM
    """
    if not text:
        return ""
    lines = text.splitlines()
    filtered = [
        line for line in lines
        if not re.match(
            r"^\s*(SYSTEM:|INSTRUCTION:|IGNORE PREVIOUS|ASSISTANT:|<\|)",
            line.strip(),
            re.IGNORECASE,
        )
    ]
    sanitized = "\n".join(filtered)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rsplit(' ', 1)[0]
    sanitized = re.sub(r'[`*_~>"]', "", sanitized)
    return sanitized
