"""Spearman vs human ratings + NDCG@5, against TF-IDF and keyword baselines. Writes reports/eval.md."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import ndcg_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agent.executor import run_match  # noqa: E402

P = Path("data/processed")
gold = pd.read_csv("eval/gold_pairs.csv").dropna(subset=["rating_1_to_5"])
res = pd.read_parquet(P / "resumes.parquet").set_index("doc_id")["text"]
jds = pd.read_parquet(P / "jds.parquet").set_index("doc_id")["text"]

tfidf = TfidfVectorizer(stop_words="english", max_features=20000).fit(pd.concat([res, jds]))
rows = []
for _, g in gold.iterrows():
    r, j = res[g.resume_id], jds[g.job_id]
    m = run_match(r, j)
    v = tfidf.transform([r, j])
    rows.append({"resume_id": g.resume_id, "job_id": g.job_id, "human": g.rating_1_to_5,
                 "ours": m.score if m.score is not None else 0, "mode": m.mode, "latency_ms": m.latency_ms,
                 "tfidf": float((v[0] @ v[1].T).toarray()[0, 0]) * 100})
df = pd.DataFrame(rows)

lines = ["# Evaluation", "", f"Pairs: {len(df)}", "", "| Method | Spearman ρ | NDCG@5 (per JD) |", "|---|---|---|"]
for col in ["ours", "tfidf"]:
    rho = spearmanr(df["human"], df[col]).statistic
    nd = [ndcg_score([g["human"].to_numpy()], [g[col].to_numpy()], k=5)
          for _, g in df.groupby("job_id") if len(g) >= 2]
    lines.append(f"| {col} | {rho:.3f} | {np.mean(nd):.3f} |" if nd else f"| {col} | {rho:.3f} | n/a |")
lines += ["", f"Latency p50 {df.latency_ms.median():.0f} ms, p95 {df.latency_ms.quantile(.95):.0f} ms",
          "", "Modes: " + ", ".join(f"{k}={v}" for k, v in df["mode"].value_counts().items())]
Path("reports").mkdir(exist_ok=True)
Path("reports/eval.md").write_text("\n".join(lines))
df.to_csv("reports/eval_rows.csv", index=False)
print("\n".join(lines))
