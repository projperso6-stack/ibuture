import os
import re
import time
import requests
import shutil
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path("site")
LIST = Path("missing_default.txt")

# On garde exactement les catégories que nous avons déjà validées
REMOVE_PATTERNS = [
    re.compile(r'<script\b[^>]*>.*?window\.LangShopConfig.*?</script\s*>', re.I | re.S),
    re.compile(r'<script\b[^>]*>.*?window\.LOLOYAL_ONSITE.*?</script\s*>', re.I | re.S),
    re.compile(r'<script\b[^>]*>.*?wpmLoader.*?</script\s*>', re.I | re.S),
    re.compile(r'<script\b[^>]*>.*?jdgmSettings.*?</script\s*>', re.I | re.S),
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

MIN_FREE_GB = 3.0

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; SiteMirror/1.0)"
})

def local_path(url):
    p = urlparse(url).path

    if not p or p == "/":
        return ROOT / "index.html"

    if p.endswith("/"):
        p += "index.html"
    else:
        p += "/index.html"

    return ROOT / unquote(p.lstrip("/"))

def clean_html(html):
    original = html

    for pattern in REMOVE_PATTERNS:
        html = pattern.sub("", html)

    return html, len(original) - len(html)

def free_space_gb():
    usage = shutil.disk_usage(ROOT)
    return usage.free / (1024 ** 3)

urls = [
    x.strip()
    for x in LIST.read_text(encoding="utf-8").splitlines()
    if x.strip()
]

# Sécurité : uniquement les 107 URLs de missing_default.txt
urls = [
    u for u in urls
    if urlparse(u).netloc.lower() in {
        "ibuture.com",
        "www.ibuture.com"
    }
]

print("=" * 70)
print("TÉLÉCHARGEMENT VERSION PAR DÉFAUT")
print("=" * 70)
print(f"URLs à traiter : {len(urls)}")
print(f"Espace libre   : {free_space_gb():.2f} Go")
print()

downloaded = 0
existing = 0
errors = 0
total_before = 0
total_after = 0

for i, url in enumerate(urls, 1):

    path = urlparse(url).path.lower()

    if any(x in path for x in SKIP):
        print(f"[{i}/{len(urls)}] SKIP {url}")
        continue

    target = local_path(url)

    if target.exists():
        existing += 1
        print(f"[{i}/{len(urls)}] EXISTE {url}")
        continue

    # Sécurité disque
    free = free_space_gb()

    if free < MIN_FREE_GB:
        print()
        print("!!! ARRÊT DE SÉCURITÉ !!!")
        print(f"Espace libre : {free:.2f} Go")
        print("Les fichiers déjà téléchargés sont conservés.")
        break

    success = False

    for attempt in range(6):

        try:
            r = session.get(
                url,
                timeout=60,
                allow_redirects=True
            )

            if r.status_code == 200:

                content_type = r.headers.get(
                    "content-type", ""
                ).lower()

                if "text/html" not in content_type:
                    print(
                        f"[{i}/{len(urls)}] "
                        f"IGNORÉ (non HTML) {url}"
                    )
                    success = True
                    break

                html = r.text

                cleaned, removed = clean_html(html)

                data = cleaned.encode("utf-8")

                target.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                # Écriture atomique
                tmp = target.with_suffix(".tmp")

                tmp.write_bytes(data)

                os.replace(tmp, target)

                before_kb = len(html.encode("utf-8")) / 1024
                after_kb = len(data) / 1024
                gain_kb = before_kb - after_kb

                total_before += before_kb
                total_after += after_kb
                downloaded += 1

                print(
                    f"[{i}/{len(urls)}] "
                    f"{before_kb:,.1f} KB -> "
                    f"{after_kb:,.1f} KB "
                    f"(gain {gain_kb:,.1f} KB) "
                    f"{url}"
                )

                success = True
                break

            elif r.status_code == 429:

                retry_after = r.headers.get("Retry-After")

                if retry_after:
                    try:
                        wait = int(retry_after)
                    except:
                        wait = 30
                else:
                    wait = min(30 * (2 ** attempt), 300)

                print(
                    f"[{i}/{len(urls)}] "
                    f"429 -> attente {wait}s"
                )

                time.sleep(wait)

            else:

                print(
                    f"[{i}/{len(urls)}] "
                    f"HTTP {r.status_code} : {url}"
                )

                break

        except Exception as e:

            print(
                f"[{i}/{len(urls)}] "
                f"ERREUR tentative {attempt + 1}: {e}"
            )

            time.sleep(min(10 * (attempt + 1), 60))

    if not success:
        errors += 1

    # Petite pause volontaire entre les requêtes
    time.sleep(2)

print()
print("=" * 70)
print("TÉLÉCHARGEMENT TERMINÉ")
print("=" * 70)

print(f"URLs prévues       : {len(urls)}")
print(f"Nouvelles pages    : {downloaded}")
print(f"Déjà présentes     : {existing}")
print(f"Erreurs            : {errors}")

if downloaded:
    print()
    print(
        f"Taille avant       : "
        f"{total_before / 1024:.2f} Mo"
    )

    print(
        f"Taille après       : "
        f"{total_after / 1024:.2f} Mo"
    )

    print(
        f"Espace économisé   : "
        f"{(total_before-total_after) / 1024:.2f} Mo"
    )

print()
print(f"Espace libre final : {free_space_gb():.2f} Go")
print("=" * 70)
