"""DoD 2 proof: model loads and answers a basic + a structured prompt. Run: python scripts/smoke_test.py"""
import sys
import time
from pathlib import Path

# `python scripts/smoke_test.py` puts this script's own directory on sys.path, not the project
# root (unlike `python -m app.cli`), so `import app` fails unless we add it ourselves.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.llm.provider import chat_json, chat_text, model_status  # noqa: E402


class Skills(BaseModel):
    skills: list[str]


def main() -> int:
    st = model_status()
    ok = st.get("loaded")
    # st["model"] (not settings.llm_model) reflects whichever provider is actually active:
    # Ollama's local phi3:mini, or the hosted openai_compatible model.
    print(f"[{'OK' if ok else 'FAIL'}] model={st.get('model')} provider={st.get('provider')} ctx={settings.num_ctx}")
    if not ok:
        print("  ->", st.get("error") or f"run: ollama pull {settings.llm_model}")
        return 1

    t0 = time.time()
    ans = chat_text("Answer with a number only.", "What is 2+2?")
    t1 = time.time() - t0
    print(f"[{'OK' if '4' in ans else 'FAIL'}] basic: {ans!r} ({t1:.1f}s)")

    t0 = time.time()
    # Mirrors the real extraction prompt's "1-4 words, no sentences" instruction (app/llm/prompts.py):
    # a vaguer prompt lets small local models like phi3:mini return whole phrases ("ETL jobs in
    # Python") instead of skill names, which is a prompt-quality bug in the test, not a model failure.
    out = chat_json(
        "Extract technical skills from a resume. Each skill: 1-3 words, a tool/technology/language "
        "name only, never a sentence or phrase describing what was done with it.",
        "Resume: Built ETL jobs in Python and SQL, dashboards in Tableau.", Skills)
    names = [s.lower() for s in out.skills]
    good = (all(len(n.split()) <= 3 for n in names)
            and any("python" in n for n in names) and any("sql" in n for n in names))
    print(f"[{'OK' if good else 'FAIL'}] structured: {out.model_dump()} ({time.time() - t0:.1f}s)")
    return 0 if ("4" in ans and good) else 1


if __name__ == "__main__":
    sys.exit(main())
