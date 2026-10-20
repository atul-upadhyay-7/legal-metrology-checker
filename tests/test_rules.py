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


def _fake_tinyfish(monkeypatch, handler):
    import httpx
    from app import tinyfish
    monkeypatch.setenv("TINYFISH_API_KEY", "test-key")
    monkeypatch.setattr(tinyfish, "validate_url", lambda u: u)
    real = httpx.Client
    monkeypatch.setattr(tinyfish.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler)))


def test_check_url_uses_tinyfish_and_listing_rules(monkeypatch):
    import json
    seen = {}

    def handler(req):
        import httpx
        seen["key"] = req.headers["x-api-key"]
        seen["body"] = json.loads(req.content)
        text = (S / "04_expiry_only_review.txt").read_text() + "\nProduct description. " * 150
        return httpx.Response(200, json={"results": [{"url": "https://shop.example/p", "final_url": "https://shop.example/p", "title": "Tea", "text": text}], "errors": []})

    _fake_tinyfish(monkeypatch, handler)
    r = TestClient(app).post("/api/check-url", data={"url": "https://shop.example/p"})
    assert r.status_code == 200
    j = r.json()
    assert seen["key"] == "test-key" and seen["body"]["ttl"] == 0
    assert j["context"] == "listing" and j["overall"] == "compliant"
    assert j["capture"]["source"] == "tinyfish-fetch" and j["capture"]["captured_at"]


def test_check_url_failed_capture_is_not_a_verdict(monkeypatch):
    import httpx
    _fake_tinyfish(monkeypatch, lambda req: httpx.Response(200, json={"results": [], "errors": [{"url": "x", "error": "blocked"}]}))
    r = TestClient(app).post("/api/check-url", data={"url": "https://shop.example/p"})
    assert r.status_code == 502 and "Needs review" in r.json()["detail"]


def test_check_url_missing_key_and_bad_url(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    c = TestClient(app)
    assert c.post("/api/check-url", data={"url": "https://shop.example/p"}).status_code == 503
    monkeypatch.setenv("TINYFISH_API_KEY", "k")
    assert c.post("/api/check-url", data={"url": "http://127.0.0.1:8000/"}).status_code == 400
    assert c.post("/api/check-url", data={"url": "file:///etc/passwd"}).status_code == 400


def test_check_url_interstitial_page_is_needs_review_not_violation(monkeypatch):
    import httpx
    page = "Click the button below to continue shopping\nContinue shopping\nConditions of Use & Sale"
    _fake_tinyfish(monkeypatch, lambda req: httpx.Response(200, json={"results": [{"url": "u", "final_url": "u", "title": "Shop", "text": page}], "errors": []}))
    j = TestClient(app).post("/api/check-url", data={"url": "https://shop.example/p"}).json()
    assert j["overall"] == "needs_review" and j["results"][0]["rule"] == "capture"


def test_address_needs_by_keyword_not_free_text():
    out = run_rules("This salt was first manufactured by Tata in a vacuum pack and is great.", "listing")
    assert status(out, "address") == "fail"
    out = run_rules("Marketed by: Foo Foods, Plot 3, Sector 9, Pune 411019", "listing")
    assert status(out, "address") == "pass"


def test_address_evidence_stops_at_next_labelled_field():
    t = "Manufacturer: Kesar Foods, Plot 4, Sector 2, Pune 411019\nCountry of Origin: India\nCustomer Care: 1800 123 4567"
    r = next(x for x in run_rules(t, "listing")["results"] if x["rule"] == "address")
    assert r["status"] == "pass" and "Country" not in r["evidence"]


def test_listing_samples_behave():
    c = TestClient(app)
    s = c.get("/api/samples").json()
    ok = next(x for x in s["listing"] if x["title"] == "Complete listing")
    bad = next(x for x in s["listing"] if x["title"] == "Missing MRP")
    assert run_rules(ok["text"], "listing", "food")["overall"] == "compliant"
    out = run_rules(bad["text"], "listing", "food")
    assert out["overall"] == "non_compliant" and status(out, "mrp") == "fail" and status(out, "mfg_date") == "not_applicable"


def test_origin_missing_is_review_not_fail():
    out = run_rules("Net Quantity: 1 kg\nMRP Rs 10 inclusive of all taxes", "package")
    assert status(out, "origin") == "review"


def test_rule_refs_and_counts_present():
    out = run_rules((S / "01_compliant.txt").read_text())
    assert all(r["ref"].startswith("Rule 6") for r in out["results"])
    assert sum(out["counts"].values()) == 6
