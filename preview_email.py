"""Render a local preview of the alert email (no sending). Usage: python preview_email.py [en|es] [out.html]"""
import sys, json, send_alerts as sa
lang=sys.argv[1] if len(sys.argv)>1 else "en"; out=sys.argv[2] if len(sys.argv)>2 else "/workspace/email_preview.html"
dogs=json.load(open("docs/dogs.json"))["dogs"]
with_p=[d for d in dogs[:40] if d["name"] and not d["name"].upper().startswith("A") and sa.has_photo(d)][:5]
no_p=[d for d in dogs if not (d.get("photo") or "").strip()][:1] or [d for d in dogs[:60] if not sa.has_photo(d)][:1]
sa.ADDR=sa.ADDR or "PO Box 000, Miami, FL 33101 (placeholder)"
open(out,"w").write(sa.body({"lang":lang,"email":"preview@example.com"},with_p[:3]+no_p+with_p[3:5],more=7)); print("wrote",out)
