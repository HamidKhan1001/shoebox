# Shoebox

Local-only receipt and invoice sorter for freelancers. Point it at a messy folder; it reads each document with an open-weight model running on your own machine (Ollama, default `llama3.2:3b`), files copies into `YYYY/YYYY-MM/category/`, flags duplicates, and writes a `ledger.csv` for your accountant. Nothing leaves your laptop: the client refuses any non-loopback host.

## Use
```bash
python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
ollama pull llama3.2:3b
shoebox ~/Downloads/receipts --out ~/books         # dry run, writes ledger only
shoebox ~/Downloads/receipts --out ~/books --apply # copies files (originals untouched)
pytest
```
Supports text-based PDFs and txt/md/csv/eml/html. Scanned images need OCR, which is not included.

## Trust checks
Small models make mistakes, so every result is validated: the extracted total must appear in the document text, dates must be plausible, and anything failing goes to `_needs-review/` instead of being filed silently.

## Sample data and eval
`python samples/make_samples.py` generates fictional documents; `python samples/evaluate.py llama3.2:3b` scores a model against ground truth. (Results not yet recorded.)

MIT licensed. Model weights are downloaded separately via Ollama under their own licenses.
