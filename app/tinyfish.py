"""TinyFish Fetch API client: live capture of an online product listing.

The page text returned by TinyFish is fed to the same rule engine as pasted/OCR text,
in the 'listing' context (Rule 6(10)). Read-only: nothing is bought, posted or changed.
Docs: https://docs.tinyfish.ai/fetch-api
"""
import ipaddress
import os
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

FETCH_URL = "https://api.fetch.tinyfish.ai"


class CaptureError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def validate_url(url: str) -> str:
    """Only public http(s) URLs. Blocks localhost, private and link-local addresses."""
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https") or not p.hostname:
        raise CaptureError("Enter a full http(s) product page URL.", 400)
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror:
        raise CaptureError("Could not resolve that host.", 400)
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise CaptureError("Only public web pages can be captured.", 400)
    return p.geturl()


def fetch_listing(url: str, client: httpx.Client | None = None) -> dict:
    """Live-fetch a page through TinyFish. Returns text plus capture metadata."""
    key = os.environ.get("TINYFISH_API_KEY", "").strip()
    if not key:
        raise CaptureError("TINYFISH_API_KEY is not set on the server.", 503)
    url = validate_url(url)
    own = client is None
    client = client or httpx.Client(timeout=150)
    try:
        r = client.post(FETCH_URL, headers={"X-API-Key": key},
                        json={"urls": [url], "format": "markdown", "ttl": 0})
    except httpx.HTTPError as e:
        raise CaptureError(f"TinyFish request failed: {type(e).__name__}.")
    finally:
        if own:
            client.close()
    if r.status_code in (401, 403):
        raise CaptureError("TinyFish rejected the API key or account.", 502)
    if r.status_code == 402:
        raise CaptureError("TinyFish account has no balance for this request.", 502)
    if r.status_code != 200:
        raise CaptureError(f"TinyFish returned HTTP {r.status_code}.")
    data = r.json()
    results = data.get("results") or []
    if not results:
        errs = data.get("errors") or []
        why = errs[0].get("error", "unknown") if errs else "no content"
        raise CaptureError(f"TinyFish could not capture the page ({why}). Treat as Needs review, not a violation.")
    res = results[0]
    text = res.get("text") or ""
    if not isinstance(text, str) or not text.strip():
        raise CaptureError("TinyFish returned an empty page. Treat as Needs review, not a violation.")
    return {
        "text": text,
        "capture": {
            "source": "tinyfish-fetch",
            "url": url,
            "final_url": res.get("final_url", url),
            "title": res.get("title", ""),
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "chars": len(text),
        },
    }


def capture_problem(text: str) -> str:
    """Return a reason if the captured text is clearly not a product page, else ''.

    Marketplaces sometimes return a consent, 'continue shopping' or bot-wall page. Running the
    rules on that would report every declaration as missing, which is a false finding.
    """
    import re
    if len(text.strip()) < 2500:
        return "The captured page is very short, so it is probably not the product page (consent or access page)."
    if not re.search(r"(?:\u20b9|\bRs\.?|\bINR\b|m\.?r\.?p)", text, re.I):
        return "The captured page shows no price or MRP, so it is probably not the product page."
    return ""
