# Scored resume/JD pairs

Real run against Groq (`openai/gpt-oss-120b` for extraction/scoring/explanation,
`qwen/qwen3.8-27b` for the ReAct agent loop), 18 Nov 2026. Pairs were selected by actual
keyword-skill overlap between a candidate resume and JD, not just a shared Kaggle category label
(same broad category does not guarantee topical overlap) — see README "Agent trace" for the
selection method. `confidence: low` and `mode: ... + keyword fallback` below reflect Groq's
free-tier tokens-per-minute cap on this large model under a rapid 5-pair/15-call batch: several
individual extraction calls hit the cap and fell back to the deterministic keyword extractor —
exactly the graceful-degradation path this project is designed to exercise, not a failure. Scores
are correct and reproducible either way, since scoring is pure Python regardless of which
extractor ran.

| # | Pair | Score | Band | Mode | Latency |
|---|---|---|---|---|---|
| 1 | Weak (37) - IT resume vs Data Scientist - Senior (V2X Inc) | 37 | weak | agent | 76825 ms |
| 2 | Good (72) - IT/Java resume vs a live-fetched posting (Remotive, Senior Data Engineer) | 72 | good | agent | 71146 ms |
| 3 | Good (67) - Accountant resume vs Financial Analyst | 67 | good | agent | 70147 ms |
| 4 | Weak (14) - Chef resume vs Lead Machine Learning Engineer | 14 | weak | agent | 72310 ms |
| 5 | Strong (100) - HR resume vs HR Consultant, Employee Benefits (RogersGray) | 100 | strong | fallback_orchestrator | 285694 ms |

## 1. Weak (37) - IT resume vs Data Scientist - Senior (V2X Inc)

**Score 37 (weak, confidence low)**

- Directly matches 1 of 3 required skills (statistics).
- Years of experience could not be determined from the resume. Education is below the stated requirement.
- Missing required skills: deep learning, natural language processing.

Missing: deep learning, natural language processing

```text
1. extract_skills(resume) -> resume profile stored: 36 skills, unknown years, mode=llm [agent, 31829 ms]
2. extract_skills(jd) -> jd profile stored: 14 skills (3 required), 20 years required, mode=keyword [agent, 31359 ms]
3. normalize_skills(both) -> normalized: resume 34 skills, jd 14 skills [agent, 0 ms]
4. score_match(run) -> score=37 band=weak required 1/3 [agent, 0 ms]
5. explain_match(run) -> 3 justifications written [agent, 5298 ms]
```

## 2. Good (72) - IT/Java resume vs a live-fetched posting (Remotive, Senior Data Engineer)

**Score 72 (good, confidence low)**

- Directly matches 8 of 15 required skills (amazon web services, java, javascript), plus 4 through related skills.
- 3 years of experience falls short of the 4-year requirement. Education meets the requirement.
- Missing required skills: c++, machine learning, python.

Missing: c++, machine learning, python

```text
1. extract_skills(resume) -> resume profile stored: 15 skills, 3 years, mode=keyword [agent, 30684 ms]
2. extract_skills(jd) -> jd profile stored: 15 skills (15 required), 4 years required, mode=keyword [agent, 31079 ms]
3. normalize_skills(both) -> normalized: resume 15 skills, jd 15 skills [agent, 0 ms]
4. score_match(run) -> score=72 band=good required 12/15 [agent, 0 ms]
5. explain_match(run) -> 3 justifications written [agent, 5111 ms]
```

## 3. Good (67) - Accountant resume vs Financial Analyst

**Score 67 (good, confidence low)**

- Directly matches 4 of 6 required skills (accounts payable, financial analysis, microsoft excel).
- Years of experience could not be determined from the resume. Education is below the stated requirement.
- Missing required skills: data visualization, sql.

Missing: data visualization, sql

```text
1. extract_skills(resume) -> resume profile stored: 8 skills, unknown years, mode=keyword [agent, 30861 ms]
2. extract_skills(jd) -> jd profile stored: 6 skills (6 required), unknown years required, mode=keyword [agent, 30650 ms]
3. normalize_skills(both) -> normalized: resume 8 skills, jd 6 skills [agent, 0 ms]
4. score_match(run) -> score=67 band=good required 4/6 [agent, 0 ms]
5. explain_match(run) -> 3 justifications written [agent, 4898 ms]
```

## 4. Weak (14) - Chef resume vs Lead Machine Learning Engineer

**Score 14 (weak, confidence low)**

- Directly matches 1 of 7 required skills (accounts receivable).
- Years of experience could not be determined from the resume. Education is below the stated requirement.
- Missing required skills: ci/cd, git, linux.

Missing: ci/cd, git, linux, numpy, pandas, statistics

```text
1. extract_skills(resume) -> resume profile stored: 5 skills, unknown years, mode=keyword [agent, 31049 ms]
2. extract_skills(jd) -> jd profile stored: 18 skills (7 required), 5 years required, mode=keyword [agent, 31589 ms]
3. normalize_skills(both) -> normalized: resume 5 skills, jd 18 skills [agent, 0 ms]
4. score_match(run) -> score=14 band=weak required 1/7 [agent, 0 ms]
5. explain_match(run) -> 3 justifications written [agent, 5197 ms]
```

## 5. Strong (100) - HR resume vs HR Consultant, Employee Benefits (RogersGray)

**Score 100 (strong, confidence low)**

- Matched skills: microsoft excel, onboarding, payroll, recruiting.
- 18 years experience vs 4 required; education requirement met.
- No required skill is missing.

Missing: none

```text
1. extract_skills(resume) -> resume profile stored: 9 skills, 18 years, mode=keyword [agent, 39514 ms]
2. extract_skills(jd) -> jd profile stored: 4 skills (4 required), 4 years required, mode=keyword [agent, 116572 ms]
3. normalize_skills(both) -> normalized: resume 9 skills, jd 4 skills [agent, 0 ms]
4. score_match(run) -> score=100 band=strong required 4/4 [agent, 0 ms]
5. explain_match(run) -> 3 justifications written [fallback, 16023 ms]
```
