# AdoptMiamiDogs (free, $0 hosting)
Free bilingual (EN/ES) site listing adoptable dogs at Miami-Dade Animal Services and Broward County Animal Care, with free new-dog alerts. No paywalls, ever.

## How it works ($0)
- `docs/` = static site served by **GitHub Pages** (index.html + dogs.json). Free URL: https://<username>.github.io/<repo>/
- `.github/workflows/update.yml` = hourly **GitHub Actions** cron: `scraper.py` (24PetConnect list pages + per-dog detail pages, 1 request/2s) -> `data.db` (SQLite, committed) -> `export.py` -> `docs/dogs.json`, commits changes.
- `digest.py` = alert digests, **PREVIEW ONLY** (uploaded as an Actions artifact; never sent).

## Alerts signup (free proposal)
1. Google Form (free) with fields email, language, size, age, sex, breed, shelter + a consent checkbox; linked Google Sheet.
2. Double opt-in: Apps Script (free) on the Sheet emails a confirm link; `confirmed` column set to yes on click. (Not built; would send from Chad's Gmail, ~100/day quota.)
3. Publish the Sheet as CSV -> store URL as repo secret `SUBSCRIBERS_CSV_URL`. Note: a published CSV URL is unlisted but not truly private.
4. Real sending later: Brevo free tier (~300 emails/day) or Gmail SMTP from Actions — needs Chad's approval + CAN-SPAM postal address (`POSTAL_ADDRESS` env).
Put the form link in `SIGNUP_URL` in docs/index.html.

## Local dev
python3 -m venv .venv && .venv/bin/pip install flask beautifulsoup4 requests
.venv/bin/python -c "import scraper; scraper.run()" && .venv/bin/python export.py
cd docs && python3 -m http.server 8000     # static site
.venv/bin/python app.py                    # optional Flask version w/ double opt-in demo, /admin/outbox

## Publish (needs Chad's GitHub account)
git remote add origin https://github.com/<user>/adoptmiamidogs.git && git push -u origin main
Settings -> Pages -> Deploy from branch `main`, folder `/docs`. Settings -> Actions -> Workflow permissions: Read and write.

## More sources (Oct 2026)
Live sources: Miami-Dade Animal Services, Broward County Animal Care, Palm Beach County Animal Care & Control (all public 24PetConnect listings),
Humane Society of Greater Miami (its own server-rendered adopt page; robots.txt allows). Polite 1 req / 2 s.

## Private-owner rehoming (moderated; nothing auto-publishes)
1. Create a free Google Form "List a dog for rehoming" (fields: owner name, email, phone (optional), dog name, breed, age, sex, weight lbs, spayed/neutered, vaccinated,
   photo upload, description, city/ZIP, why rehoming, checkbox "I own this dog and agree it may be shown publicly; no sale fee beyond a reasonable rehoming fee").
   Responses stay private in Chad's Google account.
2. Chad reviews each response. To publish, add an entry to `rehome/approved.json` with `"approved": true`
   (`id, name, breed, age, age_group, sex, size, weight_lbs, photo, contact_url, approved_on`). Only those entries appear on the site.
3. Remove the entry to unpublish.

## Email alerts (Brevo free plan: 300 emails/day, no card) — DISABLED until secrets exist
1. Create a free Brevo account; verify a single sender email (Senders, Domains & IPs > Senders).
2. Contacts > Settings: create attributes LANG, SIZE, AGE_GROUP, SEX, SHELTER (md/bw/pb/hs), BREED. Create a list "Dog alerts" (note its ID).
3. Forms: create a subscription form with double opt-in turned on, those attributes as fields, linked to the list. Copy its hosted share link into `SIGNUP_URL` in docs/index.html.
   Also create an unsubscribe form/link (or use Brevo's) for BREVO_UNSUB_URL.
4. SMTP & API > API keys: create a key. In GitHub repo Settings > Secrets > Actions add: BREVO_API_KEY, BREVO_LIST_ID, SENDER_EMAIL, POSTAL_ADDRESS (PO box OK), BREVO_UNSUB_URL.
A separate daily workflow sends one 8 AM (New York) brief per subscriber with up to 12 dogs from the last 24h, only when there are matches; capped at 280/day.
