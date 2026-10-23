"""PREVIEW-ONLY alert digests for GitHub Actions. Never sends email.
Subscribers come from a CSV (email,lang,size,age_group,sex,breed,shelter,confirmed) at env SUBSCRIBERS_CSV_URL
(e.g. a Google Form's linked Sheet published as CSV, stored as a repo secret). If unset, uses sample_subscribers.csv."""
import csv, io, os, json, datetime, requests, matcher
src=os.environ.get("SUBSCRIBERS_CSV_URL")
text=requests.get(src,timeout=30).text if src else open("sample_subscribers.csv").read()
subs=[s for s in csv.DictReader(io.StringIO(text)) if s.get("confirmed","").lower() in ("1","true","yes")]
data=json.load(open("docs/dogs.json")); since=(datetime.datetime.now()-datetime.timedelta(hours=1, minutes=5)).isoformat()
new=[d for d in data["dogs"] if d["first_seen"]>=since]
out=[]
for s in subs:
    m=[d for d in new if matcher.matches(s,d)]
    if m:
        l=s.get("lang") if s.get("lang") in ("en","es") else "en"
        head="AdoptMiamiDogs: new dogs for you" if l=="en" else "AdoptMiamiDogs: perros nuevos para ti"
        body="\n".join(f"- {d['name']} ({d['breed']}, {d['sex']}, {d['age']}) — {d['shelter']}: {d['link']}" for d in m)
        out.append(f"[PREVIEW-NOT SENT] To:{s['email']} | {head}\n{body}\n--\nFree forever. Unsubscribe: reply STOP or use the form link. {matcher.ADDR}\n")
os.makedirs("previews",exist_ok=True); open("previews/digest.txt","w").write("\n".join(out) or "no matches")
print(f"{len(new)} new dogs, {len(subs)} confirmed subs, {len(out)} digest previews (not sent)")
