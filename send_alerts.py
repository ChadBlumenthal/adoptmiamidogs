"""Real email alerts via Brevo (free plan: 300 emails/day). DISABLED unless BREVO_API_KEY + BREVO_LIST_ID + SENDER_EMAIL + POSTAL_ADDRESS are set.
Subscribers live in Brevo: they join through Brevo's hosted double-opt-in form (Brevo handles consent + unsubscribe/blocklist).
Contact attributes used (create in Brevo > Contacts > Settings): LANG, SIZE, AGE_GROUP, SEX, SHELTER, BREED (all optional text/category).
One DAILY digest (8 AM America/New_York) per subscriber with dogs from the previous 24h, max 12; already-alerted (subscriber,dog) pairs are stored as SHA-256 hashes (no emails in the public repo)."""
import os, re, sys, json, hashlib, datetime, html, requests, scraper, matcher
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
PLACEHOLDER_RE=re.compile(r"no_?pic|no[-_]?image|not[-_]available|placeholder|illustration-dog|default[-_]?(pet|image)",re.I)
import functools
@functools.lru_cache(maxsize=512)
def _remote_placeholder(url):
    """24PetConnect serves its 'No Image Available' jpeg (232x246, 7213 bytes) under normal-looking /image/<id> URLs."""
    try:
        r=requests.head(url,headers=scraper.UA,timeout=4,allow_redirects=True)
        return r.headers.get("Content-Length")==scraper.PLACEHOLDER_LEN
    except requests.RequestException: return False
def has_photo(d):
    p=(d.get("photo") or "").strip()
    if not p or PLACEHOLDER_RE.search(p) or p.lower().endswith((".svg",".gif")): return False
    return not ("24petconnect.com/image/" in p and _remote_placeholder(p))
FONT="Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
CORAL="#FF6B5B"; TEAL="#0FA3A3"; INK="#1B1F24"; MUT="#6B7280"; BG="#FBF8F4"
def _e(x): return html.escape(str(x or ""))
def _name(d,es):
    n=(d.get("name") or "").strip()
    if not n or re.fullmatch(r"A\d+|new pet",n,re.I): return ("Nombre pronto" if es else "Name coming soon"),False
    return n.title(),True
def _fill(t,**kw):
    for k,v in kw.items(): t=t.replace("[["+k+"]]",str(v))
    return t
PILL='<span style="display:inline-block;background:#F3EEE8;color:#1B1F24;font-size:12px;font-weight:600;line-height:16px;padding:4px 10px;border-radius:999px;margin:0 4px 6px 0;">[[T]]</span>'
PHOTO='<a href="[[LINK]]" style="text-decoration:none;"><img src="[[SRC]]" width="276" height="210" alt="[[ALT]]" style="display:block;width:100%;max-width:100%;height:210px;object-fit:cover;border:0;outline:none;border-radius:16px 16px 0 0;background:#EDE7E0;"></a>'
NOPHOTO=('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td height="210" align="center" valign="middle" bgcolor="#FFE3DF" '
 'style="height:210px;background:#FFE3DF;background-image:linear-gradient(135deg,#FFEDEA,#FFD3CC);border-radius:16px 16px 0 0;font-family:[[FONT]];text-align:center;">'
 '<div style="width:64px;height:64px;line-height:64px;margin:0 auto;border-radius:999px;background:#FF6B5B;color:#ffffff;font-size:28px;font-weight:800;">[[INI]]</div>'
 '<div style="font-size:13px;color:#C2554A;font-weight:600;padding-top:10px;">&#128062; [[TXT]]</div></td></tr></table>')
CARD=('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:16px;border:1px solid #EFE7DE;">'
 '<tr><td style="padding:0;">[[PH]]</td></tr><tr><td style="padding:14px 16px 16px 16px;font-family:[[FONT]];">'
 '<div style="font-size:18px;line-height:24px;font-weight:800;color:[[NC]];letter-spacing:-0.2px;">[[NAME]]</div>'
 '<div style="font-size:14px;line-height:20px;color:#6B7280;padding:2px 0 10px 0;">[[BREED]]</div>[[PILLS]]'
 '<div style="font-size:13px;line-height:18px;color:#6B7280;padding:4px 0 14px 0;">&#128205; [[SHELTER]]</div>'
 '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tr><td align="center" bgcolor="#FF6B5B" style="border-radius:999px;background:#FF6B5B;">'
 '<a href="[[LINK]]" style="display:block;padding:11px 16px;font-family:[[FONT]];font-size:14px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:999px;">[[MEET]] &rarr;</a></td></tr></table>'
 '</td></tr></table>')
def dog_url(d):
    from urllib.parse import quote
    return SITE+"?dog="+quote(d["id"],safe="")
def _card(d,es):
    link=dog_url(d)
    nm,real=_name(d,es); sex=(d.get("sex") or "").lower()
    sx=("Macho" if es else "Boy") if sex=="male" else ("Hembra" if es else "Girl") if sex=="female" else d.get("sex","")
    age=re.sub(r"\s*old$","",d.get("age") or "")
    pills="".join(_fill(PILL,T=_e(p)) for p in [sx,age] if p)
    if has_photo(d): ph=_fill(PHOTO,LINK=_e(link),SRC=_e(d["photo"]),ALT=_e(nm))
    else: ph=_fill(NOPHOTO,FONT=FONT,INI=_e(nm[:1].upper() if real else "?"),TXT="Foto pronto" if es else "Photo coming soon")
    meet=(f"Conoce a {nm}" if es else f"Meet {nm}") if real else ("Ver perro" if es else "See this dog")
    return _fill(CARD,PH=ph,FONT=FONT,NC=INK if real else MUT,NAME=_e(nm),BREED=_e(d.get("breed")),PILLS=pills,SHELTER=_e(d.get("shelter")),LINK=_e(link),MEET=_e(meet))
DOC='''<!doctype html><html lang="[[LANG]]"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light"><title>AdoptMiamiDogs</title>
<style>body{margin:0;padding:0;} img{-ms-interpolation-mode:bicubic;} a{color:#0FA3A3;}
@media only screen and (max-width:620px){ .wrap{width:100%!important;} .px{padding-left:12px!important;padding-right:12px!important;}
 .col{display:block!important;width:100%!important;max-width:100%!important;padding:0 0 14px 0!important;} .colempty{display:none!important;} .h1{font-size:25px!important;line-height:31px!important;} }</style></head>
<body style="margin:0;padding:0;background:#FBF8F4;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;font-size:1px;line-height:1px;color:#FBF8F4;">[[PRE]]&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#FBF8F4" style="background:#FBF8F4;"><tr><td align="center" style="padding:24px 10px;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;">
<tr><td class="px" style="padding:0 8px 18px 8px;"><table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
 <td width="34" height="34" align="center" valign="middle" bgcolor="#FF6B5B" style="width:34px;height:34px;background:#FF6B5B;background-image:linear-gradient(135deg,#FF6B5B,#FF8A5B);border-radius:11px;font-size:18px;line-height:34px;">&#128054;</td>
 <td style="padding-left:10px;font-family:[[FONT]];font-size:19px;font-weight:800;letter-spacing:-0.3px;"><a href="[[SITE]]" style="color:#1B1F24;text-decoration:none;">Adopt<span style="color:#0FA3A3;">Miami</span>Dogs</a></td>
</tr></table></td></tr>
<tr><td class="px" style="padding:0 8px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#0FA3A3" style="background:#0FA3A3;background-image:linear-gradient(135deg,#12AFAD,#0B8A8A);border-radius:20px;">
 <tr><td style="padding:26px 26px 24px 26px;font-family:[[FONT]];">
 <div style="font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#CFF1EE;">[[KICK]] &#128276;</div>
 <div class="h1" style="font-size:28px;line-height:34px;font-weight:800;letter-spacing:-0.5px;padding:6px 0 8px 0;color:#ffffff;">[[HEAD]]</div>
 <div style="font-size:15px;line-height:22px;color:#E6F7F6;">[[SUB]]</div></td></tr></table></td></tr>
<tr><td class="px" style="padding:16px 8px 0 8px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">[[ROWS]]</table></td></tr>
<tr><td class="px" align="center" style="padding:4px 8px 8px 8px;">[[MORE]]
 <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" bgcolor="#1B1F24" style="border-radius:999px;background:#1B1F24;">
 <a href="[[SITE]]" style="display:inline-block;padding:14px 30px;font-family:[[FONT]];font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:999px;">[[SEE]] &rarr;</a></td></tr></table></td></tr>
<tr><td class="px" align="center" style="padding:28px 16px 8px 16px;font-family:[[FONT]];font-size:12px;line-height:18px;color:#9CA3AF;">
 <div style="font-weight:600;color:#6B7280;">[[F1]]</div><div>[[F2]]</div>
 <div style="padding-top:6px;"><a href="[[UNSUB]]" style="color:#9CA3AF;text-decoration:underline;">[[UN]]</a>[[ADDR]]</div></td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table></body></html>'''
def body(s,dogs,more=0):
    es=s["lang"]=="es"; n=len(dogs)
    head=(f"{n} perro{'s' if n!=1 else ''} nuevo{'s' if n!=1 else ''} para ti hoy" if es else f"{n} new dog{'s' if n!=1 else ''} near you today")
    names=", ".join(_name(d,es)[0] for d in dogs if _name(d,es)[1])[:80]
    pre=(f"{names} y más. Se adopta por orden de llegada." if es else f"Meet {names} and more. Adoptions are first-come, first-served.") if names else head
    rows=""
    for i in range(0,n,2):
        pair=dogs[i:i+2]; cells=""
        for j,d in enumerate(pair):
            pad="0 6px 12px 0" if j==0 else "0 0 12px 6px"
            cells+=f'<td class="col" width="50%" valign="top" style="width:50%;padding:{pad};">{_card(d,es)}</td>'
        if len(pair)==1: cells+='<td class="col colempty" width="50%" style="width:50%;padding:0 0 12px 6px;">&nbsp;</td>'
        rows+=f"<tr>{cells}</tr>"
    more_html=(f'<div style="font-family:{FONT};font-size:14px;font-weight:600;color:{MUT};padding:4px 0 12px 0;">+{more} {"perros más en el sitio" if es else "more dogs on the site"}</div>' if more else "")
    return _fill(DOC,LANG="es" if es else "en",FONT=FONT,SITE=SITE,PRE=_e(pre),HEAD=_e(head),ROWS=rows,MORE=more_html,
        KICK="Tu resumen diario" if es else "Your daily brief",
        SUB=("Coinciden con tu alerta. En los refugios se adopta por orden de llegada — visítalos pronto." if es else "They match your alert. Shelter adoptions are first-come, first-served — visit soon."),
        SEE=(("Ver todos los perros" if es else "See all dogs")+(f" (+{more})" if more else "")),
        F1="AdoptMiamiDogs es gratis, siempre." if es else "AdoptMiamiDogs is free, always.",
        F2="Recibes este correo diario porque confirmaste tus alertas." if es else "You get this daily email because you confirmed alerts.",
        UNSUB=_e(UNSUB),UN="Darse de baja" if es else "Unsubscribe",ADDR=(f" &middot; {_e(ADDR)}" if ADDR else ""))
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
    TEST=os.environ.get("TEST_SEND")=="1"; subs=list(map(sub_of,contacts()))
    print(f"{len(subs)} confirmed subscriber(s) on list")
    if TEST:
        if len(subs)!=1: print("TEST aborted: test send needs exactly 1 contact on the list"); return 0
        new=sorted(data["dogs"],key=lambda d:d["first_seen"],reverse=True)[:40]
    for s in subs:
        if used+sent>=DAILY_CAP: print("daily cap reached"); break
        h=H(s["email"])
        if not TEST and c.execute("select 1 from alerts_sent where h=? and at>=?",(h,(datetime.datetime.utcnow()-datetime.timedelta(hours=20)).isoformat())).fetchone(): continue  # max 1 email/day
        m=[d for d in new if matcher.matches(s,d) and (TEST or not c.execute("select 1 from alerts_sent where h=? and dog_id=?",(h,d["id"])).fetchone())]; more=max(0,len(m)-12); m=m[:12]
        if not m: continue
        if TEST: subj0="[Test] "
        else: subj0=""
        subj=(f"AdoptMiamiDogs: {len(m)} perro(s) nuevo(s) para ti" if s["lang"]=="es" else f"AdoptMiamiDogs: {len(m)} new dog(s) for you")
        r=requests.post(f"{API}/smtp/email",headers={"api-key":KEY},timeout=30,json={"sender":{"name":"AdoptMiamiDogs","email":SENDER},"to":[{"email":s["email"]}],
            "subject":subj0+subj,"htmlContent":body(s,m,more),"headers":{"List-Unsubscribe":f"<{UNSUB}>"},"tags":["dog-alert"]})
        if r.status_code>=300: print("send failed",r.status_code,r.text[:200]); continue
        if TEST: sent+=1; print("test sent"); continue
        c.executemany("insert or ignore into alerts_sent values(?,?,?)",[(h,d["id"],now) for d in m]); c.commit(); sent+=1
    print(f"sent {sent} alert emails ({len(new)} recent dogs)"); return sent
if __name__=="__main__": main()
