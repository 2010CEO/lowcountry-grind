"""Tell Bing/DuckDuckGo/Yandex (IndexNow) about every URL in site/sitemap.xml. Run after a deploy."""
import json, re, urllib.request, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
c = json.load(open(R / "config.json")); base = c["base_url"].rstrip("/")
urls = re.findall(r"<loc>([^<]+)</loc>", (R / "site/sitemap.xml").read_text())
body = {"host": base.split("/")[2], "key": c["indexnow_key"], "keyLocation": f'{base}/{c["indexnow_key"]}.txt', "urlList": urls}
req = urllib.request.Request("https://api.indexnow.org/indexnow", json.dumps(body).encode(), {"Content-Type": "application/json; charset=utf-8"})
try: print("IndexNow", urllib.request.urlopen(req, timeout=30).status, len(urls), "urls")
except urllib.error.HTTPError as e: print("IndexNow HTTP", e.code, e.read()[:200])
