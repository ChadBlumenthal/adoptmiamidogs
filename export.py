"""Export active adoptable dogs to docs/dogs.json for the static GitHub Pages site."""
import json, datetime, scraper
c=scraper.db()
rows=[dict(r) for r in c.execute("""select id,shelter,name,breed,age,age_group,sex,size,size_source,weight_lbs,photo,intake_date,link,first_seen,substr(coalesce(description,''),1,300) as description
  from dogs where active=1 and adoptable=1 order by intake_date desc""")]
base={sl:(c.execute("select min(at) from runs where shelter=?",(sl,)).fetchone()[0] or "") for sl in scraper.SHELTERS}
for r in rows:
    if r["first_seen"]<=base.get(r["id"].split(":")[0],""): r["first_seen"]="2000-01-01T00:00:00"  # per-source baseline, not new
import os
# Private-owner rehoming: ONLY entries Chad has reviewed and copied into rehome/approved.json are published.
for a in json.load(open("rehome/approved.json")) if os.path.exists("rehome/approved.json") else []:
    if a.get("approved") is True:
        rows.append(dict(id="rehome:"+str(a["id"]),shelter="Private rehoming (reviewed)",name=a.get("name",""),breed=a.get("breed",""),age=a.get("age",""),
          age_group=a.get("age_group","adult"),sex=a.get("sex",""),size=a.get("size","medium"),size_source="owner",weight_lbs=a.get("weight_lbs"),
          photo=a.get("photo",""),intake_date=a.get("approved_on",""),link=a.get("contact_url",""),first_seen=a.get("approved_on","2000-01-01")))
META={"miad":dict(city="Doral",county="Miami-Dade County",adopt_url="https://www.miamidade.gov/global/service.page?Mduid_service=ser159925122910773"),
 "BrowardAllAnimals":dict(city="Fort Lauderdale",county="Broward County",adopt_url="https://www.broward.org/animal/Adoptions"),
 "PBCO":dict(city="West Palm Beach",county="Palm Beach County",adopt_url="https://discover.pbc.gov/publicsafety/animalcare/Pages/default.aspx"),
 "hsgm":dict(city="Doral",county="Miami-Dade County",adopt_url="https://www.humanesocietymiami.org/adopt-a-pet-today/",
   source_url="https://www.humanesocietymiami.org/adopt-a-pet-today/",source="public listings (shelter website)"),
 "hsbc":dict(city="Fort Lauderdale",county="Broward County",adopt_url="https://humanebroward.com/dogs/",source_url="https://humanebroward.com/dogs/",source="public listings (shelter website)"),
 "CCDASAllAnimals":dict(city="Naples",county="Collier County",adopt_url="https://www.colliercountyfl.gov/government/public-services/divisions/domestic-animal-services"),
 "LeeCountyAdoptablePets":dict(city="Fort Myers",county="Lee County",adopt_url="https://www.leegov.com/animalservices"),
 "SaintLucieAdopt":dict(city="Fort Pierce",county="St. Lucie County",adopt_url="https://www.stlucieco.gov/departments-services/a-z/animal-safety-services-protection-division"),
 "hstc":dict(city="Palm City",county="Martin County",adopt_url="https://www.hstc1.org/dogs/",source_url="https://www.hstc1.org/dogs/",source="public listings (PetPoint widget on shelter site)")}
REGION={"Miami-Dade County":"Miami-Dade","Broward County":"Broward","Palm Beach County":"Palm Beach","Martin County":"Treasure Coast","St. Lucie County":"Treasure Coast","Collier County":"Southwest FL","Lee County":"Southwest FL"}
shelters=[]
for slug,name in scraper.SHELTERS.items():
    last=c.execute("select max(at) from runs where shelter=?",(slug,)).fetchone()[0]
    last=datetime.datetime.fromisoformat(last).replace(tzinfo=datetime.timezone.utc).isoformat(timespec="seconds") if last else None
    m=dict(source_url=f"{scraper.BASE}/{slug}?at=DOG",source="public listings (24PetConnect)"); m.update(META[slug])
    m["region"]=REGION.get(m["county"],"Other")
    shelters.append(dict(name=name,**m,count=sum(r["shelter"]==name for r in rows),last_updated=last))
json.dump({"shelters":shelters,"updated":datetime.datetime.now().astimezone().isoformat(timespec="seconds"),"count":len(rows),"dogs":rows},
          open("docs/dogs.json","w"),ensure_ascii=False,separators=(",",":"))
print("exported",len(rows))
