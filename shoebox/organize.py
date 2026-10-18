"""Plan (and optionally apply) filing of documents into OUT/YYYY/YYYY-MM/category/."""
from __future__ import annotations

import csv
import hashlib
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .parse import Record


def slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s[:40] or "Unknown"


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


@dataclass
class Entry:
    source: Path
    record: Record | None
    error: str | None = None
    target: Path | None = None
    duplicate_of: Path | None = None


def target_for(rec: Record, src: Path, out: Path) -> Path:
    if rec.needs_review:
        folder = out / "_needs-review"
        name = src.name
    else:
        folder = out / f"{rec.date:%Y}" / f"{rec.date:%Y-%m}" / rec.category
        name = f"{rec.date:%Y-%m-%d}_{slug(rec.vendor)}_{rec.total:.2f}{src.suffix.lower()}"
    return folder / name


def plan(entries: list[Entry], out: Path) -> list[Entry]:
    """Assign targets, detect exact-duplicate files and same vendor/date/total re-sends, resolve name clashes."""
    used: set[Path] = set()
    keys: dict[tuple, Path] = {}
    hashes: dict[str, Path] = {}
    for e in entries:
        if e.record is None:
            e.target = out / "_unreadable" / e.source.name
        else:
            h = file_hash(e.source)
            key = (e.record.vendor.lower(), e.record.date, e.record.total) if not e.record.needs_review else None
            first = hashes.get(h) or (keys.get(key) if key else None)
            if first:
                e.duplicate_of = first
                e.target = out / "_duplicates" / e.source.name
            else:
                e.target = target_for(e.record, e.source, out)
                hashes[h] = e.target
                if key:
                    keys[key] = e.target
        t, n = e.target, 1
        while t in used:
            n += 1
            t = e.target.with_name(f"{e.target.stem}-{n}{e.target.suffix}")
        e.target = t
        used.add(t)
    return entries


def apply(entries: list[Entry]) -> None:
    for e in entries:
        e.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(e.source, e.target)  # copy, never move: the originals are the client's records


def write_ledger(entries: list[Entry], out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / "ledger.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "vendor", "doc_type", "category", "currency", "total", "tax", "status", "filed_as", "original", "notes"])
        for e in sorted(entries, key=lambda e: (e.record.date.isoformat() if e.record and e.record.date else "9999", e.source.name)):
            r = e.record
            status = "unreadable" if r is None else "duplicate" if e.duplicate_of else "review" if r.needs_review else "ok"
            w.writerow([
                r.date if r and r.date else "", r.vendor if r else "", r.doc_type if r else "", r.category if r else "",
                r.currency if r else "", f"{r.total:.2f}" if r and r.total else "", f"{r.tax:.2f}" if r else "",
                status, e.target.relative_to(out), e.source.name, "; ".join(r.warnings) if r else e.error or "",
            ])
    return path


def summarize(entries: list[Entry]) -> dict:
    spend: dict[tuple[str, str], float] = defaultdict(float)
    income: dict[str, float] = defaultdict(float)
    for e in entries:
        r = e.record
        if r is None or e.duplicate_of or r.needs_review or not r.total:
            continue
        if r.category == "income":
            income[r.currency] += r.total
        else:
            spend[(r.currency, r.category)] += r.total
    return {"spend": dict(spend), "income": dict(income)}
