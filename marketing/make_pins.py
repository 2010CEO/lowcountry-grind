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
TPL = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,800;0,9..144,900;1,9..144,800&family=Inter:wght@400;600&family=Space+Mono:wght@700&display=swap" rel="stylesheet">
<style>
*{margin:0;box-sizing:border-box}
body{width:1000px;height:1500px;background:radial-gradient(120% 70% at 85% 0%,#4a2a14 0%,#1a110b 60%);color:#f4e9d8;font-family:Inter,sans-serif;position:relative;overflow:hidden}
.k{position:absolute;top:90px;left:80px;font:700 26px 'Space Mono',monospace;letter-spacing:.22em;color:#e2762b}
.top{position:absolute;top:190px;left:80px;right:80px}
h1{font:900 112px/1.0 Fraunces,serif;letter-spacing:-.02em}
h1 em{display:block;color:#e2762b;font-style:italic;font-weight:800}
.dek{margin-top:48px;margin-right:30px;font:400 40px/1.4 Inter,sans-serif;color:#e9dcc6}
.steam{position:absolute;right:90px;top:790px;width:150px;height:300px;opacity:.5}
.card{position:absolute;left:80px;right:80px;bottom:150px;background:#fbf5ea;color:#22170f;border-radius:28px;padding:44px 50px}
.card b{display:block;font:800 46px/1.15 Fraunces,serif}
.card span{display:block;margin-top:14px;font:700 24px 'Space Mono',monospace;color:#e2762b;letter-spacing:.06em}
.foot{position:absolute;left:80px;right:80px;bottom:62px;display:flex;justify-content:space-between;font:700 24px 'Space Mono',monospace;color:#b8a58c;letter-spacing:.08em}
</style></head><body>
<svg class="steam" viewBox="0 0 170 420" fill="none" stroke="#e2762b" stroke-width="7" stroke-linecap="round" stroke-dasharray="14 18">
<path d="M30 400 C 0 300, 60 250, 30 150 S 40 40, 30 10"/><path d="M85 400 C 55 300, 115 250, 85 150 S 95 40, 85 10"/><path d="M140 400 C 110 300, 170 250, 140 150 S 150 40, 140 10"/></svg>
<div class="k">LOWCOUNTRY GRIND</div>
<div class="top"><h1>$h1<em>$h2</em></h1>
<div class="dek">$dek</div></div>
<div class="card"><b>$title</b><span>$picks PICKS · READ THE GUIDE →</span></div>
<div class="foot"><span>2010ceo.github.io/lowcountry-grind</span><span>#ad</span></div>
</body></html>"""
for f in sorted(glob.glob(str(ROOT / "data/guides/*.json"))):
    slug = pathlib.Path(f).stem; d = json.load(open(f)); h1, h2 = HOOK[slug]
    page = string.Template(TPL).substitute(h1=html.escape(h1), h2=html.escape(h2), dek=html.escape(d["dek"]), title=html.escape(d["title"]), picks=len(d.get("picks", [])))
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as t: t.write(page)
    out = OUT / f"{slug}.png"
    out.unlink(missing_ok=True)
    try: subprocess.run(["chromium", "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    f"--user-data-dir={tempfile.mkdtemp()}", "--virtual-time-budget=6000",
                    "--window-size=1000,1500", f"--screenshot={out}", "file://" + t.name],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except subprocess.TimeoutExpired: pass  # headless chromium often writes the PNG then never exits
    print(slug, out.exists() and out.stat().st_size)
