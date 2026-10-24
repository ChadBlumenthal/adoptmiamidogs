"""Real email alerts via Brevo (free plan: 300 emails/day). DISABLED unless BREVO_API_KEY + BREVO_LIST_ID + SENDER_EMAIL + POSTAL_ADDRESS are set.
Subscribers live in Brevo: they join through Brevo's hosted double-opt-in form (Brevo handles consent + unsubscribe/blocklist).
Contact attributes used (create in Brevo > Contacts > Settings): LANG, SIZE, AGE_GROUP, SEX, SHELTER, BREED (all optional text/category).
One DAILY digest (8 AM America/New_York) per subscriber with dogs from the previous 24h, max 12; already-alerted (subscriber,dog) pairs are stored as SHA-256 hashes (no emails in the public repo)."""
import os, sys, json, hashlib, datetime, html, requests, scraper, matcher
KEY=os.environ.get("BREVO_API_KEY",""); LIST=os.environ.get("BREVO_LIST_ID",""); SENDER=os.environ.get("SENDER_EMAIL","")
ADDR=os.environ.get("POSTAL_ADDRESS",""); UNSUB=os.environ.get("BREVO_UNSUB_URL","https://chadblumenthal.github.io/adoptmiamidogs/#alerts")
SITE="https://chadblumenthal.github.io/adoptmiamidogs/"; DAILY_CAP=int(os.environ.get("DAILY_CAP","280")); API="https://api.brevo.com/v3"
SHMAP={"hb":"Humane Society of Broward County","md":"Miami-Dade Animal Services","bw":"Broward County Animal Care","pb":"Palm Beach County Animal Care & Control","hs":"Humane Society of Greater Miami"}
def contacts():
    out=[]; off=0
    while True:
        r=requests.get(f"{API}/contacts/lists/{LIST}/contacts",headers={"api-key":KEY},params={"limit":500,"offset":off},timeout=30); r.raise_for_status()
        cs=r.json().get("contacts",[]); out+=cs; off+=500
        if len(cs)<500: return [c for c in out if not c.get("emailBlacklisted")]
def sub_of(c):
    a={k.upper():(str(v).strip() if v is not None else "") for k,v in (c.get("attributes") or {}).items()}; g=lambda k:a.get(k,"").lower()
    return dict(email=c["email"],lang=g("LANG") if g("LANG") in("en","es") else "en",size=g("SIZE"),age_group=g("AGE_GROUP"),sex=g("SEX"),
                breed=a.get("BREED",""),shelter=SHMAP.get(g("SHELTER"),a.get("SHELTER","")))
H=lambda s:hashlib.sha256(s.lower().encode()).hexdigest()[:24]
def body(s,dogs):
    es=s["lang"]=="es"
    li="".join(f'<li style="margin:0 0 14px"><a href="{html.escape(d["link"])}"><b>{html.escape(d["name"] or ("Sin nombre" if es else "Unnamed"))}</b></a> — {html.escape(d["breed"])}, {html.escape(d["sex"])}, {html.escape(d["age"])}<br><small>{html.escape(d["shelter"])}</small>'
               +(f'<br><img src="{html.escape(d["photo"])}" width="160" alt="">' if d.get("photo") else "")+"</li>" for d in dogs)
    intro="Nuevos perros que coinciden con tu alerta:" if es else "New dogs matching your alert:"
    foot=("AdoptMiamiDogs es gratis, siempre. Recibes esto porque confirmaste tus alertas." if es else "AdoptMiamiDogs is free, always. You get this because you confirmed alerts.")
    un="Darse de baja" if es else "Unsubscribe"
    return f'<p>{intro}</p><ul>{li}</ul><p>Adoptions are first-come, first-served. <a href="{SITE}">{SITE}</a></p><hr><p style="font-size:12px;color:#666">{foot}<br><a href="{html.escape(UNSUB)}">{un}</a> · {html.escape(ADDR)}</p>'
def main():
    import zoneinfo
    if os.environ.get("GATE_8AM") and datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York")).hour!=8:
        print("Not 8 AM in New York; skipping (DST-safe double cron)."); return 0
    if os.environ.get("ALERTS_ENABLED")!="true":
        print("Alerts paused (repo variable ALERTS_ENABLED is not 'true'). Nothing sent."); return 0
    if not (KEY and LIST and SENDER and ADDR):
        print("Brevo sending DISABLED (set secrets BREVO_API_KEY, BREVO_LIST_ID, SENDER_EMAIL, POSTAL_ADDRESS). Nothing sent."); return 0
    c=scraper.db(); c.execute("create table if not exists alerts_sent(h text, dog_id text, at text, primary key(h,dog_id))")
    today=datetime.datetime.utcnow().date().isoformat()
    used=c.execute("select count(distinct h||at) from alerts_sent where at>=?",(today,)).fetchone()[0]
    data=json.load(open("docs/dogs.json")); since=(datetime.datetime.utcnow()-datetime.timedelta(hours=24)).isoformat()
    new=[d for d in data["dogs"] if d["first_seen"]>=since]; sent=0; now=datetime.datetime.utcnow().isoformat(timespec="seconds")
    for s in map(sub_of,contacts()):
        if used+sent>=DAILY_CAP: print("daily cap reached"); break
        h=H(s["email"])
        if c.execute("select 1 from alerts_sent where h=? and at>=?",(h,(datetime.datetime.utcnow()-datetime.timedelta(hours=20)).isoformat())).fetchone(): continue  # max 1 email/day
        m=[d for d in new if matcher.matches(s,d) and not c.execute("select 1 from alerts_sent where h=? and dog_id=?",(h,d["id"])).fetchone()]; more=max(0,len(m)-12); m=m[:12]
        if not m: continue
        subj=(f"AdoptMiamiDogs: {len(m)} perro(s) nuevo(s) para ti" if s["lang"]=="es" else f"AdoptMiamiDogs: {len(m)} new dog(s) for you")
        r=requests.post(f"{API}/smtp/email",headers={"api-key":KEY},timeout=30,json={"sender":{"name":"AdoptMiamiDogs","email":SENDER},"to":[{"email":s["email"]}],
            "subject":subj,"htmlContent":body(s,m).replace("<hr>",(f'<p><a href="{SITE}">+{more} more on AdoptMiamiDogs</a></p><hr>' if more else "<hr>")),"headers":{"List-Unsubscribe":f"<{UNSUB}>"},"tags":["dog-alert"]})
        if r.status_code>=300: print("send failed",r.status_code,r.text[:200]); continue
        c.executemany("insert or ignore into alerts_sent values(?,?,?)",[(h,d["id"],now) for d in m]); c.commit(); sent+=1
    print(f"sent {sent} alert emails ({len(new)} recent dogs)"); return sent
if __name__=="__main__": main()
