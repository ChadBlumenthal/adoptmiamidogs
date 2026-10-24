"""Export active adoptable dogs to docs/dogs.json for the static GitHub Pages site."""
import json, datetime, scraper
c=scraper.db()
rows=[dict(r) for r in c.execute("""select id,shelter,name,breed,age,age_group,sex,size,size_source,weight_lbs,photo,intake_date,link,first_seen
  from dogs where active=1 and adoptable=1 order by intake_date desc""")]
base=c.execute("select min(at) from runs").fetchone()[0] or ""
for r in rows:
    if r["first_seen"]<=base: r["first_seen"]="2000-01-01T00:00:00"  # initial baseline, not new
META={"miad":dict(city="Doral",county="Miami-Dade County",adopt_url="https://www.miamidade.gov/global/service.page?Mduid_service=ser159925122910773"),
 "BrowardAllAnimals":dict(city="Fort Lauderdale",county="Broward County",adopt_url="https://www.broward.org/animal/Adoptions")}
shelters=[]
for slug,name in scraper.SHELTERS.items():
    last=c.execute("select max(at) from runs where shelter=?",(slug,)).fetchone()[0]
    last=datetime.datetime.fromisoformat(last).replace(tzinfo=datetime.timezone.utc).isoformat(timespec="seconds") if last else None
    shelters.append(dict(name=name,**META[slug],count=sum(r["shelter"]==name for r in rows),last_updated=last,
        source_url=f"{scraper.BASE}/{slug}?at=DOG",source="public listings (24PetConnect)"))
json.dump({"shelters":shelters,"updated":datetime.datetime.now().astimezone().isoformat(timespec="seconds"),"count":len(rows),"dogs":rows},
          open("docs/dogs.json","w"),ensure_ascii=False,separators=(",",":"))
print("exported",len(rows))
