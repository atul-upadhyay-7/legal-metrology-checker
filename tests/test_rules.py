from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.rules import run_rules

S = Path(__file__).resolve().parent.parent / "samples"
EXPECT = {
    "01_compliant": "compliant",
    "02_missing_mrp_tax": "non_compliant",
    "03_missing_origin_care": "non_compliant",
    "04_expiry_only_review": "non_compliant",
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
    assert status(out, "mfg_date") == "fail"  # best-before does not replace mfg month/year


def test_image_upload_ocr():
    c = TestClient(app)
    for name, want in EXPECT.items():
        with open(S / f"{name}.png", "rb") as f:
            r = c.post("/api/check", files={"image": (f"{name}.png", f, "image/png")})
        assert r.status_code == 200
        assert r.json()["overall"] == want, (name, r.json()["extracted_text"])


def test_empty_request():
    assert TestClient(app).post("/api/check", data={"text": ""}).status_code == 400


def test_package_context_best_before_is_not_a_substitute():
    t = (S / "04_expiry_only_review.txt").read_text()
    assert status(run_rules(t, "package", "general"), "mfg_date") == "fail"
    out = run_rules(t, "package", "food")
    assert status(out, "mfg_date") == "review" and out["overall"] == "needs_review"


def test_listing_context_skips_mfg_date_rule_6_10():
    t = (S / "04_expiry_only_review.txt").read_text()
    out = run_rules(t, "listing")
    assert status(out, "mfg_date") == "not_applicable"
    assert out["overall"] == "compliant"
    # other declarations still enforced online
    out = run_rules((S / "02_missing_mrp_tax.txt").read_text(), "listing")
    assert status(out, "mrp") == "fail" and out["overall"] == "non_compliant"


def test_package_with_mfg_date_passes():
    t = (S / "01_compliant.txt").read_text()
    assert status(run_rules(t, "package"), "mfg_date") == "pass"
    assert status(run_rules(t, "listing"), "mfg_date") == "not_applicable"


def test_api_context_param_and_validation():
    c = TestClient(app)
    t = (S / "04_expiry_only_review.txt").read_text()
    assert c.post("/api/check", data={"text": t, "context": "listing"}).json()["overall"] == "compliant"
    assert c.post("/api/check", data={"text": t}).json()["overall"] == "non_compliant"
    assert c.post("/api/check", data={"text": t, "context": "x"}).status_code == 400


def test_bad_context_raises():
    import pytest
    with pytest.raises(ValueError):
        run_rules("x", "nope")
