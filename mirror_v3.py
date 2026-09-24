import os
import re
import time
import requests
import xml.etree.ElementTree as ET

from urllib.parse import urlparse, unquote, urljoin
from bs4 import BeautifulSoup

BASE = "https://ibuture.com"
SITEMAP = BASE + "/sitemap.xml"
SITE_DIR = "site"
MAX_PAGES = 100

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; StaticMirror/3.0)"
})

stats = {
    "pages_downloaded": 0,
    "pages_existing": 0,
    "assets_downloaded": 0,
    "errors": 0
}

def local_path(url):
    p = urlparse(url)
    path = unquote(p.path).strip("/")

    if not path:
        return os.path.join(SITE_DIR, "index.html")

    return os.path.join(SITE_DIR, path, "index.html")


def is_forbidden(url):
    path = urlparse(url).path.lower()

    forbidden = [
        "/cart",
        "/checkout",
        "/account",
        "/search",
        "/apps/",
        "/admin",
        "/challenge",
        "/password"
    ]

    return any(x in path for x in forbidden)


def download(url, path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)

        r = session.get(url, timeout=60)
        r.raise_for_status()

        with open(path, "wb") as f:
            f.write(r.content)

        return True

    except Exception as e:
        print(f"[ERREUR] {url}")
        print(f"         {e}")
        stats["errors"] += 1
        return False


def asset_url(raw, page_url):
    if not raw:
        return None

    raw = raw.strip()

    if raw.startswith(("data:", "javascript:", "#", "mailto:")):
        return None

    return urljoin(page_url, raw)


def asset_local_path(url):
    p = urlparse(url)
    path = unquote(p.path)

    if not path or path.endswith("/"):
        return None

    path = path.lstrip("/")

    return os.path.join(SITE_DIR, "assets", path)


def download_asset(url, page_url):
    full = asset_url(url, page_url)

    if not full:
        return url

    parsed = urlparse(full)

    if parsed.scheme not in ("http", "https"):
        return url

    # uniquement les ressources du site ou CDN Shopify
    allowed_hosts = {
        "ibuture.com",
        "www.ibuture.com",
        "cdn.shopify.com",
        "shopify.com"
    }

    if parsed.hostname not in allowed_hosts and not (
        parsed.hostname and parsed.hostname.endswith(".shopify.com")
    ):
        return url

    local = asset_local_path(full)

    if not local:
        return url

    if os.path.isfile(local):
        return os.path.relpath(local, os.path.dirname(local_path(page_url)))

    if download(full, local):
        stats["assets_downloaded"] += 1
        return os.path.relpath(local, os.path.dirname(local_path(page_url)))

    return url


print("=" * 80)
print("MIRROR V3 — TEST DE 100 PAGES")
print("=" * 80)
print("Aucun fichier existant ne sera supprimé.")
print()

# ------------------------------------------------------------
# 1. Lire le sitemap principal
# ------------------------------------------------------------

print("Lecture du sitemap principal...")

r = session.get(SITEMAP, timeout=60)
r.raise_for_status()

root = ET.fromstring(r.content)

sitemaps = [
    x.text.strip()
    for x in root.findall(".//sm:sitemap/sm:loc", NS)
    if x.text
]

print(f"Sitemaps : {len(sitemaps)}")

# ------------------------------------------------------------
# 2. Construire la liste officielle des URLs
# ------------------------------------------------------------

all_urls = []

for i, sitemap_url in enumerate(sitemaps, 1):

    try:
        rr = session.get(sitemap_url, timeout=60)
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
        print(f"[ERREUR SITEMAP] {sitemap_url}")
        print(e)

print()
print(f"URLs trouvées : {len(all_urls)}")

# ------------------------------------------------------------
# 3. Sélectionner uniquement les pages manquantes
# ------------------------------------------------------------

missing = []

for url in all_urls:

    if is_forbidden(url):
        continue

    path = local_path(url)

    if os.path.isfile(path):
        stats["pages_existing"] += 1
    else:
        missing.append(url)

test_urls = missing[:MAX_PAGES]

print(f"Pages déjà présentes : {stats['pages_existing']}")
print(f"Pages manquantes      : {len(missing)}")
print(f"Pages du TEST         : {len(test_urls)}")
print()

# ------------------------------------------------------------
# 4. Télécharger les pages
# ------------------------------------------------------------

for i, url in enumerate(test_urls, 1):

    print()
    print("-" * 80)
    print(f"[PAGE {i}/{len(test_urls)}]")
    print(url)

    local = local_path(url)

    try:

        r = session.get(url, timeout=60)
        r.raise_for_status()

        content_type = r.headers.get("content-type", "")

        if "text/html" not in content_type:
            print(f"[SKIP] Type non HTML : {content_type}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        # ----------------------------------------------------
        # Images
        # ----------------------------------------------------

        for tag in soup.find_all(["img", "source"]):

            for attr in ["src", "data-src", "poster"]:

                if tag.has_attr(attr):
                    original = tag[attr]

                    new = download_asset(original, url)

                    tag[attr] = new

            if tag.has_attr("srcset"):

                parts = []

                for item in tag["srcset"].split(","):

                    item = item.strip()

                    if not item:
                        continue

                    bits = item.split()

                    original = bits[0]
                    new = download_asset(original, url)

                    if len(bits) > 1:
                        parts.append(new + " " + " ".join(bits[1:]))
                    else:
                        parts.append(new)

                tag["srcset"] = ", ".join(parts)

        # ----------------------------------------------------
        # CSS
        # ----------------------------------------------------

        for tag in soup.find_all("link"):

            if tag.get("href"):
                href = tag["href"]

                if "stylesheet" in " ".join(tag.get("rel", [])):
                    tag["href"] = download_asset(href, url)

        # ----------------------------------------------------
        # JS
        # ----------------------------------------------------

        for tag in soup.find_all("script"):

            if tag.get("src"):
                tag["src"] = download_asset(tag["src"], url)

        # ----------------------------------------------------
        # Vidéos
        # ----------------------------------------------------

        for tag in soup.find_all(["video", "source"]):

            if tag.get("src"):
                tag["src"] = download_asset(tag["src"], url)

        # ----------------------------------------------------
        # Sauvegarde
        # ----------------------------------------------------

        os.makedirs(os.path.dirname(local), exist_ok=True)

        with open(local, "w", encoding="utf-8") as f:
            f.write(str(soup))

        stats["pages_downloaded"] += 1

        print("[OK] Page enregistrée")

        time.sleep(0.15)

    except Exception as e:

        print(f"[ERREUR PAGE] {e}")
        stats["errors"] += 1

# ------------------------------------------------------------
# 5. Résumé
# ------------------------------------------------------------

print()
print("=" * 80)
print("MIRROR V3 — TEST TERMINÉ")
print("=" * 80)

print(f"Pages téléchargées : {stats['pages_downloaded']}")
print(f"Pages existantes    : {stats['pages_existing']}")
print(f"Assets téléchargés  : {stats['assets_downloaded']}")
print(f"Erreurs             : {stats['errors']}")

print()
print("AUCUN fichier existant n'a été supprimé.")
print("=" * 80)
