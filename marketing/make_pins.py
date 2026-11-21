"""Render one 1000x1500 Pinterest pin per guide (site fonts/colors) with headless Chromium.
python3 marketing/make_pins.py   -> marketing/pins/<slug>.png"""
import json, glob, html, subprocess, pathlib, tempfile, string
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "marketing" / "pins"; OUT.mkdir(parents=True, exist_ok=True)
HOOK = {  # big headline per pin (short, Pinterest-style)
 "coffee-gift-guide": ("Gifts coffee people", "actually use."),
 "best-coffee-grinder-for-beginners": ("Upgrade one thing:", "the grinder."),
 "best-pour-over-coffee-setup": ("Café pour-over", "at home."),
 "best-espresso-machine-for-beginners": ("Lattes at home,", "the honest way."),
 "best-drip-coffee-maker-for-families": ("Drip coffee", "that tastes right."),
 "best-cold-brew-maker": ("95° outside?", "Cold brew it."),
 "best-camp-coffee-maker": ("Deer stand coffee", "at 5 a.m."),
}
PHOTO = {"grinder":"grinder","gift":"gift","pourover":"pourover","espresso":"espresso","drip":"drip","coldbrew":"coldbrew","camp":"camp"}
TPL = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,600;0,9..144,700;1,9..144,400;1,9..144,600&family=Inter:wght@500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;box-sizing:border-box}
body{width:1000px;height:1500px;background:#f7f2ea;color:#1d1712;font-family:Inter,sans-serif;position:relative;overflow:hidden}
.ph{position:absolute;inset:0 0 auto 0;height:860px;background:url('$img') center/cover}
.ph::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,15,11,.55) 0%,rgba(20,15,11,0) 30%,rgba(20,15,11,0) 70%,rgba(20,15,11,.25) 100%)}
.brand{position:absolute;top:56px;left:64px;z-index:2;display:flex;align-items:center;gap:16px;color:#fff;font:600 34px Fraunces,serif;letter-spacing:-.01em}
.brand i{width:46px;height:46px;border-radius:50%;background:#1d1712;display:grid;place-items:center}
.brand i b{width:20px;height:28px;border-radius:50%;background:#b4532a;display:block}
.panel{position:absolute;left:0;right:0;top:780px;bottom:0;background:#f7f2ea;border-radius:44px 44px 0 0;padding:64px 70px 0}
.tag{font:700 24px Inter,sans-serif;letter-spacing:.18em;text-transform:uppercase;color:#b4532a}
h1{margin-top:22px;font:600 104px/1.0 Fraunces,serif;letter-spacing:-.03em}
h1 em{display:block;font-style:italic;font-weight:400;color:#b4532a}
.dek{margin-top:30px;font:500 32px/1.4 Inter,sans-serif;color:#3f352c}
.foot{position:absolute;left:70px;right:70px;bottom:54px;display:flex;justify-content:space-between;align-items:center;font:600 28px Inter,sans-serif;color:#1d1712}
.foot .go{background:#1d1712;color:#fff;border-radius:999px;padding:20px 34px}
.foot small{font:500 22px Inter;color:#76695c}
</style></head><body>
<div class="ph"></div>
<div class="brand"><i><b></b></i>Lowcountry Grind</div>
<div class="panel"><div class="tag">$tag &middot; $picks picks</div><h1>$h1<em>$h2</em></h1><div class="dek">$dek</div></div>
<div class="foot"><span>lowcountrygrind.com <small>&nbsp;#ad</small></span><span class="go">Read the guide &rarr;</span></div>
</body></html>"""
for f in sorted(glob.glob(str(ROOT / "data/guides/*.json"))):
    slug = pathlib.Path(f).stem; d = json.load(open(f)); h1, h2 = HOOK[slug]
    TAG = {"grinder":"Grinders","gift":"Gift guide","pourover":"Pour-over","espresso":"Espresso","drip":"Drip coffee","coldbrew":"Cold brew","camp":"Outdoors"}
    page = string.Template(TPL).substitute(h1=html.escape(h1), h2=html.escape(h2), dek=html.escape(d["dek"]), tag=TAG.get(d["glyph"],"Guide"),
        picks=len(d.get("picks", [])), img="file://" + str(ROOT / "static/img" / (PHOTO.get(d["glyph"], "gift") + ".webp")))
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as t: t.write(page)
    out = OUT / f"{slug}.png"
    out.unlink(missing_ok=True)
    try: subprocess.run(["chromium", "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    f"--user-data-dir={tempfile.mkdtemp()}", "--virtual-time-budget=6000",
                    "--window-size=1000,1500", f"--screenshot={out}", "file://" + t.name],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except subprocess.TimeoutExpired: pass  # headless chromium often writes the PNG then never exits
    print(slug, out.exists() and out.stat().st_size)
