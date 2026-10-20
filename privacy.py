"""Remove customer personal information before analysis or API use."""
import re
from typing import Iterable
import pandas as pd

PII_PATTERNS = ("name", "phone", "mobile", "address", "email", "customer", "recipient", "contact")

def is_personal_column(column: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower())
    return any(token in normalized for token in PII_PATTERNS)

def remove_personal_information(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    removed = [str(c) for c in frame.columns if is_personal_column(str(c))]
    return frame.drop(columns=removed, errors="ignore").copy(), removed

def sanitize_mapping(values: dict, allowed: Iterable[str]) -> dict:
    allowed_set = set(allowed)
    return {k: v for k, v in values.items() if k in allowed_set and "key" not in k.lower()}

def redact_text(text: str) -> str:
    """Redact common email addresses and Bangladesh-style phone numbers."""
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED EMAIL]", text)
    return re.sub(r"(?:\+?88)?01[3-9]\d{8}", "[REDACTED PHONE]", text)
