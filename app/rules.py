"""Rule engine: regex checks over label or listing text.

Statuses:
  pass            declaration found
  fail            declaration missing or incomplete ("potential issue")
  review          cannot decide automatically (needs a human look)
  not_applicable  the rule does not apply in this context

Contexts: 'package' (physical label) or 'listing' (online display, Rule 6(10)).
Source: Legal Metrology (Packaged Commodities) Rules, 2011, as amended.
A first-pass aid only, not legal advice.
"""
import re
from dataclasses import dataclass
from typing import Callable

I = re.IGNORECASE
NUM = r"\d+(?:[.,]\d+)?"
CONTEXTS = ("package", "listing")
CATEGORIES = ("general", "food")


def _norm(text: str) -> str:
    text = text.replace("\u20b9", " Rs ").replace("\u2009", " ").replace("\xa0", " ")
    text = re.sub(r"[*_`]+", "", text)           # markdown emphasis from page captures
    return re.sub(r"[ \t]+", " ", text)


@dataclass
class Result:
    rule: str
    label: str
    status: str
    detail: str
    evidence: str = ""
    ref: str = ""

    def as_dict(self):
        return self.__dict__


def _where(context: str) -> str:
    return "in the captured page text" if context == "listing" else "on the label text"


def check_net_quantity(text: str, context: str = "package", category: str = "general") -> Result:
    ref, label = "Rule 6(1)(c)", "Net quantity"
    unit = r"(?:kg|kgs|g|gm|gms|grams?|mg|ml|l|ltr|litres?|liters?|pcs?|pieces?|nos?|n|units?|m|cm|mm)\b"
    cue = r"(?:net\s*(?:qty|quantity|wt|weight|content|contents|vol|volume)|item\s*(?:weight|volume)|contents?|quantity|weight)"
    m = re.search(rf"{cue}\.?\s*[:\-]?\s*(?:\w+\s+)?{NUM}\s*(?:x\s*{NUM}\s*)?{unit}", text, I)
    if m:
        return Result("net_quantity", label, "pass", "Net quantity with a standard unit found.", m.group(0).strip(), ref)
    if re.search(r"net\s*(?:qty|quantity|wt|weight|content|contents|vol|volume)", text, I):
        return Result("net_quantity", label, "fail", "Net quantity is mentioned but no value with a standard unit was read.", "", ref)
    return Result("net_quantity", label, "fail",
                  f"No net quantity declaration found {_where(context)}. It applies to pre-packaged goods sold by weight, measure or number.", "", ref)


def check_mrp(text: str, context: str = "package", category: str = "general") -> Result:
    ref, label = "Rule 6(1)(e)", "MRP (inclusive of all taxes)"
    m = re.search(rf"(?:m\.?\s?r\.?\s?p\.?|maximum\s+retail\s+price|max\.?\s+retail\s+price)[^\n]{{0,40}}?(?:rs\.?|inr)?\s*{NUM}", text, I)
    if not m:
        return Result("mrp", label, "fail", f"No MRP amount found {_where(context)}.", "", ref)
    incl = re.search(r"incl(?:usive|\.|uding)?\s*(?:of)?\s*(?:all\s*)?taxes", text, I)
    if incl:
        return Result("mrp", label, "pass", "MRP amount and 'inclusive of all taxes' found.", m.group(0).strip(), ref)
    return Result("mrp", label, "fail", "MRP amount found but 'inclusive of all taxes' was not found next to it.", m.group(0).strip(), ref)


_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
_DATE = rf"(?:\d{{1,2}}\s*[/.\-]\s*\d{{2,4}}|{_MONTH}[\s.,\-/]*\d{{2,4}}|\d{{4}}\s*[/\-]\s*\d{{1,2}})"


def check_mfg_date(text: str, context: str = "package", category: str = "general") -> Result:
    """Month and year of manufacture, Rule 6(1)(d).

    Package label: required (food packages follow the FSS Act instead, so they go to review).
    Online listing: Rule 6(10) says e-commerce display must carry the Rule 6(1) declarations
    EXCEPT the month and year of manufacture or packing, so the check does not apply.
    A best-before / expiry date is a different declaration (Rule 6(1)(da)) and never
    substitutes for manufacture month and year.
    """
    ref, label = "Rule 6(1)(d), 6(10)", "Manufacture month and year"
    if context == "listing":
        return Result("mfg_date", label, "not_applicable",
                      "Rule 6(10): the e-commerce display requirement excludes the month and year of manufacture or packing.", "", ref)
    m = re.search(rf"(?:mfg\.?|mfd\.?|manufactured|manufacture|pkd\.?|packed|packing|date\s+of\s+(?:manufacture|packing)|month\s+(?:and|&)\s+year[^\n]{{0,25}})[^\n]{{0,30}}?{_DATE}", text, I)
    if m:
        return Result("mfg_date", label, "pass", "Month and year of manufacture or packing found.", m.group(0).strip(), ref)
    if category == "food":
        return Result("mfg_date", label, "review",
                      "Food packages follow the Food Safety and Standards Act for date marking. A person should check against FSS labelling rules.", "", ref)
    return Result("mfg_date", label, "fail", "No month and year of manufacture found on the package.", "", ref)


def check_address(text: str, context: str = "package", category: str = "general") -> Result:
    ref, label = "Rule 6(1)(a)", "Manufacturer / packer / importer name and address"
    m = re.search(r"\b(?:manufactured|marketed|packed|imported|manufacturer|packer|importer)\s*(?:&|and)?\s*(?:marketed|packed)?\s*(?:info(?:rmation)?\s*)?(?:by\b\s*[:\-]?|[:\-])\s*([^\n]{5,}(?:\n+[^\n]+){0,2})", text, I)
    if m:
        lines = m.group(1).split("\n")
        keep = [lines[0]]
        for ln in lines[1:]:
            if not ln.strip():
                continue
            if re.match(r"\s*[A-Za-z][A-Za-z .&/]{2,30}:\s", ln):   # next labelled field, not part of the address
                break
            keep.append(ln)
        block = "\n".join(keep)
        has_pin = re.search(r"\b\d{6}\b", block)
        if has_pin or re.search(r"\b(india|road|street|nagar|sector|plot|floor|industrial|lane|marg|village)\b", block, I):
            return Result("address", label, "pass", "Name and address block found.", block.strip().replace("\n", ", ")[:160], ref)
        return Result("address", label, "fail", "A manufacturer is named but a full address (street, city, PIN) was not read.", block.strip()[:120], ref)
    return Result("address", label, "fail",
                  f"No 'Manufactured / Packed / Marketed / Imported by' name and address found {_where(context)}.", "", ref)


def check_consumer_care(text: str, context: str = "package", category: str = "general") -> Result:
    ref, label = "Rule 6(2)", "Consumer complaint contact"
    phone = re.search(r"(?:\+?91[\s\-]?)?(?:1800[\s\-]?\d{3}[\s\-]?\d{3,4}|[6-9]\d{9}|\d{2,4}[\s\-]\d{6,8})", text)
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    cue = re.search(r"consumer\s*(?:care|complaint|grievance)|customer\s*(?:care|support)|toll\s*free|helpline|for\s+(?:any\s+)?complaints?", text, I)
    if cue and (phone or email):
        return Result("consumer_care", label, "pass", "Complaint contact cue with phone or email found.", (phone or email).group(0), ref)
    if phone or email:
        return Result("consumer_care", label, "review", "A phone or email is printed but not labelled as a consumer complaint contact.", (phone or email).group(0), ref)
    return Result("consumer_care", label, "fail", f"No consumer complaint phone or email found {_where(context)}.", "", ref)


def check_origin(text: str, context: str = "package", category: str = "general") -> Result:
    """Rule 6(1)(aa): required for imported products only. Missing = review, never fail."""
    ref, label = "Rule 6(1)(aa)", "Country of origin (imported goods)"
    m = re.search(r"(?:country\s+of\s+origin|made\s+in|product\s+of)\s*[:\-]?\s*([A-Za-z]{3,})", text, I)
    if m:
        return Result("origin", label, "pass", "Country of origin found.", m.group(0).strip(), ref)
    return Result("origin", label, "review",
                  f"No country of origin found {_where(context)}. It is required for imported goods only, so confirm whether the product is imported.", "", ref)


RULES: list[Callable[..., Result]] = [
    check_net_quantity, check_mrp, check_mfg_date, check_address, check_consumer_care, check_origin,
]

SUMMARY = {
    "package": "Package label checked against Rule 6(1) and 6(2).",
    "listing": "Online listing checked under Rule 6(10): Rule 6(1) declarations except manufacture month and year.",
}


def run_rules(text: str, context: str = "package", category: str = "general") -> dict:
    """context: 'package' (physical label) or 'listing' (online display, Rule 6(10)).
    category: 'general' or 'food'."""
    if context not in CONTEXTS:
        raise ValueError(f"context must be one of {CONTEXTS}")
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")
    text = _norm(text)
    results = [r(text, context, category).as_dict() for r in RULES]
    statuses = {r["status"] for r in results}
    overall = "non_compliant" if "fail" in statuses else ("needs_review" if "review" in statuses else "compliant")
    counts = {k: sum(1 for r in results if r["status"] == k) for k in ("pass", "fail", "review", "not_applicable")}
    return {"overall": overall, "context": context, "category": category,
            "summary": SUMMARY[context], "counts": counts, "results": results}
