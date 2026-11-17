"""SkillNER (spaCy + EMSI skill DB). Heavy: loads en_core_web_lg once."""
from functools import lru_cache


@lru_cache
def _extractor():
    import spacy
    from skillNer.general_params import SKILL_DB
    from skillNer.skill_extractor_class import SkillExtractor
    from spacy.matcher import PhraseMatcher
    nlp = spacy.load("en_core_web_lg")
    return SkillExtractor(nlp, SKILL_DB, PhraseMatcher), SKILL_DB


def skillner_skills(text: str) -> list[str]:
    ext, db = _extractor()
    res = ext.annotate(text[:20000])["results"]
    ids = {m["skill_id"] for m in res["full_matches"]} | {m["skill_id"] for m in res["ngram_scored"]}
    return sorted({db[i]["skill_name"] for i in ids if i in db})
