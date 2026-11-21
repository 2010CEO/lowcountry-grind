#!/usr/bin/env python3
"""Lowcountry Grind site engine. Python 3.9+, standard library only.

  python3 lcg.py build                 # regenerate ./site from data/ + templates/
  python3 lcg.py check-links           # check every Amazon ASIN, flag dead ones, write data/link-report.json
  python3 lcg.py new-guide KEYWORDS    # draft guides from a keyword list (file, one per line, or a quoted keyword)
  python3 lcg.py publish SLUG          # move a reviewed draft from data/drafts/ into data/guides/
  python3 lcg.py enrich                # Creators API hook (unlocks after Amazon approves API access)

Affiliate tag lives in ONE place: config.json -> "affiliate_tag" (or env AFF_TAG overrides it).
"""
import json, os, re, sys, html, shutil, time, random, datetime, urllib.request, urllib.error, gzip
from string import Template
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA, TPL, OUT, STATIC = ROOT/"data", ROOT/"templates", ROOT/"site", ROOT/"static"
E = html.escape

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p, obj): Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
def cfg():
    c = load(ROOT/"config.json")
    c["affiliate_tag"] = os.environ.get("AFF_TAG") or c["affiliate_tag"]  # empty Actions var must not wipe the tag
    return c
def tpl(name): return Template((TPL/name).read_text(encoding="utf-8"))

def amazon_link(asin, c):
    return f"https://{c['amazon_domain']}/dp/{asin}?tag={c['affiliate_tag']}"

GLYPHS = {  # tiny inline SVGs, cream/crema on dark
 "grinder": '<svg viewBox="0 0 40 40"><path d="M12 6h16l-3 9H15z" fill="#f2a65a"/><rect x="11" y="15" width="18" height="19" rx="3" fill="none" stroke="#f4e9d8" stroke-width="2.4"/><path d="M20 4v-2M20 2h8" stroke="#f4e9d8" stroke-width="2.4" stroke-linecap="round"/><circle cx="20" cy="25" r="4" fill="#f2a65a"/></svg>',
 "pourover": '<svg viewBox="0 0 40 40"><path d="M8 8h24l-9 13h-6z" fill="#f2a65a"/><rect x="12" y="22" width="16" height="13" rx="3" fill="none" stroke="#f4e9d8" stroke-width="2.4"/><path d="M20 21v3" stroke="#f4e9d8" stroke-width="2.4" stroke-dasharray="1.5 2"/></svg>',
 "drip": '<svg viewBox="0 0 40 40"><rect x="9" y="5" width="22" height="8" rx="2" fill="#f2a65a"/><path d="M11 13v22h18" fill="none" stroke="#f4e9d8" stroke-width="2.4"/><path d="M15 22h12l-1 11H16z" fill="none" stroke="#f4e9d8" stroke-width="2.4"/></svg>',
 "espresso": '<svg viewBox="0 0 40 40"><path d="M7 12h20l-3 5H10z" fill="#f2a65a"/><path d="M27 14h6" stroke="#f4e9d8" stroke-width="2.4" stroke-linecap="round"/><path d="M12 24h14v5a5 5 0 0 1-5 5h-4a5 5 0 0 1-5-5z" fill="none" stroke="#f4e9d8" stroke-width="2.4"/><path d="M26 26h3a2 2 0 0 1 0 4h-3" fill="none" stroke="#f4e9d8" stroke-width="2"/></svg>',
 "coldbrew": '<svg viewBox="0 0 40 40"><rect x="11" y="8" width="18" height="27" rx="4" fill="none" stroke="#f4e9d8" stroke-width="2.4"/><rect x="15" y="18" width="5" height="5" fill="#f2a65a" transform="rotate(12 17 20)"/><rect x="21" y="24" width="5" height="5" fill="#f2a65a" transform="rotate(-10 23 26)"/><path d="M11 13h18" stroke="#f4e9d8" stroke-width="2"/></svg>',
 "camp": '<svg viewBox="0 0 40 40"><path d="M4 34L20 8l16 26z" fill="none" stroke="#f4e9d8" stroke-width="2.4" stroke-linejoin="round"/><path d="M20 34l-5-9h10z" fill="#f2a65a"/></svg>',
 "gift": '<svg viewBox="0 0 40 40"><rect x="7" y="16" width="26" height="18" rx="2" fill="none" stroke="#f4e9d8" stroke-width="2.4"/><rect x="5" y="11" width="30" height="6" rx="1.5" fill="#f2a65a"/><path d="M20 11v23M20 11c-4-7-11-4-7 0M20 11c4-7 11-4 7 0" fill="none" stroke="#f4e9d8" stroke-width="2.2"/></svg>',
}
KIND_GLYPH = {"grinder":"grinder","pour-over":"pourover","kettle":"pourover","scale":"pourover","drip":"drip","espresso":"espresso","moka":"espresso","cold-brew":"coldbrew","press":"camp","percolator":"camp","storage":"gift"}
PHOTO = {"grinder":("grinder","A hand coffee grinder beside a sack of roasted beans"),"gift":("gift","Latte art in a cup held in two hands"),
 "pourover":("pourover","Water poured from a gooseneck kettle into a pour-over brewer"),"espresso":("espresso","Espresso pulling into a white cup"),
 "drip":("drip","A mug of coffee with cream on a wooden table"),"coldbrew":("coldbrew","Iced coffee in a glass"),
 "camp":("camp","A mug of coffee on a grill over a campfire")}
NAV = [("grinder","Grinders"),("espresso","Espresso"),("pourover","Pour-over"),("drip","Drip"),("gift","Gifts")]
FAVICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><circle cx="20" cy="20" r="19" fill="#1d1712"/><path d="M20 8c-6.5 4.5-6.5 19.5 0 24M20 8c6.5 4.5 6.5 19.5 0 24" fill="none" stroke="#e9a15b" stroke-width="2.6"/><ellipse cx="20" cy="20" rx="9" ry="12.5" fill="none" stroke="#e9a15b" stroke-width="2.6"/></svg>'
LOGO = '<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="19" fill="#1d1712"/><ellipse cx="20" cy="20" rx="9" ry="12.5" fill="#b4532a"/><path d="M20 8c-5 4.5-1 9.5 0 12s-5 7.5 0 12" fill="none" stroke="#1d1712" stroke-width="2.4" stroke-linecap="round"/></svg>'

def page(c, title, desc, body, root, canonical_path, jsonld, guides, photo="hero-alt"):
    byg = {g["glyph"]: g for g in guides}
    nav = "".join(f'<a href="{root}{byg[k]["slug"]}.html">{lbl}</a>' for k, lbl in NAV if k in byg)
    foot_links = "".join(f'<a href="{root}{g["slug"]}.html">{E(short(g["title"]))}</a>' for g in guides)
    base = c["base_url"].rstrip("/")
    return tpl("base.html").substitute(page_title=E(title), meta_desc=E(desc), canonical=E(base+"/"+canonical_path),
        og_image=E(f"{base}/img/{photo}.webp"), foot_links=foot_links,
        root=root, jsonld=json.dumps(jsonld), logo_svg=LOGO, site_name=E(c["site_name"]), nav=nav, body=body,
        tagline=E(c["tagline"]), year=c["year"], ai_note=E(c["ai_note"]), contact_html=(f' &middot; <a href="mailto:{E(c["contact_email"])}">Contact</a>' if c.get("contact_email") else ""))

def short(t):
    t = re.sub(r"^(The )?Best ", "", t); t = re.sub(r"Coffee Gift Guide:.*", "Gifts", t)
    t = t.replace(" for Beginners","").replace(" for Home","").replace(" for Families","").replace(" for Hot Southern Summers","")
    return t.replace("The ","").replace(", Boat & Deer Stand Coffee Makers"," Coffee")

def live_products():
    prods = {p["asin"]: p for p in load(DATA/"products.json")}
    return prods

def guides_list(include_drafts=False):
    gs = [load(p) for p in sorted((DATA/"guides").glob("*.json"))]
    order = cfg().get("guide_order", [])
    gs.sort(key=lambda g: order.index(g["slug"]) if g["slug"] in order else 99)
    return [g for g in gs if include_drafts or not g.get("draft")]

def nice_date(iso):
    try: d = datetime.date.fromisoformat(iso); return d.strftime("%B ") + str(d.day) + d.strftime(", %Y")
    except Exception: return iso

def card(g):
    ph, alt = PHOTO.get(g["glyph"], PHOTO["gift"])
    tag = {"grinder":"Grinders","gift":"Gift guide","pourover":"Pour-over","espresso":"Espresso","drip":"Drip coffee","coldbrew":"Cold brew","camp":"Outdoors"}.get(g["glyph"],"Guide")
    return (f'<a class="gcard" href="{g["slug"]}.html"><div class="ph"><img src="img/{ph}-sm.webp" alt="{E(alt)}" loading="lazy" width="640" height="427"></div>'
            f'<div class="gc-body"><span class="tag">{tag}</span><h3>{E(g["title"])}</h3><p>{E(g["dek"])}</p><span class="go">Read the guide &rarr;</span></div></a>')

def li(items): return "".join(f"<li>{E(x)}</li>" for x in items)

def build():
    c = cfg(); prods = live_products(); guides = guides_list()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(); shutil.copy(STATIC/"style.css", OUT/"style.css"); shutil.copytree(STATIC/"img", OUT/"img")
    (OUT/"favicon.svg").write_text(FAVICON)
    dom = re.sub(r"^https?://", "", c["base_url"]).rstrip("/")
    if "/" not in dom and not dom.endswith("github.io"): (OUT/"CNAME").write_text(dom+"\n")  # GitHub Pages custom domain
    dropped = []
    for g in guides:
        picks_html, rows, n, quick, toc = [], [], 0, [], []
        for pk in g["picks"]:
            p = prods.get(pk["asin"])
            if not p or p.get("status") == "dead":
                dropped.append((g["slug"], pk["asin"])); continue
            n += 1
            specs = "".join(f"<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>" for k, v in p["specs"].items())
            quick.append(f'<li><span><span class="qa">{E(pk["award"])}</span><a class="qn" href="#{p["asin"]}">{E(p["name"])}</a></span><a class="qb" href="{E(amazon_link(p["asin"], c))}" rel="sponsored nofollow noopener" target="_blank">Check price &#8599;</a></li>')
            toc.append(f'<a href="#{p["asin"]}">{E(p["name"])}</a>')
            picks_html.append(tpl("pick.html").substitute(asin=p["asin"], num=f"{n:02d}", glyph=GLYPHS[KIND_GLYPH.get(p["kind"],"gift")],
                award=E(pk["award"]), name=E(p["name"]), brand=E(p["brand"]), verdict=E(pk["verdict"]), specs=specs,
                pros=li(p["pros"]), cons=li(p["cons"]), link=E(amazon_link(p["asin"], c)), best_for=E(p["best_for"])))
            cells = "".join(f"<td>{E(p['specs'].get(col,'—'))}</td>" for col in g["table_columns"])
            rows.append(f'<tr><td><a href="#{p["asin"]}">{E(p["name"])}</a></td><td>{E(pk["award"])}</td>{cells}<td><a href="{E(amazon_link(p["asin"], c))}" rel="sponsored nofollow noopener" target="_blank">Check price</a></td></tr>')
        thead = "<th>Product</th><th>Best for</th>" + "".join(f"<th>{E(x)}</th>" for x in g["table_columns"]) + "<th>Amazon</th>"
        faq = "".join(f"<details><summary>{E(f['q'])}</summary><p>{E(f['a'])}</p></details>" for f in g["faq"])
        ph, alt = PHOTO.get(g["glyph"], PHOTO["gift"])
        others = [o for o in guides if o["slug"] != g["slug"]][:3]
        related = '<section class="related"><div class="wrap"><h2>Keep reading</h2><div class="cards">' + "".join(card(o) for o in others) + '</div></div></section>'
        body = tpl("guide.html").substitute(title=E(g["title"]), dek=E(g["dek"]), updated=nice_date(g["updated"]), n_picks=n,
            photo=ph, photo_alt=E(alt), quick="".join(quick), toc="".join(toc), related=related,
            intro="".join(f"<p>{E(x)}</p>" for x in g["intro"]), picks="".join(picks_html), thead=thead, tbody="".join(rows),
            bar_tip=E(g["bar_tip"]), how=E(g["how_we_picked"]), faq=faq)
        jsonld = {"@context":"https://schema.org","@type":"ItemList","name":g["title"],"itemListElement":[
            {"@type":"ListItem","position":i+1,"name":prods[pk["asin"]]["name"]} for i,pk in enumerate(x for x in g["picks"] if x["asin"] in prods and prods[x["asin"]].get("status")!="dead")]}
        (OUT/f'{g["slug"]}.html').write_text(page(c, f'{g["title"]} ({c["year"]}) | {c["site_name"]}', g["dek"], body, "", f'{g["slug"]}.html', jsonld, guides, ph), encoding="utf-8")
    # home

    bykey = lambda k: next((g["slug"] for g in guides if g["glyph"] == k), guides[0]["slug"])
    latest = max(g["updated"] for g in guides)
    home = tpl("home.html").substitute(tagline=E(c["tagline"]), featured_cards="".join(card(g) for g in guides[:3]), more_cards="".join(card(g) for g in guides[3:]),
        n_guides=len(guides), updated=nice_date(latest), slug_espresso=bykey("espresso"), slug_cold=bykey("coldbrew"),
        slug_camp=bykey("camp"), slug_gift=bykey("gift"), slug_grinder=bykey("grinder"), slug_drip=bykey("drip"), slug_pour=bykey("pourover"),
        guide_names=json.dumps({g["slug"]: g["title"] for g in guides}))
    (OUT/"index.html").write_text(page(c, f'{c["site_name"]}: {c["tagline"]}', c["tagline"], home, "", "", {"@context":"https://schema.org","@type":"WebSite","name":c["site_name"],"url":c["base_url"]}, guides), encoding="utf-8")
    # static pages
    disc = f'''<section class="page-head"><div class="wrap"><div class="eyebrow">The fine print</div><h1>How we make money</h1></div></section><main class="wrap page-body"><div class="prose">
<p><b>As an Amazon Associate I earn from qualifying purchases.</b> {E(c["site_name"])} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com.</p>
<p><b>FTC disclosure:</b> Many links on this site are affiliate links. If you click one and buy something, we may earn a commission at no extra cost to you. Commissions never decide what we recommend, and we do not accept payment from brands for placement.</p>
<p><b>Prices and ratings:</b> we don't publish prices, star ratings, or review counts because they change constantly. Always check the current price and details on Amazon before you buy.</p>
<p><b>AI assistance:</b> {E(c["ai_note"])}</p></div></main>'''
    (OUT/"disclosure.html").write_text(page(c, f'Disclosure | {c["site_name"]}', "How this site makes money.", disc, "", "disclosure.html", {}, guides), encoding="utf-8")
    try: cr = load(DATA/"photo-credits.json")
    except Exception: cr = {}
    credits = ", ".join(f'<a href="{E(v["page"])}" rel="nofollow noopener" target="_blank">{E(v.get("creator") or v["source"])}</a> ({E(v["source"])})' for v in cr.values() if v.get("page"))
    about = (f'<section class="page-head"><div class="wrap"><div class="eyebrow">About</div><h1>About {E(c["site_name"])}</h1></div></section><main class="wrap page-body">'
        f'<img class="about-img" src="img/beans.webp" alt="Roasted coffee beans"><div class="prose"><p>{E(c["owner_blurb"])}</p><h2>How these guides are made</h2><p>{E(c["ai_note"])}</p>'
        + (f'<p>Questions or a product you want us to look at? <a href="mailto:{E(c["contact_email"])}">{E(c["contact_email"])}</a></p>' if c.get("contact_email") else "")
        + (f'<h2>Photo credits</h2><p class="credits">Photos are public-domain (CC0) images from {credits}. They show coffee in general, not the specific products we recommend.</p>' if credits else "") + '</div></main>')
    (OUT/"about.html").write_text(page(c, f'About | {c["site_name"]}', c["tagline"], about, "", "about.html", {}, guides), encoding="utf-8")
    # sitemap + robots
    today = datetime.date.today().isoformat(); base = c["base_url"].rstrip("/")
    urls = [""] + [f'{g["slug"]}.html' for g in guides] + ["about.html","disclosure.html"]
    (OUT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join(f"<url><loc>{base}/{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)+"</urlset>\n")
    (OUT/"robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    if c.get("indexnow_key"):  # IndexNow (Bing/DuckDuckGo/Yandex) ownership file
        (OUT/f'{c["indexnow_key"]}.txt').write_text(c["indexnow_key"])
    print(f"built {len(guides)} guides -> {OUT}  (tag={c['affiliate_tag']})")
    for s, a in dropped: print(f"  hid dead/unknown ASIN {a} in {s}")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
def fetch_status(asin, domain):
    req = urllib.request.Request(f"https://{domain}/dp/{asin}", headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read(); body = gzip.decompress(raw).decode("utf-8","ignore") if r.headers.get("Content-Encoding")=="gzip" else raw.decode("utf-8","ignore")
            m = re.search(r"<title>([^<]*)", body); title = html.unescape(m.group(1)).strip() if m else ""
            if "captcha" in body.lower() or "api-services-support@amazon.com" in body: return r.status, "blocked", title
            return r.status, ("ok" if title and title != "Amazon.com" else "unknown"), title
    except urllib.error.HTTPError as e:
        return e.code, ("dead" if e.code == 404 else "unknown"), ""
    except Exception as e:
        return None, "unknown", str(e)[:80]

def check_links():
    c = cfg(); prods = load(DATA/"products.json"); report = []
    for p in prods:
        code, state, title = fetch_status(p["asin"], c["amazon_domain"])
        if state in ("blocked","unknown"):  # retry once, slower
            time.sleep(8 + random.random()*4); code, state, title = fetch_status(p["asin"], c["amazon_domain"])
        prev = p.get("status")
        # only a hard 404 marks a product dead; captcha/5xx never removes anything
        if state == "ok": p["status"], p["amazon_title"] = "ok", title[:200]
        elif state == "dead": p["status"] = "dead"
        p["last_checked"] = datetime.datetime.now().isoformat(timespec="seconds"); p["last_http"] = code
        report.append({"asin":p["asin"],"name":p["name"],"http":code,"state":state,"was":prev})
        print(f'{p["asin"]} {str(code):>4} {state:<8} {p["name"]}')
        time.sleep(1.5 + random.random()*2)
    save(DATA/"products.json", prods)
    dead = [r for r in report if r["state"]=="dead"]
    save(DATA/"link-report.json", {"checked_at":datetime.datetime.now().isoformat(timespec="seconds"),"total":len(report),
        "ok":sum(r["state"]=="ok" for r in report),"dead":dead,"unknown":[r for r in report if r["state"] in ("unknown","blocked")]})
    print(f"\n{len(report)} checked, {len(dead)} dead" + (": " + ", ".join(d["asin"] for d in dead) if dead else ""))
    if dead and os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text("## Dead ASINs\n" + "\n".join(f"- {d['asin']} {d['name']}" for d in dead))
    return 1 if dead else 0

KIND_WORDS = {"grinder":["grind","grinder","burr"],"espresso":["espresso","latte","cappuccino"],"cold-brew":["cold brew","iced"],
  "drip":["drip","coffee maker","coffee machine","pot"],"pour-over":["pour over","pour-over","v60","chemex"],"kettle":["kettle","gooseneck"],
  "scale":["scale"],"press":["aeropress","travel","camp","camping","hiking","boat"],"percolator":["percolator","camp","camping","hunting"],
  "moka":["moka","stovetop","cuban"],"storage":["canister","storage","fresh","beans"]}
def new_guide(arg):
    kws = [l.strip() for l in Path(arg).read_text().splitlines() if l.strip() and not l.startswith("#")] if Path(arg).exists() else [arg]
    prods = [p for p in load(DATA/"products.json") if p.get("status") != "dead"]
    for kw in kws:
        k = kw.lower(); slug = re.sub(r"[^a-z0-9]+","-",k).strip("-")
        if (DATA/"guides"/f"{slug}.json").exists() or (DATA/"drafts"/f"{slug}.json").exists(): print(f"skip {slug} (exists)"); continue
        scored = []
        for p in prods:
            s = sum(3 for w in KIND_WORDS.get(p["kind"],[]) if w in k) + sum(1 for w in re.findall(r"[a-z]+", k) if len(w)>3 and w in (p["best_for"]+" "+p["name"]).lower())
            if s: scored.append((s,p))
        scored.sort(key=lambda x:-x[0]); picks = [p for _,p in scored[:6]]
        cols = []
        for p in picks:
            for key in p["specs"]:
                if key not in cols: cols.append(key)
        title = kw.strip().title() if k.startswith("best") else "The Best " + kw.strip().title()
        draft = {"slug":slug,"title":title,"dek":"TODO: one sentence promise for this reader.","keyword":kw,"glyph":KIND_GLYPH.get(picks[0]["kind"],"gift") if picks else "gift",
          "updated":datetime.date.today().isoformat(),
          "intro":[f"TODO: who searches '{kw}', what problem they have, and what actually matters. Write from behind-the-bar experience; no invented testing claims.","TODO: second paragraph: what to look for."],
          "how_we_picked":"TODO: honest criteria. Say where info comes from (Amazon listings, our own use).",
          "picks":[{"asin":p["asin"],"award":"TODO award","verdict":f"TODO verdict. Auto-matched because: {p['best_for']}"} for p in picks],
          "table_columns":cols[:5],"bar_tip":"TODO: one practical tip.","faq":[{"q":"TODO question","a":"TODO answer"}],"draft":True,
          "_todo":"Add new products to data/products.json first (ASIN from the product URL), run check-links, then fill TODOs and run: python3 lcg.py publish "+slug}
        save(DATA/"drafts"/f"{slug}.json", draft); print(f"draft data/drafts/{slug}.json  ({len(picks)} auto-matched picks)")

def publish(slug):
    src = DATA/"drafts"/f"{slug}.json"; g = load(src)
    blob = json.dumps(g)
    if "TODO" in blob.replace(g.get("_todo",""),""): sys.exit("Draft still has TODOs; finish editing it first.")
    g["draft"] = False; g.pop("_todo", None); save(DATA/"guides"/f"{slug}.json", g); src.unlink(); print("published", slug)

def enrich():
    """Creators API hook (PA-API 5 is deprecated). Amazon only grants Creators API access after the Associates account is
    approved AND has 10+ qualifying sales in the last 30 days. When you have credentials, set CREATORS_CLIENT_ID /
    CREATORS_CLIENT_SECRET and implement GetItems below to pull live title, image URL and price (Amazon requires prices
    shown from the API to be refreshed at least every 24h, so only render them from a daily build)."""
    if not (os.environ.get("CREATORS_CLIENT_ID") and os.environ.get("CREATORS_CLIENT_SECRET")):
        print("No Creators API credentials yet. Site runs fine without them (no prices/images shown by design)."); return
    raise NotImplementedError("Wire up GetItems from https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction")

if __name__ == "__main__":
    a = sys.argv[1:] or ["build"]
    if a[0] == "build": build()
    elif a[0] == "check-links": sys.exit(check_links())
    elif a[0] == "new-guide" and len(a) > 1: new_guide(" ".join(a[1:]))
    elif a[0] == "publish" and len(a) > 1: publish(a[1])
    elif a[0] == "enrich": enrich()
    else: print(__doc__)
