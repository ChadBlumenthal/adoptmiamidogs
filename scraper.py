"""Polite fetcher for 24PetConnect county shelter pages (no robots.txt exists on site: 404).
1 request / 2s, identifying UA."""
import re, sqlite3, time, datetime, requests
from bs4 import BeautifulSoup
DB="data.db"; BASE="https://24petconnect.com"
SHELTERS={"miad":"Miami-Dade Animal Services","BrowardAllAnimals":"Broward County Animal Care","PBCO":"Palm Beach County Animal Care & Control","hsgm":"Humane Society of Greater Miami","hsbc":"Humane Society of Broward County"}
NON24={"hsgm","hsbc"}
UA={"User-Agent":"AdoptMiamiDogs-MVP/0.2 (free non-commercial adoption alerts; polite 1 req/2s)"}
SMALL=("chihuahua","yorkshire","shih tzu","maltese","pomeranian","dachshund","miniature","toy","rat terrier","pug","bichon","jack russell","small")
LARGE=("shepherd","pit bull","american staff","labrador","retriever","rottweiler","mastiff","husky","great dane","doberman","boxer","cane corso","bulldog, american","american bulldog","dogo","large","pyrenees","malinois")
def size_of(b):
    b=b.lower()
    if any(k in b for k in SMALL): return "small"
    if any(k in b for k in LARGE): return "large"
    return "medium"
def age_years(a):
    y=re.search(r"(\d+)\s*year",a); m=re.search(r"(\d+)\s*month",a); w=re.search(r"(\d+)\s*week",a)
    return (int(y.group(1)) if y else 0)+(int(m.group(1))/12 if m else 0)+(int(w.group(1))/52 if w else 0)
def age_group(y): return "puppy" if y<1 else "adult" if y<7 else "senior"
def db():
    c=sqlite3.connect(DB, timeout=30); c.row_factory=sqlite3.Row
    c.executescript("""create table if not exists dogs(id text primary key, shelter text, name text, breed text, age text, age_years real,
      age_group text, sex text, size text, photo text, intake_date text, link text, view_type text, first_seen text, last_seen text, active int default 1);
    create table if not exists subscribers(id integer primary key, email text, lang text, size text, age_group text, breed text, sex text, shelter text, created text);
    create table if not exists outbox(id integer primary key, subscriber_id int, dog_id text, subject text, body text, created text, status text default 'preview', unique(subscriber_id,dog_id));
    create table if not exists runs(id integer primary key, at text, shelter text, fetched int, new int);""")
    for col in ["weight_lbs real","size_source text default 'breed-guess'","description text","kennel text","adoptable int default 1","detail_fetched int default 0","photo_checked int default 0"]:
        try: c.execute(f"alter table dogs add column {col}")
        except sqlite3.OperationalError: pass
    for col in ["confirmed int default 0","token text"]:
        try: c.execute(f"alter table subscribers add column {col}")
        except sqlite3.OperationalError: pass
    c.commit(); return c
CODES={"miad":"MIAD","BrowardAllAnimals":"BRWD","PBCO":"PBCO"}
def size_from_weight(w): return "small" if w<25 else "medium" if w<=55 else "large"
def fetch_details(c, limit=None):
    """Fetch per-dog detail pages (1 req / 2s) for dogs not yet detailed."""
    rows=c.execute("select id from dogs where active=1 and detail_fetched=0").fetchall()[:limit]; n=0
    for (i,) in rows:
        slug,aid=i.split(":"); url=f"{BASE}/{slug}/Details/{CODES[slug]}/{aid}"
        try:
            r=requests.get(url,headers=UA,timeout=30); s=BeautifulSoup(r.text,"html.parser")
            g=lambda k:(s.select_one(f".text_{k}").get_text(" ",strip=True) if s.select_one(f".text_{k}") else "")
            if not s.select_one(".text_Description"): c.execute("update dogs set detail_fetched=-1, link=? where id=?",(url,i))
            else:
                w=re.search(r"weigh\s+([\d.]+)\s*pound",g("MoreInfo")); w=float(w.group(1)) if w else None
                upd=dict(id=i,link=url,desc=g("Description"),kennel=g("KennelNumber"),w=w)
                c.execute("update dogs set link=:link,description=:desc,kennel=:kennel,weight_lbs=:w,detail_fetched=1 where id=:id",upd)
                if w: c.execute("update dogs set size=?,size_source='weight' where id=?",(size_from_weight(w),i))
            n+=1
            c.commit()
            if n%50==0: print("details",n,"/",len(rows),flush=True)
        except Exception as e: print("detail err",i,e)
        time.sleep(2)
    c.commit(); return n
PLACEHOLDER_LEN="7213"  # 24PetConnect "No Image Available" jpeg (md5 1e52179377469e3a38bb081c507c06ed)
def check_photos(c):
    """Blank out shelter placeholder photos (1 req / 2s, headers only)."""
    rows=c.execute("select id,photo from dogs where active=1 and photo_checked=0").fetchall(); n=0
    for i,p in rows:
        if not p or "No_pic" in p: c.execute("update dogs set photo='',photo_checked=1 where id=?",(i,)); c.commit(); continue
        try:
            r=requests.get(p,headers=UA,timeout=30,stream=True); ln=r.headers.get("Content-Length"); r.close()
            c.execute("update dogs set photo=?,photo_checked=1 where id=?",("" if ln==PLACEHOLDER_LEN else p,i)); c.commit(); n+=1
        except Exception as e: print("photo err",i,e)
        time.sleep(2)
    return n
def parse(html, slug):
    s=BeautifulSoup(html,"html.parser"); out=[]
    for g in s.select("div.gridResult"):
        t=lambda k:(g.select_one(f".text_{k}").get_text(strip=True) if g.select_one(f".text_{k}") else "")
        aid=g["id"].replace("Result_",""); name=re.sub(r"\s*\(A\d+\)","",t("Name")).title()
        img=g.select_one("img"); ay=age_years(t("Age"))
        out.append(dict(id=f"{slug}:{aid}",shelter=SHELTERS[slug],name=name,breed=t("Breed"),age=t("Age"),age_years=round(ay,2),age_group=age_group(ay),
          sex=t("Gender"),size=size_of(t("Breed")),photo=BASE+img["src"] if img else "",intake_date=t("Broughttotheshelter").replace(".","-"),
          link=f"{BASE}/{slug}/Details/{CODES[slug]}/{aid}",view_type=t("ViewType"),
          adoptable=0 if (slug in ("BrowardAllAnimals","PBCO") and re.fullmatch(r"A\d+",name.strip(), re.I)) else 1))
    tot=re.search(r"of (\d+)",s.select_one("#AnimalCountHeader").get_text()) if s.select_one("#AnimalCountHeader") else None
    return out,int(tot.group(1)) if tot else 0
HSGM="https://www.humanesocietymiami.org"
def fetch_hsgm():
    """HSGM's own WordPress page (robots.txt allows it); all cards are server-rendered."""
    r=requests.get(HSGM+"/adopt-a-pet-today/",headers=UA,timeout=30); r.raise_for_status()
    out=[]
    for g in BeautifulSoup(r.text,"html.parser").select("li.adoptable-pet-card"):
        if g.get("data-species")!="Dog": continue
        a=g.select_one("a"); m=re.search(r"id=(\d+)",a["href"]) if a else None
        if not m: continue
        sp=[x.get_text(" ",strip=True).replace("●","").strip() for x in g.select(".adoptable-pet-details > span")]
        age=next((x for x in sp if re.search(r"year|month|week",x)),""); sex=next((x for x in sp if x in("Male","Female")),"")
        w=next((float(re.search(r"[\d.]+",x).group()) for x in sp if "pound" in x),None)
        breed=(g.select_one(".adoptable-pet-breed") or BeautifulSoup("","html.parser")).get_text(strip=True)
        img=g.select_one("img"); ay=age_years(age)
        out.append(dict(id=f"hsgm:{m.group(1)}",shelter=SHELTERS["hsgm"],name=g.select_one(".adoptable-pet-name").get_text(strip=True).title(),
          breed=breed,age=age,age_years=round(ay,2),age_group=age_group(ay),sex=sex,size=size_from_weight(w) if w else size_of(breed),
          photo=img["src"] if img else "",intake_date="",link=HSGM+a["href"],view_type="",adoptable=1,weight=w))
    return out
HSBC="https://humanebroward.com"
def fetch_hsbc():
    """Humane Society of Broward's public WordPress JSON endpoint (robots.txt: Disallow nothing). 21 per page, 1 req / 2s."""
    import json as _j, html as _h
    out=[]; pg=1
    while pg<20:
        r=requests.get(HSBC+"/wp-json/petfinder-unl/v1/get-pets",params={"type":"dog","page":pg},headers=UA,timeout=30); r.raise_for_status()
        d=r.json(); d=_j.loads(d) if isinstance(d,str) else d; s=BeautifulSoup(d["display"],"html.parser"); n=0
        for g in s.select(".pet-item"):
            a=g.select_one("a.pet-item-link"); m=re.search(r"id=(A\d+)",a["href"]) if a else None
            if not m or any(o["id"]=="hsbc:"+m.group(1) for o in out): continue
            det=[x.get_text(" ",strip=True) for x in g.select(".pet-detail")]; n+=1
            breed=det[1] if len(det)>1 else ""; sex=det[2] if len(det)>2 else ""; aw=det[3] if len(det)>3 else ""
            age=aw.split("–")[0].strip(); w=re.search(r"([\d.]+)\s*lbs",aw); w=float(w.group(1)) if w else None
            img=g.select_one("img"); ay=age_years(age); name=g.select_one(".pet-name").get_text(strip=True).title()
            out.append(dict(id="hsbc:"+m.group(1),shelter=SHELTERS["hsbc"],name=name,breed=breed,age=age,age_years=round(ay,2),age_group=age_group(ay),sex=sex,
              size=size_from_weight(w) if w else size_of(breed),photo=img["src"] if img else "",intake_date="",
              link=f"{HSBC}/pet/?id={m.group(1)}&type=dog",view_type="",adoptable=0 if re.fullmatch(r"A\d+",name,re.I) else 1,weight=w))
        tot=re.search(r"of (\d+)",s.get_text()); 
        if not n or not tot or len(out)>=int(tot.group(1)): return out
        pg+=1; time.sleep(2)
    return out
def fetch(slug):
    if slug=="hsgm": return fetch_hsgm()
    if slug=="hsbc": return fetch_hsbc()
    dogs=[]; idx=0
    while True:
        r=requests.get(f"{BASE}/{slug}",params={"at":"DOG","index":idx},headers=UA,timeout=30); r.raise_for_status()
        page,total=parse(r.text,slug); dogs+=page; idx+=30
        if not page or idx>=total: return dogs
        time.sleep(2)
def run():
    c=db(); now=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"); first=c.execute("select count(*) from dogs").fetchone()[0]==0; new=[]
    for slug in SHELTERS:
        base=not c.execute("select 1 from runs where shelter=?",(slug,)).fetchone()
        dogs=fetch(slug); ids={d["id"] for d in dogs}; n=0
        for d in dogs:
            if not c.execute("select 1 from dogs where id=?",(d["id"],)).fetchone():
                n+=1; (None if base else new.append(d["id"])); c.execute(f"insert into dogs(id,shelter,name,breed,age,age_years,age_group,sex,size,photo,intake_date,link,view_type,first_seen,last_seen,active,adoptable) values(:id,:shelter,:name,:breed,:age,:age_years,:age_group,:sex,:size,:photo,:intake_date,:link,:view_type,'{now}','{now}',1,:adoptable)",d)
            if d.get("weight"): c.execute("update dogs set weight_lbs=?,size=?,size_source='weight',detail_fetched=1 where id=?",(d["weight"],d["size"],d["id"]))
            elif slug in NON24: c.execute("update dogs set detail_fetched=1 where id=?",(d["id"],))
            c.execute("update dogs set last_seen=?,active=1,adoptable=?,link=? where id=?",(now,d["adoptable"],d["link"],d["id"]))
        for (i,) in c.execute("select id from dogs where shelter=? and active=1",(SHELTERS[slug],)).fetchall():
            if i not in ids: c.execute("update dogs set active=0 where id=?",(i,))
        c.execute("insert into runs(at,shelter,fetched,new) values(?,?,?,?)",(now,slug,len(dogs),n)); c.commit()
        print(f"{slug}: fetched {len(dogs)}, new {n}")
    fetch_details(c); check_photos(c)
    return [] if first else new   # first run = baseline, no alerts
if __name__=="__main__": run()
