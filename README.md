# Legal Metrology Checker

Checks product declarations against the Legal Metrology (Packaged Commodities) Rules, 2011 (as amended) and shows the evidence and the rule behind every finding. It works on two kinds of input:

- **Online listing**: paste a product-page URL (captured live with TinyFish) or paste the listing text. Checked under Rule 6(10).
- **Package label**: upload a label photo (read with Tesseract OCR) or paste the label text. Checked against Rule 6(1) and 6(2).

## What is checked

| Declaration | Rule |
| --- | --- |
| Net quantity in a standard unit | 6(1)(c) |
| MRP, inclusive of all taxes | 6(1)(e) |
| Manufacture month and year | 6(1)(d), 6(10) |
| Manufacturer, packer or importer name and address | 6(1)(a) |
| Consumer complaint contact (phone, email) | 6(2) |
| Country of origin (imported goods only) | 6(1)(aa) |

Statuses: found, potential issue, needs review, not applicable.

**Rule 6(10).** An e-commerce display must carry the Rule 6(1) declarations except the month and year of manufacture or packing. So on an online listing the manufacture check is "not applicable". The physical package still needs it. A best-before or use-by date is a separate declaration (6(1)(da)) and never replaces manufacture month and year. Food packages follow the Food Safety and Standards Act for date marking, so a missing date goes to review when the category is Food. Country of origin is required for imported goods only, so a missing one is a review item, not a failure.

Sources: Legal Metrology (Packaged Commodities) Rules, 2011 with amendments (DoCA consolidated book, Dec 2024), and the Department of Consumer Affairs FAQ (Q27, Q50). Not covered: unit sale price, font size and display panel rules, dimensions, other e-commerce provisions, and amendments after the Dec 2024 consolidation.

## Limits (read before relying on a result)

- First-pass aid, not legal advice. "No issue detected" means no issue in the checked rules.
- The checks are text patterns. On a real product page, a declaration in a section the capture missed shows as a potential issue. Treat findings as leads for a person to confirm.
- A page TinyFish cannot read (blocked, consent page, no price) is reported as Needs review, never as a violation.
- Net quantity applies to pre-packaged goods sold by weight, measure or number. The tool does not decide whether a product is such a good.

## TinyFish integration

For an online listing the server calls the TinyFish **Fetch API** (`POST https://api.fetch.tinyfish.ai`, `ttl: 0` for a live fetch, markdown output). It receives the rendered page text, title, final URL and capture time, then runs the same rules in listing context. The result shows the capture source and time.

- Endpoint: `POST /api/check-url` (form fields `url`, optional `category`).
- Only public http(s) URLs are accepted; localhost and private addresses are rejected. Read-only: no purchases, logins or seller changes.
- Needs `TINYFISH_API_KEY` in the environment (key from https://agent.tinyfish.ai/api-keys). Fetch is free up to 1,000 URLs per day.
- Tests mock the TinyFish response. A live call needs the key.

## Run locally

Needs Python 3.10+ and Tesseract OCR (`sudo apt install tesseract-ocr`, `sudo dnf install tesseract`, or `brew install tesseract`).

```
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export TINYFISH_API_KEY=your_key   # only needed for URL capture
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Pages: Home `/`, Checker `/check`, Results `/results`, How it works `/how-it-works`, About `/about`. The checker page has sample listings and labels so you can try it without a photo or a URL.

## Test

```
python scripts/make_samples.py   # regenerates the sample label images
python -m pytest
```

## Layout

- `app/rules.py` rule engine (one function per rule, with rule references)
- `app/tinyfish.py` TinyFish Fetch client, URL safety check, capture-quality gate
- `app/ocr.py` Tesseract wrapper
- `app/main.py` FastAPI app: `/api/check`, `/api/check-url`, `/api/samples`
- `app/pages/` page bodies (home, check, results, how it works, about) and the shared base with nav and footer
- `app/static/` styles, motion, form and results scripts
- `samples/` sample labels (png and txt) and sample listing texts

## Third-party code

- anime.js 4.5.0 (MIT, Julian Garnier), vendored at `app/static/vendor/anime.umd.min.js` with its licence file. Used for the page-in and the results reveal in `app/static/motion.js`. No CDN. Motion is skipped when the browser asks for reduced motion.
