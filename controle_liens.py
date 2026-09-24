import re
from pathlib import Path
from urllib.parse import urlparse, unquote

SITE = Path("site")

if not SITE.exists():
    print("ERREUR : dossier site/ introuvable.")
    raise SystemExit(1)

print("=" * 70)
print("CONTRÔLE DES LIENS INTERNES DU MIRROR")
print("=" * 70)

# -------------------------------------------------------------------
# 1. Construire l'index des pages locales
# -------------------------------------------------------------------

print("\n[1] INDEXATION DES PAGES LOCALES")
print("-" * 70)

local_pages = set()

for p in SITE.rglob("index.html"):
    rel = p.relative_to(SITE).as_posix()

    if rel == "index.html":
        local_url = "/"
    else:
        # ex: fr-at/products/test/index.html -> /fr-at/products/test/
        local_url = "/" + rel[:-len("index.html")]

    local_pages.add(local_url)

print(f"Pages locales trouvées : {len(local_pages):,}")

# -------------------------------------------------------------------
# 2. Fonction de normalisation
# -------------------------------------------------------------------

def normalize_internal_url(url, current_file):
    if not url:
        return None

    url = url.strip()

    # Protocoles / liens non HTML
    if url.startswith((
        "mailto:",
        "tel:",
        "javascript:",
        "data:",
        "blob:",
        "#"
    )):
        return None

    # URL absolue
    parsed = urlparse(url)

    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return None

    # Domaine externe
    if parsed.netloc:
        host = parsed.netloc.lower().split(":")[0]

        if host not in (
            "ibuture.com",
            "www.ibuture.com"
        ):
            return None

    path = unquote(parsed.path)

    if not path:
        path = "/"

    # Normalisation
    if not path.startswith("/"):
        path = "/" + path

    # Retirer plusieurs /
    path = re.sub(r"/+", "/", path)

    # Ressources non HTML
    lower = path.lower()

    if lower.endswith((
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".svg", ".ico", ".css", ".js",
        ".woff", ".woff2", ".ttf", ".otf",
        ".mp4", ".webm", ".pdf", ".xml", ".json"
    )):
        return None

    # Shopify peut avoir des URLs avec index.html localement
    if path.endswith("/index.html"):
        path = path[:-len("index.html")]

    # Une URL sans slash final correspond à notre dossier index.html
    if not path.endswith("/"):
        path += "/"

    return path


# -------------------------------------------------------------------
# 3. Analyse des liens
# -------------------------------------------------------------------

print("\n[2] ANALYSE DES LIENS")
print("-" * 70)

# href uniquement : ce sont les vrais liens de navigation
href_re = re.compile(
    r"""<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE
)

total_links = 0
internal_links = 0
external_links = 0
valid_links = 0

missing = {}
external_domains = {}

html_files = list(SITE.rglob("*.html"))

for i, html_file in enumerate(html_files, 1):

    if i % 500 == 0:
        print(
            f"Analyse : {i:,}/{len(html_files):,}",
            end="\r"
        )

    try:
        with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        continue

    for raw_url in href_re.findall(text):

        total_links += 1

        parsed = urlparse(raw_url)

        # -----------------------------------------------------------
        # Externe
        # -----------------------------------------------------------

        if parsed.netloc:
            host = parsed.netloc.lower().split(":")[0]

            if host not in ("ibuture.com", "www.ibuture.com"):
                external_links += 1

                external_domains[host] = external_domains.get(host, 0) + 1
                continue

        # -----------------------------------------------------------
        # Interne
        # -----------------------------------------------------------

        normalized = normalize_internal_url(
            raw_url,
            html_file
        )

        if normalized is None:
            continue

        internal_links += 1

        if normalized in local_pages:
            valid_links += 1
        else:
            missing.setdefault(normalized, {
                "count": 0,
                "sources": []
            })

            missing[normalized]["count"] += 1

            if len(missing[normalized]["sources"]) < 3:
                missing[normalized]["sources"].append(
                    html_file.relative_to(SITE).as_posix()
                )

print("\n")

# -------------------------------------------------------------------
# 4. Résultats
# -------------------------------------------------------------------

print("[3] RÉSULTATS")
print("-" * 70)

print(f"Liens <a> analysés       : {total_links:,}")
print(f"Liens internes           : {internal_links:,}")
print(f"Liens internes valides   : {valid_links:,}")
print(f"Liens internes absents   : {len(missing):,}")

if internal_links:
    percentage = valid_links / internal_links * 100
else:
    percentage = 0

print(f"Taux de résolution       : {percentage:.2f}%")

# -------------------------------------------------------------------
# 5. Liens manquants
# -------------------------------------------------------------------

print("\n[4] LIENS INTERNES ABSENTS")
print("-" * 70)

if not missing:
    print("✅ Aucun lien interne manquant détecté.")
else:

    # Trier par nombre d'occurrences
    sorted_missing = sorted(
        missing.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )

    print(
        f"URLs internes absentes : {len(sorted_missing):,}"
    )

    print("\nTop 100 :\n")

    for url, info in sorted_missing[:100]:

        print(
            f"{info['count']:>6}x  {url}"
        )

        for source in info["sources"]:
            print(
                f"       depuis : {source}"
            )

# -------------------------------------------------------------------
# 6. Sauvegarde complète
# -------------------------------------------------------------------

missing_file = Path("liens_manquants.txt")

with open(
    missing_file,
    "w",
    encoding="utf-8"
) as f:

    for url, info in sorted(
        missing.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    ):

        f.write(
            f"{info['count']}x\t{url}\n"
        )

print(
    f"\nListe complète sauvegardée dans : {missing_file}"
)

# -------------------------------------------------------------------
# 7. Domaines externes
# -------------------------------------------------------------------

print("\n[5] DOMAINES EXTERNES")
print("-" * 70)

for domain, count in sorted(
    external_domains.items(),
    key=lambda x: x[1],
    reverse=True
)[:30]:

    print(f"{count:>8}x  {domain}")

# -------------------------------------------------------------------
# 8. Rapport final
# -------------------------------------------------------------------

print("\n" + "=" * 70)
print("RAPPORT")
print("=" * 70)

if not missing:
    print("\n✅ EXCELLENT")
    print("Tous les liens internes détectés correspondent")
    print("à une page présente dans le mirror.")
else:
    print(
        f"\n⚠️ {len(missing):,} URLs internes différentes "
        "ne correspondent pas à une page locale."
    )

    print(
        "\nLe fichier liens_manquants.txt contient "
        "la liste complète."
    )

print("\nContrôle terminé.")
print("=" * 70)
