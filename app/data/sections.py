"""Split a resume or JD into named sections using a header dictionary."""
import re

RESUME_HEADERS = {
    "summary": ["professional summary", "executive profile", "career overview", "summary", "profile", "objective"],
    "skills": ["skill highlights", "technical skills", "core competencies", "highlights", "skills", "qualifications"],
    "experience": ["professional experience", "work experience", "work history", "employment history", "experience"],
    "education": ["education and training", "academic background", "education"],
    "certifications": ["licenses and certifications", "certifications", "certificates", "licenses"],
    "projects": ["accomplishments", "projects"],
}
JD_HEADERS = {
    "responsibilities": ["responsibilities", "what you will do", "what you'll do", "key duties", "duties", "the role"],
    "requirements": ["minimum qualifications", "basic qualifications", "requirements", "qualifications",
                     "what you bring", "must have", "required skills", "who you are"],
    "preferred": ["preferred qualifications", "nice to have", "preferred", "bonus points", "pluses"],
    "about": ["about the company", "about us", "who we are", "benefits", "perks"],
}


def _regex(headers: dict[str, list[str]]) -> re.Pattern:
    alts = sorted({h for hs in headers.values() for h in hs}, key=len, reverse=True)
    return re.compile(r"^[ \t]*(?:##[ \t]*)?(" + "|".join(map(re.escape, alts)) + r")[ \t]*:?[ \t]*$", re.I | re.M)


_RX = {"resume": _regex(RESUME_HEADERS), "jd": _regex(JD_HEADERS)}
_LOOKUP = {
    "resume": {h: k for k, hs in RESUME_HEADERS.items() for h in hs},
    "jd": {h: k for k, hs in JD_HEADERS.items() for h in hs},
}


def split_sections(text: str, doc_type: str) -> dict[str, str]:
    """Return {section_name: body}. Text before the first header goes to 'other'."""
    rx, lookup = _RX[doc_type], _LOOKUP[doc_type]
    sections: dict[str, str] = {}
    key, last_end = "other", 0

    def add(k: str, body: str) -> None:
        body = body.strip()
        if body:
            sections[k] = (sections.get(k, "") + "\n" + body).strip()

    for m in rx.finditer(text):
        add(key, text[last_end:m.start()])
        key, last_end = lookup[m.group(1).lower()], m.end()
    add(key, text[last_end:])
    return sections
