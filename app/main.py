from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .ocr import extract_text
from .tinyfish import CaptureError, capture_problem, fetch_listing
from .rules import CATEGORIES, CONTEXTS, run_rules

BASE = Path(__file__).parent
app = FastAPI(title="Legal Metrology Checker")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/api/check")
async def check(image: UploadFile | None = File(None), text: str = Form(""),
                context: str = Form("package"), category: str = Form("general")):
    """Check a label. Send an image (OCR is run) or pasted label text."""
    if image is not None and image.filename:
        data = await image.read()
        try:
            text = extract_text(data)
        except Exception:
            raise HTTPException(400, "Could not read that file as an image.")
    if not text.strip():
        raise HTTPException(400, "Send a label image or some label text.")
    if context not in CONTEXTS or category not in CATEGORIES:
        raise HTTPException(400, "context must be package or listing; category must be general or food.")
    out = run_rules(text, context, category)
    out["extracted_text"] = text
    return out


@app.post("/api/check-url")
async def check_url(url: str = Form(...), category: str = Form("general")):
    """Capture an online listing live with TinyFish, then run the listing-context rules.

    A failed or empty capture is an error (never a pass or a violation): the reviewer
    should treat the product as Needs review.
    """
    if category not in CATEGORIES:
        raise HTTPException(400, "category must be general or food.")
    try:
        cap = fetch_listing(url)
    except CaptureError as e:
        raise HTTPException(e.status, str(e))
    problem = capture_problem(cap["text"])
    if problem:
        # An interstitial, consent or bot-wall page says nothing about the product.
        out = {"overall": "needs_review", "context": "listing", "category": category,
               "results": [{"rule": "capture", "label": "Page capture", "status": "review",
                            "detail": problem + " No declaration was assessed. Needs review, not a violation.",
                            "evidence": ""}]}
    else:
        out = run_rules(cap["text"], "listing", category)
    out["extracted_text"] = cap["text"]
    out["capture"] = cap["capture"]
    return out
