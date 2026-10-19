from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .ocr import extract_text
from .rules import run_rules

BASE = Path(__file__).parent
app = FastAPI(title="Legal Metrology Checker")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/api/check")
async def check(image: UploadFile | None = File(None), text: str = Form("")):
    """Check a label. Send an image (OCR is run) or pasted label text."""
    if image is not None and image.filename:
        data = await image.read()
        try:
            text = extract_text(data)
        except Exception:
            raise HTTPException(400, "Could not read that file as an image.")
    if not text.strip():
        raise HTTPException(400, "Send a label image or some label text.")
    out = run_rules(text)
    out["extracted_text"] = text
    return out
