import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse, unquote
import statistics
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

def local_path(url):
    p = urlparse(url).path
    if not p or p == "/":
        return ROOT / "index.html"

    if p.endswith("/"):
        p += "index.html"
    else:
        p += "/index.html"

    return ROOT / unquote(p.lstrip("/"))

def get_xml(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return ET.fromstring(r.content)

print("Lecture du sitemap...")

root = get_xml(SITEMAP)

ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

sitemaps = [
    x.text.strip()
    for x in root.findall(".//sm:sitemap/sm:loc", ns)
]

urls = []

for sm in sitemaps:
    try:
        tree = get_xml(sm)
        for loc in tree.findall(".//sm:url/sm:loc", ns):
            if loc.text:
                urls.append(loc.text.strip())
    except Exception as e:
        print("Erreur sitemap:", sm, e)

missing = []

for url in urls:
    path = urlparse(url).path.lower()

    if any(x in path for x in SKIP):
        continue

    if not local_path(url).exists():
        missing.append(url)

print()
print("=" * 70)
print("PAGES MANQUANTES")
print("=" * 70)
print(f"Total officiel : {len(urls)}")
print(f"Manquantes     : {len(missing)}")
print("=" * 70)

# Échantillon réparti dans toute la liste
SAMPLE_SIZE = min(50, len(missing))

if SAMPLE_SIZE == 0:
    print("Aucune page manquante.")
    raise SystemExit

step = max(1, len(missing) // SAMPLE_SIZE)

sample = [
    missing[i]
    for i in range(0, len(missing), step)
][:SAMPLE_SIZE]

print(f"\nTest de {len(sample)} pages réparties dans l'ensemble des pages manquantes...\n")

sizes = []
success = 0
errors = 0

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

for i, url in enumerate(sample, 1):
    try:
        r = session.get(url, timeout=30)

        if r.status_code == 200:
            size = len(r.content)
            sizes.append(size)
            success += 1

            print(
                f"[{i}/{len(sample)}] "
                f"{size/1024:.1f} KB  "
                f"{url}"
            )
        else:
            errors += 1
            print(
                f"[{i}/{len(sample)}] HTTP {r.status_code} "
                f"{url}"
            )

    except Exception as e:
        errors += 1
        print(f"[{i}/{len(sample)}] ERREUR {url} -> {e}")

    time.sleep(0.1)

if not sizes:
    print("\nImpossible d'estimer la taille.")
    raise SystemExit

avg = statistics.mean(sizes)
median = statistics.median(sizes)

estimated = avg * len(missing)
estimated_median = median * len(missing)

print()
print("=" * 70)
print("ESTIMATION DE L'ESPACE NÉCESSAIRE")
print("=" * 70)

print(f"Pages manquantes        : {len(missing)}")
print(f"Pages testées           : {success}")
print(f"Erreurs pendant test    : {errors}")
print(f"Taille moyenne          : {avg/1024:.1f} KB")
print(f"Taille médiane          : {median/1024:.1f} KB")
print()
print(
    f"Estimation moyenne     : "
    f"{estimated/1024/1024/1024:.2f} Go"
)
print(
    f"Estimation médiane     : "
    f"{estimated_median/1024/1024/1024:.2f} Go"
)

print("=" * 70)
print("AUCUNE PAGE N'A ÉTÉ ENREGISTRÉE.")
print("=" * 70)
