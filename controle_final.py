import os
import re
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse, unquote

SITE = Path("site")

HTML_RE = re.compile(r"\.html?$", re.I)

def human(n):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

print("=" * 70)
print("CONTRÔLE FINAL DU MIRROR")
print("=" * 70)

if not SITE.exists():
    print("ERREUR : dossier site/ introuvable.")
    raise SystemExit(1)

# ---------------------------------------------------------
# 1. STATISTIQUES GÉNÉRALES
# ---------------------------------------------------------

files = []
html_files = []

for p in SITE.rglob("*"):
    if p.is_file():
        files.append(p)
        if HTML_RE.search(p.name):
            html_files.append(p)

total_size = sum(p.stat().st_size for p in files)
html_size = sum(p.stat().st_size for p in html_files)

print("\n[1] STATISTIQUES")
print("-" * 70)
print(f"Fichiers totaux       : {len(files):,}")
print(f"Pages HTML            : {len(html_files):,}")
print(f"Taille totale         : {human(total_size)}")
print(f"Taille HTML           : {human(html_size)}")

# ---------------------------------------------------------
# 2. PAGES PAR TYPE
# ---------------------------------------------------------

types = {
    "products": 0,
    "collections": 0,
    "blogs": 0,
    "pages": 0,
    "root": 0,
}

for p in html_files:
    rel = "/" + str(p.relative_to(SITE)).replace("\\", "/")

    if "/products/" in rel:
        types["products"] += 1
    elif "/collections/" in rel:
        types["collections"] += 1
    elif "/blogs/" in rel:
        types["blogs"] += 1
    elif "/pages/" in rel:
        types["pages"] += 1
    elif rel == "/index.html":
        types["root"] += 1

print("\n[2] PAGES PAR TYPE")
print("-" * 70)

for k, v in types.items():
    print(f"{k:<18}: {v:,}")

# ---------------------------------------------------------
# 3. CONTRÔLE DU CONTENU IMPORTANT
# ---------------------------------------------------------

checks = {
    "title": re.compile(r"<title\b[^>]*>.*?</title>", re.I | re.S),
    "description": re.compile(
        r'<meta[^>]+name=["\']description["\'][^>]*>',
        re.I
    ),
    "images": re.compile(r"<img\b", re.I),
    "json_ld": re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\']',
        re.I
    ),
    "price": re.compile(
        r"(price|product.*price|price.*product)",
        re.I
    ),
    "variant": re.compile(
        r"(variant|variants)",
        re.I
    ),
    "add_to_cart": re.compile(
        r"(add.?to.?cart|add_to_cart)",
        re.I
    ),
}

stats = {k: 0 for k in checks}

for i, p in enumerate(html_files, 1):

    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    for name, pattern in checks.items():
        if pattern.search(text):
            stats[name] += 1

print("\n[3] INTÉGRITÉ DU CONTENU")
print("-" * 70)

for name, count in stats.items():
    pct = (count / len(html_files) * 100) if html_files else 0
    print(f"{name:<18}: {count:,}/{len(html_files):,} ({pct:.1f}%)")

# ---------------------------------------------------------
# 4. RECHERCHE DES PAGES VIDES / ANORMALEMENT PETITES
# ---------------------------------------------------------

tiny = []

for p in html_files:
    size = p.stat().st_size

    if size < 500:
        tiny.append(p)

print("\n[4] PAGES ANORMALEMENT PETITES")
print("-" * 70)
print(f"HTML < 500 octets : {len(tiny):,}")

if tiny:
    print("\nExemples :")
    for p in tiny[:20]:
        print(" -", p.relative_to(SITE))

# ---------------------------------------------------------
# 5. RECHERCHE DE PAGES AVEC ERREUR SHOPIFY
# ---------------------------------------------------------

error_patterns = [
    r"404",
    r"page not found",
    r"not found",
    r"internal server error",
    r"access denied",
    r"too many requests",
]

error_files = []

for p in html_files:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    # On cherche seulement des formulations très typiques.
    if any(re.search(pattern, text, re.I) for pattern in error_patterns):
        error_files.append(p)

print("\n[5] PAGES SUSPECTES")
print("-" * 70)
print(f"Pages contenant un motif d'erreur : {len(error_files):,}")

if error_files:
    print("\nExemples :")
    for p in error_files[:20]:
        print(" -", p.relative_to(SITE))

# ---------------------------------------------------------
# 6. CONTRÔLE DES SCRIPTS SUPPRIMÉS
# ---------------------------------------------------------

removed_patterns = {
    "LangShopConfig": re.compile(r"window\.LangShopConfig", re.I),
    "wpmLoader": re.compile(r"wpmLoader", re.I),
    "Shortly": re.compile(r"shortly-version", re.I),
    "JudgeMe": re.compile(r"jdgmSettings", re.I),
}

removed_found = {k: 0 for k in removed_patterns}

for p in html_files:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    for name, pattern in removed_patterns.items():
        if pattern.search(text):
            removed_found[name] += 1

print("\n[6] VÉRIFICATION DU NETTOYAGE")
print("-" * 70)

for name, count in removed_found.items():
    status = "OK" if count == 0 else "ATTENTION"
    print(f"{name:<18}: {count:,} pages -> {status}")

# ---------------------------------------------------------
# 7. VÉRIFICATION DES DONNÉES PRODUITS
# ---------------------------------------------------------

product_files = [
    p for p in html_files
    if "/products/" in ("/" + str(p.relative_to(SITE)).replace("\\", "/"))
]

variant_files = 0
product_data_files = 0

for p in product_files:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    if "xcotton_pp_variants" in text:
        variant_files += 1

    if "application/ld+json" in text:
        product_data_files += 1

print("\n[7] DONNÉES PRODUITS")
print("-" * 70)
print(f"Pages produits              : {len(product_files):,}")
print(f"Produits avec variants JSON : {variant_files:,}")
print(f"Produits avec JSON-LD       : {product_data_files:,}")

# ---------------------------------------------------------
# 8. LIENS INTERNES ABSOLUS
# ---------------------------------------------------------

internal_links = 0
external_links = 0

link_re = re.compile(
    r'''(?:href|src)=["']([^"']+)["']''',
    re.I
)

for p in html_files:

    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    for url in link_re.findall(text):

        if url.startswith("https://ibuture.com"):
            internal_links += 1

        elif url.startswith("http://ibuture.com"):
            internal_links += 1

        elif url.startswith("http://") or url.startswith("https://"):
            external_links += 1

print("\n[8] LIENS")
print("-" * 70)
print(f"Liens internes détectés : {internal_links:,}")
print(f"Liens externes détectés : {external_links:,}")

# ---------------------------------------------------------
# 9. FICHIERS CSS / JS / IMAGES
# ---------------------------------------------------------

extensions = {
    "CSS": {".css"},
    "JS": {".js"},
    "Images": {
        ".jpg", ".jpeg", ".png", ".webp",
        ".gif", ".svg", ".avif"
    },
    "Fonts": {
        ".woff", ".woff2", ".ttf", ".otf", ".eot"
    },
}

print("\n[9] ASSETS")
print("-" * 70)

for label, exts in extensions.items():

    matching = [
        p for p in files
        if p.suffix.lower() in exts
    ]

    size = sum(p.stat().st_size for p in matching)

    print(
        f"{label:<10}: "
        f"{len(matching):,} fichiers | "
        f"{human(size)}"
    )

# ---------------------------------------------------------
# 10. DOUBLONS EXACTS
# ---------------------------------------------------------

print("\n[10] DOUBLONS EXACTS")
print("-" * 70)

hashes = {}
duplicates = []

for p in html_files:

    try:
        h = sha256(p)
    except Exception:
        continue

    if h in hashes:
        duplicates.append((p, hashes[h]))
    else:
        hashes[h] = p

print(f"Doublons HTML exacts : {len(duplicates):,}")

# ---------------------------------------------------------
# 11. RAPPORT FINAL
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("RAPPORT FINAL")
print("=" * 70)

warnings = []

if len(tiny) > 20:
    warnings.append(
        f"{len(tiny)} pages HTML font moins de 500 octets"
    )

if error_files:
    warnings.append(
        f"{len(error_files)} pages contiennent un motif d'erreur"
    )

if removed_found["LangShopConfig"] > 0:
    warnings.append("LangShopConfig encore présent")

if removed_found["wpmLoader"] > 0:
    warnings.append("wpmLoader encore présent")

if variant_files == 0 and product_files:
    warnings.append(
        "Aucune page produit ne contient xcotton_pp_variants"
    )

if warnings:
    print("\n⚠️ POINTS À VÉRIFIER :")
    for w in warnings:
        print(" -", w)
else:
    print("\n✅ AUCUNE ANOMALIE MAJEURE DÉTECTÉE")

print("\nContrôle terminé.")
print("=" * 70)


