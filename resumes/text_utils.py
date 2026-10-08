"""
Small shared text helpers.

Used by both resume parsing (PDF/DOCX) and job-page extraction. Extraction
engines leave behind inconsistent whitespace; normalizing it in one place
keeps behavior identical everywhere (and every wasted character costs tokens).
"""


def clean_text(text):
    """
    Normalize the messy whitespace that extraction tools leave behind.

    Each line gets inner whitespace collapsed, then runs of 3+ blank lines
    are squeezed to a single blank line. Keeps the text readable for both
    the user and the AI.
    """
    lines = []

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = " ".join(raw_line.split())
        lines.append(line)

    cleaned = "\n".join(lines)

    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")

    return cleaned.strip()
