import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
from pathlib import Path
from collections import Counter, defaultdict
import time

SITEMAP = "https://ibuture.com/sitemap.xml"
ROOT = Path("site")

SKIP = [
    "/cart",
    "/checkout",
    "/account",
    "/search",
    "/apps/",
    "/admin",
    "/challenge",
    "/password",
]

def get_xml(url):
    wait = 30

    for attempt in range(6):
        r = requests.get(
            url,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; SiteMirror/1.0)"
            }
        )

        if r.status_code == 200:
            return ET.fromstring(r.content)

        if r.status_code == 429:
            print(f"429 -> attente {wait}s")
            time.sleep(wait)
            wait = min(wait * 2, 300)
            continue

        r.raise_for_status()

    raise RuntimeError("Impossible de récupérer " + url)

def local_path(url):
    p = urlparse(url).path

    if not p or p == "/":
        return ROOT / "index.html"

    if p.endswith("/"):
        p += "index.html"
    else:
        p += "/index.html"

    return ROOT / unquote(p.lstrip("/"))

print("Lecture du sitemap principal...")

root = get_xml(SITEMAP)

ns = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9"
}

sitemaps = [
    x.text.strip()
    for x in root.findall(".//sm:sitemap/sm:loc", ns)
]

print(f"Sitemaps : {len(sitemaps)}")

urls = []

for i, sm in enumerate(sitemaps, 1):

    print(f"[{i}/{len(sitemaps)}]")

    try:
        tree = get_xml(sm)

        for loc in tree.findall(".//sm:url/sm:loc", ns):
            if loc.text:
                urls.append(loc.text.strip())

        time.sleep(3)

    except Exception as e:
        print("ERREUR :", e)

print()
print("URLs :", len(urls))

missing = []

for url in urls:

    path = urlparse(url).path.lower()

    if any(x in path for x in SKIP):
        continue

    if not local_path(url).exists():
        missing.append(url)

print("Pages manquantes :", len(missing))

# --------------------------------------------------
# ANALYSE PAR TYPE
# --------------------------------------------------

types = Counter()
languages = Counter()
markets = Counter()

for url in missing:

    path = urlparse(url).path.strip("/")

    parts = path.split("/")

    if not parts:
        types["root"] += 1
        continue

    first = parts[0]

    # Détection du type
    if "/products/" in "/" + path:
        typ = "products"
    elif "/collections/" in "/" + path:
        typ = "collections"
    elif "/blogs/" in "/" + path:
        typ = "blogs"
    elif first == "pages" or "/pages/" in "/" + path:
        typ = "pages"
    elif path == "agents.md":
        typ = "agents"
    else:
        typ = "other"

    types[typ] += 1

    # Premier segment = locale/market quand présent
    if first in [
        "de", "fr", "pl", "es", "it",
        "de-de", "fr-de", "pl-de", "es-de", "it-de", "en-de",
        "de-es", "fr-es", "pl-es", "es-es", "it-es", "en-es",
        "de-it", "fr-it", "pl-it", "es-it", "it-it", "en-it",
        "de-fr", "fr-fr", "pl-fr", "es-fr", "it-fr", "en-fr",
        "de-pl", "fr-pl", "pl-pl", "es-pl", "it-pl", "en-pl",
        "de-nl", "fr-nl", "pl-nl", "es-nl", "it-nl", "en-nl",
        "de-at", "fr-at", "pl-at", "es-at", "it-at", "en-at",
        "de-lu", "fr-lu", "pl-lu", "es-lu", "it-lu", "en-lu",
    ]:
        languages[first] += 1
    else:
        languages["default"] += 1

print()
print("=" * 70)
print("PAGES MANQUANTES PAR TYPE")
print("=" * 70)

for k, v in types.most_common():
    print(f"{k:20} {v:8}")

print()
print("=" * 70)
print("PAGES MANQUANTES PAR LOCALE / MARCHÉ")
print("=" * 70)

for k, v in languages.most_common():
    print(f"{k:20} {v:8}")

# --------------------------------------------------
# ÉCHANTILLONS
# --------------------------------------------------

print()
print("=" * 70)
print("ÉCHANTILLON DES PAGES MANQUANTES")
print("=" * 70)

for url in missing[:30]:
    print(url)

# --------------------------------------------------
# SAUVEGARDE DE LA LISTE
# --------------------------------------------------

with open("missing_urls.txt", "w", encoding="utf-8") as f:
    for url in missing:
        f.write(url + "\n")

print()
print("Liste sauvegardée dans : missing_urls.txt")
print("=" * 70)
