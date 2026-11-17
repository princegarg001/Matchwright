"""DoD 1 pipeline: download -> clean -> redact -> dedupe -> section/chunk -> split -> pairs -> samples.

Usage:  python -m app.data.pipeline --download --jd-limit 5000 [--live python]
"""
import argparse
import re
import subprocess
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from app.core.config import settings
from app.data.chunk import chunk_document
from app.data.clean import clean_text, doc_hash, html_to_text, mark_inline_headers, near_dup_key
from app.data.redact import redact

RAW = Path(settings.data_dir) / "raw"
OUT = Path(settings.data_dir) / "processed"
SEED = 42
STATS: list[dict] = []

# LinkedIn title -> Kaggle resume category (silver labels). Extend freely.
TITLE_RULES = [
    (r"data scien|machine learning|software|developer|engineer.*(software|data|devops|cloud)|devops|it support|"
     r"system admin|network|cyber|programmer|full.?stack|front.?end|back.?end", "INFORMATION-TECHNOLOGY"),
    (r"\bhr\b|human resources|recruit|talent acquisition", "HR"),
    (r"accountant|accounting|bookkeep|auditor", "ACCOUNTANT"),
    (r"financial analyst|finance|fp&a|controller", "FINANCE"),
    (r"bank|teller|loan officer", "BANKING"),
    (r"sales|account executive|business development", "SALES"),
    (r"teacher|tutor|instructor|educator", "TEACHER"),
    (r"chef|cook|culinary|kitchen", "CHEF"),
    (r"nurse|medical|healthcare|clinical|physician", "HEALTHCARE"),
    (r"designer|ux|ui designer|graphic", "DESIGNER"),
    (r"construction|site manager|foreman", "CONSTRUCTION"),
    (r"pilot|aviation|aircraft", "AVIATION"),
    (r"public relations|\bpr\b|communications", "PUBLIC-RELATIONS"),
    (r"consultant", "CONSULTANT"),
    (r"lawyer|attorney|paralegal|legal", "ADVOCATE"),
    (r"fitness|personal trainer", "FITNESS"),
    (r"mechanical engineer|civil engineer|electrical engineer", "ENGINEERING"),
]


def stat(stage: str, rows_in: int, rows_out: int, note: str = "") -> None:
    STATS.append({"stage": stage, "rows_in": rows_in, "rows_out": rows_out, "dropped": rows_in - rows_out,
                  "note": note})


def download() -> None:
    for slug, dest in [("snehaanbhawal/resume-dataset", RAW / "resume"),
                       ("arshkon/linkedin-job-postings", RAW / "linkedin")]:
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(["kaggle", "datasets", "download", "-d", slug, "-p", str(dest), "--unzip"], check=True)


def load_resumes() -> pd.DataFrame:
    path = next((RAW / "resume").rglob("Resume.csv"))
    df = pd.read_csv(path)
    n0 = len(df)
    df["doc_id"] = "res_" + df["ID"].astype(str)
    from_html = df["Resume_html"].fillna("").map(html_to_text)
    from_str = df["Resume_str"].fillna("").map(mark_inline_headers)
    # Prefer the HTML version when it produced section markers, else the inline-header version.
    df["text"] = [h if h.count("## ") >= 2 else s for h, s in zip(from_html, from_str, strict=True)]
    df["text"] = df["text"].map(clean_text).map(redact)
    df = df[df["text"].str.len() >= 300]
    stat("resumes: load+clean+min_len", n0, len(df), "drop < 300 chars")
    return dedupe(df, "resumes")[["doc_id", "Category", "text"]].rename(columns={"Category": "category"})


def load_jds(limit: int) -> pd.DataFrame:
    path = next((RAW / "linkedin").rglob("postings.csv"))
    cols = ["job_id", "title", "company_name", "description", "skills_desc", "formatted_experience_level", "location"]
    df = pd.read_csv(path, usecols=cols)
    n0 = len(df)
    df = df.dropna(subset=["description", "title"])
    if limit and len(df) > limit:
        df = df.sample(limit, random_state=SEED)
    stat("jds: load+sample", n0, len(df), f"dropna + sample {limit}")
    df["doc_id"] = "jd_" + df["job_id"].astype(str)
    skills = df["skills_desc"].fillna("")
    df["text"] = (df["description"] + "\n\nSkills: " + skills).where(skills != "", df["description"])
    n1 = len(df)
    df["text"] = df["text"].map(clean_text).map(redact)
    df = df[df["text"].str.len() >= 300]
    stat("jds: clean+min_len", n1, len(df), "drop < 300 chars")
    df["category"] = df["title"].map(title_to_category)
    return dedupe(df, "jds")[["doc_id", "title", "company_name", "formatted_experience_level", "category", "text"]]


def dedupe(df: pd.DataFrame, name: str) -> pd.DataFrame:
    n0 = len(df)
    df = df.assign(doc_hash=df["text"].map(doc_hash), near_key=df["text"].map(near_dup_key))
    df = df.drop_duplicates("doc_hash").drop_duplicates("near_key")
    stat(f"{name}: dedupe", n0, len(df), "exact + near duplicates")
    return df


def title_to_category(title: str) -> str | None:
    t = (title or "").lower()
    for rx, cat in TITLE_RULES:
        if re.search(rx, t):
            return cat
    return None


def validate(df: pd.DataFrame, name: str, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"{name}: missing columns {missing}"
    assert df["doc_id"].is_unique, f"{name}: duplicate doc_id"
    assert df["text"].str.len().between(300, 60_000).all(), f"{name}: text length out of bounds"


def build_pairs(resumes: pd.DataFrame, jds: pd.DataFrame, n_gold: int = 50) -> None:
    labelled = jds.dropna(subset=["category"])
    test = resumes[resumes["split"] == "test"]
    rows = []
    for _, r in test.iterrows():
        pos = labelled[labelled["category"] == r["category"]]
        neg = labelled[labelled["category"] != r["category"]]
        if len(pos):
            rows.append({"resume_id": r["doc_id"], "job_id": pos.sample(1, random_state=SEED)["doc_id"].iat[0],
                         "silver_label": 1})
        if len(neg):
            rows.append({"resume_id": r["doc_id"], "job_id": neg.sample(1, random_state=SEED)["doc_id"].iat[0],
                         "silver_label": 0})
    pairs = pd.DataFrame(rows)
    pairs.to_csv(OUT / "silver_pairs.csv", index=False)
    per_class = min(n_gold // 2, int(pairs["silver_label"].value_counts().min()))
    gold = pairs.groupby("silver_label").sample(n=per_class, random_state=SEED)
    gold.assign(rating_1_to_5="").to_csv("eval/gold_pairs_template.csv", index=False)
    print(f"pairs: {len(pairs)} silver, {len(gold)} gold candidates -> label them in eval/gold_pairs_template.csv")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--jd-limit", type=int, default=5000)
    ap.add_argument("--live", default="", help="also fetch live JDs for this query from Remotive")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    Path("samples").mkdir(exist_ok=True)
    Path("eval").mkdir(exist_ok=True)

    if args.download:
        download()
    resumes, jds = load_resumes(), load_jds(args.jd_limit)

    if args.live:
        from app.data import live_jobs
        live = pd.DataFrame(live_jobs.search(args.live, "remotive", 50))
        if len(live):
            live = live.rename(columns={"job_id": "doc_id", "company": "company_name"})
            live["category"] = live["title"].map(title_to_category)
            live["text"] = live["text"].map(redact)
            jds = pd.concat([jds, live[live["text"].str.len() >= 300]], ignore_index=True)
            stat("jds: + live remotive", 0, len(live), args.live)

    # stratified 70/15/15 split of resumes by category
    train, rest = train_test_split(resumes, test_size=0.30, stratify=resumes["category"], random_state=SEED)
    dev, test = train_test_split(rest, test_size=0.50, stratify=rest["category"], random_state=SEED)
    resumes["split"] = "train"
    resumes.loc[dev.index, "split"] = "dev"
    resumes.loc[test.index, "split"] = "test"

    validate(resumes, "resumes", ["doc_id", "category", "text", "split"])
    validate(jds, "jds", ["doc_id", "title", "text"])

    chunks = [c for _, r in resumes.iterrows() for c in chunk_document(r.doc_id, r.text, "resume",
                                                                      {"category": r.category})]
    chunks += [c for _, r in jds.iterrows() for c in chunk_document(r.doc_id, r.text, "jd", {"title": r.title})]
    chunk_df = pd.DataFrame(chunks)
    stat("chunks", len(chunk_df), len(chunk_df), f"{len(resumes)} resumes + {len(jds)} JDs -> {len(chunk_df)} chunks")

    resumes.to_parquet(OUT / "resumes.parquet", index=False)
    jds.to_parquet(OUT / "jds.parquet", index=False)
    chunk_df.to_parquet(OUT / "chunks.parquet", index=False)
    build_pairs(resumes, jds)

    sample = chunk_df.groupby("doc_type").head(3).dropna(axis=1, how="all")
    sample.to_json("samples/chunks_sample.json", orient="records", indent=2, force_ascii=False)

    print("\n=== Stage summary ===")
    print(pd.DataFrame(STATS).to_string(index=False))
    print("\n=== Resume categories (split counts) ===")
    print(pd.crosstab(resumes["category"], resumes["split"]).to_string())
    print("\n=== Sections per chunk ===")
    print(chunk_df.groupby(["doc_type", "section"]).size().to_string())
    print("\nWrote data/processed/*.parquet and samples/chunks_sample.json")


if __name__ == "__main__":
    main()
