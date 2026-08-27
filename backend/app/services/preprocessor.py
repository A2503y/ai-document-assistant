import re


def normalize_text(text: str) -> str:
    """
    Clean and normalize extracted document text
    without changing its meaning.
    """

    # Remove leading and trailing whitespace
    text = text.strip()

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces into one
    text = re.sub(r"[ ]{2,}", " ", text)

    # Preserve paragraph breaks (maximum one blank line)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text