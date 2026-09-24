import os
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
from collections import Counter

BASE = "https://ibuture.com/sitemap.xml"
SITE_DIR = "site"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

print("=" * 80)
print("INVENTAIRE SITEMAP — AUCUN TÉLÉCHARGEMENT DU SITE")
print("=" * 80)

r = requests.get(BASE, timeout=60)
r.raise_for_status()
root = ET.fromstring(r.content)

sitemaps = [
    x.text.strip()
    for x in root.findall(".//sm:sitemap/sm:loc", NS)
    if x.text
]

print(f"Sitemaps trouvés : {len(sitemaps)}")
print()

all_urls = []

for i, sitemap_url in enumerate(sitemaps, 1):
    try:
        rr = requests.get(sitemap_url, timeout=60)
        rr.raise_for_status()
        sr = ET.fromstring(rr.content)

        urls = [
            x.text.strip()
            for x in sr.findall(".//sm:url/sm:loc", NS)
            if x.text
        ]

        all_urls.extend(urls)

        print(f"[{i:3}/{len(sitemaps)}] {len(urls):4} URLs")

    except Exception as e:
        print(f"[ERREUR] {sitemap_url}")
        print(e)

def local_path(url):
    p = urlparse(url)
    path = unquote(p.path).strip("/")

    if not path:
        return os.path.join(SITE_DIR, "index.html")

    return os.path.join(SITE_DIR, path, "index.html")

existing = []
missing = []

for url in all_urls:
    if os.path.isfile(local_path(url)):
        existing.append(url)
    else:
        missing.append(url)

print()
print("=" * 80)
print("RÉSULTAT GLOBAL")
print("=" * 80)

print(f"URLs officielles Shopify : {len(all_urls)}")
print(f"Déjà présentes           : {len(existing)}")
print(f"Manquantes               : {len(missing)}")

if all_urls:
    print(f"Couverture actuelle      : {len(existing) / len(all_urls) * 100:.2f}%")

print()
print("URLS MANQUANTES PAR MARCHÉ")
print("-" * 80)

markets = Counter()

for url in missing:
    parts = urlparse(url).path.strip("/").split("/")

    if parts and parts[0]:
        markets[parts[0]] += 1
    else:
        markets["ROOT"] += 1

for market, count in markets.most_common():
    print(f"{market:12} {count:6}")

print()
print("URLS MANQUANTES PAR TYPE")
print("-" * 80)

types = Counter()

for url in missing:
    parts = urlparse(url).path.strip("/").split("/")

    if len(parts) >= 2:
        types[parts[1]] += 1
    else:
        types["root"] += 1

for typ, count in types.most_common():
    print(f"{typ:20} {count:6}")

print()
print("20 PREMIÈRES URLS MANQUANTES")
print("-" * 80)

for url in missing[:20]:
    print(url)

with open("sitemap_inventory.txt", "w", encoding="utf-8") as f:
    f.write("INVENTAIRE IBUTURE\n")
    f.write("=" * 80 + "\n")
    f.write(f"Sitemaps : {len(sitemaps)}\n")
    f.write(f"URLs : {len(all_urls)}\n")
    f.write(f"Présentes : {len(existing)}\n")
    f.write(f"Manquantes : {len(missing)}\n")
    f.write(f"Couverture : {len(existing) / len(all_urls) * 100:.2f}%\n\n")

    f.write("URLS MANQUANTES\n")
    f.write("-" * 80 + "\n")

    for url in missing:
        f.write(url + "\n")

print()
print("=" * 80)
print("INVENTAIRE TERMINÉ")
print("=" * 80)
print("Fichier créé : sitemap_inventory.txt")
print("Aucun fichier de site/ n'a été modifié.")
