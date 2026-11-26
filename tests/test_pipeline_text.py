from app.data.chunk import chunk_document
from app.data.clean import clean_text, mark_inline_headers
from app.data.redact import redact
from app.data.sections import split_sections


def test_redact_keeps_dates_removes_contacts():
    t = redact("Call +91 98765 43210 or mail a.b@x.com, worked 2015-2019, see linkedin.com/in/abc")
    assert "[PHONE]" in t and "[EMAIL]" in t and "[URL]" in t and "2015-2019" in t


def test_inline_headers_and_sections():
    raw = "DATA ANALYST   Summary    Analyst with 4 years.   Skills    Python, SQL   Experience   Acme 2019-2023"
    text = clean_text(mark_inline_headers(raw))
    s = split_sections(text, "resume")
    assert {"summary", "skills", "experience"} <= set(s)
    assert "Python" in s["skills"]


def test_mandatory_only_near_trigger_and_preferred_zone():
    from app.tools.extract import keyword_profile
    jd = "Requirements: Python, SQL, food safety depending on the role. Must have Excel. Nice to have: Docker."
    p = keyword_profile(jd, "jd")
    assert p.skills["microsoft excel"].mandatory
    assert not p.skills["food safety"].mandatory and not p.skills["python"].mandatory
    assert p.skills["docker"].required is False and p.skills["sql"].required is True


def test_chunks_have_metadata():
    text = "## Skills\n" + "Python, SQL. " * 200
    ch = chunk_document("d1", text, "resume")
    assert ch and all(c["n_chars"] <= 1200 and c["section"] == "skills" for c in ch)


def test_live_jobs_search_all_interleaves_and_survives_partial_failure(monkeypatch):
    from app.data import live_jobs

    monkeypatch.setattr(live_jobs, "adzuna", lambda q, limit: [
        {"source": "adzuna", "job_id": "a1", "title": "A1", "company": "C1", "url": "u1", "text": "t1"},
    ])
    monkeypatch.setattr(live_jobs, "remotive", lambda q, limit: [
        {"source": "remotive", "job_id": "r1", "title": "R1", "company": "C2", "url": "u2", "text": "t2"},
    ])
    rows = live_jobs.search("python", source="all", limit=5)
    assert [r["job_id"] for r in rows] == ["a1", "r1"]

    def boom(q, limit):
        raise RuntimeError("remotive down")

    monkeypatch.setattr(live_jobs, "remotive", boom)
    rows2 = live_jobs.search("python", source="all", limit=5)
    assert [r["job_id"] for r in rows2] == ["a1"]
