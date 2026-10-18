from datetime import date
from pathlib import Path

import pytest

from shoebox import organize
from shoebox.cli import main, process
from shoebox.extract import ExtractError, extract_text
from shoebox.llm import LLMError, OllamaClient
from shoebox.parse import validate

TODAY = date(2026, 10, 18)
GOOD = {"doc_type": "receipt", "vendor": "GitHub", "date": "2026-04-02", "total": 4.0, "tax": 0, "currency": "usd", "category": "software"}
TEXT = "GitHub\nReceipt 2026-04-02\nTotal paid $4.00\n"


class Fake:
    def __init__(self, out): self.out = out
    def complete_json(self, system, user, schema): return dict(self.out)


def test_refuses_remote_host():
    with pytest.raises(LLMError):
        OllamaClient(base_url="https://api.example.com")
    OllamaClient(base_url="http://localhost:11434")


def test_validate_ok():
    r = validate(GOOD, TEXT, TODAY)
    assert not r.needs_review and r.currency == "USD" and r.total == 4.0


def test_hallucinated_total_flagged():
    r = validate({**GOOD, "total": 40.0}, TEXT, TODAY)
    assert r.needs_review and any("not found" in w for w in r.warnings)


def test_future_and_bad_dates_flagged():
    assert validate({**GOOD, "date": "2027-01-01"}, TEXT, TODAY).needs_review
    assert validate({**GOOD, "date": "someday"}, TEXT, TODAY).needs_review


def test_invoice_sent_is_income():
    r = validate({**GOOD, "doc_type": "invoice_sent", "category": "software"}, TEXT, TODAY)
    assert r.category == "income"


def test_extract_txt_and_short(tmp_path):
    p = tmp_path / "a.txt"; p.write_text(TEXT)
    assert "GitHub" in extract_text(p)
    q = tmp_path / "b.txt"; q.write_text("hi")
    with pytest.raises(ExtractError):
        extract_text(q)


def test_plan_dedupe_and_names(tmp_path):
    inbox = tmp_path / "in"; inbox.mkdir()
    (inbox / "a.txt").write_text(TEXT); (inbox / "b.txt").write_text(TEXT)  # byte-identical re-send
    (inbox / "c.txt").write_text("GitHub\nReceipt 2026-04-02\nTotal paid $4.00\nextra line\n")  # same vendor/date/total
    out = tmp_path / "out"
    es = organize.plan(process(inbox, Fake(GOOD)), out)
    assert es[0].target == out / "2026" / "2026-04" / "software" / "2026-04-02_GitHub_4.00.txt"
    assert es[1].duplicate_of and es[2].duplicate_of
    assert not out.exists()  # planning never touches disk


def test_cli_dry_run_then_apply(tmp_path, monkeypatch):
    inbox = tmp_path / "in"; inbox.mkdir(); (inbox / "a.txt").write_text(TEXT); (inbox / "scan.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    monkeypatch.setattr("shoebox.cli.OllamaClient", lambda m: Fake(GOOD))
    out = tmp_path / "out"
    assert main([str(inbox), "--out", str(out)]) == 0
    assert (out / "ledger.csv").exists() and not (out / "2026").exists()
    assert main([str(inbox), "--out", str(out), "--apply"]) == 0
    assert (out / "2026" / "2026-04" / "software" / "2026-04-02_GitHub_4.00.txt").exists()
    assert (out / "_unreadable" / "scan.pdf").exists()
    assert (inbox / "a.txt").exists()  # originals untouched
    assert "unreadable" in (out / "ledger.csv").read_text()
