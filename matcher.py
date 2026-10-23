import os
SITE=os.environ.get("SITE_URL","http://localhost:8080")
ADDR=os.environ.get("POSTAL_ADDRESS","[POSTAL ADDRESS REQUIRED BEFORE SENDING]")
"""Queue alert emails for new dogs matching subscriber criteria. PREVIEW ONLY - never sends."""
import datetime, scraper
FOOT={"en":"\n--\nAdoptMiamiDogs — free alerts, always. You get this because you confirmed alerts for: {crit}.\nUnsubscribe (one click): {site}/unsubscribe/{tok}?lang=en\n{addr}",
 "es":"\n--\nAdoptMiamiDogs — alertas gratis, siempre. Recibes esto porque confirmaste alertas para: {crit}.\nDarse de baja (un clic): {site}/unsubscribe/{tok}?lang=es\n{addr}"}
CONF={"en":("Confirm your free AdoptMiamiDogs alerts","Click to confirm: {site}/confirm/{tok}?lang=en\nIf you didn't sign up, ignore this email — you won't hear from us again."),
 "es":("Confirma tus alertas gratis de AdoptMiamiDogs","Haz clic para confirmar: {site}/confirm/{tok}?lang=es\nSi no te suscribiste, ignora este correo.")}
def crit(s): return ", ".join(f"{k}={s[k]}" for k in ["size","age_group","sex","breed","shelter"] if s[k]) or "any dog"
def log(email,sub,body): open("outbox_preview.log","a").write(f"[PREVIEW-NOT SENT] To:{email} | {sub}\n{body}\n\n")
def queue_confirmation(sid):
    c=scraper.db(); s=c.execute("select * from subscribers where id=?",(sid,)).fetchone(); l=s["lang"] if s["lang"] in CONF else "en"
    sub,body=CONF[l]; body=body.format(site=SITE,tok=s["token"])+FOOT[l].format(crit=crit(s),site=SITE,tok=s["token"],addr=ADDR)
    c.execute("insert or ignore into outbox(subscriber_id,dog_id,subject,body,created) values(?,?,?,?,datetime('now'))",(sid,"CONFIRM",sub,body)); c.commit(); log(s["email"],sub,body)
T={"en":("AdoptMiamiDogs: {name} just arrived at {shelter}","{name} ({breed}, {sex}, {age}) just arrived at {shelter} on {intake_date}.\nPhoto: {photo}\nSee: {link}\nAdoptions are first-come, first-served — visit soon!"),
   "es":("AdoptMiamiDogs: {name} acaba de llegar a {shelter}","{name} ({breed}, {sex}, {age}) acaba de llegar a {shelter} el {intake_date}.\nFoto: {photo}\nVer: {link}\n¡Las adopciones son por orden de llegada — visítalo pronto!")}
def matches(s,d):
    return all([(not s["size"] or s["size"]==d["size"]),(not s["age_group"] or s["age_group"]==d["age_group"]),(not s["sex"] or s["sex"].lower()==d["sex"].lower()),
                (not s["shelter"] or s["shelter"]==d["shelter"]),(not s["breed"] or s["breed"].lower() in d["breed"].lower())])
def queue(dog_ids):
    c=scraper.db(); now=datetime.datetime.now().isoformat(timespec="seconds"); n=0
    for i in dog_ids:
        d=c.execute("select * from dogs where id=? and adoptable=1",(i,)).fetchone()
        if not d: continue
        for s in c.execute("select * from subscribers where confirmed=1").fetchall():
            if matches(s,d):
                sub,body=T.get(s["lang"],T["en"]); cur=c.execute("insert or ignore into outbox(subscriber_id,dog_id,subject,body,created) values(?,?,?,?,?)",(s["id"],i,sub.format(**d),body.format(**d)+FOOT.get(s["lang"],FOOT["en"]).format(crit=crit(s),site=SITE,tok=s["token"],addr=ADDR),now)); n+=cur.rowcount
    c.commit()
    for r in c.execute("select o.*,s.email from outbox o join subscribers s on s.id=o.subscriber_id where o.created=?",(now,)):
        open("outbox_preview.log","a").write(f"[PREVIEW-NOT SENT] To:{r['email']} | {r['subject']}\n{r['body']}\n\n")
    print(f"queued {n} alert previews (not sent)"); return n
if __name__=="__main__":
    import sys; queue(scraper.run())
