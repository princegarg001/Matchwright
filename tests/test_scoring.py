from app.core.models import Profile, SkillEntry
from app.taxonomy.normalizer import Normalizer
from app.tools.explain import facts, grounded, template_bullets
from app.tools.scoring import score_match

NORM = Normalizer("config/aliases.yaml")


def prof(doc_type, skills, years=None, edu="unknown", required=None, mandatory=()):
    required = required if required is not None else set(skills)
    return Profile(doc_type=doc_type, normalized=True, years_experience=years, education_level=edu,
                   extraction_mode="llm", agreement=0.8,
                   skills={s: SkillEntry(canonical=s, required=s in required, mandatory=s in mandatory)
                           for s in skills})


def test_alias_and_clean():
    assert NORM.canon("Sklearn") == "scikit-learn"
    assert NORM.canon("PySpark") == "apache spark"
    assert NORM.canon("Python 3") == "python"
    assert NORM.related("tensorflow", "pytorch")


def test_perfect_match_is_strong():
    jd = prof("jd", ["python", "sql", "tableau"], years=3, edu="bachelor")
    cv = prof("resume", ["python", "sql", "tableau", "git"], years=5, edu="master")
    b = score_match(cv, jd, NORM)
    assert b.score == 100 and b.band == "strong" and b.missing_skills == []


def test_no_overlap_is_weak():
    jd = prof("jd", ["python", "machine learning", "docker"], years=3)
    cv = prof("resume", ["food safety", "customer service"], years=6)
    b = score_match(cv, jd, NORM)
    assert b.band == "weak" and set(b.missing_skills) == {"python", "machine learning", "docker"}


def test_closest_related_skill_wins():
    jd = prof("jd", ["pytorch"])
    cv = prof("resume", ["statistics", "tensorflow"])
    b = score_match(cv, jd, NORM)
    assert b.matches[0].matched_with == "tensorflow"


def test_evidence_snippet_is_cut_at_words():
    from app.taxonomy.normalizer import snippet
    text = "Data analyst with 5 years of experience. Skills: Python, SQL, Tableau and more tools here."
    i = text.index("Python")
    out = snippet(text, i, i + 6, pad=20)
    assert out.startswith("…") and "Python" in out and not out[1:].startswith(("ears", "yst"))


def test_related_skill_gets_partial_credit():
    jd = prof("jd", ["pytorch"])
    cv = prof("resume", ["tensorflow"])
    b = score_match(cv, jd, NORM)
    assert b.matches[0].kind == "related" and b.sub_scores["required"] == 0.7


def test_knockout_caps_at_60():
    jd = prof("jd", ["python", "sql", "kubernetes"], mandatory={"kubernetes"})
    cv = prof("resume", ["python", "sql"])
    b = score_match(cv, jd, NORM)
    assert b.knockout_applied and b.score <= 60


def test_experience_shortfall_lowers_score():
    jd = prof("jd", ["python"], years=6)
    a = score_match(prof("resume", ["python"], years=6), jd, NORM).score
    b = score_match(prof("resume", ["python"], years=2), jd, NORM).score
    assert a > b


def test_semantic_weight_renormalised_when_missing():
    jd, cv = prof("jd", ["python"]), prof("resume", ["python"])
    b = score_match(cv, jd, NORM, text_sim=None)
    assert "semantic" not in b.weights and abs(sum(b.weights.values()) - 1) < 0.01


def test_deterministic():
    jd = prof("jd", ["python", "sql", "docker"], years=3)
    cv = prof("resume", ["python", "docker"], years=2)
    assert score_match(cv, jd, NORM).score == score_match(cv, jd, NORM).score


def test_template_bullets_are_three_and_grounded():
    jd = prof("jd", ["python", "sql", "docker"], years=3)
    cv = prof("resume", ["python"], years=2)
    b = score_match(cv, jd, NORM)
    bullets = template_bullets(b)
    assert len(bullets) == 3
    assert all(grounded(x, facts(b)) for x in bullets)


def test_grounding_rejects_invented_numbers():
    jd, cv = prof("jd", ["python"], years=3), prof("resume", ["python"], years=4)
    f = facts(score_match(cv, jd, NORM))
    assert not grounded("Has 12 years of python experience.", f)
