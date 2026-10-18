"""Generate synthetic receipts/invoices (txt + PDF) with ground truth in truth.json. All data is fictional."""
import json, sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

out = Path(sys.argv[1] if len(sys.argv) > 1 else "samples/inbox"); out.mkdir(parents=True, exist_ok=True)

# (filename, doc_type, vendor, date, subtotal, tax, currency, category, layout)
DOCS = [
 ("adobe.pdf","receipt","Adobe","2026-03-14",49.99,0.00,"USD","software","pdf"),
 ("github.txt","receipt","GitHub","2026-04-02",4.00,0.00,"USD","software","txt"),
 ("delta.pdf","receipt","Delta Air Lines","2026-05-09",412.30,0.00,"USD","travel","pdf"),
 ("cafe.txt","receipt","Blue Door Cafe","2026-05-10",18.40,1.47,"USD","meals","txt"),
 ("staples.pdf","receipt","Staples","2026-06-21",126.75,10.14,"USD","office","pdf"),
 ("comcast.txt","invoice_received","Comcast Business","2026-06-30",89.00,7.12,"USD","utilities","txt"),
 ("apple.pdf","receipt","Apple Store","2026-07-04",1299.00,103.92,"USD","hardware","pdf"),
 ("figma.txt","receipt","Figma","2026-07-15",15.00,0.00,"USD","software","txt"),
 ("lawyer.pdf","invoice_received","Hart & Lowell LLP","2026-08-01",750.00,0.00,"USD","professional-services","pdf"),
 ("acme_inv.pdf","invoice_sent","Acme Robotics","2026-08-12",3200.00,0.00,"USD","income","pdf"),
 ("globex_inv.txt","invoice_sent","Globex Corp","2026-09-03",1850.00,0.00,"USD","income","txt"),
 ("facebook_ads.txt","receipt","Meta Ads","2026-09-18",240.00,0.00,"USD","marketing","txt"),
 ("train.txt","receipt","Deutsche Bahn","2026-09-22",89.90,14.35,"EUR","travel","txt"),
 ("domain.txt","receipt","Namecheap","2026-10-01",14.98,0.00,"USD","software","txt"),
 ("coworking.pdf","invoice_received","Hubspace Coworking","2026-10-03",320.00,25.60,"USD","office","pdf"),
]
truth = {}
for fn, dt, vendor, d, sub, tax, cur, cat, layout in DOCS:
    total = round(sub + tax, 2)
    sym = {"USD": "$", "EUR": "€"}[cur]
    if dt == "invoice_sent":
        lines = ["INVOICE", f"From: Jordan Rivera Design (freelancer)", f"Bill To: {vendor}", f"Invoice date: {d}", "Description: Brand identity project", f"Subtotal {sym}{sub:,.2f}", f"Amount due {sym}{total:,.2f}"]
    elif dt == "invoice_received":
        lines = [vendor.upper(), f"Invoice for Jordan Rivera Design", f"Invoice date: {d}", f"Services {sym}{sub:,.2f}", f"Tax {sym}{tax:,.2f}", f"TOTAL DUE {sym}{total:,.2f}"]
    else:
        lines = [vendor, f"Receipt  {d}", f"Item(s) {sym}{sub:,.2f}", f"Tax {sym}{tax:,.2f}", f"Total paid {sym}{total:,.2f}", "Thank you for your purchase"]
    if layout == "txt":
        (out / fn).write_text("\n".join(lines) + "\n")
    else:
        c = canvas.Canvas(str(out / fn), pagesize=letter); y = 720
        for ln in lines: c.drawString(72, y, ln); y -= 22
        c.save()
    truth[fn] = {"doc_type": dt, "vendor": vendor, "date": d, "total": total, "currency": cur, "category": cat}
(out / "truth.json").write_text(json.dumps(truth, indent=1))
# duplicate re-send and an unreadable scan stand-in
(out / "github_resend.txt").write_text((out / "github.txt").read_text())
(out / "scan_0042.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
print(f"wrote {len(DOCS)+2} files to {out}")
