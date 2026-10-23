"""Export active adoptable dogs to docs/dogs.json for the static GitHub Pages site."""
import json, datetime, scraper
c=scraper.db()
rows=[dict(r) for r in c.execute("""select id,shelter,name,breed,age,age_group,sex,size,size_source,weight_lbs,photo,intake_date,link,first_seen
  from dogs where active=1 and adoptable=1 order by intake_date desc""")]
base=c.execute("select min(at) from runs").fetchone()[0] or ""
for r in rows:
    if r["first_seen"]<=base: r["first_seen"]="2000-01-01T00:00:00"  # initial baseline, not new
json.dump({"updated":datetime.datetime.now().astimezone().isoformat(timespec="seconds"),"count":len(rows),"dogs":rows},
          open("docs/dogs.json","w"),ensure_ascii=False,separators=(",",":"))
print("exported",len(rows))
