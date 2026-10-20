"""Rule engine: a list of regex checks over OCR text.

Each rule returns a status:
  pass    - declaration found
  fail    - declaration missing or incomplete
  review  - cannot decide automatically (needs a human look)
"""
import re
from dataclasses import dataclass
from typing import Callable

I = re.IGNORECASE
NUM = r"\d+(?:[.,]\d+)?"


def _norm(text: str) -> str:
    text = text.replace("\u20b9", " Rs ")
    return re.sub(r"[ \t]+", " ", text)


@dataclass
class Result:
    rule: str
    label: str
    status: str
    detail: str
    evidence: str = ""

    def as_dict(self):
        return self.__dict__


def check_net_quantity(text: str) -> Result:
    unit = r"(?:kg|g|gm|gms|grams?|mg|ml|l|ltr|litres?|liters?|pcs?|pieces?|nos?|n|units?|m|cm|mm)\b"
    m = re.search(
        rf"(?:net\s*(?:qty|quantity|wt|weight|content|contents|vol|volume)\.?|contents?)\s*[:\-]?\s*(?:\w+\s+)?{NUM}\s*(?:x\s*{NUM}\s*)?{unit}",
        text, I)
    if m:
        return Result("net_quantity", "Net quantity", "pass", "Net quantity with a standard unit found.", m.group(0).strip())
    if re.search(r"net\s*(?:qty|quantity|wt|weight|content|contents|vol|volume)", text, I):
        return Result("net_quantity", "Net quantity", "fail", "Net quantity is mentioned but no value with a standard unit was read.")
    return Result("net_quantity", "Net quantity", "fail", "No net quantity declaration found.")


def check_mrp(text: str) -> Result:
    m = re.search(rf"(?:m\.?\s?r\.?\s?p\.?|maximum\s+retail\s+price)[^\n]{{0,40}}?(?:rs\.?|inr)?\s*{NUM}", text, I)
    if not m:
        return Result("mrp", "MRP (inclusive of all taxes)", "fail", "No MRP amount found.")
    incl = re.search(r"incl(?:usive|\.|uding)?\s*(?:of)?\s*(?:all\s*)?taxes", text, I)
    if incl:
        return Result("mrp", "MRP (inclusive of all taxes)", "pass", "MRP amount and 'inclusive of all taxes' found.", m.group(0).strip())
    return Result("mrp", "MRP (inclusive of all taxes)", "fail", "MRP amount found but 'inclusive of all taxes' is missing.", m.group(0).strip())


_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
_DATE = rf"(?:\d{{1,2}}\s*[/.\-]\s*\d{{2,4}}|{_MONTH}[\s.,\-/]*\d{{2,4}}|\d{{4}}\s*[/\-]\s*\d{{1,2}})"


def check_mfg_date(text: str, context: str = "package", category: str = "general") -> Result:
    """Month and year of manufacture, Rule 6(1)(d).

    Package label: required (food packages follow the FSS Act instead, so they go to review).
    Online listing: Rule 6(10) says e-commerce display must carry the Rule 6(1) declarations
    EXCEPT the month and year of manufacture or packing, so the check does not apply.
    A best-before / expiry date is a different declaration (Rule 6(1)(h)) and never
    substitutes for manufacture month and year.
    """
    label = "Manufacture month and year"
    if context == "listing":
        return Result("mfg_date", label, "not_applicable",
                      "Rule 6(10): the e-commerce display requirement excludes the month and year of manufacture or packing.")
    m = re.search(rf"(?:mfg\.?|mfd\.?|manufactured|manufacture|pkd\.?|packed|packing|date\s+of\s+(?:manufacture|packing)|month\s+(?:and|&)\s+year[^\n]{{0,25}})[^\n]{{0,30}}?{_DATE}", text, I)
    if m:
        return Result("mfg_date", label, "pass", "Month and year of manufacture or packing found.", m.group(0).strip())
    if category == "food":
        return Result("mfg_date", label, "review",
                      "Food packages follow the Food Safety and Standards Act for date marking. A person should check against FSS labelling rules.")
    return Result("mfg_date", label, "fail", "No month and year of manufacture found on the package.")


def check_address(text: str) -> Result:
    m = re.search(r"\b(?:manufactured|marketed|packed|imported)\s*(?:&|and)?\s*(?:marketed|packed)?\s*(?:by\b\s*[:\-]?|[:\-])\s*([^\n]{5,}(?:\n[^\n]+){0,2})", text, I)
    if m:
        block = m.group(1)
        has_pin = re.search(r"\b\d{6}\b", block + text)
        if has_pin or re.search(r"(india|road|street|nagar|sector|plot|floor|industrial)", block, I):
            return Result("address", "Manufacturer / packer / importer address", "pass", "Name and address block found.", block.strip().replace("\n", ", ")[:160])
        return Result("address", "Manufacturer / packer / importer address", "fail", "Manufacturer is named but a full address (street/city/PIN) was not read.", block.strip()[:120])
    return Result("address", "Manufacturer / packer / importer address", "fail", "No 'Manufactured / Packed / Marketed / Imported by' address found.")


def check_consumer_care(text: str) -> Result:
    phone = re.search(r"(?:\+?91[\s\-]?)?(?:1800[\s\-]?\d{3}[\s\-]?\d{3,4}|[6-9]\d{9}|\d{2,4}[\s\-]\d{6,8})", text)
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    cue = re.search(r"consumer\s*(?:care|complaint|grievance)|customer\s*care|toll\s*free|helpline|for\s+(?:any\s+)?complaints?", text, I)
    if cue and (phone or email):
        return Result("consumer_care", "Consumer care details", "pass", "Consumer care cue with phone or email found.", (phone or email).group(0))
    if phone or email:
        return Result("consumer_care", "Consumer care details", "review", "A phone or email is printed but not labelled as consumer care.", (phone or email).group(0))
    return Result("consumer_care", "Consumer care details", "fail", "No consumer care phone, email or address found.")


def check_origin(text: str) -> Result:
    m = re.search(r"(?:country\s+of\s+origin|made\s+in|product\s+of)\s*[:\-]?\s*([A-Za-z]{3,})", text, I)
    if m:
        return Result("origin", "Country of origin", "pass", "Country of origin found.", m.group(0).strip())
    return Result("origin", "Country of origin", "fail", "No country of origin found.")


CONTEXTS = ("package", "listing")
CATEGORIES = ("general", "food")
RULES: list[Callable[[str], Result]] = [
    check_net_quantity, check_mrp, check_address, check_consumer_care, check_origin,
]


def run_rules(text: str, context: str = "package", category: str = "general") -> dict:
    """context: 'package' (physical label) or 'listing' (online display, Rule 6(10)).
    category: 'general' or 'food'."""
    if context not in CONTEXTS:
        raise ValueError(f"context must be one of {CONTEXTS}")
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")
    text = _norm(text)
    results = [r(text).as_dict() for r in RULES]
    results.insert(2, check_mfg_date(text, context, category).as_dict())
    statuses = {r["status"] for r in results}
    overall = "non_compliant" if "fail" in statuses else ("needs_review" if "review" in statuses else "compliant")
    return {"overall": overall, "context": context, "category": category, "results": results}
