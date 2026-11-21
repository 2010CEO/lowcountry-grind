# Lowcountry Grind: automated Amazon affiliate site

Home coffee gear buying guides (grinders, pour-over, drip, espresso, cold brew, camp coffee, gifts).
Static HTML, Python standard library only, no database, free hosting.

```
config.json           site name, URL, AFFILIATE TAG (one value), owner blurb, AI note
data/products.json    28 products (real ASINs, checked against amazon.com 2026-11-20)
data/guides/*.json    7 published guides
data/drafts/*.json    auto-generated guide drafts (not published)
templates/  static/   HTML templates + CSS
lcg.py                the engine
site/                 build output (what you deploy)
.github/workflows/weekly.yml   weekly link check + rebuild + deploy (GitHub Pages)
```

## Commands
| Command | What it does |
|---|---|
| `python3 lcg.py build` | Regenerates `site/` from data + templates. Hides any product marked `dead`. |
| `python3 lcg.py check-links` | Fetches every `amazon.com/dp/<ASIN>`. Only an HTTP 404 marks a product `dead`; captchas/5xx are logged as `unknown` and never remove anything. Writes `data/link-report.json`; exits 1 if anything died. |
| `python3 lcg.py new-guide keywords.txt` | One draft per keyword in `data/drafts/`, auto-matching products from the catalog. Fill the TODOs, then `python3 lcg.py publish <slug>`. |
| `python3 lcg.py enrich` | Creators API hook for live prices/images later (see below). |

Adding a product: copy its ASIN from the Amazon URL (`/dp/B0XXXXXXXX`), add an entry to `data/products.json`, run `check-links`, add it to a guide's `picks`.

## 1. Set your tag (one place)
After Amazon gives you a tracking ID (looks like `yourname-20`), either:
- edit `config.json` -> `"affiliate_tag": "yourname-20"`, or
- on GitHub: Settings > Secrets and variables > Actions > Variables > `AFF_TAG = yourname-20`.

Also set `base_url` (your real URL) and `contact_email` in `config.json`.

## 2. Host it free (pick one)
**GitHub Pages (recommended: the weekly automation is already wired up)**
1. Create a GitHub repo (public is free for Pages), e.g. `lowcountry-grind`, and push this folder to `main`.
2. Repo > Settings > Pages > Build and deployment > Source: **GitHub Actions**.
3. Settings > Actions > General > Workflow permissions: **Read and write**.
4. Add the `AFF_TAG` variable (above). Push, or run the workflow from the Actions tab.
5. Site goes live at `https://<user>.github.io/lowcountry-grind/`. Custom domain (optional, about $10-12/yr): Settings > Pages > Custom domain, then add a CNAME DNS record.

**Cloudflare Pages:** dash.cloudflare.com > Workers & Pages > Create > Pages > Connect to Git > pick the repo.
Build command `python3 lcg.py build`, output directory `site`, env var `AFF_TAG`. (The weekly link check still runs in GitHub Actions; you can delete the deploy job.)

**Netlify:** app.netlify.com > Add new site > Import from Git. Build `python3 lcg.py build`, publish dir `site`, env var `AFF_TAG`. Or drag-and-drop the `site/` folder at app.netlify.com/drop for a 30-second test.

## 3. Amazon Associates signup (verified 2026-11-20)
1. Go live first: Amazon reviews your site, so it should be public with these guides on it.
2. affiliate-program.amazon.com > Sign up. Use your Amazon account, enter the site URL (and any social profiles you'll post from), describe the site as coffee gear buying guides, and give your traffic methods honestly.
3. Enter tax info (W-9) and payment info (direct deposit) under Account Settings.
4. Copy your tracking ID into `AFF_TAG`, rebuild, deploy.

**Rules that matter:**
- **3 qualifying sales within 180 days** of applying, or the application is withdrawn and the ID can't be reinstated. Amazon then reviews the site, usually within a day or two.
- **Payout:** about **60 days after the end of the month** a sale happened. $10 minimum for direct deposit or gift card. A December sale pays around the end of February.
- **Commission (Kitchen category, where most of this gear sits): 4.5%.** Sports & Outdoors items (the Stanley percolator) and Home are 3%. Grocery is 1%: the Hario Mizudashi is listed under Grocery. Prime trial sign-ups through your links pay a $12 bounty.
- Your own purchases don't count. Don't offer rewards for clicks.
- **No Amazon links in email, text messages, printed flyers, or PDFs/ebooks.** Offline and email promotion has to point to *your site*, not to Amazon.
- Every page needs the disclosure "As an Amazon Associate I earn from qualifying purchases" (built in: top bar, footer, every guide, disclosure page).
- **Don't hardcode prices or star ratings** (Amazon only allows prices pulled from its API and refreshed every 24h). This site shows none by design.

## 4. Live prices and images later (Creators API)
PA-API 5 is **deprecated**: calls now return 403. The replacement is the **Creators API**, which needs final Associates acceptance **plus at least 10 qualifying sales in the past 30 days**. Until then the site works without it: no images, no prices, just "Check current price on Amazon." Once you qualify, register in Associates Central > Tools > Creators API, put the credentials in `CREATORS_CLIENT_ID` / `CREATORS_CLIENT_SECRET`, and implement `enrich()` in `lcg.py` (GetItems -> title, image, price, run daily).
Docs: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction

## Honesty guardrails baked in
No invented prices, ratings, review counts or "we tested 50 grinders" claims. Product specs are taken from the Amazon listing titles and features. The AI-assist note is in the footer and on the About and Disclosure pages. **Before launch, TJ should read each guide, add real notes from Mad Hooter where they're true, and cut anything that doesn't match his experience.**
