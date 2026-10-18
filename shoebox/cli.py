from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import organize
from .extract import SUPPORTED, ExtractError, extract_text
from .llm import LLMError, OllamaClient
from .parse import SCHEMA, SYSTEM, validate


def process(inbox: Path, client) -> list[organize.Entry]:
    entries = []
    for p in sorted(inbox.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in SUPPORTED or p.name.startswith("."):
            continue
        try:
            text = extract_text(p)
            rec = validate(client.complete_json(SYSTEM, f"Document text:\n---\n{text}\n---", SCHEMA), text)
            entries.append(organize.Entry(p, rec))
        except ExtractError as e:
            entries.append(organize.Entry(p, None, str(e)))
    return entries


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="shoebox", description="Sort receipts and invoices locally.")
    ap.add_argument("inbox", type=Path)
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--apply", action="store_true", help="copy files into OUT (default is a dry run that only writes the ledger)")
    a = ap.parse_args(argv)
    if not a.inbox.is_dir():
        print(f"not a folder: {a.inbox}", file=sys.stderr)
        return 2
    try:
        entries = organize.plan(process(a.inbox, OllamaClient(a.model)), a.out)
    except LLMError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    ledger = organize.write_ledger(entries, a.out)
    if a.apply:
        organize.apply(entries)
    for e in entries:
        tag = "DUP " if e.duplicate_of else "????" if e.record is None else "REV " if e.record.needs_review else "ok  "
        print(f"{tag} {e.source.name} -> {e.target.relative_to(a.out)}")
    s = organize.summarize(entries)
    for (cur, cat), v in sorted(s["spend"].items()):
        print(f"  spend  {cat:<22}{cur} {v:>10.2f}")
    for cur, v in s["income"].items():
        print(f"  income {'':<22}{cur} {v:>10.2f}")
    print(f"ledger: {ledger}" + ("" if a.apply else "  (dry run: re-run with --apply to copy files)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
