import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
from pathlib import Path
import time
import statistics

SITEMAP = "https://ibuture.com/sitemap.xml"
ROOT = Path("site")

SCRIPT_RE = re.compile(
    r"<script\b[^>]*>.*?</script\s*>",
    re.IGNORECASE | re.DOTALL
)

REMOVE = [
    "window.langshopconfig",
    "wpmloader",
    "shortly-version",
    "jdgmsettings",
]

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

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; SiteMirror/1.0)"
})

def get_xml(url, attempts=6):
    wait = 30

    for attempt in range(1, attempts + 1):
        try:
            r = session.get(url, timeout=60)

            if r.status_code == 200:
                return ET.fromstring(r.content)

            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")

                if retry_after:
                    try:
                        wait = max(wait, int(retry_after))
                    except:
                        pass

                print(f"HTTP 429 sur {url}")
                print(f"Attente {wait}s avant nouvel essai ({attempt}/{attempts})...")
                time.sleep(wait)
                wait = min(wait * 2, 300)
                continue

            r.raise_for_status()

        except Exception as e:
            if attempt == attempts:
                raise

            print(f"Erreur: {e}")
            print(f"Nouvelle tentative dans {wait}s...")
            time.sleep(wait)
            wait = min(wait * 2, 300)

    raise RuntimeError(f"Impossible de récupérer {url}")

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

print(f"Sitemaps trouvés : {len(sitemaps)}")

urls = []

for i, sm in enumerate(sitemaps, 1):
    print(f"[Sitemap {i}/{len(sitemaps)}] {sm}")

    try:
        tree = get_xml(sm)

        for loc in tree.findall(".//sm:url/sm:loc", ns):
            if loc.text:
                urls.append(loc.text.strip())

        time.sleep(2)

    except Exception as e:
        print("Erreur sitemap :", e)

print(f"\nURLs officielles trouvées : {len(urls)}")

missing = []

for url in urls:
    path = urlparse(url).path.lower()

    if any(x in path for x in SKIP):
        continue

    if not local_path(url).exists():
        missing.append(url)

print(f"Pages manquantes : {len(missing)}")

if not missing:
    print("Aucune page manquante.")
    raise SystemExit

# 10 pages réparties dans toute la liste
sample = []

for i in range(10):
    index = int(i * (len(missing) - 1) / 9) if len(missing) > 1 else 0
    sample.append(missing[index])

print("\nTest de 10 pages réparties dans les pages manquantes :\n")

results = []

for i, url in enumerate(sample, 1):

    success = False
    wait = 20

    for attempt in range(5):

        try:
            r = session.get(url, timeout=60)

            if r.status_code == 429:
                print(f"[{i}/10] HTTP 429")
                print(f"Attente {wait}s...")
                time.sleep(wait)
                wait = min(wait * 2, 180)
                continue

            if r.status_code != 200:
                print(f"[{i}/10] HTTP {r.status_code} -> {url}")
                break

            original = len(r.content)

            html = r.content.decode(
                "utf-8",
                errors="ignore"
            )

            def repl(match):
                block = match.group(0)

                if any(
                    keyword in block.lower()
                    for keyword in REMOVE
                ):
                    return ""

                return block

            cleaned = SCRIPT_RE.sub(repl, html)

            cleaned_size = len(
                cleaned.encode("utf-8")
            )

            gain = original - cleaned_size

            results.append(
                (original, cleaned_size, gain)
            )

            print(
                f"[{i}/10] "
                f"{original/1024:.1f} KB -> "
                f"{cleaned_size/1024:.1f} KB "
                f"(gain {gain/1024:.1f} KB)"
            )

            success = True
            break

        except Exception as e:
            print(f"[{i}/10] ERREUR : {e}")
            time.sleep(wait)
            wait = min(wait * 2, 180)

    # pause volontaire entre les pages
    if success:
        time.sleep(8)

if not results:
    print("\nAucun résultat exploitable.")
    raise SystemExit

avg_original = statistics.mean(
    x[0] for x in results
)

avg_cleaned = statistics.mean(
    x[1] for x in results
)

avg_gain = statistics.mean(
    x[2] for x in results
)

estimated_final = avg_cleaned * len(missing)

print("\n" + "=" * 70)
print("ESTIMATION APRÈS NETTOYAGE")
print("=" * 70)

print(f"Pages manquantes       : {len(missing)}")
print(f"Pages testées          : {len(results)}")
print(f"Taille moyenne avant  : {avg_original/1024:.1f} KB")
print(f"Taille moyenne après  : {avg_cleaned/1024:.1f} KB")
print(f"Gain moyen/page        : {avg_gain/1024:.1f} KB")
print(f"Estimation finale      : {estimated_final/1024/1024/1024:.2f} Go")

print("=" * 70)
print("AUCUNE PAGE N'A ÉTÉ ENREGISTRÉE.")
print("=" * 70)
