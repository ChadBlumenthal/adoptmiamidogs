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
