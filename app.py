import datetime, re
from flask import Flask, request, render_template_string, redirect
import scraper
app=Flask(__name__)
L={"en":dict(title="AdoptMiamiDogs",tag="Free new-dog alerts for Miami-Dade & Broward county shelters, — always 100% free.",size="Size",age="Age",sex="Sex",breed="Breed",shelter="Shelter",any="Any",filter="Filter",
  sub="Get free alerts when a matching dog arrives",email="Email",signup="Sign up — free",thanks="Almost done! Check your email to confirm. (MVP: confirmation email is previewed at /admin/outbox, not sent.)",confirmed="Confirmed! You will get free alerts for matching dogs.",unsub="You are unsubscribed. No more emails.",weight="lbs",new="NEW",intake="Arrived",view="View at shelter",
  small="Small",medium="Medium",large="Large",puppy="Puppy (<1y)",adult="Adult (1-7y)",senior="Senior (7y+)",male="Male",female="Female",showing="Showing",dogs="dogs",sponsor="Sponsor slot — local pet businesses",bad="Please enter a valid email."),
 "es":dict(title="AdoptMiamiDogs",tag="Alertas gratis de perros nuevos en los refugios de Miami-Dade y Broward — siempre 100% gratis.",size="Tamaño",age="Edad",sex="Sexo",breed="Raza",shelter="Refugio",any="Cualquiera",filter="Filtrar",
  sub="Recibe alertas gratis cuando llegue un perro para ti",email="Correo",signup="Suscribirse — gratis",thanks="¡Casi listo! Revisa tu correo para confirmar. (MVP: el correo se previsualiza en /admin/outbox, no se envía.)",confirmed="¡Confirmado! Recibirás alertas gratis.",unsub="Te has dado de baja. No recibirás más correos.",weight="lb",new="NUEVO",intake="Llegó",view="Ver en el refugio",
  small="Pequeño",medium="Mediano",large="Grande",puppy="Cachorro (<1a)",adult="Adulto (1-7a)",senior="Mayor (7a+)",male="Macho",female="Hembra",showing="Mostrando",dogs="perros",sponsor="Espacio para patrocinador — negocios locales",bad="Correo inválido.")}
SH=list(scraper.SHELTERS.values())
TPL="""<!doctype html><html lang="{{lang}}"><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>{{t.title}}</title>
<style>body{font-family:system-ui;margin:0;background:#f6f7fb}header{background:#0a7d8c;color:#fff;padding:16px}a{color:#0a7d8c}header a{color:#fff}
form{background:#fff;padding:12px;margin:12px;border-radius:8px;display:flex;flex-wrap:wrap;gap:8px;align-items:end}label{font-size:12px;display:flex;flex-direction:column}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin:12px}.c{background:#fff;border-radius:8px;overflow:hidden;font-size:14px}
.c img{width:100%;height:180px;object-fit:cover;background:#ddd}.c div{padding:8px}.n{background:#e8483f;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px}
.sp{margin:12px;padding:10px;border:1px dashed #aaa;color:#888;text-align:center;font-size:12px}.msg{margin:12px;padding:10px;background:#dff5e3}</style>
<header><b>{{t.title}}</b> · {{t.tag}} <span style=float:right><a href="?{{qs}}&lang=en">EN</a> | <a href="?{{qs}}&lang=es">ES</a></span></header>
{% if msg %}<div class=msg>{{msg}}</div>{% endif %}
{% macro sel(name,opts) %}<select name={{name}}><option value="">{{t.any}}</option>{% for v,l in opts %}<option value="{{v}}" {{'selected' if f[name]==v}}>{{l}}</option>{% endfor %}</select>{% endmacro %}
{% set O=dict(size=[('small',t.small),('medium',t.medium),('large',t.large)],age_group=[('puppy',t.puppy),('adult',t.adult),('senior',t.senior)],sex=[('Male',t.male),('Female',t.female)],shelter=sh) %}
<form><input type=hidden name=lang value={{lang}}>{% for k,lab in [('size',t.size),('age_group',t.age),('sex',t.sex),('shelter',t.shelter)] %}<label>{{lab}}{{sel(k,O[k])}}</label>{% endfor %}
<label>{{t.breed}}<input name=breed value="{{f.breed}}"></label><button>{{t.filter}}</button></form>
<form method=post action="/subscribe"><b style=width:100%>🔔 {{t.sub}}</b><input type=hidden name=lang value={{lang}}>{% for k,lab in [('size',t.size),('age_group',t.age),('sex',t.sex),('shelter',t.shelter)] %}<label>{{lab}}{{sel(k,O[k])}}</label>{% endfor %}
<label>{{t.breed}}<input name=breed value="{{f.breed}}"></label><label>{{t.email}}<input name=email type=email required></label><button>{{t.signup}}</button></form>
<div class=sp>{{t.sponsor}}</div><p style=margin:12px>{{t.showing}} {{dogs|length}} {{t.dogs}}</p>
<div class=grid>{% for d in dogs %}<div class=c><img loading=lazy src="{{d.photo}}" alt="{{d.name}}"><div>{% if d.first_seen>=recent %}<span class=n>{{t.new}}</span> {% endif %}<b>{{d.name}}</b><br>{{d.breed}}<br>{{d.sex}} · {{d.age}} · {{t[d.size]}}{% if d.weight_lbs %} ({{d.weight_lbs|int}} {{t.weight}}){% endif %}<br>
<small>{{d.shelter}} · {{t.intake}} {{d.intake_date}}</small><br><a href="{{d.link}}" target=_blank>{{t.view}} ({{d.id.split(':')[1]}})</a></div></div>{% endfor %}</div><footer style='margin:12px;font-size:12px;color:#666'>AdoptMiamiDogs is free and independent; not affiliated with Miami-Dade or Broward County. Data from public shelter listings — confirm with the shelter.</footer></html>"""
def page(msg=None):
    lang=request.values.get("lang","en"); lang=lang if lang in L else "en"; t=L[lang]
    f={k:request.values.get(k,"") for k in ["size","age_group","sex","shelter","breed"]}
    q="select * from dogs where active=1 and adoptable=1"; a=[]
    for k in ["size","age_group","sex","shelter"]:
        if f[k]: q+=f" and {k}=?"; a.append(f[k])
    if f["breed"]: q+=" and breed like ?"; a.append(f"%{f['breed']}%")
    dogs=scraper.db().execute(q+" order by intake_date desc",a).fetchall()
    recent=(datetime.datetime.now()-datetime.timedelta(days=2)).isoformat()
    qs="&".join(f"{k}={v}" for k,v in f.items() if v)
    return render_template_string(TPL,t=t,lang=lang,f=f,dogs=dogs,sh=[(s,s) for s in SH],msg=msg,recent=recent,qs=qs)
@app.get("/")
def index(): return page()
@app.post("/subscribe")
def subscribe():
    e=request.form.get("email","").strip(); t=L.get(request.form.get("lang"),L["en"])
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",e): return page(t["bad"])
    import secrets, matcher; tok=secrets.token_urlsafe(16); lang=request.form.get("lang","en")
    c=scraper.db(); cur=c.execute("insert into subscribers(email,lang,size,age_group,breed,sex,shelter,created,confirmed,token) values(?,?,?,?,?,?,?,?,0,?)",
      (e,lang,*[request.form.get(k,"") for k in ["size","age_group","breed","sex","shelter"]],datetime.datetime.now().isoformat(),tok)); c.commit()
    matcher.queue_confirmation(cur.lastrowid)
    return page(t["thanks"])
@app.get("/confirm/<tok>")
def confirm(tok):
    c=scraper.db(); r=c.execute("update subscribers set confirmed=1 where token=?",(tok,)); c.commit()
    return page(L.get(request.args.get("lang"),L["en"])["confirmed"] if r.rowcount else "Invalid link")
@app.get("/unsubscribe/<tok>")
def unsubscribe(tok):
    c=scraper.db(); s=c.execute("select id from subscribers where token=?",(tok,)).fetchone()
    if s: c.execute("delete from outbox where subscriber_id=? and status='preview'",(s[0],)); c.execute("delete from subscribers where id=?",(s[0],)); c.commit()
    return page(L.get(request.args.get("lang"),L["en"])["unsub"])
@app.get("/admin/outbox")
def outbox():
    rows=scraper.db().execute("select o.*,s.email from outbox o join subscribers s on s.id=o.subscriber_id order by o.id desc limit 200").fetchall()
    return "<h3>AdoptMiamiDogs — email previews (NOT sent)</h3>"+"".join(f"<pre>To: {r['email']}\n{r['subject']}\n{r['body']}</pre><hr>" for r in rows)
if __name__=="__main__": app.run(port=8080)
