"""DoD 2 proof: model loads and answers a basic + a structured prompt. Run: python scripts/smoke_test.py"""
import sys
import time

from pydantic import BaseModel

from app.core.config import settings
from app.llm.provider import chat_json, chat_text, model_status


class Skills(BaseModel):
    skills: list[str]


def main() -> int:
    st = model_status()
    ok = st.get("loaded")
    print(f"[{'OK' if ok else 'FAIL'}] model={settings.llm_model} provider={st.get('provider')} ctx={settings.num_ctx}")
    if not ok:
        print("  ->", st.get("error") or f"run: ollama pull {settings.llm_model}")
        return 1

    t0 = time.time()
    ans = chat_text("Answer with a number only.", "What is 2+2?")
    t1 = time.time() - t0
    print(f"[{'OK' if '4' in ans else 'FAIL'}] basic: {ans!r} ({t1:.1f}s)")

    t0 = time.time()
    out = chat_json("Extract technical skills as a JSON list.",
                    "Resume: Built ETL jobs in Python and SQL, dashboards in Tableau.", Skills)
    names = {s.lower() for s in out.skills}
    good = {"python", "sql"} <= names
    print(f"[{'OK' if good else 'FAIL'}] structured: {out.model_dump()} ({time.time() - t0:.1f}s)")
    return 0 if ("4" in ans and good) else 1


if __name__ == "__main__":
    sys.exit(main())
