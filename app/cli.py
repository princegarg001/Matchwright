"""python -m app.cli match --resume r.txt --jd j.txt
   python -m app.cli batch samples/pairs.yaml --out reports/pairs.md"""
import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from app.agent.executor import run_match
from app.core.config import settings

PROC = Path(settings.data_dir) / "processed"


def resolve(ref: str) -> str:
    if ref.startswith("kaggle:"):
        df = pd.read_parquet(PROC / "resumes.parquet")
        return df.loc[df["doc_id"] == "res_" + ref.split(":", 1)[1], "text"].iat[0]
    if ref.startswith("linkedin:"):
        df = pd.read_parquet(PROC / "jds.parquet")
        return df.loc[df["doc_id"] == "jd_" + ref.split(":", 1)[1], "text"].iat[0]
    return Path(ref).read_text(encoding="utf-8")


def cmd_match(a) -> None:
    res = run_match(resolve(a.resume), resolve(a.jd), return_trace=True)
    print(json.dumps(res.model_dump(), indent=2))


def cmd_batch(a) -> None:
    cfg = yaml.safe_load(Path(a.file).read_text())
    lines = ["# Scored resume/JD pairs", "",
             "| # | Pair | Score | Band | Mode | Latency |", "|---|---|---|---|---|---|"]
    details = []
    for i, p in enumerate(cfg["pairs"], 1):
        r = run_match(resolve(p["resume"]), resolve(p["jd"]), return_trace=True)
        lines.append(f"| {i} | {p['name']} | {r.score} | {r.band} | {r.mode} | {r.latency_ms} ms |")
        bullets = "\n".join(f"- {b}" for b in r.justifications) or f"- {r.message}"
        trace = "\n".join(f"{s.get('step')}. {s.get('tool')}({s.get('input')}) -> {s.get('output')} "
                          f"[{s.get('by')}, {s.get('ms')} ms]" for s in r.trace if "tool" in s)
        details.append(f"## {i}. {p['name']}\n\n**Score {r.score} ({r.band}, confidence {r.confidence})**\n\n"
                       f"{bullets}\n\nMissing: {', '.join(r.missing_skills) or 'none'}\n\n"
                       f"```text\n{trace}\n```\n")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines) + "\n\n" + "\n".join(details))
    print("\n".join(lines))
    print(f"\nWrote {a.out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(required=True)
    m = sub.add_parser("match"); m.add_argument("--resume", required=True); m.add_argument("--jd", required=True)
    m.set_defaults(fn=cmd_match)
    b = sub.add_parser("batch"); b.add_argument("file"); b.add_argument("--out", default="reports/pairs.md")
    b.set_defaults(fn=cmd_batch)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
