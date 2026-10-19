# Legal Metrology Checker

Checks a packaged-commodity label against the mandatory Legal Metrology declarations. Upload a label image (or paste text): OCR extracts the text, a regex rule engine runs, and the page shows pass / fail / review per declaration.

Checks: net quantity, MRP inclusive of all taxes, manufacture or pack month and year, manufacturer/packer/importer address, consumer care details, country of origin. If the manufacture date is missing but an expiry or best-before is printed, the result is "review" (the Rule 6(10) exception may apply), not a hard fail.

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
