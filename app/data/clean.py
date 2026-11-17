"""Text cleaning: HTML -> text, mojibake, unicode, boilerplate, whitespace."""
import hashlib
import re
import unicodedata

import ftfy
from bs4 import BeautifulSoup

BOILERPLATE = [
    r"(we are an |is an )?equal opportunity employer[^.]*\.?",
    r"all qualified applicants will receive consideration[^.]*\.?",
    r"reasonable accommodations?[^.]*\.?",
]
ZERO_WIDTH = re.compile(r"[​-‏⁠﻿]")

RESUME_HEADER_WORDS = [
    "Professional Summary", "Executive Profile", "Career Overview", "Summary", "Profile", "Objective",
    "Skill Highlights", "Technical Skills", "Core Competencies", "Highlights", "Skills", "Qualifications",
    "Professional Experience", "Work Experience", "Work History", "Experience",
    "Education and Training", "Education", "Certifications", "Licenses", "Accomplishments", "Projects",
]
_INLINE_HEADER = re.compile(
    r"(?:^|\s{2,})(" + "|".join(re.escape(h) for h in RESUME_HEADER_WORDS) + r")(?=\s{2,}|\s*$)",
    re.M,
)


def html_to_text(html: str) -> str:
    """Keep section titles as '## Title' markers so sectioning works later."""
    soup = BeautifulSoup(html or "", "lxml")
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        tag.insert_before("\n## ")
        tag.insert_after("\n")
    # LiveCareer exports usually mark headings with class="sectiontitle"; inspect one row and adjust if not.
    for div in soup.select(".sectiontitle"):
        div.insert_before("\n## ")
        div.insert_after("\n")
    return soup.get_text("\n")


def mark_inline_headers(text: str) -> str:
    """Kaggle Resume_str puts headings inline between runs of spaces: '   Summary     Dedicated...'."""
    return _INLINE_HEADER.sub(lambda m: f"\n## {m.group(1)}\n", text or "")


def clean_text(text: str) -> str:
    text = ftfy.fix_text(text or "")
    text = unicodedata.normalize("NFKC", text)
    text = ZERO_WIDTH.sub("", text)  # also strips a common prompt-injection hiding trick
    for pat in BOILERPLATE:
        text = re.sub(pat, " ", text, flags=re.I)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def doc_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def near_dup_key(text: str) -> str:
    """Cheap near-duplicate key: first 600 alphanumerics. Swap for MinHash (datasketch) if you want."""
    norm = re.sub(r"\W+", "", text.lower())[:600]
    return hashlib.md5(norm.encode()).hexdigest()
