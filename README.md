# Legal Metrology Checker

Checks a packaged-commodity label against the mandatory Legal Metrology declarations. Upload a label image (or paste text): OCR extracts the text, a regex rule engine runs, and the page shows pass / fail / review per declaration.

Checks: net quantity, MRP inclusive of all taxes, manufacture or pack month and year, manufacturer/packer/importer address, consumer care details, country of origin. Two contexts: a **package label** is checked for all six declarations. An **online listing** is checked under Rule 6(10), which requires the Rule 6(1) declarations on the e-commerce display *except* the month and year of manufacture or packing, so that check is marked not applicable. A best-before or expiry date is a separate declaration and never replaces manufacture month and year. Food packages follow the Food Safety and Standards Act for date marking, so a missing manufacture date goes to review. Sources: Legal Metrology (Packaged Commodities) Rules, 2011 as amended (rule 6(1)(d), 6(10)); DCA FAQ Q27 and Q50 (https://consumeraffairs.nic.in/sites/default/files/file-uploads/latestnews/LM_FAQs.pdf). This is a first-pass aid, not legal advice.

## Run

Needs Python 3.10+ and Tesseract OCR (`sudo apt install tesseract-ocr`, or `brew install tesseract`, or the Windows installer from UB Mannheim).

```
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Test

```
python scripts/make_samples.py   # regenerates samples/
python -m pytest
```

## Layout

- `app/rules.py` rule engine (one function per rule)
- `app/ocr.py` Tesseract wrapper
- `app/main.py` FastAPI app, `POST /api/check`
- `app/static/index.html` single page UI
- `samples/` five sample labels (png + txt)
