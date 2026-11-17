"""Uploaded file -> text. Rejects image-only PDFs (no text layer) with a clear error."""
import io

from fastapi import HTTPException, UploadFile

from app.data.clean import clean_text

ALLOWED = {"application/pdf", "text/plain",
           "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


async def file_to_text(f: UploadFile, max_mb: float) -> str:
    data = await f.read()
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"File larger than {max_mb} MB")
    name = (f.filename or "").lower()
    if f.content_type not in ALLOWED and not name.endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(415, "Upload a PDF, DOCX or TXT file")
    try:
        if name.endswith(".pdf") or f.content_type == "application/pdf":
            from pypdf import PdfReader
            text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
        elif name.endswith(".docx"):
            from docx import Document
            text = "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
        else:
            text = data.decode("utf-8", errors="ignore")
    except Exception as e:  # corrupt or password-protected file
        raise HTTPException(422, f"Could not read this file ({type(e).__name__}). Re-export it and try again.") from e
    if len(text.strip()) < 50:
        raise HTTPException(422, "No readable text found (scanned image PDF?). Upload a text-based PDF or DOCX.")
    return clean_text(text)
