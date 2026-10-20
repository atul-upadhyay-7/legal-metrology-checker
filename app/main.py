from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .ocr import extract_text
from .tinyfish import CaptureError, capture_problem, fetch_listing
from .rules import CATEGORIES, CONTEXTS, run_rules

BASE = Path(__file__).parent
app = FastAPI(title="Legal Metrology Checker")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.get("/api/samples")
def samples():
    """Sample texts for the UI so the demo works without a photo or a live page."""
    S = BASE.parent / "samples"
    rd = lambda n: (S / n).read_text()
    return {
        "listing": [
            {"title": "Complete listing", "text": rd("listing_01_complete.txt"), "category": "food"},
            {"title": "Missing MRP", "text": rd("listing_02_missing_mrp.txt"), "category": "food"},
        ],
        "package": [
            {"title": "Compliant label", "text": rd("01_compliant.txt"), "category": "general"},
            {"title": "No tax on MRP", "text": rd("02_missing_mrp_tax.txt"), "category": "general"},
            {"title": "Best-before only", "text": rd("04_expiry_only_review.txt"), "category": "general"},
        ],
    }


PAGES = [
    ("/", "home", "Home", "Home"),
    ("/check", "check", "Checker", "Check a product"),
    ("/results", "results", "Results", "Results"),
    ("/how-it-works", "how", "How it works", "How it works"),
    ("/about", "about", "About", "About"),
]
NAV = [p for p in PAGES if p[1] != "results"]
PAGE_SCRIPTS = {"check": ["check.js"], "results": ["results.js"]}


def _nav(active: str) -> str:
    out = []
    for path, key, label, _ in NAV:
        cur = ' aria-current="page"' if key == active else ""
        out.append(f'<a href="{path}"{cur}>{label}</a>')
    return "".join(out)


def render_page(key: str) -> str:
    """Tiny server-side template: shared header, nav and footer around each page body."""
    _, _, _, title = next(p for p in PAGES if p[1] == key)
    base = (BASE / "pages" / "base.html").read_text()
    content = (BASE / "pages" / f"{key}.html").read_text()
    scripts = "".join(f'<script src="/static/{n}"></script>' for n in PAGE_SCRIPTS.get(key, []))
    footnav = " &middot; ".join(f'<a href="{path}">{label}</a>' for path, _, label, _ in NAV)
    return (base.replace("{{content}}", content).replace("{{title}}", title)
            .replace("{{nav}}", _nav(key)).replace("{{footnav}}", footnav).replace("{{scripts}}", scripts))


def _make_route(key: str):
    def view():
        return HTMLResponse(render_page(key))
    return view


for _path, _key, _label, _title in PAGES:
    app.get(_path, response_class=HTMLResponse, name=f"page_{_key}")(_make_route(_key))


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
