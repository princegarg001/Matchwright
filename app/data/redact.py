"""PII redaction before any text reaches the LLM. Add Microsoft Presidio for names/addresses if needed."""
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
URL = re.compile(r"https?://\S+|www\.\S+|(?:linkedin|github)\.com/\S+", re.I)
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")


def _phone(m: re.Match) -> str:
    # 10+ digits = phone; keeps date ranges like 2015-2019 (8 digits) intact
    return "[PHONE]" if sum(c.isdigit() for c in m.group()) >= 10 else m.group()


def redact(text: str) -> str:
    text = EMAIL.sub("[EMAIL]", text or "")
    text = URL.sub("[URL]", text)
    return PHONE.sub(_phone, text)
