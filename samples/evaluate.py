"""Score a model against samples/truth.json: field accuracy and how many errors Shoebox's validator flags."""
import json, sys, time
from pathlib import Path
from shoebox.extract import extract_text
from shoebox.llm import OllamaClient
from shoebox.parse import SCHEMA, SYSTEM, validate

model = sys.argv[1]; inbox = Path("samples/inbox"); truth = json.load(open("samples/truth.json"))
c = OllamaClient(model); fields = ["doc_type", "vendor", "date", "total", "category"]
hit = {f: 0 for f in fields}; n = 0; wrong_unflagged = 0; wrong_flagged = 0; t0 = time.time()
for fn, t in truth.items():
    text = extract_text(inbox / fn); r = validate(c.complete_json(SYSTEM, f"Document text:\n---\n{text}\n---", SCHEMA), text)
    got = {"doc_type": r.doc_type, "vendor": r.vendor, "date": str(r.date), "total": r.total, "category": r.category}
    ok = {f: (got[f] == t[f] if f != "vendor" else got[f].lower() == t[f].lower()) for f in fields}
    for f in fields: hit[f] += ok[f]
    n += 1
    if not all(ok.values()):
        wrong_flagged += r.needs_review; wrong_unflagged += not r.needs_review
        print("MISS", fn, {f: (got[f], t[f]) for f in fields if not ok[f]}, r.warnings)
print(f"\n{model}: {n} docs in {time.time()-t0:.0f}s")
for f in fields: print(f"  {f:<9}{hit[f]}/{n}")
print(f"  docs with any wrong field: {wrong_flagged+wrong_unflagged} (flagged for review: {wrong_flagged}, silent: {wrong_unflagged})")
