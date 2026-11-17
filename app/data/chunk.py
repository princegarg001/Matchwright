"""Section-aware chunking sized for Phi-3-mini's 4K context."""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.data.sections import split_sections

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1200, chunk_overlap=150, separators=["\n\n", "\n", "; ", ". ", " ", ""]
)
# Most useful sections first: extraction stops after settings.max_chunks_per_doc chunks.
PRIORITY = {
    "resume": ["skills", "experience", "summary", "certifications", "projects", "education", "other"],
    "jd": ["requirements", "preferred", "responsibilities", "other", "about"],
}


def chunk_document(doc_id: str, text: str, doc_type: str, meta: dict | None = None) -> list[dict]:
    sections = split_sections(text, doc_type)
    order = PRIORITY[doc_type] + [s for s in sections if s not in PRIORITY[doc_type]]
    chunks, cursor = [], 0
    for section in order:
        if section not in sections:
            continue
        for piece in SPLITTER.split_text(sections[section]):
            start = text.find(piece[:80], 0)
            cursor = start if start >= 0 else cursor
            chunks.append({
                "doc_id": doc_id, "doc_type": doc_type, "section": section,
                "chunk_idx": len(chunks), "char_span": [cursor, cursor + len(piece)],
                "text": piece, "n_chars": len(piece), **(meta or {}),
            })
    return chunks
