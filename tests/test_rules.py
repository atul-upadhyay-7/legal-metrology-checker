from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.rules import run_rules

S = Path(__file__).resolve().parent.parent / "samples"
EXPECT = {
    "01_compliant": "compliant",
    "02_missing_mrp_tax": "non_compliant",
    "03_missing_origin_care": "non_compliant",
    "04_expiry_only_review": "needs_review",
    "05_empty_label": "non_compliant",
}


def status(out, rule):
    return next(r["status"] for r in out["results"] if r["rule"] == rule)


def test_text_samples():
    for name, want in EXPECT.items():
        assert run_rules((S / f"{name}.txt").read_text())["overall"] == want, name


def test_specific_findings():
    out = run_rules((S / "02_missing_mrp_tax.txt").read_text())
    assert status(out, "mrp") == "fail"
    out = run_rules((S / "04_expiry_only_review.txt").read_text())
    assert status(out, "mfg_date") == "review"


def test_image_upload_ocr():
    c = TestClient(app)
    for name, want in EXPECT.items():
        with open(S / f"{name}.png", "rb") as f:
            r = c.post("/api/check", files={"image": (f"{name}.png", f, "image/png")})
        assert r.status_code == 200
        assert r.json()["overall"] == want, (name, r.json()["extracted_text"])


def test_empty_request():
    assert TestClient(app).post("/api/check", data={"text": ""}).status_code == 400
