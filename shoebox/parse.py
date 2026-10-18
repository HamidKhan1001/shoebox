"""LLM extraction plus deterministic validation of the result."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

CATEGORIES = ["software", "hardware", "travel", "meals", "office", "utilities", "marketing", "professional-services", "income", "other"]

SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {"type": "string", "enum": ["receipt", "invoice_received", "invoice_sent", "other"]},
        "vendor": {"type": "string"},
        "date": {"type": "string", "description": "YYYY-MM-DD"},
        "total": {"type": "number"},
        "tax": {"type": "number"},
        "currency": {"type": "string"},
        "category": {"type": "string", "enum": [c for c in CATEGORIES if c != "income"]},
    },
    "required": ["doc_type", "vendor", "date", "total", "currency", "category"],
}

SYSTEM = (
    "You extract bookkeeping fields from one receipt or invoice. Reply with JSON only.\n"
    "doc_type: 'receipt' = proof of a purchase already paid. 'invoice_received' = a supplier or vendor is billing the owner "
    "(the owner is the one named 'Invoice for' or 'Bill To'). 'invoice_sent' = the owner is billing a client: the owner's own name "
    "appears after 'From:' and the client after 'Bill To:'.\n"
    "vendor: for receipt and invoice_received, the business that issued the document. For invoice_sent, the client named after 'Bill To:'.\n"
    "category: what the money was spent on (software subscriptions and domains = software; computers = hardware; flights and trains = travel; "
    "food = meals; supplies and coworking = office; phone/internet = utilities; ads = marketing; lawyers and accountants = professional-services).\n"
    "total: final amount due or paid, tax included. date: YYYY-MM-DD. currency: ISO code. tax: 0 if none shown."
)


@dataclass
class Record:
    doc_type: str = "other"
    vendor: str = "Unknown"
    date: date | None = None
    total: float | None = None
    tax: float = 0.0
    currency: str = "USD"
    category: str = "other"
    warnings: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return bool(self.warnings)


_AMOUNT = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{2}))(?!\d)")


def amounts_in(text: str) -> list[float]:
    return [float(a.replace(",", "") + "." + b) for a, b in _AMOUNT.findall(text)]


def _parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None


def validate(raw: dict, source_text: str, today: date | None = None) -> Record:
    """Coerce model output into a Record and flag anything that does not check out against the source text."""
    today = today or date.today()
    r = Record()
    r.doc_type = raw.get("doc_type") if raw.get("doc_type") in {"receipt", "invoice_received", "invoice_sent", "other"} else "other"
    r.vendor = re.sub(r"\s+", " ", str(raw.get("vendor") or "")).strip() or "Unknown"
    if r.vendor == "Unknown":
        r.warnings.append("no vendor")
    r.category = raw.get("category") if raw.get("category") in CATEGORIES else "other"
    if r.doc_type == "invoice_sent":
        r.category = "income"
    r.currency = str(raw.get("currency") or "USD").upper()[:3]

    r.date = _parse_date(str(raw.get("date") or ""))
    if r.date is None:
        r.warnings.append("unreadable date")
    elif r.date > today or r.date.year < today.year - 15:
        r.warnings.append(f"implausible date {r.date}")

    try:
        r.total = round(float(raw.get("total")), 2)
    except (TypeError, ValueError):
        r.total = None
    try:
        r.tax = round(float(raw.get("tax") or 0), 2)
    except (TypeError, ValueError):
        r.tax = 0.0
    seen = amounts_in(source_text)
    if r.total is None or r.total <= 0:
        r.warnings.append("missing total")
    elif seen and r.total not in seen:
        # small models sometimes hallucinate or add up wrong; the real total must appear in the document
        r.warnings.append(f"total {r.total:.2f} not found in document text")
        biggest = max(seen)
        if abs(biggest - r.total) > 0.01:
            r.warnings.append(f"largest amount in document is {biggest:.2f}")
    if r.tax and r.total and r.tax >= r.total:
        r.warnings.append("tax >= total")
    return r
